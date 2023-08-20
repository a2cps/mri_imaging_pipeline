FROM mambaorg/micromamba:1.4.3-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml /tmp/env.yml

# need to install python first for fsl installer (env handled by some python packages)
# # (otherwise python will not be found)
ENV TZ=Europe/London
RUN micromamba install -q --name base --yes --file /tmp/env.yml \
    && rm -f /tmp/env.yml \
    && micromamba clean --yes --all

COPY --chown=$MAMBA_USER:$MAMBA_USER assets/entrypoint.py /opt/entrypoint.py

ENTRYPOINT [ "/usr/local/bin/_entrypoint.sh", "python", "/opt/entrypoint.py" ]
