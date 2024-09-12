FROM python:3.12.3-bullseye

RUN pip install --no-cache-dir \
    tapipy==1.6.3 \
    ibis-framework[duckdb]==8.0.0

COPY reactor.py /opt/reactor.py
COPY job.json /opt/job.json

ENTRYPOINT [ "python" ]
CMD [ "/opt/reactor.py" ]