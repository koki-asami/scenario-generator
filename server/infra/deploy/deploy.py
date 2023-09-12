import logging
import os
import time

import boto3
import botocore
import yaml
from model import SageMakerModel

SAGEMAKER_ASYNC = 'sagemaker'
AWS_BATCH = 'aws_batch'

Env = os.environ.get('Env')
Project = os.environ.get('Project')
RELEASE_VERSION = os.environ.get('RELEASE_VERSION')
REPOSITORY_URI = os.environ.get('REPOSITORY_URI')

configs = yaml.load(
    open(f'{os.getcwd()}/../configs/{Project}-{Env}-algorithm-server-infra.yml').read(),
    Loader=yaml.SafeLoader,
)
VPC_BASE_PROJECT = configs.get('vpc_base_project', Project)
ECR_DEPLOY_TAG = configs['ECR_DEPLOY_TAG']
MODEL_DATA = f's3://{Project}-{Env}/{configs["SAGEMAKER_WEIGHT_SOURCE_S3KEY"]}'
IMAGE = f'{REPOSITORY_URI}:{ECR_DEPLOY_TAG}'
SAGEMAKER_ROLE = f'{Project}-{Env}-sagemaker'
ACCOUNT_ID = configs['account_id']
SAGEMAKER_ROLE_ARN = f'arn:aws:iam::{ACCOUNT_ID}:role/{SAGEMAKER_ROLE}'
ENDPOINT_NAME = configs.get('SAGEMAKER_ENDPOINT_NAME', f'{Project}-{Env}-{RELEASE_VERSION}')
INSTANCE_TYPE = configs['SAGEMAKER_INSTANCE_TYPE']
ASYNC_COMPONENT_SERVICE = configs.get('ASYNC_COMPONENT_SERVICE', AWS_BATCH)
IS_SERVERLESS = configs.get('SAGEMAKER_SERVERLESS', False)

logger = logging.getLogger(__name__)


def main():
    session = boto3.session.Session(region_name='ap-northeast-1')
    ec2_client = session.client('ec2')

    tags = [
        {
            'Key': 'Project',
            'Value': Project,
        },
        {
            'Key': 'Env',
            'Value': Env,
        },
        {
            'Key': 'Name',
            'Value': f'{Project}-{Env}-sagemaker',
        },
    ]

    env_vars = {
        'Project': Project,
        'Env': Env,
        'DATA_PATH': configs['SAGEMAKER_DATA_PATH'],
        'MEM_PROFILE': configs.get('MEM_PROFILE', '1'),
        'TIME_PROFILE': configs.get('TIME_PROFILE', '1'),
        'GPU_PROFILE': configs.get('GPU_PROFILE', '1'),
        'METRICS_TOPIC_ARN': configs['METRICS_TOPIC_ARN'],
        'REQUEST_LOG_TOPIC_ARN': configs['REQUEST_LOG_TOPIC_ARN'],
    }

    # get subnets
    subnets = ec2_client.describe_subnets(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    f'{VPC_BASE_PROJECT}-{Env}-private-1',
                    f'{VPC_BASE_PROJECT}-{Env}-private-2',
                    f'{VPC_BASE_PROJECT}-{Env}-private-3',
                ],
            },
        ],
    )
    subnet_ids = [sn['SubnetId'] for sn in subnets['Subnets']]

    # get security groups
    security_groups = ec2_client.describe_security_groups(
        Filters=[
            {'Name': 'tag:Name', 'Values': [f'{Project}-{Env}-security-sagemaker']},
        ],
    )
    security_group_ids = [sg['GroupId'] for sg in security_groups['SecurityGroups']]

    # detect SageMaker endpoint already exists or not
    sagemaker_client = session.client('sagemaker')
    update_endpoint = True
    try:
        sagemaker_client.describe_endpoint(EndpointName=ENDPOINT_NAME)
    except botocore.exceptions.ClientError as e:
        if 'Could not find endpoint' in e.response['Error']['Message']:
            update_endpoint = False
            response = sagemaker_client.list_endpoint_configs(NameContains=ENDPOINT_NAME)
            if response['EndpointConfigs']:
                sagemaker_client.delete_endpoint_config(
                    EndpointConfigName=response['EndpointConfigs'][0]['EndpointConfigName']
                )
        else:
            logger.error(str(e), exc_info=True)
            raise e

    # create endpoint
    if IS_SERVERLESS or ASYNC_COMPONENT_SERVICE == SAGEMAKER_ASYNC:
        model_name = f'{ENDPOINT_NAME}-srvless' if IS_SERVERLESS else f'{ENDPOINT_NAME}-async'
        try:
            sagemaker_client.delete_model(ModelName=model_name)
        except botocore.exceptions.ClientError:
            pass
        sagemaker_client.create_model(
            ModelName=model_name,
            Containers=[
                {
                    "Image": IMAGE,
                    "Mode": "SingleModel",
                    "ModelDataUrl": MODEL_DATA,
                    "Environment": env_vars,
                }
            ],
            VpcConfig={
                'Subnets': subnet_ids,
                'SecurityGroupIds': security_group_ids,
            },
            ExecutionRoleArn=SAGEMAKER_ROLE_ARN,
        )
        try:
            response = sagemaker_client.list_endpoint_configs(NameContains=ENDPOINT_NAME)
            if response['EndpointConfigs']:
                sagemaker_client.delete_endpoint_config(
                    EndpointConfigName=response['EndpointConfigs'][0]['EndpointConfigName']
                )
        except botocore.exceptions.ClientError:
            pass
        if IS_SERVERLESS:
            response = sagemaker_client.create_endpoint_config(
                EndpointConfigName=model_name,
                ProductionVariants=[
                    {
                        "ModelName": model_name,
                        "VariantName": "AllTraffic",
                        "ServerlessConfig": {
                            "MemorySizeInMB": configs['SAGEMAKER_SERVERLESS_MAX_MB'],
                            "MaxConcurrency": configs['SAGEMAKER_MAX_CONCURRENCY'],
                        },
                    },
                ],
            )
        else:
            response = sagemaker_client.create_endpoint_config(
                EndpointConfigName=model_name,
                ProductionVariants=[
                    {
                        "ModelName": model_name,
                        "VariantName": "AllTraffic",
                        "InstanceType": INSTANCE_TYPE,
                        "InitialInstanceCount": configs['SAGEMAKER_INITIAL_INSTANCE_COUNT'],
                    }
                ],
                AsyncInferenceConfig={
                    "OutputConfig": {
                        "S3OutputPath": f"s3://{Project}-{Env}/sagemaker/output",
                        # Optionally specify Amazon SNS topics
                        # "NotificationConfig": {
                        # "SuccessTopic": "arn:aws:sns:::",
                        # "ErrorTopic": "arn:aws:sns:::",
                        # }
                    },
                    "ClientConfig": {
                        "MaxConcurrentInvocationsPerInstance": configs['SAGEMAKER_MAX_CONCURRENCY'],
                    },
                },
            )
        # deploy model & endpoint
        try:
            sagemaker_client.delete_endpoint(EndpointName=ENDPOINT_NAME)
            time.sleep(3)
        except botocore.exceptions.ClientError:
            pass
        sagemaker_client.create_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=model_name,
        )
    else:
        model_name = ENDPOINT_NAME
        try:
            # delete model firstly. (for private env)
            sagemaker_client.delete_model(ModelName=model_name)
        except botocore.exceptions.ClientError as e:
            pass
        model = SageMakerModel(
            MODEL_DATA,
            IMAGE,
            env=env_vars,
            name=model_name,
            role=SAGEMAKER_ROLE,
            vpc_config={'Subnets': subnet_ids, 'SecurityGroupIds': security_group_ids},
        )
        try:
            model.deploy(
                initial_instance_count=configs['SAGEMAKER_INITIAL_INSTANCE_COUNT'],
                instance_type=INSTANCE_TYPE,
                endpoint_name=ENDPOINT_NAME,
                update_endpoint=update_endpoint,
                tags=tags,
            )
        except botocore.exceptions.ClientError as e:
            if (
                'Cannot update failed endpoint' in e.response['Error']['Message']
                or 'Cannot create already existing endpoint' in e.response['Error']['Message']
            ):
                response = sagemaker_client.list_endpoint_configs(NameContains=ENDPOINT_NAME)
                if response['EndpointConfigs']:
                    sagemaker_client.delete_endpoint_config(
                        EndpointConfigName=response['EndpointConfigs'][0]['EndpointConfigName']
                    )
                sagemaker_client.delete_endpoint(EndpointName=ENDPOINT_NAME)
                model.deploy(
                    instance_type=INSTANCE_TYPE,
                    endpoint_name=ENDPOINT_NAME,
                    update_endpoint=False,
                    tags=tags,
                )
            else:
                raise e


if __name__ == '__main__':
    main()
