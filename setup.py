from setuptools import setup
import re

_version_re = re.compile(r"(?<=^__version__ = (\"|'))(.+)(?=\"|')")

def get_version(rel_path: str) -> str:
    """
    Searches for the ``__version__ = `` line in a source code file.

    https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
    """
    with open(rel_path, 'r') as f:
        matches = map(_version_re.search, f)
        filtered = filter(lambda m: m is not None, matches)
        version = next(filtered, None)
        if version is None:
            raise RuntimeError(f'Could not find __version__ in {rel_path}')
        return version.group(0)


setup(
    name='subdivide-mnc',
    version=get_version('subdivide/__init__.py'),
    description='Use either nibabel or mincreshape to subdivide a volumetric image in the MINC file format.',
    author='Jennings Zhang',
    author_email='Jennings.Zhang@childrens.harvard.edu',
    url='https://github.com/FNNDSC/ep-subdivide-mnc-methods',
    packages=['subdivide'],
    py_modules=['subdivide_minc', 'subdivide_nibabel'],
    install_requires=['chris_plugin==0.1.1', 'nibabel', 'numpy', 'seaborn', 'pandas', 'h5py', 'loguru~=0.6.0'],
    license='MIT',
    # multiple console_scripts not supported
    # https://github.com/FNNDSC/chris_plugin/issues/4
    entry_points={
        'console_scripts': [
            'subdivide = subdivide.__main__:main',
        ]
    },
    scripts=[
        'subdivide_minc.py',
        'subdivide_nibabel.py'
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.'
    ],
    extras_require={
        'none': [],
        'dev': [
            'pytest~=7.1'
        ]
    }
)
