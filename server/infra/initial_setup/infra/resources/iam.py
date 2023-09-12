#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aws_cdk import aws_autoscaling, aws_ec2, aws_iam, aws_ssm, core

user_data = """MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="==MYBOUNDARY=="

--==MYBOUNDARY==
Content-Type: text/x-shellscript; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

#!/bin/bash
echo 'ECS_IMAGE_PULL_BEHAVIOR=once' >> /etc/ecs/ecs.config
echo 'ECS_ENGINE_TASK_CLEANUP_WAIT_DURATION=180m' >> /etc/ecs/ecs.config
echo 'ECS_IMAGE_CLEANUP_INTERVAL=30m' >> /etc/ecs/ecs.config
echo 'ECS_IMAGE_MINIMUM_CLEANUP_AGE=60m' >> /etc/ecs/ecs.config
curl https://s3.us-east-2.amazonaws.com/aws-xray-assets.us-east-2/xray-daemon/aws-xray-daemon-3.x.rpm -o /home/ec2-user/xray.rpm
yum install -y /home/ec2-user/xray.rpm

--==MYBOUNDARY==--\
"""


def create_iam(scope: core.Construct, configs: object):
    batch_trigger_s3_bucket_name = configs['batch_trigger_s3_bucket']

    task_policy = aws_iam.Policy(
        scope, f'{scope.system}-task',
        policy_name=f'{scope.system}-task',
        statements=[
            aws_iam.PolicyStatement(
                actions=[
                    "s3:Get*",
                    "s3:List*",
                    "s3:PutObject"
                ],
                resources=[
                    f"arn:aws:s3:::{scope.system}/*",
                    f"arn:aws:s3:::{scope.system}",
                    f"arn:aws:s3:::{batch_trigger_s3_bucket_name}/*",
                    f"arn:aws:s3:::{batch_trigger_s3_bucket_name}",
                    f'arn:aws:s3:::aces-vision*',
                ],
                effect=aws_iam.Effect.ALLOW
            ),
            aws_iam.PolicyStatement(
                actions= [
                    'batch:SubmitJob',
                ],
                resources= [
                    f'arn:aws:batch:{scope.region}:{scope.account}:job-definition/*',
                    f'arn:aws:batch:{scope.region}:{scope.account}:job-queue/*',
                ],
            ),
            aws_iam.PolicyStatement(
                actions= [
                    'sagemaker:InvokeEndpoint'
                ],
                resources= [
                    f'arn:aws:sagemaker:{scope.region}:{scope.account}:endpoint/*',
                ],
                effect=aws_iam.Effect.ALLOW
            ),
            aws_iam.PolicyStatement(
                actions= [
                    'SNS:Publish',
                ],
                resources= [
                    f'arn:aws:sns:{scope.region}:*:*',
                ],
            ),
            aws_iam.PolicyStatement(
                actions=[
                    "iam:CreateRole"
                ],
                resources=['*'],
                effect=aws_iam.Effect.ALLOW
            ),
            aws_iam.PolicyStatement(
                actions=[
                    "iam:AttachRolePolicy",
                    "iam:GetRole",
                    "iam:GetRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:TagRole",
                    "iam:UntagRole",
                    "sts:AssumeRole"
                ],
                resources=[
                    f"arn:aws:iam::*:role/{scope.system}*",
                    f"arn:aws:iam::*:policy/{scope.system}*"
                ],
                effect=aws_iam.Effect.ALLOW
            ),
            aws_iam.PolicyStatement(
                actions= [
                    'ssm:DescribeParameters'
                ],
                resources= [
                    '*'
                ],
                effect=aws_iam.Effect.ALLOW
            ),
            aws_iam.PolicyStatement(
                actions= [
                    "ssm:GetParameter",
                    "ssm:GetParameters"
                ],
                resources= [
                    '*',
                ],
                effect=aws_iam.Effect.ALLOW
            ),
        ]
    )

    cross_account_service_role = aws_iam.Role(
        scope, f'{scope.system}-service-ext-role',
        role_name=f'{scope.system}-service-ext-role',
        path='/',
        inline_policies={
            f'{scope.system}-external-service-role': aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        actions= [
                            "s3:Get*",
                            "s3:List*",
                            's3:PutObject',
                        ],
                        resources= [
                            f'arn:aws:s3:::{scope.system}/*',
                            f'arn:aws:s3:::{scope.system}',
                            f'arn:aws:s3:::{batch_trigger_s3_bucket_name}/*',
                            f'arn:aws:s3:::{batch_trigger_s3_bucket_name}',
                        ],
                    ),
                    aws_iam.PolicyStatement(
                        actions= [
                            'batch:SubmitJob',
                        ],
                        resources= [
                            f'arn:aws:batch:{scope.region}:{scope.account}:job-definition/*',
                            f'arn:aws:batch:{scope.region}:{scope.account}:job-queue/*'
                        ],
                    ),
                    aws_iam.PolicyStatement(
                        actions= [
                            'sagemaker:InvokeEndpoint*'
                        ],
                        resources= [
                            f'arn:aws:sagemaker:{scope.region}:{scope.account}:endpoint/*'
                        ]
                    ),
                ]
            )
        },
        assumed_by=aws_iam.AccountPrincipal(configs['shared_services_account_id'])
    )

    # task role
    task_role = aws_iam.Role(
        scope,
        id=f"{scope.system}-job-role",
        role_name=f"{scope.system}-job-role",
        assumed_by=aws_iam.ServicePrincipal("ecs-tasks.amazonaws.com")
    )

    task_role.attach_inline_policy(task_policy)

    task_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            id=f"{scope.system}-AmazonECSTaskExecutionRolePolicy",
            managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
        )
    )

    task_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            id=f"{scope.system}-AmazonS3FullAccess",
            managed_policy_arn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
        )
    )

    task_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            id=f"{scope.system}-CloudWatchLogsFullAccess",
            managed_policy_arn="arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
        )
    )

    task_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSXrayWriteOnlyAccess"))

    # sagemaker role
    sagemaker_role = aws_iam.Role(
        scope,
        id=f"{scope.system}-sagemaker",
        role_name=f"{scope.system}-sagemaker",
        assumed_by=aws_iam.ServicePrincipal("sagemaker.amazonaws.com")
    )

    sagemaker_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            id=f"{scope.system}-sagemaker-AmazonS3FullAccess",
            managed_policy_arn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
        )
    )

    sagemaker_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            id=f"{scope.system}-sagemaker-CloudWatchLogsFullAccess",
            managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
        )
    )


    # Instance Profile & Launch Template
    #  現状CDK(CloudFormation)では、DependsOnでリソース構築時に順序関係をLaunchTemplateに関係づけられず、
    #  AWS Batch構築時にLaunchTemplateが構築に間に合わずエラーになるのでこれらのリソースだけnetwork側であらかじめ作成しています
    ecs_instance_role = aws_iam.Role(
        scope,
        id=f"{scope.system}-ecs-instance-role",
        assumed_by=aws_iam.ServicePrincipal("ec2.amazonaws.com"),
        managed_policies=[
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            ),
            aws_iam.ManagedPolicy.from_managed_policy_arn(
                scope,
                id=f"{scope.system}-ecs-instance-role-AmazonEC2ContainerServiceforEC2Role",
                managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
            ),
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "AWSXrayWriteOnlyAccess"
            )
        ]
    )

    # aws_launch_template = aws_ec2.CfnLaunchTemplate(
    #     scope=scope,
    #     id=f'{scope.system}-batch-template',
    #     launch_template_name=f'{scope.system}-batch-template',
    #     launch_template_data=aws_ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
    #         user_data=core.Fn.base64(user_data)
    #     ),
    # )
    setup_commands = aws_ec2.UserData.for_linux()
    setup_commands.add_commands("echo 'ECS_IMAGE_PULL_BEHAVIOR=once' >> /etc/ecs/ecs.config")
    setup_commands.add_commands("curl https://s3.us-east-2.amazonaws.com/aws-xray-assets.us-east-2/xray-daemon/aws-xray-daemon-3.x.rpm -o /home/ec2-user/xray.rpm")
    setup_commands.add_commands("yum install -y /home/ec2-user/xray.rpm")
    multipart_user_data = aws_ec2.MultipartUserData()
    # The docker has to be configured at early stage, so content type is overridden to boothook
    multipart_user_data.add_part(aws_ec2.MultipartBody.from_user_data(setup_commands, "text/x-shellscript; charset='us-ascii'"))
    aws_launch_template = aws_ec2.LaunchTemplate(
        scope,
        id=f"{scope.system}-batch-launch-template",
        launch_template_name=f"{scope.system}-batch-launch-template",
        user_data=multipart_user_data,
        # launch_template_data=aws_ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
        #     user_data=core.Fn.base64(user_data)
        # ),
        block_devices=[aws_ec2.BlockDevice(
            device_name="/dev/xvda",
            volume=aws_ec2.BlockDeviceVolume.ebs(
                volume_size=100,
                volume_type=aws_ec2.EbsDeviceVolumeType.GP2,
                delete_on_termination=True,
                encrypted=False,
            )
        )],
        ebs_optimized=True,
        role=ecs_instance_role,
        instance_initiated_shutdown_behavior=aws_ec2.InstanceInitiatedShutdownBehavior.TERMINATE,
    )

    ecs_instance_profile = aws_iam.CfnInstanceProfile(
        scope,
        id=f"{scope.system}-ecs-instance-profile",
        instance_profile_name=f"{scope.system}-ecs-instance-profile",
        roles=[ecs_instance_role.role_name]
    )

    batch_role = aws_iam.Role(
        scope=scope,
        id=f"{scope.system}-aws-batch-service",
        role_name=f"{scope.system}-aws-batch-service",
        assumed_by=aws_iam.ServicePrincipal("batch.amazonaws.com")
    )

    batch_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope=scope,
            id=f"{scope.system}-AWSBatchServiceRole",
            managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
        )
    )

    # batch_role.add_to_policy(
    #     aws_iam.PolicyStatement(
    #         effect=aws_iam.Effect.ALLOW,
    #         resources=[
    #             "arn:aws:logs:*:*:*"
    #         ],
    #         actions=[
    #             "logs:CreateLogGroup",
    #             "logs:CreateLogStream",
    #             "logs:PutLogEvents",
    #             "logs:DescribeLogStreams"
    #         ]
    #     )
    # )

    # IAM Role for Cloud9
    cloud9_role = aws_iam.Role(
        scope, f'{scope.system}-cloud9-role',
        role_name=f'{scope.system}-cloud9-role',
        path='/',
        inline_policies={
            f'{scope.system}-cloud9-policy': aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        actions=[
                            "iam:AttachRolePolicy",
                            "iam:GetRole",
                            "iam:GetRolePolicy",
                            "iam:PutRolePolicy",
                            "iam:TagRole",
                            "iam:UntagRole",
                            "sts:AssumeRole"
                        ],
                        resources=[
                            f"arn:aws:iam::*:role/{scope.system}*",
                            f"arn:aws:iam::*:policy/{scope.system}*"
                        ],
                        effect=aws_iam.Effect.ALLOW),
                    aws_iam.PolicyStatement(
                        actions=[
                            "iam:CreateRole"
                        ],
                        resources=['*'],
                        effect=aws_iam.Effect.ALLOW),
                ]
            )
        },
        assumed_by=aws_iam.CompositePrincipal(
            aws_iam.ServicePrincipal('cloud9.amazonaws.com'),
            aws_iam.ServicePrincipal('ec2.amazonaws.com')
        ),
    )

    cloud9_role.attach_inline_policy(task_policy)

    cloud9_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            id=f"{scope.system}-cloud9-AmazonEC2RoleforSSM",
            managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
        )
    )

    cloud9_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))

    cloud9_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            id=f"{scope.system}-cloud9-AmazonEC2ContainerServiceforEC2Role",
            managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
        )
    )

    cloud9_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("PowerUserAccess"))

    cloud9_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSCloud9SSMInstanceProfile"))

    cloud9_instance_profile = aws_iam.CfnInstanceProfile(
        scope,
        id=f"{scope.system}-cloud9-profile",
        instance_profile_name=f"{scope.system}-cloud9-profile",
        roles=[cloud9_role.role_name]
    )

    # github actions IAM Role
    if 'open_id_connect_provider_arn' in configs:
        aws_iam_openid_connect_provider = aws_iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            scope,
            id=f"{scope.system}-github-actions-oidc-provider",
            open_id_connect_provider_arn=configs['open_id_connect_provider_arn']
        )
    else:
        aws_iam_openid_connect_provider = aws_iam.OpenIdConnectProvider(
            scope,
            id=f"{scope.system}-github-actions-oidc-provider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sigstore", "sts.amazonaws.com"],
            thumbprints=["a031c46782e6e6c662c2c87c76da9aa62ccabd8e", "6938fd4d98bab03faadb97b34396831e3780aea1"],
        )

    github_actions_role = aws_iam.Role(
        scope,
        id=f"{scope.system}-github-actions-role",
        role_name=f"{scope.short_system}-github-actions-role",
        assumed_by=aws_iam.FederatedPrincipal(
            federated=aws_iam_openid_connect_provider.open_id_connect_provider_arn,
            conditions={
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": f'repo:{configs["github_owner"]}/{configs["github_repo"]}:*'
                }
            },
            assume_role_action="sts:AssumeRoleWithWebIdentity"
        )
    )

    github_actions_role.attach_inline_policy(
        aws_iam.Policy(
            scope, f'{scope.system}-github-actions-policy',
            policy_name=f'{scope.system}-github-actions-policy',
            statements=[
                aws_iam.PolicyStatement(
                    actions=[
                        "sts:TagSession"
                    ],
                    resources=[
                        github_actions_role.role_arn
                    ]
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "s3:ListAllMyBuckets",
                        "s3:GetBucketLocation"
                    ],
                    resources=[
                        "arn:aws:s3:::*"
                    ]
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "s3:*",
                    ],
                    resources=[
                        f"arn:aws:s3:::{scope.system}/*",
                        f"arn:aws:s3:::{scope.system}",
                    ]
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "ecr:GetAuthorizationToken",
                        "ecr:GetManifest"
                    ],
                    resources=[
                        "*"
                    ]
                ),
                aws_iam.PolicyStatement(
                    actions=[
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
                    ],
                    resources=[
                        "arn:aws:ecr:*:*:repository/*"
                    ]
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "autoscaling:SetDesiredCapacity"
                    ],
                    resources=[
                        "arn:aws:autoscaling:ap-northeast-1:*:*:autoScalingGroupName/aces-platform-*"
                    ]
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "sts:AssumeRole"
                    ],
                    resources=[
                        f"arn:aws:iam::*:role/{scope.system}-*",
                        f"arn:aws:iam::*:policy/{scope.system}-*"
                    ]
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "codebuild:StartBuild",
                        "codebuild:BatchGetBuilds"
                    ],
                    resources=[
                        f"arn:aws:codebuild:{scope.region}:{scope.account}:project/{scope.system}-*"
                    ]
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "logs:GetLogEvents"
                    ],
                    resources=[
                        f"arn:aws:logs:{scope.region}:{scope.account}:log-group:/aws/codebuild/{scope.system}-*"
                    ]
                )
            ]
        )
    )

    github_actions_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope=scope,
            id=f"{scope.system}-githubactions-AmazonECSFullAccess",
            managed_policy_arn="arn:aws:iam::aws:policy/AmazonECS_FullAccess"
        )
    )

    github_actions_role.add_managed_policy(
        aws_iam.ManagedPolicy.from_managed_policy_arn(
            scope=scope,
            id=f"{scope.system}-githubactions-AmazonSageMakerFullAccess",
            managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
        )
    )

    aws_ssm.StringParameter(scope, f'{scope.system}-task_role_arn',
        parameter_name=f'/{scope.env}/{scope.Project}/task_role_arn',
        string_value=task_role.role_arn,
        description=f'{scope.env} {scope.Project} task_role_arn'
    )

    aws_ssm.StringParameter(scope, f'{scope.system}-cross_account_service_role_arn',
        parameter_name=f'/{scope.env}/{scope.Project}/cross_account_service_role_arn',
        string_value=cross_account_service_role.role_arn,
        description=f'{scope.env} {scope.Project} cross_account_service_role_arn'
    )

    aws_ssm.StringParameter(scope, f'{scope.system}-instance_role_arn',
        parameter_name=f'/{scope.env}/{scope.Project}/instance_role_arn',
        string_value=ecs_instance_profile.attr_arn,
        description=f'{scope.env} {scope.Project} instance_role_arn'
    )

    aws_ssm.StringParameter(scope, f'{scope.system}-batch_service_role_arn',
        parameter_name=f'/{scope.env}/{scope.Project}/batch_service_role_arn',
        string_value=batch_role.role_arn,
        description=f'{scope.env} {scope.Project} batch_service_role_arn'
    )
