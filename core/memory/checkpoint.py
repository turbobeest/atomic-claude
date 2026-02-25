"""
Checkpoint Manager

Handles checkpoint creation, restoration, and pruning.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .types import Checkpoint, CheckpointStatus, MemoryHead
from .store import MemoryStore

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manage memory checkpoints for recovery."""

    def __init__(self, state_dir: Path, store: MemoryStore, graph=None):
        """
        Initialize checkpoint manager.

        Args:
            state_dir: State directory
            store: Memory store instance
            graph: Optional GraphManager for dual-write to FalkorDB
        """
        self.state_dir = Path(state_dir)
        self.checkpoint_dir = self.state_dir / "memory-checkpoints"
        self.head_file = self.state_dir / "memory-head.json"
        self.store = store
        self._graph = graph

        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(
        self,
        phase: int,
        phase_name: str,
        summary: str,
        key_decisions: Optional[List[str]] = None,
        artifacts: Optional[List[str]] = None,
        state_snapshot: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a checkpoint.

        Args:
            phase: Phase number
            phase_name: Phase name
            summary: Checkpoint summary
            key_decisions: List of key decisions
            artifacts: List of artifact paths
            state_snapshot: State snapshot data

        Returns:
            Checkpoint ID
        """
        # Generate checkpoint ID
        checkpoint_id = f"phase{phase}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"

        # Get project name from head
        head = self._load_head()
        project = head.project if head else "atomic-claude"

        # Get previous checkpoint
        previous_checkpoint = head.head_checkpoint if head else None

        # Get relevant context from memory store
        context = self.store.query(phase=f"{phase}-{phase_name.lower()}", limit=10)

        # Create checkpoint
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            project=project,
            phase=phase,
            phase_name=phase_name,
            summary=summary,
            key_decisions=key_decisions or [],
            artifacts=artifacts or [],
            state_snapshot=state_snapshot or {},
            context=context,
            status=CheckpointStatus.VALID,
            previous_checkpoint=previous_checkpoint
        )

        # Save to file
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        from core.utils.file_ops import write_json
        write_json(checkpoint_file, checkpoint.model_dump())

        # Dual-write to graph
        if self._graph:
            try:
                self._graph.save_checkpoint(
                    checkpoint_id=checkpoint_id,
                    phase=phase,
                    phase_name=phase_name,
                    summary=summary,
                    key_decisions=key_decisions,
                    artifacts=artifacts,
                )
            except Exception as e:
                logger.warning("Graph checkpoint write failed (non-blocking): %s", e)

        # Update head
        self._update_head(phase, checkpoint_id)

        return checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Restore from checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to restore

        Returns:
            Checkpoint data or None if not found
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Checkpoint(**data)

    def list_checkpoints(
        self,
        phase: Optional[int] = None,
        status: Optional[CheckpointStatus] = None
    ) -> List[Checkpoint]:
        """
        List all checkpoints.

        Args:
            phase: Filter by phase
            status: Filter by status

        Returns:
            List of checkpoints
        """
        checkpoints = []

        for checkpoint_file in sorted(self.checkpoint_dir.glob("*.json")):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                checkpoint = Checkpoint(**data)

                # Apply filters
                if phase is not None and checkpoint.phase != phase:
                    continue

                if status is not None and checkpoint.status != status:
                    continue

                checkpoints.append(checkpoint)

            except (json.JSONDecodeError, OSError, TypeError, KeyError) as e:
                # Skip invalid checkpoints
                logger.debug("Skipping invalid checkpoint file %s: %s", checkpoint_file, e)
                continue

        # Sort by created_at (newest first)
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)

        return checkpoints

    def get_latest_checkpoint(self, phase: Optional[int] = None) -> Optional[Checkpoint]:
        """
        Get most recent checkpoint.

        Args:
            phase: Filter by phase

        Returns:
            Latest checkpoint or None
        """
        checkpoints = self.list_checkpoints(
            phase=phase,
            status=CheckpointStatus.VALID
        )

        return checkpoints[0] if checkpoints else None

    def prune_checkpoints(self, keep_count: int = 10) -> int:
        """
        Remove old checkpoints, keeping the most recent N.

        Args:
            keep_count: Number of checkpoints to keep

        Returns:
            Number of checkpoints removed
        """
        checkpoints = self.list_checkpoints()

        # Keep only the most recent N valid checkpoints
        to_keep = set()
        kept = 0

        for checkpoint in checkpoints:
            if checkpoint.status == CheckpointStatus.VALID and kept < keep_count:
                to_keep.add(checkpoint.checkpoint_id)
                kept += 1

        # Remove old checkpoints
        removed = 0
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            checkpoint_id = checkpoint_file.stem

            if checkpoint_id not in to_keep:
                checkpoint_file.unlink()
                removed += 1

        return removed

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Remove a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            True if deleted
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True

        return False

    def invalidate_after_phase(self, phase_num: int) -> int:
        """
        Invalidate checkpoints after a phase (for backtracking).

        Args:
            phase_num: Phase number

        Returns:
            Number of checkpoints invalidated
        """
        checkpoints = self.list_checkpoints()
        invalidated = 0

        for checkpoint in checkpoints:
            if checkpoint.phase > phase_num:
                # Update status
                checkpoint.status = CheckpointStatus.INVALIDATED

                # Save updated checkpoint
                checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
                from core.utils.file_ops import write_json
                write_json(checkpoint_file, checkpoint.model_dump())

                invalidated += 1

        # Also invalidate in graph
        if self._graph:
            try:
                self._graph.invalidate_checkpoints_after(phase_num)
            except Exception as e:
                logger.warning("Graph checkpoint invalidation failed (non-blocking): %s", e)

        return invalidated

    def _load_head(self) -> Optional[MemoryHead]:
        """Load head state."""
        if not self.head_file.exists():
            return None

        with open(self.head_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return MemoryHead(**data)

    def _update_head(self, phase: int, checkpoint_id: str) -> None:
        """Update head state."""
        head = self._load_head()

        if not head:
            head = MemoryHead(
                project="atomic-claude",
                head_phase=phase,
                head_checkpoint=checkpoint_id
            )
        else:
            head.head_phase = phase
            head.head_checkpoint = checkpoint_id
            head.updated_at = datetime.now()

        # Add checkpoint to tracking
        head.checkpoints.append({
            "id": checkpoint_id,
            "phase": phase,
            "status": "valid",
            "created_at": datetime.now().isoformat()
        })

        # Save head
        from core.utils.file_ops import write_json
        write_json(self.head_file, head.model_dump())
