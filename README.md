# Senatio Generator
This repository is for project-senario-generator. The algorithm is used for generating disaster senario by LLM.


- Code that is not required for the quality of the project repository, such as jupyter notebook scripts for experiments,
should be implemented in `senario-generator/sandbox`.


## 1. Clone & Prepare .env  
```commandline
$ git clone git@github.com:koki-asami/senario-generator.git --recursive
$ cd senario-generator
```

Before building dokcer container, prepare `.env` file by the following command.

```commandline
$ cp .env{.example,}
```

.env file should be as follows:

```
# replace {template} with your project name
CUDA_VISIBLE_DEVICES=0
DOCKER_IMAGE=project-senerio-generator-dev
DOCKER_SHM_SIZE=4g
# CPU: runc, GPU: nvidia
DOCKER_RUNTIME=nvidia
# If you use Delta Proprietary Server, you can use `/datadrive` as HOST_DATADRIVE.
HOST_DATADRIVE=~/datadrive
# server data mount point (sagemaker: /opt/ml/model)
DATA_PATH=/opt/ml/model
# Mac: /run/host-services/ssh-auth.sock, Other: /ssh-agent
DOCKER_SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock
```

## 2. Docker Build & Run  
```commandline
$ DOCKER_BUILDKIT=1 docker build --ssh default . -t project-senerio-generator-dev
$ docker-compose run --rm project
```

If you would like to use jupyter notebook,

run with the specified port (e.g. `8888`),
```commandline
$ docker-compose run --rm -p 8888:8888 project
```

run notebook in the docker container with the port,
```commandline
jupyter notebook --ip 0.0.0.0 --no-browser --allow-root --port 8888
```

set port fowarding with the port in the local computer,
```commandline
ssh -fNL localhost:8888:localhost:8888 {host}
```
## 3. Create project algorithm server

[Create project algorithm server](server/README.md)
