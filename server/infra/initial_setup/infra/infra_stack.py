#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from aws_cdk import aws_autoscaling, aws_ec2, aws_ssm, core
from infra.resources import iam, vpc

Env = os.environ.get('Env')
Project = os.environ.get('Project')


class InfraInfraStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, configs: object, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.system = f'{Project}-{Env}'
        self.short_system = f'{Project}-{Env[:4]}'
        self.Project = Project
        self.env = Env

        if 'vpc_base_project' in configs:
            v, sg_dict = vpc.get_vpc(self, configs=configs)
        else:
            v, sg_dict = vpc.create_vpc(self, configs=configs)

        aws_ssm.StringParameter(self, f'{self.system}-vpc-id',
            parameter_name=f'/{Env}/{Project}/vpc-id',
            string_value=v.vpc_id,
            description=f'{Env} {Project} vpc_id'
        )

        core.CfnOutput(self, f'{self.system}-vpc-out', export_name=f'{self.system}-vpc-id', value=v.vpc_id)

        for name, sg in sg_dict.items():
            aws_ssm.StringParameter(self, f'{self.system}-{name}-sg-id',
                parameter_name=f'/{Env}/{Project}/{name}-sg-id',
                string_value=sg.security_group_id,
                description=f'{Env} {Project} {name} sg_id'
            )

            core.CfnOutput(self, f'{self.system}-{name}-sg-out', export_name=f'{self.system}-{name}-sg-id', value=sg.security_group_id)

        iam.create_iam(self, configs=configs)
