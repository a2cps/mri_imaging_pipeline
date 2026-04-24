FROM ghcr.io/prefix-dev/pixi:0.67.2 AS build

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

FROM ubuntu:24.04 AS production

COPY --from=build /app/.pixi/envs/default /app/.pixi/envs/default
COPY --from=build  /shell-hook.sh /shell-hook.sh
ADD --chmod=+rw https://surfer.nmr.mgh.harvard.edu/docs/synthstrip/requirements/synthstrip.1.pt \
    https://surfer.nmr.mgh.harvard.edu/docs/synthstrip/requirements/synthstrip.nocsf.1.pt \
    /opt/synthstrip/
ADD https://raw.githubusercontent.com/freesurfer/freesurfer/9636483c91e04cc17775ce4cb430b86f67046f1a/mri_synthstrip/mri_synthstrip \
    /tmp/
COPY --chmod=+x assets/entrypoint.py /opt/synthstrip/entrypoint.py
# first line of mri_synthstrip
RUN sed '1d' /tmp/mri_synthstrip > /opt/synthstrip/mri_synthstrip.py \
    && rm /tmp/mri_synthstrip \
    && chmod +x /opt/synthstrip/mri_synthstrip.py

# set the entrypoint to the shell-hook script (activate the environment and run the command)
# no more pixi needed in the prod container
ENTRYPOINT ["/bin/bash", "/shell-hook.sh", "python", "/opt/synthstrip/entrypoint.py"]

# CMD ["-h"]