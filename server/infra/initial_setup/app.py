#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import yaml
from aws_cdk import core
from infra.infra_stack import InfraInfraStack
from service.service_stack import AlgorithmServiceStack, ComputeResouceStack
from store.store_stack import AlgorithmStoreStack

Env = os.environ.get('Env')
Project = os.environ.get('Project')
configs = yaml.load(
    open(f'{os.getcwd()}/../configs/{Project}-{Env}-algorithm-server-infra.yml').read(), Loader=yaml.SafeLoader,
)

app = core.App()
for region in configs['regions']:
    cdk_env = core.Environment(account=configs['account_id'], region=region)

    store_stack = AlgorithmStoreStack(app, f'{Project}-{Env}-algorithm-store-{region}', configs=configs, env=cdk_env)
    core.Tags.of(store_stack).add('Env', Env)
    core.Tags.of(store_stack).add('Project', Project)

    infra_stack = InfraInfraStack(app, f'{Project}-{Env}-algorithm-server-infra-{region}', configs=configs, env=cdk_env)
    core.Tags.of(infra_stack).add('Env', Env)
    core.Tags.of(infra_stack).add('Project', Project)

    compute_resource = ComputeResouceStack(app, f'{Project}-{Env}-algorithm-compute-resource-{region}', configs=configs, env=cdk_env)
    core.Tags.of(compute_resource).add('Env', Env)
    core.Tags.of(compute_resource).add('Project', Project)

    service_stack = AlgorithmServiceStack(app, f'{Project}-{Env}-algorithm-service-{region}', configs=configs, env=cdk_env)
    core.Tags.of(service_stack).add('Env', Env)
    core.Tags.of(service_stack).add('Project', Project)

app.synth()
