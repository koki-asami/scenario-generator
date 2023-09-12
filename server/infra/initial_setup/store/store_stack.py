#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#

import os

from aws_cdk import aws_ecr, aws_logs, aws_s3, core

Env = os.environ.get('Env')
Project = os.environ.get('Project')


class AlgorithmStoreStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, configs: object, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.system = f'{Project}-{Env}'
        self.Project = Project
        self.env = Env

        aws_s3.Bucket(
            self, f'{self.system}-s3',
            bucket_name=self.system,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            object_ownership=aws_s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            cors=[
                aws_s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[aws_s3.HttpMethods.GET],
                    allowed_origins=["*"],
                    max_age=3000,
                )
            ]
        )

        batch_trigger_s3_bucket_name = configs['batch_trigger_s3_bucket']
        aws_s3.Bucket(
            self, batch_trigger_s3_bucket_name,
            bucket_name=batch_trigger_s3_bucket_name,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
        )

        aws_ecr.Repository(
            self, f'{self.system}-ecr-repository',
            repository_name=configs['ECR_REPOSITORY']
        )

        aws_logs.LogGroup(self, f'{self.system}-loggroup-batch-status',
            log_group_name=f'/aws/events/{self.system}-batch-status'
        )
        aws_logs.LogGroup(self, f'{self.system}-loggroup-longtime-batch-status',
            log_group_name=f'/aws/events/{self.system}-longtime-batch-status'
        )
