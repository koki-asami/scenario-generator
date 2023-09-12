# syntax=docker/dockerfile:1.0.0-experimental

ARG AWSCLI=2.1.25
ARG POETRY=1.2.2
ARG TENSORRT=8.2.3.0
ARG PYTHON=3.8.7
ARG CUDA=11.1.1
ARG CUDNN=8
ARG UBUNTU=18.04
FROM acesdev/algo-base:awscli${AWSCLI}-poetry${POETRY}-tensorrt${TENSORRT}-python${PYTHON}-cuda${CUDA}-cudnn${CUDNN}-devel-ubuntu${UBUNTU}

ENV LANG C.UTF-8
ENV LANGUAGE en_US

RUN pip install --upgrade pip

# Install jupyter nbextensions
# RUN pip install jupyter_contrib_nbextensions && \
#     jupyter contrib nbextension install --user && \
#     jupyter notebook --generate-config && \
#     jupyter nbextension enable codefolding/main && \
#     jupyter nbextension enable contrib_nbextensions_help_item/main && \
#     jupyter nbextension enable code_font_size/code_font_size && \
#     jupyter nbextension enable collapsible_headings/main && \
#     jupyter nbextension enable move_selected_cells/main && \
#     jupyter nbextension enable printview/main

COPY pyproject.toml poetry.lock poetry.toml $WORKDIR/
RUN mkdir -m 700 $HOME/.ssh && ssh-keyscan github.com > $HOME/.ssh/known_hosts
# RUN --mount=type=ssh poetry install --no-root

RUN echo "alias flake8='pflake8'" >> $HOME/.bash_aliases
