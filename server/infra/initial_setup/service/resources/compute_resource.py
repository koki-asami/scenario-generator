#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aws_cdk import aws_batch, aws_ec2, aws_iam, aws_ssm, core


def create(scope: core.Construct, configs: object, vpc):

    security_group_id = aws_ssm.StringParameter.value_from_lookup(scope, f'/{scope.env}/{scope.Project}/sagemaker-sg-id')
    instance_role_arn = aws_ssm.StringParameter.value_from_lookup(scope, f'/{scope.env}/{scope.Project}/instance_role_arn')
    ecs_optimized_gpu_ami_id = aws_ec2.MachineImage.from_ssm_parameter(parameter_name="/aws/service/ecs/optimized-ami/amazon-linux-2/gpu/recommended/image_id", os=aws_ec2.OperatingSystemType.UNKNOWN)
    batch_service_role_arn = aws_ssm.StringParameter.value_for_string_parameter(scope, f'/{scope.env}/{scope.Project}/batch_service_role_arn')

    batch_service_role = aws_iam.Role.from_role_arn(scope, f"{scope.system}-batch_service_role", batch_service_role_arn)

    subnet_type = aws_ec2.SubnetType.PRIVATE
    # subnet_type = aws_ec2.SubnetType.ISOLATED

    batch_compute_resources = aws_batch.ComputeResources(
        vpc=vpc,
        vpc_subnets=aws_ec2.SubnetSelection(subnet_type=subnet_type, one_per_az=True),
        maxv_cpus=configs['aws_batch_max_job'] * configs['aws_batch_vcpu_per_instance'],
        minv_cpus=configs['aws_batch_min_job'] * configs['aws_batch_vcpu_per_instance'],
        security_groups=[aws_ec2.SecurityGroup.from_security_group_id(scope, f"{scope.system}-batch-sg", security_group_id)],
        image=ecs_optimized_gpu_ami_id,
        instance_role=instance_role_arn,
        instance_types=[aws_ec2.InstanceType(configs['aws_batch_instance_type'])],
        type=aws_batch.ComputeResourceType.ON_DEMAND,
        launch_template=aws_batch.LaunchTemplateSpecification(
            # created by network/resource/iam.py
            #  現状CDK(CloudFormation)では、DependsOnでリソース構築時に順序関係をLaunchTemplateに関係づけられず、
            #  AWS Batch構築時にLaunchTemplateが構築に間に合わずエラーになるのでこれらのリソースだけnetwork側であらかじめ作成しています
            launch_template_name=f"{scope.system}-batch-launch-template",
            # version="$Latest"
        ),
    )

    longtime_batch_compute_resources = aws_batch.ComputeResources(
        vpc=vpc,
        vpc_subnets=aws_ec2.SubnetSelection(subnet_type=subnet_type, one_per_az=True),
        maxv_cpus=configs['aws_longtime_batch_max_job'] * configs['aws_batch_vcpu_per_instance'],
        minv_cpus=0,
        security_groups=[aws_ec2.SecurityGroup.from_security_group_id(scope, f"{scope.system}-longtime-batch-sg", security_group_id)],
        image=ecs_optimized_gpu_ami_id,
        instance_role=instance_role_arn,
        instance_types=[aws_ec2.InstanceType(configs['aws_longtime_batch_instance_type'])],
        type=aws_batch.ComputeResourceType.ON_DEMAND,
        launch_template=aws_batch.LaunchTemplateSpecification(
            # created by network/resource/iam.py
            #  現状CDK(CloudFormation)では、DependsOnでリソース構築時に順序関係をLaunchTemplateに関係づけられず、
            #  AWS Batch構築時にLaunchTemplateが構築に間に合わずエラーになるのでこれらのリソースだけnetwork側であらかじめ作成しています
            launch_template_name=f"{scope.system}-batch-launch-template",
            # version="$Latest"
        ),
    )

    batch_compute_environment = aws_batch.ComputeEnvironment(
        scope=scope,
        id=f"{scope.system}-batch",
        compute_environment_name=f"{scope.system}-batch",
        compute_resources=batch_compute_resources,
        managed=True,
        service_role=batch_service_role,
    )

    longtime_batch_compute_environment = aws_batch.ComputeEnvironment(
        scope=scope,
        id=f"{scope.system}-longtime-batch",
        compute_environment_name=f"{scope.system}-longtime-batch",
        compute_resources=longtime_batch_compute_resources,
        managed=True,
        service_role=batch_service_role,
    )

    aws_ssm.StringParameter(scope, f'{scope.system}-compute-environment-arn',
        parameter_name=f'/{scope.env}/{scope.Project}/compute-environment-arn',
        string_value=batch_compute_environment.compute_environment_arn,
        description=f'{scope.env} {scope.Project} compute_environment_arn'
    )

    aws_ssm.StringParameter(scope, f'{scope.system}-longtime-compute-environment-arn',
        parameter_name=f'/{scope.env}/{scope.Project}/longtime-compute-environment-arn',
        string_value=longtime_batch_compute_environment.compute_environment_arn,
        description=f'{scope.env} {scope.Project} longtime compute_environment_arn'
    )
