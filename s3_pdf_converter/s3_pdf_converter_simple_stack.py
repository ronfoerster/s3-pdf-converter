from aws_cdk import (
    Aspects,
    Duration,
    Stack,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_s3 as _s3,
    aws_s3_notifications,
)
from constructs import Construct
from cdk_nag import AwsSolutionsChecks, NagSuppressions
import os


class S3PdfConverterSimpleStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add CDK Nag
        Aspects.of(self).add(AwsSolutionsChecks())
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {"id": "AwsSolutions-IAM4", "reason": "AWS managed policies."},
                {"id": "AwsSolutions-IAM5", "reason": "Wildcard permissions allowed."},
                {"id": "AwsSolutions-S1", "reason": "Server access logs not relevant."},
                {"id": "AwsSolutions-S10", "reason": "SSL not relevant."},
            ],
        )

        lambdafunction = _lambda.DockerImageFunction(
            self,
            "s3trigger_lambda_function",
            code=_lambda.DockerImageCode.from_image_asset(directory="./lambda"),
            timeout=Duration.seconds(300),
            memory_size=256,
        )
        lambdafunction.add_alias("Prod")

        s3bucket = _s3.Bucket(
            self,
            "documentbucket",
            bucket_name=f"s3pdfconverter-{self.account}-{self.region}-documents",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # create s3 notification for lambda function
        notification = aws_s3_notifications.LambdaDestination(lambdafunction)
        # assign notification for the s3 event type (ex: OBJECT_CREATED)
        s3bucket.add_event_notification(
            _s3.EventType.OBJECT_CREATED,
            notification,
            _s3.NotificationKeyFilter(suffix=".odt"),
        )
        # permission for lambda function to read odt file and write the pdf file
        s3bucket.grant_read_write(lambdafunction)
        # add lifecycle rule to expire documents after 30 days
        s3bucket.add_lifecycle_rule(expiration=Duration.days(30))
