FROM alpine:latest
MAINTAINER Alex Headley "aheadley@nexcess.net"

COPY . /app
WORKDIR /app

RUN apk update && apk add alpine-sdk

RUN apk add python python-dev py-pip git \
    && pip install -r requirements.txt \
    && pip install gunicorn \
    && pip freeze

ENV RAC_DEBUG=1
ENV RAC_SETTINGS="/app/docker.cfg"

VOLUME /data
EXPOSE 5000

ENTRYPOINT ["sh", "docker-entry.sh"]
CMD ["run_server"]
