from pathlib import Path
import pytest
from subdivide import _find_kroned_output


@pytest.mark.parametrize('example, expected', [
    ('hello.subdiv.4.mt.trilinear.mnc', 'hello.subdiv.4.np.mnc'),
    ('/share/outgoing/hello.subdiv.8.mt.nearest_neighbour.mnc', '/share/outgoing/hello.subdiv.8.np.mnc'),

])
def test_find_kroned_output(example, expected):
    assert _find_kroned_output(Path(example)) == Path(expected)
