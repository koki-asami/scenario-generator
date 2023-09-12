import boto3

from sagemaker.model import Model
from sagemaker.session import Session


def get_sagemaker_session():
    """Return sagemaker.session.Session created by `aces_platform` profile."""
    boto_session = boto3.Session(region_name='ap-northeast-1')
    sagemaker_session = Session(boto_session)
    return sagemaker_session


class SageMakerModel():
    """A SageMaker ``Model`` that can be deployed to an ``Endpoint``."""

    ROLE = 'SageMakerExcutionRole'
    PREDICTOR_CLS = None
    VPC_CONFIG = None
    SAGEMAKER_SESSION = get_sagemaker_session()
    ENABLE_NETWORK_ISOLATION = False
    INITIAL_INSTANCE_COUNT = 1
    INSTANCE_TYPE = 'local'
    ACCELERATOR_TYPE = None
    UPDATE_ENDPOINT = False
    TAGS = None
    KMS_KEY = None
    WAIT = True

    def __init__(
            self,
            model_data,
            image,
            role=ROLE,
            predictor_cls=PREDICTOR_CLS,
            env=None,
            name=None,
            vpc_config=VPC_CONFIG,
            sagemaker_session=SAGEMAKER_SESSION,
            enable_network_isolation=ENABLE_NETWORK_ISOLATION,
    ):
        """Initialize an SageMaker ``Model``.
        Args:
            model_data (str): The S3 location of a SageMaker model data
                ``.tar.gz`` file.
            image (str): A Docker image URI.
            role (str): An AWS IAM role (either name or full ARN). The Amazon
                SageMaker training jobs and APIs that create Amazon SageMaker
                endpoints use this role to access training data and model
                artifacts. After the endpoint is created, the inference code
                might use the IAM role if it needs to access some AWS resources.
                It can be null if this is being used to create a Model to pass
                to a ``PipelineModel`` which has its own Role field. (default:
                None)
            predictor_cls (callable[string, sagemaker.session.Session]): A
                function to call to create a predictor (default: None). If not
                None, ``deploy`` will return the result of invoking this
                function on the created endpoint name.
            env (dict[str, str]): Environment variables to run with ``image``
                when hosted in SageMaker (default: None).
            name (str): The model name. If None, a default model name will be
                selected on each ``deploy``.
            vpc_config (dict[str, list[str]]): The VpcConfig set on the model
                (default: None)
                * 'Subnets' (list[str]): List of subnet ids.
                * 'SecurityGroupIds' (list[str]): List of security group ids.
            sagemaker_session (sagemaker.session.Session): A SageMaker Session
                object, used for SageMaker interactions (default: None). If not
                specified, one is created using the default AWS configuration
                chain.
            enable_network_isolation (Boolean): Default False. if True, enables
                network isolation in the endpoint, isolating the model
                container. No inbound or outbound network calls can be made to
                or from the model container.
        """
        self.name = name
        self.model = Model(
            model_data=model_data,
            image_uri=image,
            role=role,
            predictor_cls=predictor_cls,
            env=env,
            name=name,
            vpc_config=vpc_config,
            sagemaker_session=sagemaker_session,
            enable_network_isolation=enable_network_isolation
        )

    def deploy(
            self,
            initial_instance_count=INITIAL_INSTANCE_COUNT,
            instance_type=INSTANCE_TYPE,
            accelerator_type=ACCELERATOR_TYPE,
            endpoint_name=None,
            update_endpoint=UPDATE_ENDPOINT,
            tags=TAGS,
            kms_key=KMS_KEY,
            wait=WAIT,
    ):
        """Deploy this ``Model`` to an ``Endpoint`` and optionally return a
        ``Predictor``.
        Create a SageMaker ``Model`` and ``EndpointConfig``, and deploy an
        ``Endpoint`` from this ``Model``. If ``self.predictor_cls`` is not None,
        this method returns a the result of invoking ``self.predictor_cls`` on
        the created endpoint name.
        The name of the created model is accessible in the ``name`` field of
        this ``Model`` after deploy returns
        The name of the created endpoint is accessible in the
        ``endpoint_name`` field of this ``Model`` after deploy returns.
        Args:
            initial_instance_count (int): The initial number of instances to run
                in the ``Endpoint`` created from this ``Model``.
            instance_type (str): The EC2 instance type to deploy this Model to.
                For example, 'ml.p2.xlarge'.
            accelerator_type (str): Type of Elastic Inference accelerator to
                deploy this model for model loading and inference, for example,
                'ml.eia1.medium'. If not specified, no Elastic Inference
                accelerator will be attached to the endpoint. For more
                information:
                https://docs.aws.amazon.com/sagemaker/latest/dg/ei.html
            endpoint_name (str): The name of the endpoint to create (default:
                None). If not specified, a unique endpoint name will be created.
            update_endpoint (bool): Flag to update the model in an existing
                Amazon SageMaker endpoint. If True, this will deploy a new
                EndpointConfig to an already existing endpoint and delete
                resources corresponding to the previous EndpointConfig. If
                False, a new endpoint will be created. Default: False
            tags (List[dict[str, str]]): The list of tags to attach to this
                specific endpoint.
            kms_key (str): The ARN of the KMS key that is used to encrypt the
                data on the storage volume attached to the instance hosting the
                endpoint.
            wait (bool): Whether the call should wait until the deployment of
                this model completes (default: True).
        Returns:
            callable[string, sagemaker.session.Session] or None: Invocation of
                ``self.predictor_cls`` on the created endpoint name, if ``self.predictor_cls``
                is not None. Otherwise, return None.
        """
        if endpoint_name is None:
            endpoint_name = self.name

        return self.model.deploy(
            initial_instance_count=initial_instance_count,
            instance_type=instance_type,
            accelerator_type=accelerator_type,
            endpoint_name=endpoint_name,
            update_endpoint=update_endpoint,
            tags=tags,
            kms_key=kms_key,
            wait=wait,
        )
