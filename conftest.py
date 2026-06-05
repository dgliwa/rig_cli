"""Worktree conftest: ensure the worktree src is first on sys.path.

The worktree's .venv has an editable install pointing to the worktree src,
but when the system pytest binary is used, the global editable install
(pointing to the main repo's src) may be resolved first. This conftest
explicitly inserts the worktree src at index 0 to guarantee the worktree's
version of the rig package is used in tests.
"""

import os
import sys

_worktree_src = os.path.join(os.path.dirname(__file__), "src")
if _worktree_src not in sys.path:
    sys.path.insert(0, _worktree_src)
elif sys.path.index(_worktree_src) != 0:
    sys.path.remove(_worktree_src)
    sys.path.insert(0, _worktree_src)
