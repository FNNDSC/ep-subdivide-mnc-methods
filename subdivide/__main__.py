import itertools
import json
import math
import os
import sys
import time
from argparse import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Sequence, TypeVar, Generic, Optional

import pandas as pd
from chris_plugin import chris_plugin, PathMapper
from loguru import logger

from subdivide import DISPLAY_TITLE, __version__
from subdivide.types import MINCRESAMPLE_OPTIONS
from subdivide.voldiff import VolDiff, voldiff_between
from subdivide_minc import resample as mincresample
from subdivide_nibabel import resample as resample_using_numpy

parser = ArgumentParser(description='Subdivide voxels of a MINC volume using several methods',
                        formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument('-p', '--pattern', default='**/*.mnc', type=str,
                    help='input file glob')
parser.add_argument('-d', '--divisions', default=2, type=int,
                    help='number of cuts along voxel edge, valid values are powers of 2')
parser.add_argument('-V', '--version', action='version',
                    version=f'%(prog)s {__version__}')

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
        calls = pool.map(lambda f: f(), jobs)
        mincresampled = [p for p in calls if isinstance(p, Path)]

        logger.info('Done processing files, counting voxel differences...')
        diffs = list(pool.map(_report_voldiff, mincresampled))

    df = pd.DataFrame(diffs)
    counts_file = outputdir / 'voxel_counts.csv'
    df.to_csv(counts_file, index=False)
    logger.info('voxel counts written to {}', counts_file)

    summary = _summarize(df)
    summary_file = outputdir / 'summary.json'
    with summary_file.open('w') as out:
        json.dump(summary, out, indent=2)
    logger.info('summary written to --> {}', summary_file)

    # TODO
    # double histograms:
    # kron v.s. interpolated total voxel count
    # kron v.s. interpolated percent_change


class LazyCall(Generic[T], Callable[[], T]):

    def __init__(self, fn: Callable[[...], T], *args, **kwargs):
        self.__fn = fn
        self.__args = args
        self.__kwargs = kwargs

    def __call__(self) -> T:
        return self.__fn(*self.__args, **self.__kwargs)


def __jobs4files(t: tuple[Path, Path], divisions: int) -> Sequence[Callable[[], Optional[Path]]]:
    """
    Preloads functions with the parameters to call them with, preparing a set of functions which
    creates resampled volumes for each of the methods we want to try.

    Returned functions will optionally return the output file's ``Path`` if it is a call to ``mincresample``.
    """
    input_file, output_file = t
    output_file = output_file.with_suffix(f'.subdiv.{divisions}.mnc')
    jobs = [LazyCall(logger.info, 'enqueueing tasks for {}', input_file)]
    mt_output_files = [output_file.with_suffix(f'.mt.{method}.mnc') for method in MINCRESAMPLE_OPTIONS]
    jobs.extend(
        LazyCall(__mincresample_wrapper, input_file, mt_output_file, divisions, interpolation_method)
        for mt_output_file, interpolation_method in zip(mt_output_files, MINCRESAMPLE_OPTIONS)
    )
    jobs.append(LazyCall(resample_using_numpy, input_file, output_file.with_suffix('.np.mnc'), divisions))
    return jobs


def __mincresample_wrapper(input_file: Path, output_file: Path, divisions: int, interpolation_option: str) -> Path:
    mincresample(input_file, output_file, divisions, options=['-' + interpolation_option])
    return output_file


def _find_kroned_output(other_path: Path) -> Path:
    i = other_path.name.rindex('.mt.')
    kron_path = other_path.with_name(other_path.name[:i] + '.np.mnc')
    if not kron_path.is_file():
        raise RuntimeError(f'Expected {kron_path} to exist next to '
                           f'{other_path}, but it does not.')
    return kron_path


def _summarize(df: pd.DataFrame) -> dict:
    sums = df.groupby('method').sum(numeric_only=True)
    summary = {
        key: sums[key].to_dict()
        for key in ('additions', 'deletions', 'count_changes')
    }

    summary['count_inputs'] = df.shape[0]

    pc_group = df[['method', 'percent_change']].groupby(['method'])
    pc = pc_group.agg(['mean', 'std'])
    pc.columns = pc.columns.get_level_values(1)
    summary['percent_change'] = pc.to_dict('index')

    return summary


def _report_voldiff(other_path: Path) -> VolDiff:
    start_ns = time.monotonic_ns()
    kron_path = _find_kroned_output(other_path)
    diff = voldiff_between(kron_path, other_path)
    report_path = other_path.with_name(other_path.name + '.diff.json')
    with report_path.open('w') as f:
        json.dump(diff, f, indent=2)
    end_ns = time.monotonic_ns()
    elapsed = f'{(end_ns - start_ns) / 1e9:.1f}s'
    logger.info('counted voxel difference: {} -> {} (took {})', other_path, report_path, elapsed)
    return diff
