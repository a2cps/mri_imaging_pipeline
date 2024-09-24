FROM python:3.11.9-bullseye

RUN pip install --no-cache-dir \
    git+https://github.com/a2cps/mri-actor-utils.git@eca6bc1334dfd3d35d0b4d3a543a779750bc3b20 \
    && pip uninstall -y polars \
    && pip --no-cache-dir install polars-lts-cpu==1.8.2


COPY reactor.py /opt/reactor.py
COPY job.json /opt/job.json

ENTRYPOINT [ "python", "/opt/reactor.py" ]
