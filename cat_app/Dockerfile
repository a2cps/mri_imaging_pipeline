# bring in the micromamba image so we can copy files from it
FROM mambaorg/micromamba:1.5 AS micromamba

FROM psadil/cat12:12.9

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

SHELL ["/usr/local/bin/_dockerfile_shell.sh"]
ENV ENV_NAME=base

COPY --chown=$MAMBA_USER:$MAMBA_USER  env.yml /tmp/

RUN micromamba install -q --name ${ENV_NAME} --yes -c conda-forge -f /tmp/env.yml \
    && rm /tmp/env.yml \
    && micromamba clean --all --yes

# files searched for in entrypoint.py
COPY assets/entrypoint.py /opt/cat_app/
ENV TZ=US/Central

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "/opt/cat_app/entrypoint.py"]
CMD [ "--help" ]
