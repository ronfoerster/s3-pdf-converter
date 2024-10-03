
import boto3
import os
import subprocess

s3 = boto3.client('s3')

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        fileending = key[-3:]
        if fileending!="odt":
            raise Exception("Wrong file ending.")
        file = f'/tmp/{key}'
        newkey = key[:-3]+'pdf'
        newfile = f'/tmp/{newkey}'
        # save file in /tmp
        s3.download_file(bucket, key, file)
        print(f'{file} saved in /tmp')
        # important to set HOME - needs libreoffice to set cache-files there + /tmp is writeable (default paths in this docker container are not)
        os.environ['HOME'] ="/tmp"
        return_code = subprocess.call(["libreoffice", "--headless", "--norestore","--invisible","--nodefault","--nolockcheck", "--convert-to", "pdf:writer_pdf_Export", "--outdir", "/tmp", file], timeout=120)
        if return_code != 0:
            raise Exception("Libreoffice converter fails.")
        if not os.path.isfile(newfile):
            raise Exception("No pdf-file found.")
        s3.upload_file(newfile, bucket, newkey)