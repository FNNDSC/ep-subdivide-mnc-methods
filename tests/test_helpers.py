import pytest
from subdivide.__main__ import _find_kroned_output


@pytest.mark.parametrize('example, expected', [
    ('hello.subdiv.4.mt.trilinear.mnc', 'hello.subdiv.4.np.mnc'),
    ('share/outgoing/hello.subdiv.8.mt.nearest_neighbour.mnc', 'share/outgoing/hello.subdiv.8.np.mnc'),

])
def test_find_kroned_output(example, expected, tmp_path):
    example = tmp_path / example
    expected = tmp_path / expected
    expected.parent.mkdir(parents=True, exist_ok=True)
    expected.touch()
    assert _find_kroned_output(example) == expected
