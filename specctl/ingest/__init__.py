"""Reading the .docx (§10).

The conversion path is purely algorithmic — DEC-03, non-negotiable principle 1. Nothing
in this package may reach the network; `tests/test_netguard.py` proves it mechanically
rather than by comment.

`walk.py` is where content is silently lost if it is written casually, so it is the one
module in the package written recursively with its rules named after §10.5's W1–W6.
"""

from __future__ import annotations
