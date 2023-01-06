from pathlib import Path
from typing import TypedDict

import nibabel as nib
import numpy.typing as npt

from subdivide.types import InterpolationOption, MINCRESAMPLE_OPTIONS


class VolDiff(TypedDict):
    """
    Data about the difference between a Kronecker product and a ```mincresample``` interpolation result.

    Volumes must be binary masks.
    """
    additions: int
    deletions: int
    total: int

    change: int
    count_changes: int
    percent_change: float

    method: InterpolationOption
    path: str


def _count_3d_diff(a: npt.NDArray, b: npt.NDArray) -> tuple[int, int]:
    if not a.shape == b.shape:
        b = b.reshape(a.shape)

    diff = a - b
    additions = (diff < -0.5).sum()
    deletions = (diff > +0.5).sum()

    return int(additions), int(deletions)


def _method_of(p: Path) -> InterpolationOption:
    parts = p.name.split('.')
    if not len(parts) >= 6:
        raise ValueError(f'Naming convention violated: {p} '
                         '(expected name to be something.subdiv.N.mt.METHOD.mnc)')
    method = parts[-2]
    if method not in MINCRESAMPLE_OPTIONS:
        raise ValueError(f'Method "{method}" (fname: {p})'
                         f'is not one of: {MINCRESAMPLE_OPTIONS}')
    return method  # type: ignore


def voldiff_between(kron_path: Path, other_path: Path) -> VolDiff:
    kron = nib.load(kron_path)
    other = nib.load(other_path)
    kron_data = kron.get_fdata()
    other_data = other.get_fdata()
    additions, deletions = _count_3d_diff(kron_data, other_data)
    total = int(other_data.sum())
    inter_option: InterpolationOption = _method_of(other_path)
    change = additions - deletions
    return VolDiff(
        additions=additions,
        deletions=deletions,
        total=total,
        method=inter_option,
        path=str(other_path),
        change=change,
        count_changes=additions + deletions,
        percent_change=change / total,
    )
