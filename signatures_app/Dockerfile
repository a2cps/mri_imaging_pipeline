FROM mambaorg/micromamba:1.5.6-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/mri_signatures /tmp/mri_signatures/

# need to install python first for fsl installer (env handled by some python packages)
# # (otherwise python will not be found)
ENV TZ=America/Chicago
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && micromamba run -n base pip install --no-deps /tmp/mri_signatures/ \
    && rm -rf /tmp/mri_signatures /tmp/env.yml \
    && micromamba clean --yes --all

ENV PREFECT_HOME=/tmp/prefect
ENV PREFECT_LOCAL_STORAGE_PATH="${PREFECT_HOME}/storage"
ENV PREFECT_API_DATABASE_CONNECTION_URL="sqlite+aiosqlite:///${PREFECT_HOME}/orion.db"
ENV PREFECT_API_DATABASE_CONNECTION_TIMEOUT=1200
ENV PREFECT_API_DATABASE_TIMEOUT=1200
ENV PREFECT_API_REQUEST_TIMEOUT=2400
ENV APPTAINER_SHELL=/usr/local/bin/_apptainer_shell.sh

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/2013_Wager_NEJM_NPS/*gz /opt/conda/lib/python3.11/site-packages/signatures/data/2013_Wager_NEJM_NPS

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py"]
CMD [ "--help" ]