#!/usr/bin/env python

import os
import sys
import argparse
import subprocess as sp
from dataclasses import dataclass
from typing import Union, Tuple, List, Optional, Sequence

SPACES = ('xspace', 'yspace', 'zspace')


@dataclass(frozen=True)
class MincInfo:
    """
    Dimensional information of 3D volume. 3-tuples are always in the order of
    (xspace, yspace, zspace)
    """
    length: Tuple[int, int, int]
    step: Tuple[int, int, int]


@dataclass(frozen=True)
class MincFile:
    fname: str

    def dimlength(self, dim: str) -> int:
        cmd = ['mincinfo', '-dimlength', dim, self.fname]
        length = sp.check_output(cmd, text=True)
        return int(length)

    def step(self, dim: str) -> float:
        cmd = ['mincinfo', '-attvalue', f'{dim}:step', self.fname]
        step = sp.check_output(cmd, text=True)
        return float(step)

    def mincinfo(self) -> MincInfo:
        # noinspection PyTypeChecker
        return MincInfo(
            length=tuple(map(self.dimlength, SPACES)),
            step=tuple(map(self.step, SPACES))
        )


def resample(input_file: Union[str, os.PathLike], output_file: Union[str, os.PathLike], divisions: float,
             binarize: bool = True,
             verbose: bool = False, options: Optional[Sequence[str]] = None) -> None:
    """
    Wrapper for ``mincresample``.
    """
    info = MincFile(input_file).mincinfo()
    quiet_flag = [] if verbose else ['-quiet']
    cmd = [
        'mincresample',
        *quiet_flag,
        '-nelements',
        *(str(int(divisions * l)) for l in info.length),
        '-step',
        *(str(s / divisions) for s in info.step),
        *(options if options else []),
        input_file,
        output_file
    ]
    sp.run(cmd, check=True)

    if binarize:
        tmp = str(output_file) + '.binarized.mnc'
        cmd = ['minccalc', *quiet_flag, '-unsigned', '-byte', '-expression', 'A[0]>0.5', output_file, tmp]
        sp.run(cmd, check=True)
        os.rename(tmp, output_file)


def ssv_str(s: str) -> List[str]:
    """
    Parse a space-separated list of strings.
    """
    return s.strip().split()


def main():
    parser = argparse.ArgumentParser(description='Use mincresample to subdivide voxels in a MINC file.')
    parser.add_argument('-d', '--divisions', type=float, default=2.0,
                        help='number of cuts along voxel edge. Float values are accepted, mincresample '
                             'performs interpolation.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print out log messages as processing is being done')
    parser.add_argument('-o', '--options', type=ssv_str,
                        help='Additional options to pass to mincresample as space-separated list, e.g.'
                             ' specify interpolation as -tricubic or -trilinear')
    parser.add_argument('-n', '--no-binarize', dest='binarize', action='store_false',
                        help='Skip extra step minccalc -expr A[0]>0.5, '
                             'allowing for floating point values')
    parser.add_argument('input', type=str, help='input file')
    parser.add_argument('output', type=str, help='output file')

    options = parser.parse_args()
    try:
        resample(options.input, options.output, options.divisions, options.binarize, options.verbose, options.options)
    except sp.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == '__main__':
    main()
