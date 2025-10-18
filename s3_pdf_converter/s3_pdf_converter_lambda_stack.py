from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_s3 as _s3,
    aws_s3_notifications,
    aws_sqs as sqs,
    CfnOutput
)
from constructs import Construct

class S3PdfConverterLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, architecture: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        job_success_queue = sqs.Queue(
            self, "JobSuccessQueue",
            queue_name="s3pdfconverter-job-success",
            visibility_timeout=Duration.seconds(30),
            retention_period=Duration.hours(1),
            delivery_delay=Duration.seconds(0),
            receive_message_wait_time=Duration.seconds(10),
            removal_policy=RemovalPolicy.DESTROY,
        )

        lambdafunction = _lambda.DockerImageFunction(
            self,
            "s3trigger_lambda_function",
            code=_lambda.DockerImageCode.from_image_asset(directory="./lambda"),
            timeout=Duration.seconds(300),
            memory_size=256,
            architecture=_lambda.Architecture.ARM_64 if architecture=="ARM64" else _lambda.Architecture.X86_64,
            environment={
                'JOB_SUCCESS_SQS_URL': job_success_queue.queue_url
            }
        )
        lambdafunction.add_alias("Prod")

        job_success_queue.grant_send_messages(lambdafunction)

        self.s3bucket = _s3.Bucket(
            self,
            "documentbucket",
            bucket_name=f"s3pdfconverter-{self.account}-{self.region}-documents",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # create s3 notification for lambda function
        notification = aws_s3_notifications.LambdaDestination(lambdafunction)
        # assign notification for the s3 event type (ex: OBJECT_CREATED)
        self.s3bucket.add_event_notification(
            _s3.EventType.OBJECT_CREATED,
            notification,
            _s3.NotificationKeyFilter(suffix=".odt"),
        )
        # permission for lambda function to read odt file and write the pdf file
        self.s3bucket.grant_read_write(lambdafunction)
        # add lifecycle rule to expire documents after 30 days
        self.s3bucket.add_lifecycle_rule(expiration=Duration.days(30))

        self.documentbucketname = CfnOutput(
            self, "DocumentBucketName",
            value=self.s3bucket.bucket_name,
            description="S3 bucket for documents."
        )

        self.jobsuccesssqsurl = CfnOutput(
            self, "JobSuccessSQSUrl",
            value=job_success_queue.queue_url,
            description="Url of the job success queue."
        )
