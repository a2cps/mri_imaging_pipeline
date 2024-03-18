FROM python:3.9

RUN pip install tapipy

ADD reactor.py /reactor.py

CMD ["python", "/reactor.py"]

# Onbuild support
ONBUILD ADD requirements.txt /tmp/requirements.txt
ONBUILD RUN pip3 install -r /tmp/requirements.txt
ONBUILD ADD reactor.py /
ONBUILD ADD config.yml /
ONBUILD ADD message.json* /message.jsonschema