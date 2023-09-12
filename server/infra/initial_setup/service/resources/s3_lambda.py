#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aws_cdk import aws_iam, aws_lambda, aws_s3, aws_ssm, core, custom_resources


def create_s3_trigger(scope: core.Construct, configs: object) -> None:

    shared_services_account_id = configs['shared_services_account_id']

    # S3
    batch_trigger_s3_bucket_name = configs['batch_trigger_s3_bucket']
    batch_trigger_s3_bucket = aws_s3.Bucket.from_bucket_name(
        scope,
        f'{scope.system}-s3',
        bucket_name=batch_trigger_s3_bucket_name
    )

    # batch_trigger_s3_bucket = aws_s3.Bucket(
    #     scope, batch_trigger_s3_bucket_name,
    #     bucket_name=batch_trigger_s3_bucket_name,
    #     encryption=aws_s3.BucketEncryption.S3_MANAGED,
    #     cors=[
    #         aws_s3.CorsRule(
    #             allowed_headers=['*'],
    #             allowed_methods=[aws_s3.HttpMethods.PUT, aws_s3.HttpMethods.POST, aws_s3.HttpMethods.GET, aws_s3.HttpMethods.DELETE],
    #             allowed_origins=['*'],
    #         )
    #     ],
    # )

    # IAM role and S3 Bucket policy for cross account (ACES Platform shared service)
    if shared_services_account_id != scope.account:
        bucket_policy = aws_iam.PolicyStatement(
            actions=['s3:PutObject'],
            principals=[
                aws_iam.AccountPrincipal(shared_services_account_id)
            ],
            resources=[
                f'arn:aws:s3:::{batch_trigger_s3_bucket_name}/*'
            ],
            # https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html
            conditions={
                'StringEquals': {
                    's3:x-amz-acl': 'bucket-owner-full-control'
                }
            }
        )
        batch_trigger_s3_bucket.add_to_resource_policy(bucket_policy)

    # lambda
    common_lambda_params = dict(
        runtime=aws_lambda.Runtime.PYTHON_3_8,
        handler='lambda_function.lambda_handler',
        timeout=core.Duration.seconds(10),
        memory_size=128,
        environment={
            'BATCH_JOB_PREFIX': f'{scope.system}',
            'BATCH_JOB_QUEUE': configs['BATCH_LONGTIME_JOB_QUEUE'],
            'SSM_PARAMETER_BATCH_JOB_DEFINITION': configs['SSM_PARAMETER_BATCH_JOB_DEFINITION'],
        }
    )
    lambda_ = aws_lambda.Function(
        scope,
        f'{scope.system}-s3-algorithm-batch-trigger',
        function_name=f'{scope.short_system}-algorithm-batch-trigger',
        code=aws_lambda.Code.asset('service/lambda'),
        **common_lambda_params,
    )

    lambda_.add_permission(
        f'{scope.system}-s3-trigger-lambda-s3-invoke-function',
        principal=aws_iam.ServicePrincipal('s3.amazonaws.com'),
        action='lambda:InvokeFunction',
        source_arn=batch_trigger_s3_bucket.bucket_arn)

    custom_s3_resource = custom_resources.AwsCustomResource(
        scope,
        f'{scope.system}-s3-incoming-documents-notification-resource',
        policy=custom_resources.AwsCustomResourcePolicy.from_statements([
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                resources=['*'],
                actions=['s3:PutBucketNotification']
            )
        ]),
        on_create=custom_resources.AwsSdkCall(
            service='S3',
            action='putBucketNotificationConfiguration',
            parameters={
                'Bucket': batch_trigger_s3_bucket.bucket_name,
                'NotificationConfiguration': {
                    'LambdaFunctionConfigurations': [
                        {
                            'Events': ['s3:ObjectCreated:*'],
                            'LambdaFunctionArn': lambda_.function_arn,
                            'Filter': {
                                'Key': {
                                    'FilterRules': [
                                        {'Name': 'prefix', 'Value': 'uploads/raw/'}]
                                }
                            }
                        }
                    ]
                }
            },
            physical_resource_id=custom_resources.PhysicalResourceId.of(
                f'{scope.system}-s3-notification-resource'),
            region=scope.region
        ))

    custom_s3_resource.node.add_dependency(
        lambda_.permissions_node.find_child(
            f'{scope.system}-s3-trigger-lambda-s3-invoke-function'))

    lambda_.add_to_role_policy(aws_iam.PolicyStatement(
        resources=[
            f'arn:aws:batch:{scope.region}:{scope.account}:job-definition/*',
            f'arn:aws:batch:{scope.region}:{scope.account}:job-queue/*'
        ],
        actions=[
            'batch:SubmitJob',
        ]
    ))
    lambda_.add_to_role_policy(aws_iam.PolicyStatement(
        resources=['*'],
        actions=['ssm:DescribeParameters', 'ssm:GetParameter', 'ssm:GetParameters']
    ))

    # lambdaの権限
    batch_trigger_s3_bucket.grant_read(lambda_)
