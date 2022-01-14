import io

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from config import PHONE_NUMBER, S3_BUCKET

s3 = boto3.client('s3')
sns = boto3.client('sns', region_name="us-west-2")

def sms(message: str) -> None:
    """Send text message

    Args:
        message (str): Message body
    """
    sns.publish(
        PhoneNumber = PHONE_NUMBER,
        Message = message)
    return

def s3Upload(file: str) -> None:
    """Uploads file to S3

    Args:
        file (str): Path to file and S3 file key
    """
    s3.upload_file(file, S3_BUCKET, file)
    return

def s3Download(file: str) -> pd.DataFrame:
    """Downloads CSV files from s3 and loads into dataframe

    Args:
        s3 (boto3.client): S3 Client
        file (str): File name

    Returns:
        pd.DataFrame: Position data. None if file not found.
    """
    try:
        obj = s3.get_object(Bucket = S3_BUCKET, Key = file)
        df = pd.read_csv(io.BytesIO(obj['Body'].read()), encoding='utf8')
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'NoSuchKey': raise
        return
    return df
