#!/usr/bin/env bash

# -e option instructs bash to immediately exit if any command [1] has a non-zero exit status
# We do not want users to end up with a partially working install, so we exit the script
# instead of continuing the installation with something broken
set -e

echo "RUNNING TEST"
echo "============"
BUCKETNAME=$(jq -r '.S3PdfConverterLambdaStack.DocumentBucketName' $1)
QUEUE_URL=$(jq -r '.S3PdfConverterLambdaStack.JobSuccessSQSUrl' $1)

echo "SQS Url is $QUEUE_URL"
echo "Bucketname is $BUCKETNAME"

aws s3 cp sample.odt $(echo "s3://$BUCKETNAME")


TIME_LIMIT=60  # 1min
START_TIME=$(date +%s)
END_TIME=$((START_TIME + TIME_LIMIT))

while [ $(date +%s) -lt $END_TIME ]; do
    # Receive messages with long polling (10 seconds wait time)
    MESSAGES=$(aws sqs receive-message \
        --queue-url "$QUEUE_URL" \
        --wait-time-seconds 10 \
        --max-number-of-messages 1 \
        --output json)

    # Check if messages were received
    if echo "$MESSAGES" | jq -e '.Messages' > /dev/null 2>&1; then
      if [[ $(echo "$MESSAGES" | jq -r '.Messages[] | .Body') == "sample.odt converted to sample.pdf" ]]; then
        echo "FETCHED SQS CONVERT SUCCESS MESSAGE."
        aws s3api head-object --bucket $BUCKETNAME --key sample.pdf > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "TEST IN $BUCKETNAME SUCCEEDED."
        else
            echo "TEST IN $BUCKETNAME FAILED."
        fi
        # Delete processed messages
        RECEIPT_HANDLE=$(echo "$MESSAGES" | jq -r '.Messages[] | "\(.ReceiptHandle)"')
        aws sqs delete-message --queue-url "$QUEUE_URL" --receipt-handle "$RECEIPT_HANDLE" 
      fi
    fi
done
