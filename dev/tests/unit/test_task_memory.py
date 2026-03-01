"""Tests for orchestration.task_memory.TaskMemory."""

import pytest
from orchestration.task_memory import TaskMemory


@pytest.mark.unit
class TestTaskMemory:
    """Tests for the TaskMemory class."""

    def test_init(self):
        mem = TaskMemory("0-setup", "002", "Provider detection")
        assert mem.phase_id == "0-setup"
        assert mem.task_id == "002"
        assert mem.task_name == "Provider detection"
        assert not mem.has_entries()

    def test_has_entries_empty(self):
        mem = TaskMemory("0-setup", "001", "Bootstrap")
        assert not mem.has_entries()

    def test_has_entries_after_add(self):
        mem = TaskMemory("0-setup", "001", "Bootstrap")
        mem.finding("Something found")
        assert mem.has_entries()

    def test_decision(self):
        mem = TaskMemory("0-setup", "003", "Wizard")
        mem.decision("Selected opus model")
        assert mem._entries == [("decision", "Selected opus model")]

    def test_finding(self):
        mem = TaskMemory("0-setup", "002", "Detection")
        mem.finding("3 providers detected")
        assert mem._entries == [("finding", "3 providers detected")]

    def test_conversation(self):
        mem = TaskMemory("1-discovery", "104", "Dialogue")
        mem.conversation("5 turns completed")
        assert mem._entries == [("conversation", "5 turns completed")]

    def test_configuration(self):
        mem = TaskMemory("0-setup", "003", "Wizard")
        mem.configuration("LLM: claude-code/opus")
        assert mem._entries == [("configuration", "LLM: claude-code/opus")]

    def test_warning(self):
        mem = TaskMemory("1-discovery", "105", "Discovery")
        mem.warning("Ollama unavailable")
        assert mem._entries == [("warning", "Ollama unavailable")]

    def test_build_content_empty(self):
        mem = TaskMemory("0-setup", "001", "Bootstrap")
        content = mem.build_content()
        assert content == "Task 001 (Bootstrap) completed."

    def test_build_content_single_category(self):
        mem = TaskMemory("0-setup", "002", "Detection")
        mem.finding("Provider A detected")
        mem.finding("Provider B detected")
        content = mem.build_content()
        assert "Task 002 (Detection) completed." in content
        assert "Findings:" in content
        assert "- Provider A detected" in content
        assert "- Provider B detected" in content

    def test_build_content_multiple_categories(self):
        mem = TaskMemory("0-setup", "003", "Wizard")
        mem.finding("OS: Linux")
        mem.decision("Selected full pipeline")
        mem.configuration("LLM: claude-code/opus")
        mem.warning("No Ollama hosts")

        content = mem.build_content()
        assert "Task 003 (Wizard) completed." in content
        assert "Findings:" in content
        assert "- OS: Linux" in content
        assert "Decisions:" in content
        assert "- Selected full pipeline" in content
        assert "Configuration:" in content
        assert "- LLM: claude-code/opus" in content
        assert "Warnings:" in content
        assert "- No Ollama hosts" in content

    def test_build_content_category_order(self):
        """Categories should appear in stable order regardless of insertion order."""
        mem = TaskMemory("0-setup", "003", "Wizard")
        mem.warning("Watch out")
        mem.decision("Chose A")
        mem.finding("Found X")
        mem.configuration("Set Y")
        mem.conversation("Talked about Z")

        content = mem.build_content()
        lines = content.split("\n")

        # Find category header positions
        category_positions = {}
        for i, line in enumerate(lines):
            for cat in ["Findings:", "Decisions:", "Configuration:", "Conversation:", "Warnings:"]:
                if line == cat:
                    category_positions[cat] = i

        # Verify stable order matches CATEGORIES: decision, finding, conversation, configuration, warning
        assert category_positions["Decisions:"] < category_positions["Findings:"]
        assert category_positions["Findings:"] < category_positions["Conversation:"]
        assert category_positions["Conversation:"] < category_positions["Configuration:"]
        assert category_positions["Configuration:"] < category_positions["Warnings:"]

    def test_build_metadata_empty(self):
        mem = TaskMemory("0-setup", "001", "Bootstrap")
        metadata = mem.build_metadata()
        assert metadata == {}

    def test_build_metadata_with_entries(self):
        mem = TaskMemory("0-setup", "002", "Detection")
        mem.finding("Found 3 providers")
        mem.decision("Primary: claude-code")
        mem.configuration("Ollama: disabled")

        metadata = mem.build_metadata()
        assert metadata["phase_id"] == "0-setup"
        assert metadata["task_id"] == "002"
        assert "task_memory" in metadata
        tm = metadata["task_memory"]
        assert tm["finding"] == ["Found 3 providers"]
        assert tm["decision"] == ["Primary: claude-code"]
        assert tm["configuration"] == ["Ollama: disabled"]
        assert "warning" not in tm
        assert "conversation" not in tm

    def test_build_metadata_groups_by_category(self):
        mem = TaskMemory("1-discovery", "104", "Dialogue")
        mem.finding("A")
        mem.finding("B")
        mem.conversation("C")

        metadata = mem.build_metadata()
        tm = metadata["task_memory"]
        assert tm["finding"] == ["A", "B"]
        assert tm["conversation"] == ["C"]

    def test_build_content_preserves_multiline(self):
        """Ensure entries with long text are preserved correctly."""
        mem = TaskMemory("0-setup", "003", "Wizard")
        mem.finding("Detected stack: Python, Rust, C++")
        mem.decision("Project: foo-processor — Field of Overlap Processor for spatial intersections")
        content = mem.build_content()
        assert "Python, Rust, C++" in content
        assert "foo-processor" in content
