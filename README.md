# cenario-generator

This repository is an implementation of cenario-generator algorithms.

## 1. Clone

```
$ git clone git@github.com:koki-asami/scenario-generator.git
$ cd cenario-generator
```

NOTE: If `acesvision` is installed via `pip install`, you can also use `poetry run` commands. We listed up the commands.

## 2. Setup

Before building dokcer container, prepare `.env` file by the following command.

```
$ cp .env{.example,}
```

After that, set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `.env` file. You can use [this .env](https://github.com/aces-inc/secret-Algorithm/blob/master/aces-vision/.env) for this algorithm.

## 3. Docker build & run

### 3.1. default setup
```
$ DOCKER_BUILDKIT=1 docker build -t scenario-generator --ssh default .
$ docker-compose run --rm algo
```

### 3.2. manual setup
You can specifiy the base image by passing `--build-arg` to `docker build`.
```
$ PYTHON=3.8.7
$ DOCKER_BUILDKIT=1 docker build -t aces-vision --ssh default --build-args PYTHON=$PYTHON .
$ docker-compose run --rm algo
```

This is a list of variables you can specify as build-arg:
- `AWSCLI`
- `POETRY`
- `TENSORRT`
- `PYTHON`
- `CUDA`
- `CUDNN`
- `UBUNTU`

Available base images can be checked in [dockerhub](https://hub.docker.com/r/acesdev/algo-base/tags).

