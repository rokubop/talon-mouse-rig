"""QA Module Init

Imports and exposes test suites from submodules.
"""

from .position import POSITION_TESTS
from .speed import SPEED_TESTS
from .direction import DIRECTION_TESTS

# Combine all tests
ALL_TESTS = POSITION_TESTS + SPEED_TESTS + DIRECTION_TESTS
