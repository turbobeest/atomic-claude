"""
Curses-based multi-select widget for interactive file exclusion.

Provides a keyboard-navigable tree of selectable items with toggle cascade.
Falls back gracefully when curses is unavailable (piped input, Windows, dumb terminal).
"""

import sys
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable

try:
    import curses
    HAS_CURSES = True
except ImportError:
    HAS_CURSES = False


class ItemType(Enum):
    CATEGORY = "category"
    DIRECTORY = "directory"
    FILE = "file"


@dataclass
class SelectableItem:
    label: str
    item_type: ItemType
    path: str
    category: str
    depth: int              # 0=category, 1=dir, 2=file
    excluded: bool = False
    children_count: int = 0
    parent_idx: Optional[int] = None
    child_indices: List[int] = field(default_factory=list)


def build_selection_tree(
    manifest: Dict[str, Any],
    categories: Optional[List[str]] = None,
) -> List[SelectableItem]:
    """
    Transform manifest['files'] into a flat list with hierarchy metadata.

    Groups files by parent directory within each category. Categories with
    no files are omitted.

    Args:
        manifest: Material scan manifest with 'files' dict keyed by category.
        categories: Optional list of category keys to include. Defaults to
            ['documentation', 'configuration', 'source_code', 'tests'].

    Returns:
        Flat list of SelectableItem with parent/child indices populated.
    """
    items: List[SelectableItem] = []
    if categories is None:
        categories = ['documentation', 'configuration', 'source_code', 'tests']

    for cat in categories:
        file_list = manifest.get('files', {}).get(cat, [])
        if not file_list:
            continue

        # Group files by parent directory
        dir_groups: Dict[str, List[str]] = {}
        for fpath in sorted(file_list):
            parts = fpath.rsplit('/', 1)
            if len(parts) == 1:
                parent_dir = '.'
            else:
                parent_dir = parts[0]
            dir_groups.setdefault(parent_dir, []).append(fpath)

        # Category header
        cat_idx = len(items)
        cat_label = cat.replace('_', ' ').title()
        cat_item = SelectableItem(
            label=f"{cat_label} ({len(file_list)} files)",
            item_type=ItemType.CATEGORY,
            path=cat,
            category=cat,
            depth=0,
            children_count=len(file_list),
        )
        items.append(cat_item)

        # Sort directories: root first, then alphabetical
        sorted_dirs = sorted(dir_groups.keys(), key=lambda d: ("" if d == "." else d))

        for dir_path in sorted_dirs:
            dir_files = dir_groups[dir_path]
            dir_label = "./" if dir_path == "." else f"{dir_path}/"

            dir_idx = len(items)
            dir_item = SelectableItem(
                label=f"{dir_label} ({len(dir_files)} files)",
                item_type=ItemType.DIRECTORY,
                path=dir_path,
                category=cat,
                depth=1,
                children_count=len(dir_files),
                parent_idx=cat_idx,
            )
            items.append(dir_item)
            items[cat_idx].child_indices.append(dir_idx)

            for fpath in sorted(dir_files):
                fname = fpath.rsplit('/', 1)[-1] if '/' in fpath else fpath
                file_idx = len(items)
                file_item = SelectableItem(
                    label=fname,
                    item_type=ItemType.FILE,
                    path=fpath,
                    category=cat,
                    depth=2,
                    parent_idx=dir_idx,
                )
                items.append(file_item)
                items[dir_idx].child_indices.append(file_idx)
                items[cat_idx].child_indices.append(file_idx)

    return items


def _count_total_files(items: List[SelectableItem]) -> int:
    """Count total file-type items."""
    return sum(1 for it in items if it.item_type == ItemType.FILE)


def _count_excluded_files(items: List[SelectableItem]) -> int:
    """Count excluded file-type items."""
    return sum(1 for it in items if it.item_type == ItemType.FILE and it.excluded)


def _toggle_item(items: List[SelectableItem], idx: int) -> None:
    """
    Toggle an item's excluded state with cascade.

    - Category: toggles all child directories and files
    - Directory: toggles all child files, updates parent category
    - File: toggles self, updates parent directory and category
    """
    item = items[idx]
    new_state = not item.excluded

    if item.item_type == ItemType.CATEGORY:
        item.excluded = new_state
        for ci in item.child_indices:
            items[ci].excluded = new_state

    elif item.item_type == ItemType.DIRECTORY:
        item.excluded = new_state
        for ci in item.child_indices:
            items[ci].excluded = new_state
        # Update parent category
        if item.parent_idx is not None:
            _update_parent_state(items, item.parent_idx)

    elif item.item_type == ItemType.FILE:
        item.excluded = new_state
        # Update parent directory
        if item.parent_idx is not None:
            _update_parent_state(items, item.parent_idx)
            # Update grandparent category
            dir_item = items[item.parent_idx]
            if dir_item.parent_idx is not None:
                _update_parent_state(items, dir_item.parent_idx)


def _update_parent_state(items: List[SelectableItem], parent_idx: int) -> None:
    """
    Update a parent's excluded state based on its children.

    All children excluded → parent excluded.
    No children excluded → parent not excluded.
    Mixed → parent not excluded (displayed as [-] in UI).
    """
    parent = items[parent_idx]
    if not parent.child_indices:
        return

    # For categories, check only direct file children
    # For directories, check direct file children
    if parent.item_type == ItemType.CATEGORY:
        file_children = [
            ci for ci in parent.child_indices
            if items[ci].item_type == ItemType.FILE
        ]
    else:
        file_children = parent.child_indices

    if not file_children:
        return

    all_excluded = all(items[ci].excluded for ci in file_children)
    parent.excluded = all_excluded


def _parent_is_mixed(items: List[SelectableItem], idx: int) -> bool:
    """Check if a parent item has mixed (some excluded, some not) children."""
    item = items[idx]
    if not item.child_indices:
        return False

    if item.item_type == ItemType.CATEGORY:
        file_children = [
            ci for ci in item.child_indices
            if items[ci].item_type == ItemType.FILE
        ]
    else:
        file_children = item.child_indices

    if not file_children:
        return False

    states = {items[ci].excluded for ci in file_children}
    return len(states) > 1


def _toggle_all(items: List[SelectableItem]) -> None:
    """Toggle all items. If any file is not excluded, exclude all. Otherwise, un-exclude all."""
    any_not_excluded = any(
        not it.excluded for it in items if it.item_type == ItemType.FILE
    )
    new_state = any_not_excluded

    for it in items:
        it.excluded = new_state


def _checkbox(item: SelectableItem, items: List[SelectableItem], idx: int) -> str:
    """Return checkbox string for an item."""
    if item.item_type in (ItemType.CATEGORY, ItemType.DIRECTORY):
        if _parent_is_mixed(items, idx):
            return "[-]"
        return "[x]" if item.excluded else "[ ]"
    return "[x]" if item.excluded else "[ ]"


def curses_multi_select(
    items: List[SelectableItem],
    title: str = "Exclude files from context",
    footer: str = "↑↓/jk:navigate  space:toggle  a:toggle-all  q/enter:done",
) -> List[SelectableItem]:
    """
    Launch a fullscreen curses multi-select UI.

    Args:
        items: List of SelectableItem (modified in place).
        title: Header title text.
        footer: Keybinding hint text.

    Returns:
        The same items list with excluded flags updated.

    Raises:
        RuntimeError: If curses is unavailable or terminal too small.
    """
    if not HAS_CURSES:
        raise RuntimeError("curses not available")

    if not items:
        return items

    def _main(stdscr: 'curses.window') -> None:
        curses.curs_set(0)
        curses.use_default_colors()

        # Init color pairs
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # category
        curses.init_pair(2, curses.COLOR_RED, -1)      # excluded
        curses.init_pair(3, curses.COLOR_GREEN, -1)    # status
        curses.init_pair(4, curses.COLOR_YELLOW, -1)   # header

        cursor = 0
        scroll_offset = 0

        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()

            if max_y < 10 or max_x < 40:
                raise RuntimeError("Terminal too small")

            total = _count_total_files(items)
            excluded = _count_excluded_files(items)
            keeping = total - excluded

            # Header
            header = f" {title}"
            counter = f"{excluded}/{total} files excluded"
            pad = max_x - len(header) - len(counter) - 2
            if pad < 1:
                pad = 1
            try:
                stdscr.addnstr(0, 0, header, max_x - 1,
                               curses.A_BOLD | curses.color_pair(4))
                stdscr.addnstr(0, len(header) + pad, counter, max_x - 1,
                               curses.color_pair(4))
            except curses.error:
                pass

            # Separator
            try:
                stdscr.addnstr(1, 0, " " + "─" * (max_x - 2), max_x - 1,
                               curses.color_pair(1))
            except curses.error:
                pass

            # Content area
            content_start = 2
            content_end = max_y - 3  # Leave room for status + footer
            visible_rows = content_end - content_start

            if visible_rows < 1:
                raise RuntimeError("Terminal too small")

            # Adjust scroll
            if cursor < scroll_offset:
                scroll_offset = cursor
            if cursor >= scroll_offset + visible_rows:
                scroll_offset = cursor - visible_rows + 1

            # Draw items
            for row_idx in range(visible_rows):
                item_idx = scroll_offset + row_idx
                if item_idx >= len(items):
                    break

                y = content_start + row_idx
                item = items[item_idx]
                cb = _checkbox(item, items, item_idx)
                indent = "    " * item.depth
                line = f" {indent}{cb} {item.label}"

                # Truncate to fit
                if len(line) > max_x - 1:
                    line = line[:max_x - 4] + "..."

                attr = curses.A_NORMAL
                if item_idx == cursor:
                    attr |= curses.A_REVERSE
                if item.item_type == ItemType.CATEGORY:
                    attr |= curses.A_BOLD | curses.color_pair(1)
                elif item.excluded:
                    attr |= curses.color_pair(2)

                try:
                    stdscr.addnstr(y, 0, line.ljust(max_x - 1), max_x - 1, attr)
                except curses.error:
                    pass

            # Status line
            status_y = max_y - 2
            status = f" Keeping {keeping} of {total} files in context"
            try:
                stdscr.addnstr(status_y, 0, status, max_x - 1,
                               curses.A_BOLD | curses.color_pair(3))
            except curses.error:
                pass

            # Footer
            footer_y = max_y - 1
            try:
                stdscr.addnstr(footer_y, 0, f" {footer}", max_x - 1,
                               curses.color_pair(1))
            except curses.error:
                pass

            stdscr.refresh()

            # Input
            key = stdscr.getch()

            if key in (ord('q'), ord('\n'), curses.KEY_ENTER, 10, 13):
                break
            elif key in (curses.KEY_UP, ord('k')):
                cursor = max(0, cursor - 1)
            elif key in (curses.KEY_DOWN, ord('j')):
                cursor = min(len(items) - 1, cursor + 1)
            elif key == ord(' '):
                _toggle_item(items, cursor)
            elif key == ord('a'):
                _toggle_all(items)
            elif key in (curses.KEY_PPAGE,):  # Page Up
                cursor = max(0, cursor - visible_rows)
            elif key in (curses.KEY_NPAGE,):  # Page Down
                cursor = min(len(items) - 1, cursor + visible_rows)
            elif key == curses.KEY_HOME:
                cursor = 0
            elif key == curses.KEY_END:
                cursor = len(items) - 1

    curses.wrapper(_main)
    return items
