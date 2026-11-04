import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stats import mean  # noqa: E402


def test_mean():
    assert mean([1, 2, 3]) == 2
    assert mean([5]) == 5
    assert mean([0.5, 1.5]) == 1.0
