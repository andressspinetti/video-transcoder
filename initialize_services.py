import boto3
import uuid
import os

# Feel free to change the region.
region = "us-west-1"
LAMBDA_FUNCTION_NAME = "lambda_video_converter"
PIPELINE_NAME = "Video Transcoder"

# Change this to proper values.
LAMBDA_ROLE_NAME = "CustomLambdaRoleS3Permission"
ELASTIC_TRANSCODE_ROLE_NAME = "ElasticTranscoderVideoConverterRole"

# SNS TOPIC ARN
SNS_COMPLETE_TOPIC = "arn:aws:sns:us-west-1:994940181655:video_transcode_complete"
SNS_ERROR_TOPIC = "arn:aws:sns:us-west-1:994940181655:video_transcode_error"


def main():
    # AWS Clients
    s3_client = boto3.client("s3")
    lambda_client = boto3.client("lambda", region_name=region)
    iam_client = boto3.client("iam")
    transcoder_client = boto3.client("elastictranscoder", region)

    # Roles
    # Get the already created CustomLambdaRoleS3Permission role from AWS
    lambda_role = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)
    # Get the already created ElasticTranscoderVideoConverterRole transcode role from AWS
    elastic_transcode_role = iam_client.get_role(RoleName=ELASTIC_TRANSCODE_ROLE_NAME)

    # S3
    bucket_name = "video-converter-2019"
    bucket_arn = "arn:aws:s3:::{}".format(bucket_name)
    bucket_conf = dict(
        ACL="public-read", CreateBucketConfiguration={"LocationConstraint": region}
    )

    # Create the bucket, if exists append a some random characters to the name
    print("Creating Bucket...")
    try:
        response = s3_client.create_bucket(Bucket=bucket_name, **bucket_conf)
    except s3_client.exceptions.BucketAlreadyExists:
        # Generate a random name for the bucket in case of existing bucket.
        bucket_name = "{}-{}".format(bucker_name, uuid.uuid4().hex[:8])
        bucket_arn = "arn:aws:s3:::{}".format(bucket_name)
        response = s3_client.create_bucket(Bucket=bucket_name, **bucket_conf)
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        pass

    # Create the lambda zip file with all the requirements.
    print("Building Zip file...")
    cmd = "./lambda_package_generator.sh 2> /dev/null 1> /dev/null"
    os.system(cmd)
    with open("lambda_function/lambda.zip", "rb") as f:
        zipped_code = f.read()

    print("Creating Lambda Function...")
    # Look for a pipeline with the specified name, if it doesn't exist proceed by creating it.
    try:
        lambda_info = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        lambda_arn = lambda_info["Configuration"]["FunctionArn"]
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME, ZipFile=zipped_code
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        lambda_info = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime="python3.6",
            Role=lambda_role["Role"]["Arn"],
            Handler="main.lambda_handler",
            Code=dict(ZipFile=zipped_code),
            Timeout=300,
        )
        lambda_arn = lambda_info["FunctionArn"]

    print("Grant S3 access permissions to Lambda...")
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId="1",
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=bucket_arn,
        )
    except lambda_client.exceptions.ResourceConflictException:
        pass

    print("Setting up Lambda trigger for new video files under S3...")
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": lambda_arn,
                    "Events": ["s3:ObjectCreated:*"],
                    "Filter": {
                        "Key": {
                            "FilterRules": [
                                {"Name": "prefix", "Value": "input/"},
                                {"Name": "suffix", "Value": ".mp4"},
                            ]
                        }
                    },
                }
            ]
        },
    )

    # Create a pipeline
    print("Creating Transcode Pipeline...")
    pipelines_list = transcoder_client.list_pipelines()
    pipeline_id = None
    for pipeline in pipelines_list["Pipelines"]:
        if pipeline["Name"] == PIPELINE_NAME:
            pipeline_id = pipeline["Id"]
    if not pipeline_id:
        transcoder_client.create_pipeline(
            Name=PIPELINE_NAME,
            InputBucket=bucket_name,
            OutputBucket=bucket_name,
            Role=elastic_transcode_role["Role"]["Arn"],
            Notifications={
                "Completed": SNS_COMPLETE_TOPIC,
                "Progressing": "",
                "Warning": "",
                "Error": SNS_ERROR_TOPIC,
            },  # Set notifications for complete and error transcoding
        )


if __name__ == "__main__":
    main()
