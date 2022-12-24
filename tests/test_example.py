from typing import Iterable

import pytest
import json
from pathlib import Path

from subdivide import parser, main


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

    expected_top_keys = {'additions', 'deletions', 'total_changes', 'mean_percent_change'}
    expected_sub_keys = {'trilinear', 'tricubic', 'nearest_neighbour'}
    assert set(summary.keys()) >= expected_top_keys
    for key in expected_top_keys:
        assert set(summary[key].keys()) == expected_sub_keys

    assert 'count_inputs' in summary
    assert summary['count_inputs'] == len(list(inputdir.rglob('*.mnc')))


def _rel(directory: Path) -> frozenset[Path]:
    return frozenset(
        filename.relative_to(directory)
        for filename in directory.rglob('*')
    )
