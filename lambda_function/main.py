import boto3
import json
import os

PIPELINE_NAME = "Video Transcoder"
REGION = "us-west-1"
transcoder_client = boto3.client("elastictranscoder", REGION)
BASE_S3_OUPUT_FOLDER = "output"


def get_pipeline_id(pipeline_name):
    pipelines_list = transcoder_client.list_pipelines()
    pipeline_id = None
    for pipeline in pipelines_list["Pipelines"]:
        if pipeline["Name"] == pipeline_name:
            pipeline_id = pipeline["Id"]
    return pipeline_id


def lambda_handler(event, context):
    sourceKey = event["Records"][0]["s3"]["object"]["key"]
    pipeline_id = get_pipeline_id(PIPELINE_NAME)
    base_file_name = os.path.basename(sourceKey).split(".")[0]
    job = transcoder_client.create_job(
        PipelineId=pipeline_id,
        Input={
            "Key": sourceKey,
            "FrameRate": "auto",
            "Resolution": "auto",
            "AspectRatio": "auto",
            "Interlaced": "auto",
            "Container": "auto",
        },
        ## List of item presets:
        # https://docs.aws.amazon.com/elastictranscoder/latest/developerguide/system-presets.html
        Outputs=[
            {
                "Key": "{}/HLS/1M/{}".format(BASE_S3_OUPUT_FOLDER, base_file_name),
                "PresetId": "1351620000001-200030",  # System preset: HLS 1M
                "SegmentDuration": "2",
            },
            {
                "Key": "{}/mp3/{}.mp3".format(BASE_S3_OUPUT_FOLDER, base_file_name),
                "PresetId": "1351620000001-300040",  # System preset: MP3 128k
            },
            {
                "Key": "{}/webm/{}.webm".format(BASE_S3_OUPUT_FOLDER, base_file_name),
                "PresetId": "1351620000001-100240",  # System preset: webM
                "ThumbnailPattern": "{}/webm/thumbs-{}".format(
                    BASE_S3_OUPUT_FOLDER, base_file_name
                )
                + "-{count}",
            },
        ],
    )

    return {"statusCode": 200, "body": {"transcode_job": job}}
    # transcoder_client.list_pipelines()['Pipelines'][0]['Name']
