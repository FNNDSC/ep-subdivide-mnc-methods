FROM docker.io/fnndsc/mni-conda-base:civet2.1.1-python3.11.0

LABEL org.opencontainers.image.authors="FNNDSC <dev@babyMRI.org>" \
      org.opencontainers.image.title="ep-subdivide-mnc-methods" \
      org.opencontainers.image.description="Use either nibabel or mincreshape to subdivide a volumetric image in the MINC file format."

WORKDIR /usr/local/src/ep-subdivide-mnc-methods

RUN conda install -c conda-forge numpy=1.23.5 nibabel=4.0.2 h5py=3.7.0 seaborn=0.12.2 pandas=1.5.2

COPY . .
ARG extras_require=none
RUN pip install ".[${extras_require}]"

CMD ["subdivide", "--help"]
