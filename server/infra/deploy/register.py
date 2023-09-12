import json
import os

import requests
import yaml

AWS_BATCH = 'aws_batch'
SAGEMAKER_ASYNC = 'sagemaker'
DEPRECATED_SAGEMAKER_SYNC = 'sagemaker_sync'
AWS_ASYNC_COMPONENT_SERVICE_ALL = [SAGEMAKER_ASYNC, DEPRECATED_SAGEMAKER_SYNC, AWS_BATCH]

Env = os.environ.get('Env')
Project = os.environ.get('Project')
RELEASE_VERSION = os.environ.get('RELEASE_VERSION')
ACES_PLATFORM_REGISTER_URL = os.environ.get('ACES_PLATFORM_REGISTER_URL')

configs = yaml.load(
    open(f'{os.getcwd()}/../configs/{Project}-{Env}-algorithm-server-infra.yml').read(),
    Loader=yaml.SafeLoader,
)
ASYNC_COMPONENT_SERVICE = configs.get('ASYNC_COMPONENT_SERVICE', AWS_BATCH)
ENDPOINT_NAME = configs.get('SAGEMAKER_ENDPOINT_NAME', f'{Project}-{Env}-{RELEASE_VERSION}')


def main():
    if ASYNC_COMPONENT_SERVICE not in AWS_ASYNC_COMPONENT_SERVICE_ALL:
        raise Exception(f'{ASYNC_COMPONENT_SERVICE=} invalid')

    with open(f'{os.getcwd()}/../../algorithms/register.json') as f:
        data = json.load(f)
        for i, service in enumerate(data['services']):
            data['services'][i]['sagemaker_endpoint_name'] = ENDPOINT_NAME
            if not data['services'][i].get('async_component_service'):
                data['services'][i]['async_component_service'] = ASYNC_COMPONENT_SERVICE
            data['services'][i]['role_arn'] = os.environ.get('ROLE_ARN')
            data['services'][i]['s3_bucket_name'] = os.environ.get('S3_BUCKET_NAME')
            data['services'][i]['longtime_batch_s3_bucket_name'] = os.environ.get('LONGTIME_BATCH_S3_BUCKET_NAME')
            data['services'][i]['job_queue_arn'] = os.environ.get('JOB_QUEUE')
            data['services'][i]['job_definition_arn'] = os.environ.get('JOB_DEFINITION')
        print(data)
        res = requests.put(
            ACES_PLATFORM_REGISTER_URL, headers={'content-type': 'application/json'}, data=json.dumps(data),
        )
        print(res.text)
        res.raise_for_status()


if __name__ == '__main__':
    main()
