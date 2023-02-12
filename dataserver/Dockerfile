FROM python:3.8.1-slim-buster

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y netcat curl tree

# RUN mkdir /home/pipinstall && mkdir /home/flaskapp
# RUN cd home/pipinstall && apt install python3-pip -y

ENV FLASK_APP head.py

# ENV LC_ALL C.UTF-8
# ENV LANG C.UTF-8

# EXPOSE 5000

RUN mkdir -p /opt/mcds/datalogs
RUN mkdir -p /opt/mcds/datasocket
RUN mkdir -p /opt/mcds/datastatic

COPY requirements.txt /opt/mcds/dataserver/requirements.txt
WORKDIR /opt/mcds/dataserver
RUN pip3 install -r requirements.txt
COPY . /opt/mcds/dataserver

# RUN ./init.sh
# CMD ["gunicorn","--bind","0.0.0.0:5000","head:serveri"]

ENTRYPOINT ["./entrypoint.sh"]
