FROM debian:stable-slim

RUN mkdir /var/task
WORKDIR /var/task
COPY lambda.py lambda.py

RUN apt update && apt install python3 python3-pip libreoffice-writer curl -y --no-install-recommends 

RUN python3 -m pip install --no-cache-dir --target /var/task awslambdaric boto3

# Trigger dummy run to generate bootstrap files to improve cold start performance
RUN touch /tmp/test.txt \
    && cd /tmp \
    && libreoffice --headless --nologo --nofirststartwizard --norestore --convert-to pdf --outdir /tmp /tmp/test.txt \
    && rm /tmp/test.*

# Lambda Runtime Interface Emulator
ARG TARGETPLATFORM
RUN if [ "$TARGETPLATFORM" = "linux/arm64" ]; then RIE=aws-lambda-rie-arm64; else RIE=aws-lambda-rie; fi \
    && curl -Lo /usr/local/bin/aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/${RIE} && chmod +x /usr/local/bin/aws-lambda-rie

COPY entry_script.sh /entry_script.sh
RUN chmod +x /entry_script.sh

ENTRYPOINT [ "/entry_script.sh" ]
CMD [ "lambda.lambda_handler" ]
