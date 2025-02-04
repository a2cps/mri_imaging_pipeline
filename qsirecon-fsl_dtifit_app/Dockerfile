# bring in the micromamba image so we can copy files from it
FROM mambaorg/micromamba:2.0 AS micromamba
FROM pennlinc/qsirecon:1.0.0

USER root

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

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
SHELL ["/usr/local/bin/_dockerfile_shell.sh"]
ENV ENV_NAME=qsiprep
RUN micromamba install -q --name ${ENV_NAME} --yes --file /tmp/env.yml \
    && rm /tmp/env.yml \
    && micromamba clean --yes --all

# files searched for in entrypoint.py
ENV TZ=US/Central \
    FSLOUTPUTTYPE=NIFTI_GZ \
    FSLDIR=/opt/conda/envs/qsiprep

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py assets/license /opt/qsirecon_app/
COPY --chmod=0775 --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.sh /opt/conda/envs/qsiprep/lib/python3.10/site-packages/biomarkers/data/dtifit_wrapper
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "/opt/qsirecon_app/entrypoint.py"]
CMD [ "--help" ]