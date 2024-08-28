FROM python:3.12.5-bullseye

RUN pip install --no-cache-dir \
    git+https://github.com/a2cps/mri-utils.git@b5b0749bc8d6721df8b6b6e692e74e85526ad5c3


COPY reactor.py /opt/reactor.py
COPY job.json /opt/job.json

ENTRYPOINT [ "python", "/opt/reactor.py" ]
