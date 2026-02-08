"""Tests for task dependency graph."""

import pytest
from core.task.dependencies import TaskDependencyGraph, CyclicDependencyError
from core.task.types import TaskDefinition, TaskDependency


class TestTaskDependencyGraph:
    """Tests for TaskDependencyGraph."""

    def setup_method(self):
        """Set up test fixtures."""
        self.graph = TaskDependencyGraph()

    def test_add_task(self):
        """Test adding a task to the graph."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Task 1"
        )
        self.graph.add_task(task)
        assert self.graph.has_task("001")

    def test_add_duplicate_task_raises_error(self):
        """Test adding duplicate task raises ValueError."""
        task = TaskDefinition(
            task_id="001",
            phase_id="0-setup",
            name="Task 1"
        )
        self.graph.add_task(task)

        with pytest.raises(ValueError):
            self.graph.add_task(task)

    def test_add_dependency(self):
        """Test adding a dependency between tasks."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_dependency("002", "001")

        deps = self.graph.get_dependencies("002")
        assert len(deps) == 1
        assert deps[0].task_id == "001"

    def test_add_dependency_nonexistent_task_raises_error(self):
        """Test adding dependency with nonexistent task raises ValueError."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        self.graph.add_task(task1)

        with pytest.raises(ValueError):
            self.graph.add_dependency("002", "001")  # 002 doesn't exist

        with pytest.raises(ValueError):
            self.graph.add_dependency("001", "003")  # 003 doesn't exist

    def test_remove_dependency(self):
        """Test removing a dependency."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_dependency("002", "001")
        self.graph.remove_dependency("002", "001")

        deps = self.graph.get_dependencies("002")
        assert len(deps) == 0

    def test_get_dependencies(self):
        """Test getting task dependencies."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_task(task3)
        self.graph.add_dependency("003", "001")
        self.graph.add_dependency("003", "002")

        deps = self.graph.get_dependencies("003")
        assert len(deps) == 2
        dep_ids = [d.task_id for d in deps]
        assert "001" in dep_ids
        assert "002" in dep_ids

    def test_get_dependents(self):
        """Test getting tasks that depend on a given task."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_task(task3)
        self.graph.add_dependency("002", "001")
        self.graph.add_dependency("003", "001")

        dependents = self.graph.get_dependents("001")
        assert len(dependents) == 2
        dependent_ids = [d.task_id for d in dependents]
        assert "002" in dependent_ids
        assert "003" in dependent_ids

    def test_is_ready_no_dependencies(self):
        """Test task with no dependencies is ready."""
        task = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        self.graph.add_task(task)

        assert self.graph.is_ready("001", set())

    def test_is_ready_dependencies_completed(self):
        """Test task is ready when dependencies are completed."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_dependency("002", "001")

        assert self.graph.is_ready("002", {"001"})

    def test_is_ready_dependencies_not_completed(self):
        """Test task is not ready when dependencies are not completed."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_dependency("002", "001")

        assert not self.graph.is_ready("002", set())

    def test_validate_acyclic_graph(self):
        """Test validating an acyclic graph."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_task(task3)
        self.graph.add_dependency("002", "001")
        self.graph.add_dependency("003", "002")

        assert self.graph.validate() is True

    def test_detect_cycle(self):
        """Test detecting a cycle in the graph."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_dependency("002", "001")

        with pytest.raises(CyclicDependencyError):
            self.graph.add_dependency("001", "002")  # Creates cycle

    def test_get_execution_order_linear(self):
        """Test getting execution order for linear dependencies."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_task(task3)
        self.graph.add_dependency("002", "001")
        self.graph.add_dependency("003", "002")

        levels = self.graph.get_execution_order()
        assert len(levels) == 3
        assert levels[0][0].task_id == "001"
        assert levels[1][0].task_id == "002"
        assert levels[2][0].task_id == "003"

    def test_get_execution_order_parallel(self):
        """Test getting execution order for parallel tasks."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")
        task4 = TaskDefinition(task_id="004", phase_id="0-setup", name="Task 4")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_task(task3)
        self.graph.add_task(task4)
        self.graph.add_dependency("002", "001")
        self.graph.add_dependency("003", "001")
        self.graph.add_dependency("004", "002")
        self.graph.add_dependency("004", "003")

        levels = self.graph.get_execution_order()
        assert len(levels) == 3
        assert levels[0][0].task_id == "001"

        # Level 1 should have tasks 002 and 003 (can run in parallel)
        level1_ids = {t.task_id for t in levels[1]}
        assert level1_ids == {"002", "003"}

        assert levels[2][0].task_id == "004"

    def test_get_parallel_tasks(self):
        """Test get_parallel_tasks returns same as get_execution_order."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")

        self.graph.add_task(task1)
        self.graph.add_task(task2)

        parallel = self.graph.get_parallel_tasks()
        execution = self.graph.get_execution_order()

        assert parallel == execution

    def test_get_root_tasks(self):
        """Test getting root tasks (no dependencies)."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_task(task3)
        self.graph.add_dependency("003", "001")

        roots = self.graph.get_root_tasks()
        root_ids = {t.task_id for t in roots}
        assert root_ids == {"001", "002"}

    def test_get_leaf_tasks(self):
        """Test getting leaf tasks (no dependents)."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_task(task3)
        self.graph.add_dependency("002", "001")

        leaves = self.graph.get_leaf_tasks()
        leaf_ids = {t.task_id for t in leaves}
        assert leaf_ids == {"002", "003"}

    def test_get_depth(self):
        """Test getting task depth in the graph."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
        task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_task(task3)
        self.graph.add_dependency("002", "001")
        self.graph.add_dependency("003", "002")

        assert self.graph.get_depth("001") == 0
        assert self.graph.get_depth("002") == 1
        assert self.graph.get_depth("003") == 2

    def test_clear(self):
        """Test clearing the graph."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.clear()

        assert not self.graph.has_task("001")
        assert not self.graph.has_task("002")

    def test_to_dict(self):
        """Test exporting graph as dictionary."""
        task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
        task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")

        self.graph.add_task(task1)
        self.graph.add_task(task2)
        self.graph.add_dependency("002", "001")

        graph_dict = self.graph.to_dict()
        assert "tasks" in graph_dict
        assert "001" in graph_dict["tasks"]
        assert "002" in graph_dict["tasks"]
        assert graph_dict["tasks"]["002"]["dependencies"] == ["001"]
