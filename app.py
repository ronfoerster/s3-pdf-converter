#!/usr/bin/env python3
import os
import subprocess
import aws_cdk as cdk

from s3_pdf_converter.s3_pdf_converter_simple_stack import S3PdfConverterSimpleStack
from s3_pdf_converter.s3_pdf_converter_lambda_stack import S3PdfConverterLambdaStack
from s3_pdf_converter.s3_pdf_converter_pipeline_stack import S3PdfConverterPipelineStack

app = cdk.App()

# call cdk deploy -c local=False

# decide if you want build the docker image local or remote in aws codebuild
try:
     build_local = app.node.get_context("local").lower() in ('true', '1') or False
except Exception as e:
    print(f"Error getting 'local' context: {e}. Defaulting to False.")
    build_local = False


if build_local:
    S3PdfConverterSimpleStack(app, "S3PdfConverterSimpleStack",
        # If you don't specify 'env', this stack will be environment-agnostic.
        # Account/Region-dependent features and context lookups will not work,
        # but a single synthesized template can be deployed anywhere.

        # Uncomment the next line to specialize this stack for the AWS Account
        # and Region that are implied by the current CLI configuration.

        env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

        # Uncomment the next line if you know exactly what Account and Region you
        # want to deploy the stack to. */

        #env=cdk.Environment(account='123456789012', region='us-east-1'),

        # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
        )
else:
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
    architecture = app.node.get_context("architecture") or "AMD64"  # AMD64 or ARM64
    if architecture != "AMD64" or architecture != "ARM64":
         architecture = "AMD64" # default value


    deploy_lambdastack = app.node.get_context("lambdastack").lower() in ('true', '1') or False
    if deploy_lambdastack:
            S3PdfConverterLambdaStack(app, "S3PdfConverterLambdaStack", architecture=architecture, env=env)
    
    else:
        # request codeconnection ARN for github from default aws environment values
        cmd = [
            "aws", "codeconnections", "list-connections",
            "--no-paginate",
            "--provider-type", "GitHub",
            "--query", "Connections[?ConnectionStatus=='AVAILABLE'] | [0].ConnectionArn",
            "--output", "text"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            code_connection_arn = result.stdout.strip()
            if code_connection_arn[:8].lower() != "arn:aws:":
                print("Error: Invalid CodeConnection ARN. Please check your AWS CodeConnections setup.")
                code_connection_arn = ""
            else:
                print(f"Use Codeconnection-ARN {code_connection_arn}")
            
            S3PdfConverterPipelineStack(app, "S3PdfConverterStack", architecture=architecture, code_connection_arn=code_connection_arn, env=env)

        except subprocess.CalledProcessError as e:
            print(f"Error executing aws codeconnections command: {e}")

app.synth()
