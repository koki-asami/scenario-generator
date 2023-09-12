#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#

import os

from aws_cdk import aws_ec2, aws_iam, aws_ssm, core
from service.resources import batch, codebuild, compute_resource, s3_lambda

Env = os.environ.get('Env')
Project = os.environ.get('Project')


class ComputeResouceStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, configs: object, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.system = f'{Project}-{Env}'
        self.short_system = f'{Project}-{Env[:4]}'
        self.Project = Project
        self.env = Env

        vpc_id = aws_ssm.StringParameter.value_from_lookup(self, f'/{Env}/{Project}/vpc-id')
        vpc = aws_ec2.Vpc.from_lookup(self, 'vpc', vpc_id=vpc_id)
        compute_resource.create(self, configs=configs, vpc=vpc)


class AlgorithmServiceStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, configs: object, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.system = f'{Project}-{Env}'
        self.short_system = f'{Project}-{Env[:4]}'
        self.Project = Project
        self.env = Env

        vpc_id = aws_ssm.StringParameter.value_from_lookup(self, f'/{Env}/{Project}/vpc-id')
        vpc = aws_ec2.Vpc.from_lookup(self, 'vpc', vpc_id=vpc_id)

        # aws batch
        job_queue_arn, longtime_job_queue_arn, job_definition_arn = batch.create_batch(self, configs=configs)
        configs['BATCH_JOB_QUEUE'] = job_queue_arn
        configs['BATCH_LONGTIME_JOB_QUEUE'] = longtime_job_queue_arn
        configs['BATCH_JOB_DEFINITION'] = job_definition_arn

        # cloudwatch envet / s3 / lambda
        s3_lambda.create_s3_trigger(self, configs=configs)

        # codebuild
        codebuild.create_codebuild(self, configs=configs, vpc=vpc)
