import logging
import os

try:
    import boto3
except ImportError as err:
    raise ImportError(
        "boto3 not found. It is required for uploading to S3 with the "
        "'--storage=s3' option. "
        "It can be installed with 'pip install boto3'."
    ) from err

from zelt.kubernetes.storage.protocol import LocustfileStorage


class S3Storage(LocustfileStorage):
    def __init__(self, bucket: str, key: str) -> None:
        super().__init__()
        self.bucket = bucket
        self.key = key

    def upload(self, locustfile: os.PathLike) -> None:
        def _upload_callback(nb_bytes_transferred: int) -> None:
            logging.info(
                "Uploading %s to %s as %s: %s bytes transferred.",
                locustfile,
                self.bucket,
                self.key,
                nb_bytes_transferred,
            )

        boto3.resource("s3").Object(self.bucket, self.key).upload_file(
            Filename=os.fspath(locustfile), Callback=_upload_callback
        )

    def delete(self) -> None:
        logging.info("Deleting %s from S3 bucket %s...", self.key, self.bucket)
        boto3.resource("s3").Object(self.bucket, self.key).delete()
