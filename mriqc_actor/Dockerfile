FROM python:3.12.5-bullseye

RUN pip install --no-cache-dir \
    git+https://github.com/a2cps/mri-actor-utils.git@97a0e48d50daae8c39cc9b0ea619c79f22af2fe9


COPY reactor.py /opt/reactor.py
COPY job.json /opt/job.json

ENTRYPOINT [ "python", "/opt/reactor.py" ]
