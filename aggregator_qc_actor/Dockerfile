FROM python:3.11.4-bullseye

RUN pip install --no-cache-dir \
    tapipy==1.4.1 

COPY reactor.py /opt/reactor.py
COPY job.json /opt/job.json

ENTRYPOINT [ "python" ]
CMD [ "/opt/reactor.py" ]