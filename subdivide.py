import dataclasses
import itertools
import json
import math
import os
import sys
from argparse import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Sequence, Iterable, Literal, TypeVar

import numpy as np
import nibabel as nib
import numpy.typing as npt
from chris_plugin import chris_plugin, PathMapper
from loguru import logger

from subdivide_minc import resample as mincresample
from subdivide_nibabel import resample as resample_using_numpy

__version__ = '1.0.0'

DISPLAY_TITLE = r"""
           _         _ _       _     _            ___  ________ _   _ _____ 
          | |       | (_)     (_)   | |           |  \/  |_   _| \ | /  __ \
 ___ _   _| |__   __| |___   ___  __| | ___ ______| .  . | | | |  \| | /  \/
/ __| | | | '_ \ / _` | \ \ / / |/ _` |/ _ \______| |\/| | | | | . ` | |    
\__ \ |_| | |_) | (_| | |\ V /| | (_| |  __/      | |  | |_| |_| |\  | \__/\
|___/\__,_|_.__/ \__,_|_| \_/ |_|\__,_|\___|      \_|  |_/\___/\_| \_/\____/
                                                                            
"""


parser = ArgumentParser(description='Subdivide voxels of a MINC volume using several methods',
                        formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument('-p', '--pattern', default='**/*.mnc', type=str,
                    help='input file glob')
parser.add_argument('-d', '--divisions', default='2', type=int,
                    help='number of cuts along voxel edge, valid values are powers of 2')
parser.add_argument('-V', '--version', action='version',
                    version=f'%(prog)s {__version__}')

__MINCRESAMPLE_OPTIONS = ('trilinear', 'tricubic', 'nearest_neighbour')
InterpolationOption = Literal['trilinear', 'tricubic', 'nearest_neighbour']

T = TypeVar('T')


@chris_plugin(
    parser=parser,
    title='Subdivide MINC Volume',
    category='MINC',
    min_memory_limit='1Gi',
    min_cpu_limit='1000m',
    min_gpu_limit=0
)
def main(options: Namespace, inputdir: Path, outputdir: Path):
    divisions: int = options.divisions
    if divisions < 1 or not math.log2(divisions).is_integer():
        print(f'error: --divisions={divisions} is not a power of 2')
        sys.exit(1)

    print(DISPLAY_TITLE, flush=True)

    nproc = len(os.sched_getaffinity(0))
    logger.info('Using {} threads', nproc)

    mapper = PathMapper.file_mapper(inputdir, outputdir, glob=options.pattern)
    jobs_map = map(__jobs4files, mapper, itertools.repeat(divisions))
    jobs = [job for jobs_per_input in jobs_map for job in jobs_per_input]

    with ThreadPoolExecutor(max_workers=nproc) as pool:
        __raise_for_exceptions(pool.map(lambda f: f(), jobs))

        report_mapper = PathMapper.file_mapper(
            outputdir, outputdir, glob='**/*.mt.*.mnc', suffix='.diff.txt'
        )
        reports = pool.map(__report_voxel_count_diff, report_mapper)

    logger.info('aggregating sums...')
    diffs = _gather_diffs(reports)
    summary = {
        'additions': {k: sum(d.additions for d in v) for k, v in diffs.items()},
        'deletions': {k: sum(d.deletions for d in v) for k, v in diffs.items()},
        'total_changes': {k: sum(d.count_changes for d in v) for k, v in diffs.items()},
        'mean_percent_change': {k: np.mean([d.percent_change for d in v]) for k, v in diffs.items()},
        'count_inputs': len(diffs)
    }
    summary_file = outputdir / 'summary.json'
    with summary_file.open('w') as out:
        json.dump(summary, out, indent=2)
    logger.info('written to {}', summary_file)


class LazyCall:

    def __init__(self, fn: Callable, *args, **kwargs):
        self.__fn = fn
        self.__args = args
        self.__kwargs = kwargs

    def __call__(self):
        return self.__fn(*self.__args, **self.__kwargs)


def __jobs4files(t: tuple[Path, Path], divisions: int) -> Sequence[Callable[[], None]]:
    """
    Preloads functions with the parameters to call them with, preparing a set of functions which
    creates resampled volumes for each of the methods we want to try.
    """
    input_file, output_file = t
    output_file = output_file.with_suffix(f'.subdiv.{divisions}.mnc')
    jobs = [LazyCall(logger.info, 'enqueueing tasks for {}', input_file)]
    mt_output_files = [output_file.with_suffix(f'.mt.{method}.mnc') for method in __MINCRESAMPLE_OPTIONS]
    jobs.extend(
        LazyCall(__mincresample_wrapper, input_file, mt_output_file, divisions, interpolation_method)
        for mt_output_file, interpolation_method in zip(mt_output_files, __MINCRESAMPLE_OPTIONS)
    )
    jobs.append(LazyCall(resample_using_numpy, input_file, output_file.with_suffix('.np.mnc'), divisions))
    return jobs


def __mincresample_wrapper(input_file: Path, output_file: Path, divisions: int, interpolation_option: str) -> None:
    """
    A wrapper which exists to make PyCharm's type checker a little happier by having a ``None`` return type.
    """
    if not interpolation_option.startswith('-'):
        interpolation_option = '-' + interpolation_option
    mincresample(input_file, output_file, divisions, options=[interpolation_option])


@dataclasses.dataclass(frozen=True)
class VolDiff:
    additions: int
    deletions: int
    total: int

    def asdict(self) -> dict:
        d = dataclasses.asdict(self)
        d['change'] = self.change
        d['count_changes'] = self.count_changes
        d['percent_change'] = self.percent_change
        return d

    def to_csv(self) -> str:
        rows = (','.join(t) for t in self.asdict())
        return '\n'.join(rows)

    def save_csv(self, output_file: Path) -> None:
        output_file.write_text(self.to_csv())

    @property
    def change(self):
        return self.additions - self.deletions

    @property
    def count_changes(self) -> int:
        return self.additions + self.deletions

    @property
    def percent_change(self) -> float:
        return self.change / self.total

    @classmethod
    def between(cls, a: npt.NDArray, b: npt.NDArray) -> 'VolDiff':
        if not a.shape == b.shape:
            b = b.reshape(a.shape)
        max_x, max_y, max_z = a.shape
        additions = 0
        deletions = 0
        for x in range(max_x):
            for y in range(max_y):
                for z in range(max_z):
                    if a[x, y, z] > 0.5 > b[x, y, z]:
                        deletions += 1
                    elif a[x, y, z] < 0.5 < b[x, y, z]:
                        additions += 1
        total: int = np.sum(a)  # type: ignore
        return cls(additions, deletions, total)


def __report_voxel_count_diff(files: tuple[Path, Path]) -> tuple[InterpolationOption, VolDiff]:
    """
    Given a path to an output file produced by ``mincresample``, find the sibling output which was produced
    by ``np.kron``, compute the difference in voxel count between the two volumes, and write this number
    to a text file.

    :return: name of interpolation method and the difference between the kron product and resampled volume
    """
    resampled_file, report_file = files
    kroned_file = _find_kroned_output(resampled_file)
    logger.info('counting voxel difference in {}', resampled_file)

    resampled_img = nib.load(resampled_file)
    kroned_img = nib.load(kroned_file)

    diff = VolDiff.between(kroned_img.get_fdata(), resampled_img.get_fdata())
    diff.save_csv(report_file)

    inter_option: InterpolationOption = resampled_file.name.split('.')[-2]  # type: ignore
    return inter_option, diff


def _find_kroned_output(resampled_file: Path) -> Path:
    i = resampled_file.name.rindex('.mt.')
    return resampled_file.with_name(resampled_file.name[:i] + '.np.mnc')


def _gather_diffs(diffs: Iterable[tuple[InterpolationOption, T]]) -> dict[InterpolationOption, Sequence[T]]:
    sums = {o: [] for o in __MINCRESAMPLE_OPTIONS}
    for inter_option, diff in diffs:
        sums[inter_option].append(diff)
    return sums


def __raise_for_exceptions(_i: Iterable):
    for _ in _i:
        pass


if __name__ == '__main__':
    main()
