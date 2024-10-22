FROM mambaorg/micromamba:1.5.8-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

ARG MAMBA_DOCKERFILE_ACTIVATE=1
RUN micromamba config set use_lockfiles False \
    && micromamba install --name base --yes --file /tmp/env.yml \
    && rm /tmp/env.yml \
    && micromamba clean --yes --all

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/dask.yml /opt/conda/etc/dask/dask.yml

ENV FSLDIR=/opt/conda
ENV FSLOUTPUTTYPE=NIFTI_GZ
ENV PYTHONUNBUFFERED=1

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
ENV TZ=UTC

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py" ]
CMD [ "--help" ]
