# Simple Cloud Storage Service

A simple and easy to use cloud storage which automatically pushes files from local storage to cloud for easy access.

### Pre-requisites to run this application.

* A working AWS account since this project uses Amazon Simple Storage Service (S3) for cloud storage. Keep in mind that using AWS S3 incurr charges.
* Configured AWS CLI on terminal. ([Setup AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html)) 
* Python version 3
* Linux based operating system for implementing auto-running using systemd. (*Optional*)

### Install the required libraries

```sh
pip install -r rquirements
```

## Setting up AWS IoT Core

Create an AWS IoT Thing.

```sh
aws iot create-thing --thing-name Cloud_Storage_Thing
```

Create device certificates and keys. Save them inside a repository called `certificates`.

```sh
mkdir certificates
aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile "certificates/certificate.cert.pem" \
    --public-key-outfile "certificates/public.key" \
    --private-key-outfile "certificates/private.key"
```

Save the `certificateArn` from the recieved payload.

Run the following command to download the `AmazonRootCA1.pem` certificate.

```sh
curl https://www.amazontrust.com/repository/AmazonRootCA1.pem > certificates/AmazonRootCA1.pem
```

Now, we will create a policy for your AWS IoT Thing. 
First create a `policy.json` file and paste the following inside it.

```.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
```

Attach the certificate with your AWS IoT Thing.

```sh
aws iot attach-thing-principal \
    --thing-name Cloud_Storage_Thing \
    --principal your-certificateArn
```
Replace `your-certifcateArn` with the `certificateArn` recieved from creating the payload.

Then run the following command.

```sh
aws iot create-policy --policy-name cloud_project_policy --policy-document file://policy.json
```

Now we will attach our policy to the certificates.

```sh
aws iot attach-policy \
    --policy-name cloud_project_policy \
    --target your-certificateArn
```

## Setting up AWS S3

Run the following code in your terminal to create a S3 bucket called `cloud-storage-bucket`

```sh
aws s3api create-bucket \
    --bucket cloud-storage-bucket \
    --region us-west-2 \
    --create-bucket-configuration LocationConstraint=us-west-2
```

*Note: Ensure that the region of your AWS IoT Thing and your bucket is the same.*

## Setting up AWS Lambda to get pre-signed URLs for S3

Create a file called `lambda.py` and paste the following code inside it.

```py
import json
import boto3
from botocore.client import Config

s3Client = boto3.client('s3', config = Config(signature_version = 's3v4'))
iotClient = boto3.client('iot-data', region_name = 'us-west-2')

def lambda_handler(event, context):
    
    bucket_name = event['bucket_name']
    files = event['files']
    expire = 1800
    
    payload = []
    for file in files:
        try:
            signed_url = s3Client.generate_presigned_post(
                Bucket = bucket_name,
                Key = file,
                Fields = None,
                Conditions = None,
                ExpiresIn = expire
                )
        except Exception as e:
            print(e)
            signed_url = []
        
        payload.append({
            'data': signed_url
        })
    
    response = iotClient.publish(
        topic = 'cloudstorage/post/signedurl/data',
        qos = 1,
        payload = json.dumps({
            'payload' : payload
        })
        )
    
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
```

Before uploading we need to zip the lambda file.

```sh
zip my_function.zip lambda.py
```

Now we will create a `role.json` file and configure it for our lambda.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Now run the following command to create a role for our lambda function.

```sh
aws iam create-role --role-name cs-presigned-url-role --assume-role-policy-document file://role.json
```

Note down the ARN recieved after executing the code as we will be using to create our lambda function.

Additionally, attach policies to gives acccess to our lambda for using S3 and IoT resources.

```sh
aws iam attach-role-policy --role-name cs-presigned-url-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name cs-presigned-url-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name cs-presigned-url-role \
    --policy-arn arn:aws:iam::aws:policy/AWSIoTWirelessFullPublishAccess
```

Finally we will create our lambda function by uploading it to AWS. Replace `your-lambda-execution-role-arn` with the ARN recieved after creating the role.

```sh
aws lambda create-function --function-name cs_presigned_url_function \
    --zip-file fileb://my_function.zip \
    --handler lambda.handler \
    --region us-west-2 \
    --runtime python3.9 \
    --role your-lambda-execution-role-arn
```
