# Subdivide MINC Volume

[![Version](https://img.shields.io/docker/v/fnndsc/ep-subdivide-mnc-methods?sort=semver)](https://hub.docker.com/r/fnndsc/ep-subdivide-mnc-methods)
[![MIT License](https://img.shields.io/github/license/fnndsc/ep-subdivide-mnc-methods)](https://github.com/FNNDSC/ep-subdivide-mnc-methods/blob/main/LICENSE)
[![ci](https://github.com/FNNDSC/ep-subdivide-mnc-methods/actions/workflows/ci.yml/badge.svg)](https://github.com/FNNDSC/ep-subdivide-mnc-methods/actions/workflows/ci.yml)

This repository contains several wrapper scripts for increasing the
resolution of MINC volumes by subdividing voxels along their edges
and performing interpolation.

It can be ran as a _ChRIS_ *ds*-plugin, in which case it applies
several methods of subdivision to every MINC file found in its
input directory, writing outputs to a given output directory.
These results are quantified and the aggragate statistics are
written to `summary.json`.

## Installation

`ep-subdivide-mnc-methods` is a _[ChRIS](https://chrisproject.org/) plugin_, meaning it can
run from either within _ChRIS_ or the command-line.

[![Get it from chrisstore.co](https://github.com/FNNDSC/ChRIS_store_ui/blob/22a8f9fa888ba1eefbebeed5ef42ae43e6562e28/src/assets/public/badges/light.png?raw=true)](https://chrisstore.co/plugin/ep-subdivide-mnc-methods)

### Using Apptainer

To get started with local command-line usage, use [Apptainer](https://apptainer.org/)
(a.k.a. Singularity) to run `ep-subdivide-mnc-methods` as a container:

```shell
singularity exec docker://fnndsc/ep-subdivide-mnc-methods subdivide [--args values...] input/ output/
```

To print its available options, run:

```shell
singularity exec docker://fnndsc/ep-subdivide-mnc-methods subdivide --help
```

### Scripts

#### `subdivide_minc.py`

Wrapper around `mincresample` (part of [minc tools](https://bic-mni.github.io/)).

##### Example of `subdivide_minc.py`

```shell
./subdivide_minc.py --divisions=8 input_volume.mnc output_subdivided_linear.mnc
# or
./subdivide_minc.py --divisions= --options=-cubic input_volume.mnc output_subdivided_cubic.mnc
```

Flags can be passed directly to `mincresample` using `--options=...`. See
[`man mincresample`](https://bic-mni.github.io/man-pages/man/mincresample.html)
for options.

##### Understanding Interpolation Options

`mincresample` interpolates values along voxel boundaries to smoothen the output.
The options are `-trilinear` (default for registration step in CIVET), `-tricubic`,
`-nearest_neighbour`, and `-sinc`.

###### External Reading

- https://maidens.github.io/jekyll/update/2016/08/10/An-illustrated-guide-to-interpolation-methods.html
- https://graphicdesign.stackexchange.com/questions/26385/difference-between-none-linear-cubic-and-sinclanczos3-interpolation-in-image

###### Notes for Surface Extraction

- nearest-neighbor has no blurring
- sinc and cubic are similar
- linear and cubic are smooth
- linear might be preferable over cubic for surface extraction because tight fitting around voxels
  is the cause of quality problem, not smoothness of mask edge

#### `subdivide_nibabel.py`

Increases the resolution of a volume without interpolation by computing the
[Kronecker product](https://numpy.org/doc/stable/reference/generated/numpy.kron.html).

##### Install dependencies for `subdivide_nibabel.py`

```shell
pip install numpy nibabel h5py
# or
conda install numpy nibabel h5py
```

Optional dependency on `nii2mnc` for output to MINC file format.

##### Example of `subdivide_nibabel.py`

```shell
./subdivide_nibabel.py --divisions 4 input_volume.nii subdivided_output.nii
```

Both MINC and NIFTI file formats are supported.

## Development

Instructions for developers.

### Local Testing

Run tests using `pytest` inside a container.

```shell
docker build -t localhost/fnndsc/ep-subdivide-mnc-methods:dev --build-arg extras_require=dev .
docker run --rm -it -u "$(id -u):$(id -g)" \
  -v "$PWD/examples:/examples:ro" \
  -v "$PWD:/app:ro" -w /app \
  localhost/fnndsc/ep-subdivide-mnc-methods:dev \
  pytest -v -o cache_dir=/tmp/pytest
```
