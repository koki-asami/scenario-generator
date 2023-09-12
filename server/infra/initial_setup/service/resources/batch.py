#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aws_cdk import aws_batch, aws_ecr, aws_ecs, aws_events, aws_events_targets, aws_logs, aws_ssm, aws_xray, core


def create_batch(scope: core.Construct, configs: object):

    compute_environment_arn = aws_ssm.StringParameter.value_for_string_parameter(scope, f'/{scope.env}/{scope.Project}/compute-environment-arn')
    longtime_compute_environment_arn = aws_ssm.StringParameter.value_for_string_parameter(scope, f'/{scope.env}/{scope.Project}/longtime-compute-environment-arn')
    task_role_arn = aws_ssm.StringParameter.value_for_string_parameter(scope, f'/{scope.env}/{scope.Project}/task_role_arn')
    # task_role = aws_iam.Role.from_role_arn(scope, f"{scope.system}-task_role_role", task_role_arn)

    batch_compute_environment = aws_batch.ComputeEnvironment.from_compute_environment_arn(
        scope=scope,
        id=f"{scope.system}-batch",
        compute_environment_arn=compute_environment_arn
    )
    longtime_batch_compute_environment = aws_batch.ComputeEnvironment.from_compute_environment_arn(
        scope=scope,
        id=f"{scope.system}-longtime-batch",
        compute_environment_arn=longtime_compute_environment_arn
    )

    batch_job_queue = aws_batch.JobQueue(
        scope=scope,
        id=f"{scope.system}-jobqueue",
        job_queue_name=f"{scope.system}-jobqueue",
        compute_environments=[
            aws_batch.JobQueueComputeEnvironment(
                compute_environment=batch_compute_environment,
                order=1
            )
        ],
        priority=1
    )

    longtime_batch_job_queue = aws_batch.JobQueue(
        scope=scope,
        id=f"{scope.system}-longtime-jobqueue",
        job_queue_name=f"{scope.system}-longtime-jobqueue",
        compute_environments=[
            aws_batch.JobQueueComputeEnvironment(
                compute_environment=longtime_batch_compute_environment,
                order=1
            )
        ],
        priority=1
    )

    ecr_batch_repository = aws_ecr.Repository.from_repository_name(
        scope, f'{scope.system}-batch-ecr',
        repository_name=configs['ECR_REPOSITORY']
    )
    # ecr_batch_repository = aws_ecr.Repository.from_repository_arn(
    #     scope=scope,
    #     id=f"{scope.system}-ecr-repository",
    #     repository_arn=configs['ECR_REPOSITORY_ARN']
    # )

    container_image = aws_ecs.ContainerImage.from_ecr_repository(
        repository=ecr_batch_repository,
        tag=configs['ECR_DEPLOY_TAG']
    )

    # FIXME:
    # https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_batch/JobDefinitionContainer.html?highlight=jobdefinitioncontainer#aws_cdk.aws_batch.JobDefinitionContainer
    # For now, only the devices property is supported
    # Issue: https://github.com/aws/aws-cdk/issues/13023

    # batch_job_definition = aws_batch.JobDefinition(
    #     scope=scope,
    #     id=f"{scope.system}-job-definition",
    #     job_definition_name=f"{scope.system}-job-definition",
    #     container=aws_batch.JobDefinitionContainer(
    #         image=container_image,
    #         environment={
    #             "FLASK_ENV": scope.env,
    #             "S3_WEIGHT_FILE_BUCKET": f"{scope.system}",
    #             "S3_WEIGHT_FILE_PATH": configs['SAGEMAKER_WEIGHT_SOURCE_S3KEY'],
    #             "DATA_PATH": configs['AWS_BATCH_DOCKER_DATA_PATH'],
    #             "TIME_PROFILE": "1",
    #             "MEM_PROFILE": "1",
    #         },
    #         job_role=task_role,
    #         linux_params=aws_ecs.LinuxParameters(
    #             scope=scope,
    #             id=f"{scope.system}-linux-params",
    #             init_process_enabled=True,
    #             shared_memory_size=configs['aws_batch_shared_memory'],
    #         ).render_linux_parameters(),
    #         privileged=True,
    #         gpu_count=1,
    #         memory_limit_mib=configs['aws_batch_memory_per_instance'],
    #         vcpus=configs['aws_batch_vcpu_per_instance'],
    #     ),
    #     retry_attempts=1
    # )
    # job_definition_arn = batch_job_definition.job_definition_arn

    batch_job_definition = aws_batch.CfnJobDefinition(
        scope=scope,
        id=f"{scope.system}-job-definition",
        job_definition_name=f"{scope.system}-job-definition",
        type="container",
        container_properties={
            "image": container_image.image_name,
            "environment": [
                {"name": "Project", "value": scope.system},
                {"name": "Env", "value": scope.env},
                {"name": "FLASK_ENV", "value": scope.env},
                {"name": "S3_WEIGHT_FILE_BUCKET", "value": scope.system},
                {"name": "S3_WEIGHT_FILE_PATH", "value": configs['SAGEMAKER_WEIGHT_SOURCE_S3KEY']},
                {"name": "DATA_PATH", "value": configs['AWS_BATCH_DOCKER_DATA_PATH']},
                {"name": "MEM_PROFILE", "value": configs.get('MEM_PROFILE', '1')},
                {"name": "TIME_PROFILE", "value": configs.get('TIME_PROFILE', '1')},
                {"name": "GPU_PROFILE", "value": configs.get('GPU_PROFILE', '1')},
                {"name": "METRICS_TOPIC_ARN", "value": configs['METRICS_TOPIC_ARN']},
                {"name": "REQUEST_LOG_TOPIC_ARN", "value": configs['REQUEST_LOG_TOPIC_ARN']},
                {"name": "AWS_DEFAULT_REGION", "value": "ap-northeast-1"},
                {"name": "AWS_XRAY_SDK_ENABLED", "value": "true"},
            ],
            "jobRoleArn": task_role_arn,
            "memory": configs['aws_batch_memory_per_instance'],
            "vcpus": configs['aws_batch_vcpu_per_instance'],
            "linuxParameters": {
                "devices": [],
                "sharedMemorySize": configs['aws_batch_shared_memory'],
                "tmpfs": []
            },
            "mountPoints": [],
            "privileged": True,
            "resourceRequirements": [{
                "type": "GPU",
                "value": "1"
            }] if configs['aws_longtime_batch_instance_type'][0] == 'g' else [],
        }
    )

    # x-ray
    # aws_xray.CfnSamplingRule(scope, f"{scope.Project}-sampling-rule",
    #     rule_name=f"{scope.Project[:26]}-batch",
    #     sampling_rule=aws_xray.CfnSamplingRule.SamplingRuleProperty(
    #         fixed_rate=0,
    #         host= "*",
    #         http_method= "*",
    #         priority=configs['XRAY_PRIORITY'],
    #         reservoir_size=30,
    #         resource_arn= "*",
    #         service_name=f"{scope.Project}-batch",
    #         service_type="*",
    #         url_path="*",
    #         version=1
    #     )
    # )

    # import cloudwatch event bus for ACES Platform.
    event_bus = aws_events.EventBus.from_event_bus_arn(scope, f'{scope.system}-event-bus', configs['event_bus_arn'])

    # cloudwatch logs for batch metrics
    batch_status_log_group = aws_logs.LogGroup.from_log_group_name(scope, f'{scope.system}-loggroup-batch-status',
        log_group_name=f'/aws/events/{scope.system}-batch-status'
    )
    rule = aws_events.Rule(
        scope, f'{scope.system}-event-batch-status',
        event_pattern=aws_events.EventPattern(
            source=['aws.batch'],
            detail_type=['Batch Job State Change'],
            detail={'jobQueue': [batch_job_queue.job_queue_arn]}
        )
    )
    rule.add_target(aws_events_targets.CloudWatchLogGroup(batch_status_log_group))

    failed_job_rule = aws_events.Rule(
        scope, f'{scope.system}-event-batch-failed-job',
        event_pattern=aws_events.EventPattern(
            source=['aws.batch'],
            detail_type=['Batch Job State Change'],
            detail={
                'status': ['FAILED'],
                'jobQueue': [batch_job_queue.job_queue_arn]
            }
        )
    )
    failed_job_rule.add_target(aws_events_targets.EventBus(event_bus))

    longtime_batch_status_log_group = aws_logs.LogGroup.from_log_group_name(scope, f'{scope.system}-loggroup-longtime-batch-status',
        log_group_name=f'/aws/events/{scope.system}-longtime-batch-status'
    )
    longtime_batch_rule = aws_events.Rule(
        scope, f'{scope.system}-event-longtime-batch-status',
        event_pattern=aws_events.EventPattern(
            source=['aws.batch'],
            detail_type=['Batch Job State Change'],
            detail={'jobQueue': [longtime_batch_job_queue.job_queue_arn]}
        )
    )
    longtime_batch_rule.add_target(aws_events_targets.CloudWatchLogGroup(longtime_batch_status_log_group))

    longtime_batch_failed_job_rule = aws_events.Rule(
        scope, f'{scope.system}-event-longtime-batch-failed-job',
        event_pattern=aws_events.EventPattern(
            source=['aws.batch'],
            detail_type=['Batch Job State Change'],
            detail={
                'status': ['FAILED'],
                'jobQueue': [longtime_batch_job_queue.job_queue_arn]
            }
        )
    )
    longtime_batch_failed_job_rule.add_target(aws_events_targets.EventBus(event_bus))

    job_definition_arn = batch_job_definition.ref

    aws_ssm.StringParameter(scope, f'{scope.system}-job-definition-arn',
        parameter_name=configs['SSM_PARAMETER_BATCH_JOB_DEFINITION'],
        string_value=job_definition_arn,
        description=f'{scope.env} {scope.Project} batch_job_definition'
    )

    return batch_job_queue.job_queue_arn, longtime_batch_job_queue.job_queue_arn, job_definition_arn
