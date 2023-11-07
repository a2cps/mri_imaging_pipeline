FROM python:3.11.4-bullseye

# tapipy 1.4.1 depends on typing_extensions<4.6
# pydantic>=2.0 depends on typing-extensions>=4.6.1
RUN pip install --no-cache-dir \
    tapipy==1.4.1 \
    "pydantic<2.0"

COPY reactor.py /opt/reactor.py

ENTRYPOINT [ "python" ]
CMD [ "/opt/reactor.py" ]
