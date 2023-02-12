FROM python:3.8.1-slim-buster

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y gcc libffi-dev netcat curl tree

# ENV FLASK_APP head.py
# ENV LC_ALL C.UTF-8
# ENV LANG C.UTF-8

# EXPOSE 5000

RUN mkdir -p /opt/mcds/filetemp
RUN mkdir -p /opt/mcds/filelogs
RUN mkdir -p /opt/mcds/filesubmit
RUN mkdir -p /opt/mcds/filesocket
RUN mkdir -p /opt/mcds/filestatic

COPY requirements.txt /opt/mcds/fileserver/requirements.txt
WORKDIR /opt/mcds/fileserver
RUN pip3 install -r requirements.txt
COPY . /opt/mcds/fileserver

# RUN ./init.sh
# CMD ["gunicorn","--bind","0.0.0.0:5000","head:serveri"]

ENTRYPOINT ["./entrypoint.sh"]
