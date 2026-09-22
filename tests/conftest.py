"""Suite-wide fixtures.

The network guard is `autouse`: it applies to every test in the suite, including tests
written later by someone who has not read §9.5.
"""

from __future__ import annotations

from typing import Iterator

import pytest

from .support.netguard import blocked_network


@pytest.fixture(autouse=True)
def _no_network() -> Iterator[None]:
    with blocked_network():
        yield
