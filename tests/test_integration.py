from typing import List

import pytest

from docker_cp.console import main


@pytest.mark.parametrize(
    ("options", "src", "target", "exit_code"),
    [
        (["-v"], "./__init__.py", "test:/tmp/", 0),
        (["-v"], "./__init__1.py", "test:/tmp/", 2),
        (["-v"], "./__init__.py", "test:/tmp/1", 2),
        (["-v"], "test:/tmp/__init__.py", ".", 0),
        (["-v"], "test:/tmp/__init__1.py", ".", 2),
        (["-v"], "test:/tmp/__init__.py", "./aaaa", 2),
        (["-v"], "test1:/tmp/__init__.py", ".", 2),
        (["-v"], "test:tmp/__init__1.py", ".", 2),
        (["-v"], "__init__.py", ".", 2),
    ],
)
def test_main(runner, options: List[str], src, target, exit_code):
    result = runner.invoke(
        main, [*options, src, target], catch_exceptions=False,
    )
    assert result.exit_code == exit_code
