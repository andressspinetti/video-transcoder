import boto3

# Feel free to change the region.
REGION = "us-west-1"
BUCKET_NAME = "video-converter-2019"
FILE_NAME = "dark-side.mp4"


def main():
    # AWS Clients
    s3_client = boto3.client("s3")
    print("Uploading mp4 file...")
    s3_client.upload_file(
        "./{}".format(FILE_NAME), BUCKET_NAME, "input/{}".format(FILE_NAME)
    )
    print("Done...")


if __name__ == "__main__":
    main()
