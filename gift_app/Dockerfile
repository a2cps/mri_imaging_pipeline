# bring in the micromamba image so we can copy files from it
FROM mambaorg/micromamba:1.5.8 AS micromamba

FROM trends/gift-bids:v4.0.5.3

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

ARG MAMBA_DOCKERFILE_ACTIVATE=1 
COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && rm /tmp/env.yml \
    && micromamba clean --yes --all

# can't use "gift_app" as dst because that breaks gift
ADD --chown=$MAMBA_USER:$MAMBA_USER https://github.com/trendscenter/gift/raw/b0adaf01441405156ffc37ef80a65154afc07d3f/GroupICAT/icatb/icatb_templates/Neuromark_fMRI_2.0_modelorder-175.nii /opt/gift/
ADD --chown=$MAMBA_USER:$MAMBA_USER https://github.com/trendscenter/gift/raw/7312fad77273ae5a001285787586226d1238c07a/GroupICAT/icatb/icatb_templates/Neuromark_fMRI_2.1_modelorder-multi.nii /opt/gift/
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py assets/config*m /opt/gift/
ENV TZ=US/Central
WORKDIR /tmp

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "/opt/gift/entrypoint.py"]
CMD [ "--help" ]
