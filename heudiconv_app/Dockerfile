FROM bids/validator:v1.9.9 AS validator

FROM mambaorg/micromamba:1.5.6-jammy

COPY --from=validator /src/bids-validator /opt/bids-validator
COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER env-1.0.20230411.yml /tmp/env-1.0.20230411.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER env-UC.yml /tmp/env-UC.yml

RUN micromamba create --yes --file /tmp/env.yml  \
    && micromamba create --yes --file /tmp/env-1.0.20230411.yml \
    && micromamba create --yes --file /tmp/env-UC.yml \
    && rm -rf ~/.cache/pip \
    && rm -f /tmp/env*yml \
    && micromamba clean --yes --all 

USER root

RUN  micromamba run -n v1.0.20230411 git clone https://github.com/rordenlab/dcm2niix /tmp/dcm2niix \
    && cd /tmp/dcm2niix \
    && micromamba run -n v1.0.20230411 git fetch --tags \
    && mkdir /tmp/dcm2niix/build \
    && cd /tmp/dcm2niix/build \
    && micromamba run -n UC git checkout 06951ec39410625219420ff02f5e3d8c6563d7dd \
    && micromamba run -n UC cmake  -DCMAKE_INSTALL_PREFIX:PATH=/opt/conda/envs/UC .. \
    && micromamba run -n UC make \
    && micromamba run -n UC make install \
    && rm -rf /tmp/dcm2niix \
    && ln -s /opt/bids-validator/bin/bids-validator /usr/local/bin/bids-validator

USER $MAMBA_USER
