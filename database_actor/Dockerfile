FROM sd2e/reactors:python3

# reactor.py, config.yml, and message.jsonschema will be automatically
# added to the container when you run docker build or abaco deploy

RUN pip install psycopg2-binary
RUN git clone https://github.com/A2CPS/python-vbr && \
    cd python-vbr && \
    pip install -e . 