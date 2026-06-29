FROM ghcr.io/prefix-dev/pixi:0.71 AS build

RUN apt update && apt install -y git

# copy source code, pixi.toml and pixi.lock to the container
COPY  . /app
WORKDIR /app
# run some compilation / build task (if needed)
# RUN pixi run build
# run the `install` command (or any other). This will also install the dependencies into `/app/.pixi`
RUN pixi install
# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook > /shell-hook.sh

# extend the shell-hook script to run the command passed to the container
RUN echo 'exec "$@"' >> /shell-hook.sh

FROM nipreps/fmriprep:25.2.5

COPY --from=build /app/.pixi/envs/default /app/.pixi/envs/default
COPY --from=build  /shell-hook.sh /shell-hook-main.sh

# fmriprep plays fast and loose with the path
RUN sed -i '1i export PATH="/app/.pixi/envs/fmriprep/bin:/opt/freesurfer/bin:/opt/freesurfer/tktools:/opt/freesurfer/mni/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"' /shell-hook.sh \
    && echo 'exec "$@"' >> /shell-hook.sh \
    && sed -i '/CONDA_SHLVL/,$d' ${HOME}/.bashrc

# files searched for in entrypoint.py
COPY assets/entrypoint.py assets/license.txt /opt/fmriprep_app/
ENV TZ=US/Central

ENTRYPOINT ["/bin/bash", "/shell-hook-main.sh", "python", "/opt/fmriprep_app/entrypoint.py"]
CMD [ "--help" ]

