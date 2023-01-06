import json
from pathlib import Path

import pytest

from subdivide.__main__ import parser, main


@pytest.mark.skipif(not Path('/examples').is_dir(),
                    reason='volume containing example data not mounted')
def test_main(tmp_path: Path):
    inputdir = Path('/examples/incoming')
    expected = Path('/examples/outgoing')

    # simulate run of main function
    options = parser.parse_args([])
    main(options, inputdir, tmp_path)

    assert _rel(tmp_path) == _rel(expected)

    summary_file = tmp_path / 'summary.json'
    assert summary_file.is_file()
    with summary_file.open('r') as f:
        summary: dict = json.load(f)
    assert 'additions' in summary
    assert 'deletions' in summary


def _rel(directory: Path) -> frozenset[Path]:
    return frozenset(
        filename.relative_to(directory)
        for filename in directory.rglob('*')
    )
