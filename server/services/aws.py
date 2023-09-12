import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

MAX_SNS_MESSAGE = 250000
METRICS_TOPIC_ARN = os.environ.get('METRICS_TOPIC_ARN')
REQUEST_LOG_TOPIC_ARN = os.environ.get('REQUEST_LOG_TOPIC_ARN')

logger = logging.getLogger(__name__)


def send_metrics_to_sns(data):
    if not METRICS_TOPIC_ARN:
        logger.warn('METRICS_TOPIC_ARN not set.')
        return
    message = json.dumps({'default': data.to_json()})
    if len(message) > MAX_SNS_MESSAGE:
        logger.warn(f'skip send metrics. {len(message)=} > {MAX_SNS_MESSAGE}.')
        return
    try:
        sns = boto3.client('sns')
        sns.publish(
            TopicArn=METRICS_TOPIC_ARN,
            Subject='Algorithm Metrics',
            Message=message,
            MessageStructure='json',
        )
    except ClientError:
        logger.warning('SNSへのメトリクスの送信に失敗しました。', exc_info=True)


def send_request_log_to_sns(data):
    if not REQUEST_LOG_TOPIC_ARN:
        logger.warn('METRICS_TOPIC_ARN not set.')
        return
    message = json.dumps({'default': data.to_json()})
    if len(message) > MAX_SNS_MESSAGE:
        logger.warn(f'skip send metrics. {len(message)=} > {MAX_SNS_MESSAGE}.')
        return
    try:
        sns = boto3.client('sns')
        sns.publish(
            TopicArn=REQUEST_LOG_TOPIC_ARN,
            Subject='Algorithm RequestLogs',
            Message=message,
            MessageStructure='json',
        )
    except ClientError as e:
        logger.error(str(e), exc_info=True)
        raise Exception('SNSへのログ送信に失敗しました。')
