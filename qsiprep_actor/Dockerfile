FROM python:3.11.9-bullseye

RUN pip install --no-cache-dir \
    git+https://github.com/a2cps/mri-actor-utils.git@04ff0d3fc9c55fabf3b64c9ba93be02a8f912672 \
    && pip uninstall -y polars \
    && pip --no-cache-dir install polars-lts-cpu==1.8.2


COPY reactor.py /opt/reactor.py
COPY job.json /opt/job.json

ENTRYPOINT [ "python", "/opt/reactor.py" ]
