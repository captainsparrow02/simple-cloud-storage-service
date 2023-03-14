# Simple Cloud Storage Service

A simple and easy to use cloud storage which automatically pushes files from local storage to cloud for easy access.

### Pre-requisites to run this application.

* A working AWS account since this project uses Amazon Simple Storage Service (S3) for cloud storage. Keep in mind that using AWS S3 incurr charges.
* Configured AWS CLI on terminal. ([Setup AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html)) 
* Python version 3
* Linux based operating system for implementing auto-running using systemd. (*Optional*)

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

## Create IoT Rule to trigger Lambda function

To trigger our `cs_presigned_url_function` lambda function we will create an IoT rule.

Create a rule payload document `myrule.json` and paste the json content inside.
```json
{
  "sql": "SELECT * FROM 'cloudstorage/get/signedurl/data'",
  "ruleDisabled": false,
  "awsIotSqlVersion": "2016-03-23",
  "actions": [{
      "lambda": {
          "functionArn": "arn:aws:lambda:us-west-2:123456789012:function:cs_presigned_url_function"
      }
  }]
}
```
Replace the `functionArn` with your own lambda function's ARN.

In case you did not save the lambda function ARN during its creation, you can use the below command to fetch the details of your lambda function.

```sh
aws lambda get-function \
    --function-name  cs_presigned_url_function
```

Once you replace the `functionArn` with your own, upload the rule payload.

```sh
aws iot create-topic-rule \
    --rule-name signed_url_cloud_storage_rule \
    --topic-rule-payload file://myrule.json
```

## Setting up Lambda to authenticate successful upload to S3.

Create a file called `lambda.py` and paste the following code inside it.

```py
import json
import boto3
from botocore.client import Config

iotClient = boto3.client('iot-data', region_name = 'us-west-2')

def lambda_handler(event, context):
    file = event['Records'][0]['s3']['object']['key']
    response = iotClient.publish(
        topic = 'cloudstorage/post/authenticate/data',
        qos = 1,
        payload = json.dumps({
            'file' : file.replace('+',' ')
            
        })
        )
    
    return {
        'statusCode': 200,
        'body': json.dumps({ 'file' : file })
    }
```

Before uploading we need to zip the lambda file.

```sh
zip my_function.zip lambda.py
```

For this lambda function we will use the existing `cs-presigned-url-role` since it contains the required permissions.

Run the following code to create the function and replace the `cs-presigned-url-role-arn` with the actual role ARN.

```sh
aws lambda create-function --function-name cs_s3_upload_success \
    --zip-file fileb://my_function.zip \
    --handler lambda.handler \
    --region us-west-2 \
    --runtime python3.9 \
    --role cs-presigned-url-role-arn
```

## Setting up S3 put trigger for Lambda

Create a `notification.json` in the current location and paste the bewlo content inside it. Replace the `cs_s3_upload_success_arn` with the actual lambda fucntion's ARN.

```json
{
    "LambdaFunctionConfigurations": [
        {
            "LambdaFunctionArn": cs_s3_upload_success_arn,
            "Events": [
                "s3:ObjectCreated:*"
            ]
        }
    ]
}
```

Now upload the notification configuration to create the put trigger.

```sh
aws s3api put-bucket-notification-configuration \
    --bucket cloud-storage-bucket \
    --notification-configuration file://notification.json
```
## Setting the local storage confuguration file.

Local storage configuration is stored inside the `cloud.conf` file. Edit and place the AWS Iot (ARN) endpoint.

```conf
	"CLOUD": {
    	"ARN" : "a2d3jxxxxxxxxx-ats.iot.us-west-2.amazonaws.com",
    	"PORT" : "8883",
    	"MQTT_INTERVAL" : "44",
    	"BUCKET_NAME" : "cloud-storage-bucket",
    	"PUBLISH" : {
    	"CLIENT_NAME" : "Cloud-Storage-Publish-Client",
    	"TOPIC" : "cloudstorage/get/signedurl/data",
    	"QoS" : "1"
    	},
    	"SUBSCRIBE" : {
        	"CLIENT_NAME" : "Cloud-Storage-Subscribe-Client",
        	"TOPIC" : "cloudstorage/post/signedurl/data",
        	"QoS" : "0"
        	},
    	"AUTHENTICATE" : {
        	"CLIENT_NAME" : "Cloud-Storage-Autheticate-Client",
        	"TOPIC" : "cloudstorage/post/authenticate/data",
        	"QoS" : "0"
        	},
    	"ROOT_CA_PATH" : "certificates/AmazonRootCA1.pem",
    	"DEVICE_CERT_PATH" : "certificates/certificate.pem.crt",
    	"PRIVATE_KEY_PATH" : "certificates/private.pem.key"
    	},
	"LOCAL" : {
	    "STORAGE_PATH" : "cloud_storage/"
	}
}
```

You can use `aws iot describe-endpoint` to know your IoT Endpoint (ARN).

### Install the required libraries

```sh
pip install -r rquirements
```

## Running the scripts.

Inside the current location run the following command.

```sh
python3 run.py
```

Place the file(s) you want to upload inside the `cloud_storage` repository. Wait for a few seconds and you will find the files getting removed on its own. The files get removed only after getting successfully uploaded to our S3 bucket.

You can check the logs by doing `cat cloud.log`.