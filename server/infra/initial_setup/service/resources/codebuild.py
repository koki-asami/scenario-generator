#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aws_cdk import aws_codebuild, aws_ec2, aws_iam, aws_ssm, core


def create_codebuild(scope: core.Construct, configs: object, vpc):

    security_group_id = aws_ssm.StringParameter.value_from_lookup(scope, f'/{scope.env}/{scope.Project}/sagemaker-sg-id')
    role_arn = aws_ssm.StringParameter.value_for_string_parameter(scope, f'/{scope.env}/{scope.Project}/cross_account_service_role_arn')
    subnet_type = aws_ec2.SubnetType.PRIVATE
    # subnet_type = aws_ec2.SubnetType.ISOLATED

    build_project = aws_codebuild.Project(
        scope, f'{scope.system}-register-service',
        description=f'Register {scope.system} algorithm to ACES Platform service discovery',
        project_name=f'{scope.system}-register-service',
        # build_spec=aws_codebuild.BuildSpec.from_source_filename(configs['regsiter_service_buildspec_path']),
        build_spec=aws_codebuild.BuildSpec.from_object({
            "version": "0.2",
            "phases": {
                "install": {
                    "runtime-versions": {
                        "python": 3.8
                    },
                    "commands": [
                        "pip install --upgrade pip awscli",
                        "curl -sSL https://install.python-poetry.org | python3 -",
                        "export PATH=$PATH:$HOME/.local/bin"
                    ]
                },
                "build": {
                    "commands": [
                        "cd server/infra/deploy/",
                        "poetry install --no-root",
                        "poetry run python register.py"
                    ]
                }
            }
        }),
        environment=aws_codebuild.BuildEnvironment(
            build_image=aws_codebuild.LinuxBuildImage.STANDARD_5_0,
            environment_variables={
                'Env': aws_codebuild.BuildEnvironmentVariable(
                    value=scope.env,
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                'Project': aws_codebuild.BuildEnvironmentVariable(
                    value=scope.Project,
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                'ACCOUNT_ID': aws_codebuild.BuildEnvironmentVariable(
                    value=scope.account,
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                'ROLE_ARN': aws_codebuild.BuildEnvironmentVariable(
                    value=role_arn,
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                'S3_BUCKET_NAME': aws_codebuild.BuildEnvironmentVariable(
                    value=scope.system,
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                'LONGTIME_BATCH_S3_BUCKET_NAME': aws_codebuild.BuildEnvironmentVariable(
                    value=configs['batch_trigger_s3_bucket'],
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                'JOB_QUEUE': aws_codebuild.BuildEnvironmentVariable(
                    value=configs['BATCH_JOB_QUEUE'],
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
                'JOB_DEFINITION': aws_codebuild.BuildEnvironmentVariable(
                    value=configs['BATCH_JOB_DEFINITION'],
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT),
            }
        ),
        vpc=vpc,
        subnet_selection=aws_ec2.SubnetSelection(subnet_type=subnet_type, one_per_az=True),
        security_groups=[aws_ec2.SecurityGroup.from_security_group_id(scope, f"{scope.system}-codebuild-sg", security_group_id)],
    )
    build_project.add_to_role_policy(aws_iam.PolicyStatement(
        resources= [f"arn:aws:ecr:*:*:repository/{scope.env}-{scope.system}"],
        actions= [
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:GetRepositoryPolicy",
            "ecr:DescribeRepositories",
            "ecr:ListImages",
            "ecr:DescribeImages",
            "ecr:BatchGetImage",
            "ecr:GetLifecyclePolicy",
            "ecr:GetLifecyclePolicyPreview",
            "ecr:ListTagsForResource",
            "ecr:DescribeImageScanFindings",
            "ecr:InitiateLayerUpload",
            "ecr:UploadLayerPart",
            "ecr:CompleteLayerUpload",
            "ecr:BatchDeleteImage",
            "ecr:PutImage"
        ]
    ))
    # ECR Loginに必要な権限。resourceは絞れないので*で設定
    build_project.add_to_role_policy(aws_iam.PolicyStatement(
        resources= ["*"],
        actions= ['ecr:GetAuthorizationToken']
    ))
