"""
Task Dependency Graph

Manages task dependencies and execution ordering using a DAG (Directed Acyclic Graph).
"""

from typing import Dict, List, Set, Optional
from collections import defaultdict, deque

from .types import TaskDefinition, DependencyType


class CyclicDependencyError(Exception):
    """Raised when a cyclic dependency is detected."""
    pass


class TaskDependencyGraph:
    """
    Manages task dependency graph.

    Features:
    - DAG validation (no cycles)
    - Topological sorting for execution order
    - Dependency resolution
    - Parallel task identification
    """

    def __init__(self):
        """Initialize empty dependency graph."""
        self._tasks: Dict[str, TaskDefinition] = {}
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._dependents: Dict[str, Set[str]] = defaultdict(set)

    def add_task(self, task_def: TaskDefinition):
        """
        Add a task to the graph.

        Args:
            task_def: Task definition

        Raises:
            ValueError: If task already exists
        """
        if task_def.task_id in self._tasks:
            raise ValueError(f"Task {task_def.task_id} already exists in graph")

        self._tasks[task_def.task_id] = task_def

        # Add dependencies from task definition
        for dep in task_def.dependencies:
            self.add_dependency(task_def.task_id, dep.task_id)

    def add_dependency(self, task_id: str, depends_on: str):
        """
        Add a dependency relationship.

        Args:
            task_id: Task that depends on another
            depends_on: Task that must complete first

        Raises:
            ValueError: If either task doesn't exist
            CyclicDependencyError: If this creates a cycle
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found in graph")
        if depends_on not in self._tasks:
            raise ValueError(f"Dependency task {depends_on} not found in graph")

        # Check if this would create a cycle
        if self._would_create_cycle(task_id, depends_on):
            raise CyclicDependencyError(
                f"Adding dependency {task_id} -> {depends_on} would create a cycle"
            )

        self._dependencies[task_id].add(depends_on)
        self._dependents[depends_on].add(task_id)

    def remove_dependency(self, task_id: str, depends_on: str):
        """
        Remove a dependency relationship.

        Args:
            task_id: Task that depends on another
            depends_on: Task dependency to remove
        """
        if task_id in self._dependencies:
            self._dependencies[task_id].discard(depends_on)
        if depends_on in self._dependents:
            self._dependents[depends_on].discard(task_id)

    def get_dependencies(self, task_id: str) -> List[TaskDefinition]:
        """
        Get tasks that a given task depends on.

        Args:
            task_id: Task identifier

        Returns:
            List of TaskDefinition objects
        """
        dep_ids = self._dependencies.get(task_id, set())
        return [self._tasks[dep_id] for dep_id in dep_ids if dep_id in self._tasks]

    def get_dependents(self, task_id: str) -> List[TaskDefinition]:
        """
        Get tasks that depend on a given task.

        Args:
            task_id: Task identifier

        Returns:
            List of TaskDefinition objects
        """
        dependent_ids = self._dependents.get(task_id, set())
        return [
            self._tasks[dep_id]
            for dep_id in dependent_ids
            if dep_id in self._tasks
        ]

    def is_ready(self, task_id: str, completed_tasks: Set[str]) -> bool:
        """
        Check if a task is ready to execute.

        A task is ready if all its dependencies are completed.

        Args:
            task_id: Task identifier
            completed_tasks: Set of completed task IDs

        Returns:
            True if task is ready
        """
        dependencies = self._dependencies.get(task_id, set())
        return dependencies.issubset(completed_tasks)

    def validate(self) -> bool:
        """
        Validate the dependency graph (check for cycles).

        Returns:
            True if graph is valid (acyclic)

        Raises:
            CyclicDependencyError: If cycles are detected
        """
        try:
            self.get_execution_order()
            return True
        except CyclicDependencyError:
            return False

    def get_execution_order(self) -> List[List[TaskDefinition]]:
        """
        Get tasks grouped by execution level using topological sort.

        Tasks in the same level can be executed in parallel.

        Returns:
            List of lists, where each inner list contains tasks that can run in parallel

        Raises:
            CyclicDependencyError: If graph has cycles
        """
        # Calculate in-degree for each task
        in_degree = {task_id: 0 for task_id in self._tasks}
        for task_id in self._tasks:
            in_degree[task_id] = len(self._dependencies.get(task_id, set()))

        # Find tasks with no dependencies (in-degree 0)
        queue = deque([
            task_id for task_id, degree in in_degree.items() if degree == 0
        ])

        levels: List[List[TaskDefinition]] = []
        processed = set()

        while queue:
            # Process all tasks at current level
            current_level = []
            level_size = len(queue)

            for _ in range(level_size):
                task_id = queue.popleft()
                processed.add(task_id)
                current_level.append(self._tasks[task_id])

                # Reduce in-degree for dependents
                for dependent_id in self._dependents.get(task_id, set()):
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

            levels.append(current_level)

        # Check if all tasks were processed (no cycles)
        if len(processed) != len(self._tasks):
            unprocessed = set(self._tasks.keys()) - processed
            raise CyclicDependencyError(
                f"Cyclic dependency detected. Unprocessed tasks: {unprocessed}"
            )

        return levels

    def get_parallel_tasks(self) -> List[List[TaskDefinition]]:
        """
        Get tasks that can be executed in parallel.

        This is an alias for get_execution_order().

        Returns:
            List of lists, where each inner list contains tasks that can run in parallel
        """
        return self.get_execution_order()

    def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        """
        Get task definition by ID.

        Args:
            task_id: Task identifier

        Returns:
            TaskDefinition or None if not found
        """
        return self._tasks.get(task_id)

    def has_task(self, task_id: str) -> bool:
        """
        Check if task exists in graph.

        Args:
            task_id: Task identifier

        Returns:
            True if task exists
        """
        return task_id in self._tasks

    def get_all_tasks(self) -> List[TaskDefinition]:
        """Get all tasks in the graph."""
        return list(self._tasks.values())

    def clear(self):
        """Clear all tasks and dependencies."""
        self._tasks.clear()
        self._dependencies.clear()
        self._dependents.clear()

    def _would_create_cycle(self, from_task: str, to_task: str) -> bool:
        """
        Check if adding a dependency would create a cycle.

        Uses DFS to detect if there's already a path from to_task to from_task.

        Args:
            from_task: Task that would depend on to_task
            to_task: Task that from_task would depend on

        Returns:
            True if adding this dependency would create a cycle
        """
        # If to_task can reach from_task, adding from_task -> to_task creates a cycle
        visited = set()
        stack = [to_task]

        while stack:
            current = stack.pop()
            if current == from_task:
                return True

            if current in visited:
                continue
            visited.add(current)

            # Add all tasks that current depends on
            for dep in self._dependencies.get(current, set()):
                if dep not in visited:
                    stack.append(dep)

        return False

    def get_root_tasks(self) -> List[TaskDefinition]:
        """
        Get tasks with no dependencies (root tasks).

        Returns:
            List of TaskDefinition objects
        """
        return [
            self._tasks[task_id]
            for task_id in self._tasks
            if not self._dependencies.get(task_id)
        ]

    def get_leaf_tasks(self) -> List[TaskDefinition]:
        """
        Get tasks with no dependents (leaf tasks).

        Returns:
            List of TaskDefinition objects
        """
        return [
            self._tasks[task_id]
            for task_id in self._tasks
            if not self._dependents.get(task_id)
        ]

    def get_depth(self, task_id: str) -> int:
        """
        Get the depth of a task in the dependency graph.

        Depth is the longest path from a root task to this task.

        Args:
            task_id: Task identifier

        Returns:
            Depth (0 for root tasks)
        """
        if task_id not in self._tasks:
            return -1

        dependencies = self._dependencies.get(task_id, set())
        if not dependencies:
            return 0

        # Depth is 1 + max depth of dependencies
        return 1 + max(self.get_depth(dep_id) for dep_id in dependencies)

    def to_dict(self) -> Dict:
        """
        Export graph as dictionary.

        Returns:
            Dictionary representation of the graph
        """
        return {
            "tasks": {
                task_id: {
                    "name": task.name,
                    "phase_id": task.phase_id,
                    "dependencies": list(self._dependencies.get(task_id, set()))
                }
                for task_id, task in self._tasks.items()
            }
        }
