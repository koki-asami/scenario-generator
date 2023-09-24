# syntax=docker/dockerfile:1.0.0-experimental
# If you update `Dockerfile_base`, please upload `acesdev/aces-language-base:latest` to Docker Hub.

FROM acesdev/algo-base:awscli2.1.25-poetry1.2.1-tensorrt8.2.3.0-python3.8.7-cuda11.1-cudnn8-devel-ubuntu18.04

COPY pyproject.toml poetry.lock poetry.toml $WORKDIR/

RUN mkdir -m 700 $HOME/.ssh && ssh-keyscan github.com > $HOME/.ssh/known_hosts
RUN pip install --upgrade pip
RUN --mount=type=ssh poetry install --no-root
