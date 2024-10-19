# S3 Bucket PDF-Converter
Using a Lambda function, OpenDocument files (*.odt) are automatically converted into a PDF (*.pdf) when they are uploaded to an S3 bucket.

The Lambda function uses a Docker container in which LibreOffice is installed and which takes over the task of conversion to pdf.

The Docker image was kept very generic so that the PDF converter application can run on both **x86** and **arm64**.

The entire project has been configured in such a minimalistic way that it runs within the limits of the AWS Free Tier (as of 2024) and therefore no additional AWS costs should arise.
## CloudFormation Template - Demo
`Note: Using the templates may incur additional costs in AWS due to the use of the necessary AWS resources.`

Unfortunately Lambda functions supports Docker images only from your **private** ECR and not from public container registries.
Therefore, you can choose betwenn two ways to get the Docker image into your repository:
* mirror the Docker image from my own [**public** ECR repository](https://gallery.ecr.aws/z3l4u6t3/pdfconverter)
or
* you can also [create the Docker image yourself](#build-the-docker-image-on-your-own).
Both are CodeBuild projects you have to run first.
Then you can deploy the CloudFormation template `cf-s3pdfconverter.yml` which creates the necessary resources in AWS:
* S3 Bucket
* Lambda function
### Preparations
The following steps will use the AWS CLI to deploy the Cloudformation templates.
It is mandatory to connect your AWS account to your GitHub account (CodeConnections) to run the CodeBuild projects.
1. Clone this repository
```
git clone https://github.com/ronfoerster/s3-pdf-converter.git && \
cd s3-pdf-converter
```
2. Choose your stackname
```
stackname="s3pdfconverter"
```
You have to choose between the x86 or arm64 architecture because:
`Lambda does not support functions that use multi-architecture container images.`
So if you wish to run your Lambda function in x86, you need to create or mirror the corresponding x86 Docker image.
### Mirror the Docker image (first way)
```
aws cloudformation create-stack --stack-name $stackname-mirrorimage --template-body file://mirror-dockerimage/cf-codebuild-mirrorimage.yml --capabilities CAPABILITY_NAMED_IAM
```
Default deployment is the cost-effective **arm64** architecture, if you want to use **x86** then **add** the parameter:
```
--parameters ParameterKey=Architecture,ParameterValue=x86,UsePreviousValue=true
```
or you want to change the default ECR repository name
```
--parameters ParameterKey=ImageRepository,ParameterValue=s3pdfconverter,UsePreviousValue=true
```
Run the CodeBuild project:
```
aws codebuild start-build --project-name $stackname-mirrorimage
```
### Build the Docker image on your own (second way)
The actual program logic is in the `lambda.py` which is permanently integrated into the Docker image.
Here you can start to adapt the Lambda function to your needs, e.g. to send the PDF by email.
The CodeBuild template `cf-codebuild.yml` is used to create the Docker image and publish it in your **private** ECR repository.
```
aws cloudformation create-stack --stack-name $stackname-buildimage --template-body file://cf-codebuild.yml --capabilities CAPABILITY_NAMED_IAM
```
Default deployment is the cost-effective **arm64** architecture, if you want to use **x86** then **add** the parameter:
```
--parameters ParameterKey=Architecture,ParameterValue=x86,UsePreviousValue=true
```
Run the CodeBuild project:
```
aws codebuild start-build --project-name $stackname-buildimage
```
### Deploy and test the Lambda function
```
aws cloudformation create-stack --stack-name $stackname --template-body file://cf-s3pdfconverter.yml --capabilities CAPABILITY_NAMED_IAM
```
Default deployment is the **arm64** architecture, if you want to use **x86** then **add** the parameter:
```
--parameters ParameterKey=Architecture,ParameterValue=x86,UsePreviousValue=true
```
To [avoid a circular dependency](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-s3-bucket-notificationconfiguration.html) in our template we have to update the stack to add the Notification Configuration to the S3 bucket
```
 aws cloudformation update-stack --stack-name $stackname --template-body file://cf-s3pdfconverter-update.yml --capabilities CAPABILITY_NAMED_IAM
```
If you already used parameters above when creating the stack, add them here as well.

Test the deployment: upload `sample.odt`
```
AWSACCOUNTID=`aws sts get-caller-identity --query "Account" --output text` && AWSREGION=`aws configure list | grep region | awk '{print $2}' && \` 
aws s3 cp sample.odt s3://$stackname-$AWSACCOUNTID-$AWSREGION-document-bucket/
```
After a short time, the `sample.pdf` should be in the S3 bucket.
### Usage
After uploading an odt file to the bucket, it should be converted to pdf *in a timely manner* and also be in the bucket.
Large files can take longer or use up the limited memory of the Lambda function, causing the conversion to fail.
Then it is recommend to:
* increasing the `Default Memory` for the Lambda function from 128 MB to at least 256 MB or higher
* if necessary, increasing the `Timeout` of the Lambda function from `Default 3sec` to 30 seconds or more
### Cleanup
1. Empty the created S3 bucket
```
aws s3 rm s3://$stackname-$AWSACCOUNTID-$AWSREGION-document-bucket --recursive
```
2. Remove the Lambda stack
```
aws cloudformation delete-stack --stack-name $stackname
```
3. Remove the CodeBuild project

Delete the ECR repository and its images, `--repository-name $stackname` may be different for you, in this demo it is equal to the $stackname
```
aws ecr delete-repository --force --registry-id $AWSACCOUNTID --repository-name $stackname
```
The Mirror-Image project
```
aws cloudformation delete-stack --stack-name $stackname-mirrorimage
```
or the Build-Image project
```
aws cloudformation delete-stack --stack-name $stackname-buildimage
```