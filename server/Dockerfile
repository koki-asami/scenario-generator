# syntax=docker/dockerfile:1.0.0-experimental

FROM acesdev/python:3.8.7-cuda11.1.1-cudnn8-runtime-ubuntu18.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    jq \
    libmagic-dev \
    libmysqlclient-dev \
    nginx \
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV TZ Asia/Tokyo
RUN echo "${TZ}" > /etc/timezone && \
    rm /etc/localtime && \
    ln -s /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

ARG AWSCLI=2.1.25
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${AWSCLI}.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install --update \
    && rm awscliv2.zip

ARG POETRY=1.2.2
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=${POETRY} python3 -
ENV PATH $HOME/.local/bin:$PATH

ENV WORKDIR $HOME/workspace
ENV PYTHONPATH $WORKDIR
WORKDIR $WORKDIR

ENV CPATH $CPATH:/usr/local/cuda/include
ENV LIBRARY_PATH $LIBRARY_PATH:/usr/local/cuda/lib64

RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV WORKDIR /opt/program
WORKDIR $WORKDIR

ARG RELEASE_VERSION=""
ARG PRIVATE_ENV=""
ENV RELEASE_VERSION "$RELEASE_VERSION"
ENV PRIVATE_ENV "$PRIVATE_ENV"

# RUN pip install --upgrade pip setuptools
RUN pip install --upgrade pip setuptools==59.8.0

COPY server/pyproject.toml server/poetry.lock server/poetry.toml $WORKDIR/

RUN poetry config virtualenvs.create false
# hadolint ignore=SC2215,DL3003
RUN --mount=type=ssh poetry install --no-root --no-dev --no-cache && \
    rm -rf ~/.cache
RUN pip install --no-cache Cython && pip install --no-cache git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI

ENV PATH $WORKDIR:$PATH
COPY server/* $WORKDIR
RUN chmod +x serve

ENV PYTHONPATH $WORKDIR

ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES all

# project settings
ENV AWS_BUCKET aces-vision
RUN mkdir /root/datadrive && chmod 777 /root/datadrive
COPY project_template/ $WORKDIR/project_template/
