FROM mambaorg/micromamba:2.0-ubuntu24.10

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

# need to install python first for fsl installer (env handled by some python packages)
# # (otherwise python will not be found)
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && micromamba run -n base pip cache purge \
    && rm -f /tmp/env.yml \
    && micromamba clean --yes --all

COPY --chown=$MAMBA_USER:$MAMBA_USER assets /opt/tapis

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/tapis/stage.py" ]
CMD ["--help"]
