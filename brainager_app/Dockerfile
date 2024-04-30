FROM mambaorg/micromamba:1.5.8 as micromamba
FROM afni/afni_make_build:AFNI_23.1.10 as AFNI

FROM psadil/brainager:240403

ARG MAMBA_USER=mambauser
ARG MAMBA_USER_ID=57439
ARG MAMBA_USER_GID=57439
ENV MAMBA_USER=$MAMBA_USER
ENV MAMBA_ROOT_PREFIX="/opt/conda"
ENV MAMBA_EXE="/bin/micromamba"

COPY --from=micromamba "$MAMBA_EXE" "$MAMBA_EXE"
COPY --from=micromamba /usr/local/bin/_activate_current_env.sh /usr/local/bin/_activate_current_env.sh
COPY --from=micromamba /usr/local/bin/_dockerfile_shell.sh /usr/local/bin/_dockerfile_shell.sh
COPY --from=micromamba /usr/local/bin/_entrypoint.sh /usr/local/bin/_entrypoint.sh
COPY --from=micromamba /usr/local/bin/_dockerfile_initialize_user_accounts.sh /usr/local/bin/_dockerfile_initialize_user_accounts.sh
COPY --from=micromamba /usr/local/bin/_dockerfile_setup_root_prefix.sh /usr/local/bin/_dockerfile_setup_root_prefix.sh

RUN /usr/local/bin/_dockerfile_initialize_user_accounts.sh && \
    /usr/local/bin/_dockerfile_setup_root_prefix.sh

USER $MAMBA_USER

# SHELL ["/usr/local/bin/_dockerfile_shell.sh"]

# ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]
# Optional: if you want to customize the ENTRYPOINT and have a conda
# environment activated, then do this:
# ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "my_entrypoint_program"]

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && rm /tmp/env.yml \
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
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/dask.yml /opt/conda/etc/dask/dask.yml
COPY --link=true --from=AFNI /opt/afni/install/3dWarp /opt/afni/install/libf2c.so /opt/afni/install/libmri.so /opt/afni/install/

USER root

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py"]
CMD [ "--help" ]

# You can modify the CMD statement as needed....
# CMD ["/bin/bash"]


# RUN apt-get install -y parallel

# COPY --chmod=744 assets/entrypoint /opt/tapis/entrypoint
# COPY --chmod=744 assets/main /opt/tapis/main

# WORKDIR /tmp
# ENTRYPOINT [ "/opt/tapis/entrypoint" ]
