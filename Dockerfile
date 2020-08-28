FROM python:3.8.5-buster

RUN apt-get update && apt-get install -y --no-install-recommends \
  make \
  build-essential \
  libssl-dev \
  zlib1g-dev \
  libbz2-dev \
  libreadline-dev \
  libsqlite3-dev \
  wget \
  curl \
  llvm \
  libncurses5-dev \
  xz-utils \
  tk-dev \
  libxml2-dev \
  libxmlsec1-dev \
  libffi-dev \
  liblzma-dev \
  libgdbm-dev \
  uuid-dev \
  python3-openssl \
  git \
  openjdk-11-jre

ENV CXX /usr/bin/g++

RUN python -m pip install -U pip setuptools wheel
RUN python -m pip install -U Red-DiscordBot

COPY requirements.txt /requirements.txt
RUN python -m pip install -U -r /requirements.txt

RUN (echo "docker" && echo "\n" && echo "Y" && echo "1") | redbot-setup

COPY docker/main-loop.sh /main-loop.sh

CMD ["/main-loop.sh"]
