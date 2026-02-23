"""
Tests for core.utils.multi_select — build_selection_tree and toggle logic.

Curses rendering is not tested (requires a real TTY); these tests cover
the data model, hierarchy construction, and cascade toggle behaviour.
"""

import pytest
from core.utils.multi_select import (
    build_selection_tree,
    SelectableItem,
    ItemType,
    _toggle_item,
    _toggle_all,
    _parent_is_mixed,
    _count_total_files,
    _count_excluded_files,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_manifest(files_dict):
    """Wrap a files dict into a minimal manifest."""
    return {"files": files_dict}


SAMPLE_MANIFEST = _make_manifest({
    "documentation": [
        "README.md",
        "docs/guide.md",
        "docs/reference/api.md",
        "docs/reference/schema.md",
    ],
    "configuration": [
        "package.json",
    ],
    "source_code": [
        "src/main.py",
        "src/utils.py",
    ],
    "tests": [],
})


# ---------------------------------------------------------------------------
# build_selection_tree
# ---------------------------------------------------------------------------

class TestBuildSelectionTree:

    def test_empty_manifest(self):
        items = build_selection_tree(_make_manifest({}))
        assert items == []

    def test_empty_categories(self):
        items = build_selection_tree(_make_manifest({
            "documentation": [],
            "source_code": [],
        }))
        assert items == []

    def test_single_category(self):
        items = build_selection_tree(_make_manifest({
            "documentation": ["README.md"],
        }))
        # Category + directory (./) + file
        assert len(items) == 3
        assert items[0].item_type == ItemType.CATEGORY
        assert items[0].depth == 0
        assert items[1].item_type == ItemType.DIRECTORY
        assert items[1].depth == 1
        assert items[2].item_type == ItemType.FILE
        assert items[2].depth == 2
        assert items[2].path == "README.md"

    def test_hierarchy_structure(self):
        items = build_selection_tree(SAMPLE_MANIFEST)

        # Collect categories
        categories = [it for it in items if it.item_type == ItemType.CATEGORY]
        assert len(categories) == 3  # documentation, configuration, source_code (tests empty)

        cat_names = [it.category for it in categories]
        assert "documentation" in cat_names
        assert "configuration" in cat_names
        assert "source_code" in cat_names
        assert "tests" not in cat_names

    def test_file_count(self):
        items = build_selection_tree(SAMPLE_MANIFEST)
        total = _count_total_files(items)
        assert total == 7  # 4 docs + 1 config + 2 source

    def test_parent_child_indices(self):
        items = build_selection_tree(SAMPLE_MANIFEST)

        # First item is Documentation category
        cat = items[0]
        assert cat.item_type == ItemType.CATEGORY
        assert len(cat.child_indices) > 0

        # All file children should reference back to a directory parent
        for it in items:
            if it.item_type == ItemType.FILE:
                assert it.parent_idx is not None
                parent = items[it.parent_idx]
                assert parent.item_type == ItemType.DIRECTORY

    def test_directory_grouping(self):
        items = build_selection_tree(SAMPLE_MANIFEST)

        dirs = [it for it in items if it.item_type == ItemType.DIRECTORY
                and it.category == "documentation"]
        dir_paths = [it.path for it in dirs]
        assert "." in dir_paths        # README.md
        assert "docs" in dir_paths     # guide.md
        assert "docs/reference" in dir_paths  # api.md, schema.md

    def test_no_excluded_by_default(self):
        items = build_selection_tree(SAMPLE_MANIFEST)
        assert all(not it.excluded for it in items)

    def test_children_count(self):
        items = build_selection_tree(_make_manifest({
            "documentation": ["a.md", "b.md", "sub/c.md"],
        }))
        cat = items[0]
        assert cat.children_count == 3


# ---------------------------------------------------------------------------
# Toggle cascade
# ---------------------------------------------------------------------------

class TestToggleCascade:

    def _build(self):
        return build_selection_tree(SAMPLE_MANIFEST)

    def test_toggle_file(self):
        items = self._build()
        # Find a file item
        file_idx = next(i for i, it in enumerate(items) if it.item_type == ItemType.FILE)
        assert not items[file_idx].excluded
        _toggle_item(items, file_idx)
        assert items[file_idx].excluded
        _toggle_item(items, file_idx)
        assert not items[file_idx].excluded

    def test_toggle_directory_cascades_to_files(self):
        items = self._build()
        # Find a directory with children
        dir_idx = next(
            i for i, it in enumerate(items)
            if it.item_type == ItemType.DIRECTORY and len(it.child_indices) > 0
        )
        dir_item = items[dir_idx]

        _toggle_item(items, dir_idx)
        assert dir_item.excluded
        for ci in dir_item.child_indices:
            assert items[ci].excluded

        _toggle_item(items, dir_idx)
        assert not dir_item.excluded
        for ci in dir_item.child_indices:
            assert not items[ci].excluded

    def test_toggle_category_cascades_to_all(self):
        items = self._build()
        cat_idx = 0  # First category
        cat_item = items[cat_idx]

        _toggle_item(items, cat_idx)
        assert cat_item.excluded
        for ci in cat_item.child_indices:
            assert items[ci].excluded

    def test_toggle_file_updates_parent_dir(self):
        items = build_selection_tree(_make_manifest({
            "documentation": ["docs/a.md", "docs/b.md"],
        }))
        # Structure: cat(0), dir(1), file(2), file(3)
        assert items[1].item_type == ItemType.DIRECTORY

        # Exclude both files → dir should become excluded
        _toggle_item(items, 2)
        assert not items[1].excluded  # Only one of two
        assert _parent_is_mixed(items, 1)

        _toggle_item(items, 3)
        assert items[1].excluded  # Both excluded
        assert not _parent_is_mixed(items, 1)

    def test_toggle_file_updates_grandparent_category(self):
        items = build_selection_tree(_make_manifest({
            "documentation": ["a.md"],
        }))
        # cat(0), dir(1), file(2)
        _toggle_item(items, 2)
        assert items[2].excluded
        assert items[1].excluded
        assert items[0].excluded

        _toggle_item(items, 2)
        assert not items[2].excluded
        assert not items[1].excluded
        assert not items[0].excluded


# ---------------------------------------------------------------------------
# Toggle all
# ---------------------------------------------------------------------------

class TestToggleAll:

    def test_toggle_all_excludes_then_includes(self):
        items = build_selection_tree(SAMPLE_MANIFEST)
        total = _count_total_files(items)
        assert _count_excluded_files(items) == 0

        _toggle_all(items)
        assert _count_excluded_files(items) == total

        _toggle_all(items)
        assert _count_excluded_files(items) == 0

    def test_toggle_all_when_partially_excluded(self):
        items = build_selection_tree(SAMPLE_MANIFEST)
        # Exclude one file
        file_idx = next(i for i, it in enumerate(items) if it.item_type == ItemType.FILE)
        items[file_idx].excluded = True

        # Toggle all should exclude everything (some not excluded → exclude all)
        _toggle_all(items)
        total = _count_total_files(items)
        assert _count_excluded_files(items) == total


# ---------------------------------------------------------------------------
# Mixed state
# ---------------------------------------------------------------------------

class TestMixedState:

    def test_parent_not_mixed_when_all_same(self):
        items = build_selection_tree(_make_manifest({
            "documentation": ["a.md", "b.md"],
        }))
        # Neither excluded → not mixed
        assert not _parent_is_mixed(items, 1)  # dir
        assert not _parent_is_mixed(items, 0)  # cat

    def test_parent_mixed_when_partial(self):
        items = build_selection_tree(_make_manifest({
            "documentation": ["a.md", "b.md"],
        }))
        # Exclude just one file
        _toggle_item(items, 2)  # First file
        assert _parent_is_mixed(items, 1)  # dir has mixed children


# ---------------------------------------------------------------------------
# Custom categories
# ---------------------------------------------------------------------------

class TestCustomCategories:

    def test_custom_categories(self):
        manifest = {"files": {"documents": ["spec.md"], "diagrams": ["arch.svg"]}}
        items = build_selection_tree(manifest, categories=["documents", "diagrams"])
        cats = [it for it in items if it.item_type == ItemType.CATEGORY]
        assert len(cats) == 2

    def test_custom_categories_ignores_missing(self):
        manifest = {"files": {"documents": ["spec.md"]}}
        items = build_selection_tree(manifest, categories=["documents", "diagrams"])
        cats = [it for it in items if it.item_type == ItemType.CATEGORY]
        assert len(cats) == 1
        assert cats[0].category == "documents"

    def test_default_categories_unchanged(self):
        """Calling without categories arg still uses the original defaults."""
        items = build_selection_tree(SAMPLE_MANIFEST)
        cats = [it for it in items if it.item_type == ItemType.CATEGORY]
        cat_names = {it.category for it in cats}
        # Original defaults: documentation, configuration, source_code (tests empty)
        assert cat_names == {"documentation", "configuration", "source_code"}
