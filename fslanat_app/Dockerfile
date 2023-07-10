FROM ubuntu:22.04 AS fsl

RUN apt-get update \
    && apt-get install -y wget python3 \
    && wget -O /tmp/fslinstaller.py https://git.fmrib.ox.ac.uk/fsl/conda/installer/-/raw/03d60135741657094d509e648da0da13263971a5/fsl/installer/fslinstaller.py \
    && python3 /tmp/fslinstaller.py -d /opt/fsl -V 6.0.6.5

FROM mambaorg/micromamba:1.4.3-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/fslanat /tmp/fslanat/

# need to install python first for fsl installer (env handled by some python packages)
# # (otherwise python will not be found)
ENV TZ=Europe/London
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && micromamba run -n base pip install --no-deps /tmp/fslanat \
    && rm -rf /tmp/fslanat /tmp/env.yml \
    && micromamba clean --yes --all

COPY --from=fsl --chown=$MAMBA_USER:$MAMBA_USER /opt/fsl/ /opt/fsl
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py

# Unless otherwise specified each process should only use one thread - nipype
# will handle parallelization
ENV MKL_NUM_THREADS=1 
ENV OMP_NUM_THREADS=1

ENV FSLDIR=/opt/fsl
ENV FSLOUTPUTTYPE=NIFTI_GZ

ENV PATH="${FSLDIR}/share/fsl/bin:${PATH}"

ENV PREFECT_HOME=/tmp/prefect
ENV PREFECT_LOCAL_STORAGE_PATH="${PREFECT_HOME}/storage"
ENV PREFECT_API_DATABASE_CONNECTION_URL="sqlite+aiosqlite:///${PREFECT_HOME}/orion.db"
ENV PREFECT_API_DATABASE_CONNECTION_TIMEOUT=1200
ENV PREFECT_API_DATABASE_TIMEOUT=1200
ENV PREFECT_API_REQUEST_TIMEOUT=2400

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py" ]
