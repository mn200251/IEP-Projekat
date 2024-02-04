FROM python:3

RUN mkdir -p /opt/src/courier
WORKDIR /opt/src/courier

COPY store/configuration.py ./configuration.py
COPY store/owner.py ./courier.py
COPY store/rolecheck.py ./rolecheck.py
COPY store/models.py ./models.py

COPY ./requirements.txt ./requirements.txt

RUN pip install -r ./requirements.txt

ENV PYTHONPATH="/opt/src/store"

# ENTRYPOINT ["echo", "hello world"]
# ENTRYPOINT ["sleep", "1200"]
ENTRYPOINT ["python", "./courier.py"]