FROM semtech/mu-python-template:2.0.0-beta.3
LABEL maintainer="info@redpencil.io"

RUN apt-get update && \
    apt-get install -y graphviz libreoffice