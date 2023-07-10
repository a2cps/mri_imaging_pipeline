FROM python:3.11

RUN pip install --no-cache-dir tapipy

COPY reactor.py /opt/reactor.py
COPY job.json /opt/job.json

ENTRYPOINT [ "python" ]
CMD [ "/opt/reactor.py" ]