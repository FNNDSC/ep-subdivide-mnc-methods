#!/usr/bin/env python

import os
import subprocess as sp
from argparse import ArgumentParser
from tempfile import NamedTemporaryFile
from typing import Union

import nibabel as nib
import numpy as np
import numpy.typing as npt


def resample(input_file: Union[str, os.PathLike], output_file: Union[str, os.PathLike],
             divisions: int) -> None:
    """
    Use ``nibabel`` and ``numpy.kron`` to subdivide voxels evenly in a volumetric image.

    :param input_file: input file name, may be of any format supported by nibabel
    :param output_file: output file name, suffix must be either '.nii' or '.mnc'
    :param divisions: number of cuts along voxel edge, valid values are powers of 2
    """

    img = nib.load(input_file)
    data = img.get_fdata()
    transformed = _kron_helper(data, divisions)

    img.header.set_data_shape(transformed.shape)
    zooms = tuple(z / divisions for z in img.header.get_zooms())
    img.header.set_zooms(zooms)
    affine = img.affine
    affine[:, :3] /= divisions

    out = nib.Nifti1Image(transformed, img.affine, img.header)
    __save(out, output_file)


def _kron_helper(data: npt.NDArray, divisions: int) -> npt.NDArray:
    return np.kron(data, np.ones((divisions, divisions, divisions)))


def __save(img, filename, **kwargs) -> None:
    if __suffix_of(filename) == '.mnc':
        __save_as_mnc(img, filename, **kwargs)
        return
    nib.save(img, filename, **kwargs)


def __suffix_of(fname: Union[str, os.PathLike]) -> str:
    return os.path.splitext(fname)[-1]


def __save_as_mnc(img, filename: Union[str, os.PathLike], **kwargs) -> None:
    if not isinstance(img, nib.Nifti1Image):
        img = nib.Nifti1Image(img.get_fdata(), img.affine, img.header)
    with NamedTemporaryFile(suffix='.nii') as t:
        nib.save(img, t.name, **kwargs)
        nii2mnc(t.name, filename)


def nii2mnc(input_file: Union[str, os.PathLike], output_file: Union[str, os.PathLike]):
    # -quiet doesn't work
    sp.run(('nii2mnc', '-quiet', input_file, output_file),
           stdout=sp.DEVNULL, stderr=sp.DEVNULL, check=True)


def main():
    parser = ArgumentParser(description='Use nibabel and numpy.kron (Kronecker product) to subdivide voxels. '
                                        'Both NIFTI and MINC file formats are supported.')
    parser.add_argument('-d', '--divisions', type=int, default=2,
                        help='number of cuts along voxel edge. Valid values are powers of 2.')
    parser.add_argument('input', type=str, help='input file')
    parser.add_argument('output', type=str, help='output file, MINC output depends on nii2mnc')

    options = parser.parse_args()
    resample(options.input, options.output, options.divisions)


if __name__ == '__main__':
    main()
