from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_s3 as s3,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class S3PdfConverterPipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        architecture: str,
        code_connection_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket for pipeline artifacts
        artifacts_bucket = s3.Bucket(
            self,
            "PipelineArtifactsBucket",
            bucket_name=f"s3pdfconverter-pipeline-artifacts-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            lifecycle_rules=[
                # Clean up after 1 day
                s3.LifecycleRule(
                    id="DeleteCurrentVersions",
                    enabled=True,
                    expiration=Duration.days(1),  # Adjust based on your needs (1-90 days)
                    noncurrent_version_expiration=Duration.days(1),
                    abort_incomplete_multipart_upload_after=Duration.days(1)
                )
            ]
        )

        # Create CodeBuild Role for CDK deployment
        cdk_deploy_role = iam.Role(
            self,
            "CDKDeployRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("PowerUserAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("IAMFullAccess"),
            ],
        )

        # CodeBuild project
        build_project = codebuild.Project(
            self,
            "DeployProject",
            project_name="S3PdfConverter-Lambda-Image-Deploy",
            description="Create Docker Image and Lambda Function",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM_3
                if architecture == "ARM64"
                else codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.SMALL,
                environment_variables={
                    "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(
                        value=self.region
                    ),
                    "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(
                        value=self.account
                    ),
                },
            ),
            role=cdk_deploy_role,
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "install": {
                            "runtime-versions": {
                                "python": "latest",
                                "nodejs": "latest",
                            },
                            "commands": [
                                "npm install -g aws-cdk",
                                "pip install -r requirements.txt",
                            ],
                        },
                        "build": {
                            "commands": ["cdk synth --no-staging -c lambdastack=true"]
                        },
                        "post_build": {
                            "commands": [
                                "cdk deploy --all -c lambdastack=true --outputs-file outputs.json && ./test.sh outputs.json"
                            ]
                        }
                    }
                }
            ),
            timeout=Duration.minutes(10),
        )

        # Create the CodePipeline
        pipeline = codepipeline.Pipeline(
            self,
            "S3PdfConverterPipeline",
            pipeline_name="s3pdfconverter-pipeline",
            artifact_bucket=artifacts_bucket,
        )

        # Define artifacts
        source_output = codepipeline.Artifact("SourceOutput")
        build_output = codepipeline.Artifact("BuildOutput")

        # Source Stage - S3 Bucket
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                codepipeline_actions.CodeStarConnectionsSourceAction(
                    action_name="GithubSource",
                    output=source_output,
                    owner="ronfoerster",
                    repo="s3-pdf-converter",
                    branch="main",
                    connection_arn=code_connection_arn,
                )
            ],
        )

        # Build Stage - Build Docker Image and Deploy Lambda
        pipeline.add_stage(
            stage_name="BuildDockerImage",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="BuildImage",
                    project=build_project,
                    input=source_output,
                    outputs=[build_output],
                )
            ],
        )

        # Outputs
        CfnOutput(
            self,
            "PipelineName",
            value=pipeline.pipeline_name,
            description="Name of the CodePipeline",
        )

        CfnOutput(
            self,
            "ArtifactsBucketName",
            value=artifacts_bucket.bucket_name,
            description="S3 bucket for pipeline artifacts",
        )
