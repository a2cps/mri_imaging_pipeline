FROM mambaorg/micromamba:1.5.6-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/functional_connectivity /tmp/functional_connectivity/

# need to install python first for fsl installer (env handled by some python packages)
# # (otherwise python will not be found)
ENV TZ=America/Chicago
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && micromamba run -n base pip install --no-deps /tmp/functional_connectivity/ \
    && rm -rf /tmp/functional_connectivity /tmp/env.yml \
    && micromamba clean --yes --all

ENV PREFECT_HOME=/tmp/prefect
ENV PREFECT_API_DATABASE_CONNECTION_TIMEOUT=1200
ENV PREFECT_API_DATABASE_CONNECTION_URL="sqlite+aiosqlite:///${PREFECT_HOME}/prefect.db"
ENV PREFECT_API_DATABASE_TIMEOUT=1200
ENV PREFECT_API_REQUEST_TIMEOUT=2400
ENV PREFECT_API_SERVICES_FLOW_RUN_NOTIFICATIONS_ENABLED=false
ENV PREFECT_API_SERVICES_LATE_RUNS_ENABLED=false
ENV PREFECT_API_SERVICES_PAUSE_EXPIRATIONS_ENABLED=false
ENV PREFECT_API_SERVICES_SCHEDULER_ENABLED=false
ENV PREFECT_LOGGING_TO_API_ENABLED=false
ENV PREFECT_SERVER_ANALYTICS_ENABLED=false
ENV PREFECT_UI_ENABLED=false

ENV APPTAINER_SHELL=/usr/local/bin/_apptainer_shell.sh

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py
COPY --chown=$MAMBA_USER:$MAMBA_USER dask.yml /opt/conda/etc/dask/dask.yml

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py"]
CMD [ "--help" ]
