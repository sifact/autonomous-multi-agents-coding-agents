import shutil

import pytest

from coding_agent.sandbox import make_workspace


@pytest.fixture
def workspace():
    """Workspace under the Colima-shared $HOME (not pytest's tmp_path)."""
    path = make_workspace()
    yield path
    shutil.rmtree(path, ignore_errors=True)
