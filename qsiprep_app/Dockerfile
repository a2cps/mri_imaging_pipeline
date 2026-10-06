FROM ghcr.io/prefix-dev/pixi:0.76.2 AS build

RUN apt update && apt install -y git

# copy source code, pixi.toml and pixi.lock to the container
COPY . /app
WORKDIR /app
# run the `install` command (or any other). This will also install the dependencies into `/app/.pixi`
RUN pixi install
# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook > /shell-hook.sh

# extend the shell-hook script to run the command passed to the container
RUN echo 'exec "$@"' >> /shell-hook.sh

# bring in micromamba so that packages can be added to qsiprep's environment
FROM mambaorg/micromamba:1.5.8 AS micromamba

FROM pennlinc/qsiprep:26.1.0rc1

COPY --from=build /app/.pixi/envs/default /app/.pixi/envs/default
COPY --from=build /shell-hook.sh /shell-hook-main.sh
COPY --from=micromamba /bin/micromamba /bin/micromamba

# pixi writes the PATH of the build stage into the shell-hook, which would hide the
# tools that qsiprep finds on this image's PATH (eddy, ANTs, MRtrix3, niimath, ...).
# keep this image's PATH first (e.g., MRtrix3's python scripts need qsiprep's python)
# and call the python of our environment by its full path (see ENTRYPOINT)
RUN sed -i "s|^export PATH=.*|export PATH=\"${PATH}:/app/.pixi/envs/default/bin\"|" /shell-hook-main.sh \
    && test "$(grep -c '^export PATH=' /shell-hook-main.sh)" = 1

# eddy_quad calls $FSLDIR/bin/slicer, which is not part of qsiprep's environment
RUN MAMBA_ROOT_PREFIX=/tmp/micromamba micromamba install -y -p /app/.pixi/envs/qsiprep \
    -c https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public/ \
    -c conda-forge \
    --freeze-installed \
    fsl-miscvis \
    && rm -rf /tmp/micromamba

ENV TEMPLATEFLOW_HOME=/opt/templateflow
RUN /app/.pixi/envs/qsiprep/bin/python -c "\
    from templateflow import api; \
    api.get('MNI152NLin2009cAsym', resolution=1, desc=None, suffix='T1w'); \
    api.get('MNI152NLin2009cAsym', resolution=1, desc='brain', suffix='mask')" \
    && chmod -R a+rX ${TEMPLATEFLOW_HOME}

COPY assets/entrypoint.py assets/eddy_params.json assets/qsiprep.toml /opt/qsiprep_app/
ENV TZ=US/Central


ENTRYPOINT ["/bin/bash", "/shell-hook-main.sh", "/app/.pixi/envs/default/bin/python", "/opt/qsiprep_app/entrypoint.py"]

CMD [ "--help" ]
