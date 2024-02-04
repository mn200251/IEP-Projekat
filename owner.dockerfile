FROM python:3

RUN mkdir -p /opt/src/owner
WORKDIR /opt/src/owner

COPY store/configuration.py ./configuration.py
COPY store/owner.py ./owner.py
COPY store/rolecheck.py ./rolecheck.py
COPY store/models.py ./models.py

COPY ./requirements.txt ./requirements.txt

RUN pip install -r ./requirements.txt

ENV PYTHONPATH="/opt/src/store"

# ENTRYPOINT ["echo", "hello world"]
# ENTRYPOINT ["sleep", "1200"]
ENTRYPOINT ["python", "./owner.py"]
# ENTRYPOINT ["python", "./Customer/owner.py"]
# ENTRYPOINT ["python", "./Owner/owner.py"]