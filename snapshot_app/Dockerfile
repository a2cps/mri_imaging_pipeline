FROM mambaorg/micromamba:1.5.8-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER assets/snapshot /tmp/snapshot/

# need to install python first for fsl installer (env handled by some python packages)
# # (otherwise python will not be found)
ENV TZ=Europe/London
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && micromamba run -n base pip install --no-deps /tmp/snapshot/ \
    && rm -rf /tmp/snapshot /tmp/env.yml \
    && micromamba clean --yes --all

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py"]
CMD [ "--help" ]
