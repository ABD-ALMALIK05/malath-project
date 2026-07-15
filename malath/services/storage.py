import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app


class StorageError(RuntimeError):
    pass


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=current_app.config["AWS_ACCESS_KEY"],
        aws_secret_access_key=current_app.config["AWS_SECRET_KEY"],
        region_name=current_app.config["AWS_REGION"],
    )


def upload_fileobj(fileobj, storage_key, content_type):
    try:
        get_s3_client().upload_fileobj(
            fileobj,
            current_app.config["AWS_BUCKET_NAME"],
            storage_key,
            ExtraArgs={"ContentType": content_type},
        )
    except (BotoCoreError, ClientError, Exception) as error:
        raise StorageError(str(error)) from error


def create_presigned_download_url(storage_key):
    try:
        return get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": current_app.config["AWS_BUCKET_NAME"], "Key": storage_key},
            ExpiresIn=300,
        )
    except (BotoCoreError, ClientError, Exception) as error:
        raise StorageError(str(error)) from error


def delete_object(storage_key):
    try:
        get_s3_client().delete_object(
            Bucket=current_app.config["AWS_BUCKET_NAME"],
            Key=storage_key,
        )
    except (BotoCoreError, ClientError, Exception) as error:
        raise StorageError(str(error)) from error


def build_public_file_url(storage_key):
    bucket = current_app.config["AWS_BUCKET_NAME"]
    region = current_app.config["AWS_REGION"]
    return f"https://{bucket}.s3.{region}.amazonaws.com/{storage_key}"
