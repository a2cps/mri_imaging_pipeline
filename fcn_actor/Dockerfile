FROM python:3.12-bullseye

RUN pip install --no-cache-dir \
    git+https://github.com/a2cps/mri-actor-utils.git@99d7194f516b64acf2efcc261dcbc39ead778323\
    && pip uninstall -y polars \
    && pip --no-cache-dir install polars-lts-cpu==1.8.2


COPY reactor.py /opt/reactor.py
COPY job.json /opt/job.json

ENTRYPOINT [ "python", "/opt/reactor.py" ]
