FROM bids/validator:v1.9.9 AS validator

FROM mambaorg/micromamba:1.5.6-jammy

COPY --from=validator /src/bids-validator /opt/bids-validator
COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

RUN micromamba install --name base --yes --file /tmp/env.yml  \
    && rm -rf ~/.cache/pip \
    && rm -f /tmp/env*yml \
    && micromamba clean --yes --all 

USER root

RUN  micromamba run -n base git clone https://github.com/rordenlab/dcm2niix /tmp/dcm2niix \
    && cd /tmp/dcm2niix \
    && micromamba run -n base git checkout 96bb7ac5da07e154e89453b0c143db54a8bcb96d \
    && mkdir /tmp/dcm2niix/build \
    && cd /tmp/dcm2niix/build \
    && micromamba run -n base cmake -DCMAKE_INSTALL_PREFIX:PATH=/opt/conda/ .. \
    && micromamba run -n base make \
    && micromamba run -n base make install \
    && rm -rf /tmp/dcm2niix \
    && ln -s /opt/bids-validator/bin/bids-validator /usr/local/bin/bids-validator

USER $MAMBA_USER
