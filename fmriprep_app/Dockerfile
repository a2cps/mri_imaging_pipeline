# bring in the micromamba image so we can copy files from it
FROM mambaorg/micromamba:1.5.8 AS micromamba
FROM freesurfer/synthstrip:1.6 AS fs

FROM nipreps/fmriprep:24.0.0

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
ENV ENV_NAME=fmriprep

RUN micromamba install -q --name ${ENV_NAME} --yes -c conda-forge --freeze-installed \
        impi_rt=2021.12 \
        ucx=1.17.0 \
        rdma-core=52.0 \
        mpi4py=3.1.6 \
        polars=1.0.0 \
        pydantic=2.8.0 \
        pytorch=2.3.1 \
    && micromamba run -n ${ENV_NAME} pip install \
        --no-deps \
        mriqc==24.0.0 \
        git+https://github.com/a2cps/biomarker-extractor.git@2fb859247424a8a4d170188b48d1ebe890bb0f30 \
    && micromamba clean --all --yes

COPY --from=fs --chown=$MAMBA_USER:$MAMBA_USER /freesurfer/models/synthstrip.1.pt /opt/synthstrip.1.pt
COPY --from=fs --chown=$MAMBA_USER:$MAMBA_USER --chmod=774 /freesurfer/mri_synthstrip /usr/local/bin

# files searched for in entrypoint.py
COPY assets/entrypoint.py assets/license.txt /opt/fmriprep_app/
ENV TZ=US/Central

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "/opt/fmriprep_app/entrypoint.py"]

CMD [ "--help" ]

