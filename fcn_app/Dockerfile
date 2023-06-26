FROM mambaorg/micromamba:1.4.3-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/functional_connectivity /tmp/functional_connectivity/

# need to install python first for fsl installer (env handled by some python packages)
# # (otherwise python will not be found)
ENV TZ=Europe/London
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && micromamba run -n base pip install --no-deps /tmp/functional_connectivity/ \
    && rm -rf /tmp/functional_connectivity /tmp/env.yml \
    && micromamba clean --yes --all

# Unless otherwise specified each process should only use one thread - nipype
# will handle parallelization
ENV MKL_NUM_THREADS=1 
ENV OMP_NUM_THREADS=1

ENV PREFECT_HOME=/tmp/prefect
ENV PREFECT_LOCAL_STORAGE_PATH="${PREFECT_HOME}/storage"
ENV PREFECT_API_DATABASE_CONNECTION_URL="sqlite+aiosqlite:///${PREFECT_HOME}/orion.db"
ENV PREFECT_API_DATABASE_CONNECTION_TIMEOUT=1200
ENV PREFECT_API_DATABASE_TIMEOUT=1200
ENV PREFECT_API_REQUEST_TIMEOUT=2400

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py"]
CMD [ "--help" ]
