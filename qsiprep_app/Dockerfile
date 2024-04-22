# bring in the micromamba image so we can copy files from it
FROM mambaorg/micromamba:1.5.8 as micromamba

FROM pennbbl/qsiprep:0.21.1

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

RUN micromamba install -q --name qsiprep --yes -c conda-forge --freeze-installed \
        impi_rt=2021.12 \
        ucx \
        rdma-core \
        mpi4py \
    && micromamba install --name qsiprep -c conda-forge --no-deps --yes openssl=3.0.7 \
    && micromamba clean --all --yes

# files searched for in entrypoint.py
COPY --link=true assets/entrypoint.py assets/license.txt assets/eddy_params.json /opt/qsiprep_app/
ENV FS_LICENSE=/opt/qsiprep_app/license.txt
ENV EDDY_PARAMS=/opt/qsiprep_app/eddy_params.json
ENV TZ=US/Central
ENV ENV_NAME=qsiprep

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "qsiprep"]

CMD [ "--help" ]

