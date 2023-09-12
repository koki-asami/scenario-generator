ROOT=$(cd $(dirname $0); cd ../; pwd)

TASK=$1
PROJECT=$2
ALGORITHM=$3
BUCKET=$PROJECT_AWS_BUCKET

echo "create directory for {algorithm}..."
mkdir -p /root/datadrive/${TASK}/${PROJECT}/dataset/cfg
mkdir -p /root/datadrive/${TASK}/${PROJECT}/models/${ALGORITHM}/cfg
mkdir -p /root/datadrive/${TASK}/${PROJECT}/models/${ALGORITHM}/weights

echo "download cfg, and weights to execute ${algorithm}..."
aws s3 cp s3://${BUCKET}/root/datadrive/${TASK}/${PROJECT}/dataset /root/datadrive/${TASK}/${PROJECT}/dataset --recursive
# aws s3 cp s3://${BUCKET}/root/datadrive/${TASK}/${PROJECT}/models/${ALGORITHM}/weights/${ALGORITHM}_last.weights /root/datadrive/${TASK}/${PROJECT}/models/${ALGORITHM}/weights/${ALGORITHM}_last.weights
# aws s3 cp s3://${BUCKET}/root/datadrive/${TASK}/${PROJECT}/models/${ALGORITHM}/cfg/${ALGORITHM}.cfg /root/datadrive/${TASK}/${PROJECT}/models/${ALGORITHM}/cfg/${ALGORITHM}.cfg
