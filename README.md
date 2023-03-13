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

### Setting up AWS IoT Core

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
