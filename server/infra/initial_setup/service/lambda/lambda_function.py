import os
import re
from logging import DEBUG, INFO, Formatter, getLogger  # NOQA

import boto3

# set up logger
logger = getLogger()
logger.setLevel(INFO)
for h in logger.handlers:
    h.setFormatter(Formatter('[%(levelname)s] %(asctime)s %(message)s'))

ssm = boto3.client('ssm')
s3 = boto3.resource('s3')

BATCH_JOB_PREFIX = os.environ.get('BATCH_JOB_PREFIX')
BATCH_JOB_QUEUE = os.environ.get('BATCH_JOB_QUEUE')
SSM_PARAMETER_BATCH_JOB_DEFINITION = os.environ.get('SSM_PARAMETER_BATCH_JOB_DEFINITION')


def lambda_handler(event, context):

    s3_record = event['Records'][0]['s3']
    s3_bucket = s3_record['bucket']['name']
    s3_key = s3_record['object']['key']
    request_id = s3_key.split('/')[-1]

    if '.json' in request_id:
        # skip
        return {}

    job_definition = ssm.get_parameter(Name=SSM_PARAMETER_BATCH_JOB_DEFINITION)['Parameter']['Value']
    rindex = job_definition.rfind(':')
    if rindex > 0:
        job_definition = job_definition[0:rindex]

    s3_key = re.sub('^uploads/raw', 'uploads/parameter', s3_key, 1)
    s3_key = f'{s3_key}.request.json'
    s3_param_object = s3.Object(s3_bucket, s3_key).get()
    logger.info(f'{request_id} {job_definition} s3://{s3_bucket}/{s3_key}')

    message = s3_param_object['Body'].read().decode('utf-8')
    logger.info(message)

    client = boto3.client('batch')
    client.submit_job(
        jobName=f'{BATCH_JOB_PREFIX}-longtime-batch-job-{request_id}',
        jobQueue=BATCH_JOB_QUEUE,
        jobDefinition=job_definition,
        containerOverrides={
            'command': ['python', 'tasks.py', message]
        },
    )

    return {}
