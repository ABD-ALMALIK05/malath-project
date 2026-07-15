from pathlib import Path, PurePosixPath
from typing import Protocol

from flask import Response, current_app, redirect, send_file


class StorageError(RuntimeError):
    pass


class StorageConfigurationError(StorageError):
    pass


class DocumentStorage(Protocol):
    def save(self, fileobj, storage_key: str, content_type: str) -> None:
        pass

    def delete(self, storage_key: str) -> None:
        pass

    def exists(self, storage_key: str) -> bool:
        pass

    def create_download_response(
        self, storage_key: str, download_name: str, content_type: str
    ) -> Response:
        pass


class LocalStorage:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()

    def _resolve_storage_key(self, storage_key: str) -> Path:
        if "\\" in storage_key or ":" in storage_key:
            raise StorageError("Invalid storage key")

        pure_key = PurePosixPath(storage_key)
        if pure_key.is_absolute() or any(part in {"", ".", ".."} for part in pure_key.parts):
            raise StorageError("Invalid storage key")

        resolved = (self.base_path / Path(*pure_key.parts)).resolve()
        if resolved != self.base_path and self.base_path not in resolved.parents:
            raise StorageError("Invalid storage key")
        return resolved

    def save(self, fileobj, storage_key: str, content_type: str) -> None:
        del content_type
        destination = self._resolve_storage_key(storage_key)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as output:
                while chunk := fileobj.read(1024 * 1024):
                    output.write(chunk)
        except OSError as error:
            raise StorageError("Unable to save file") from error

    def delete(self, storage_key: str) -> None:
        target = self._resolve_storage_key(storage_key)
        try:
            target.unlink(missing_ok=True)
        except OSError as error:
            raise StorageError("Unable to delete file") from error

    def exists(self, storage_key: str) -> bool:
        return self._resolve_storage_key(storage_key).is_file()

    def create_download_response(
        self, storage_key: str, download_name: str, content_type: str
    ) -> Response:
        target = self._resolve_storage_key(storage_key)
        if not target.is_file():
            raise StorageError("File not found")

        return send_file(
            target,
            as_attachment=True,
            download_name=download_name,
            mimetype=content_type,
            conditional=True,
        )


class S3Storage:
    def __init__(self, bucket_name: str | None, region_name: str | None, expires_in: int):
        if not bucket_name or not region_name:
            raise StorageConfigurationError("S3 bucket and region are required")

        import boto3

        self.bucket_name = bucket_name
        self.expires_in = expires_in
        self.client = boto3.client("s3", region_name=region_name)

    def save(self, fileobj, storage_key: str, content_type: str) -> None:
        try:
            self.client.upload_fileobj(
                fileobj,
                self.bucket_name,
                storage_key,
                ExtraArgs={"ContentType": content_type},
            )
        except Exception as error:
            raise StorageError("Unable to save file") from error

    def delete(self, storage_key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=storage_key)
        except Exception as error:
            raise StorageError("Unable to delete file") from error

    def exists(self, storage_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=storage_key)
        except Exception:
            return False
        return True

    def create_download_response(
        self, storage_key: str, download_name: str, content_type: str
    ) -> Response:
        del download_name, content_type
        try:
            download_url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": storage_key},
                ExpiresIn=self.expires_in,
            )
        except Exception as error:
            raise StorageError("Unable to create download link") from error

        return redirect(download_url)


def get_storage() -> DocumentStorage:
    storage = current_app.extensions.get("malath_storage")
    if storage is not None:
        return storage

    backend = current_app.config.get("STORAGE_BACKEND", "local").lower()
    if backend == "local":
        storage = LocalStorage(current_app.config["LOCAL_STORAGE_PATH"])
    elif backend == "s3":
        storage = S3Storage(
            current_app.config.get("AWS_BUCKET_NAME"),
            current_app.config.get("AWS_REGION"),
            current_app.config["S3_PRESIGNED_EXPIRES_SECONDS"],
        )
    else:
        raise StorageConfigurationError(f"Unsupported storage backend: {backend}")

    current_app.extensions["malath_storage"] = storage
    return storage


def create_download_response(storage_key: str, download_name: str, content_type: str) -> Response:
    return get_storage().create_download_response(storage_key, download_name, content_type)


def delete_object(storage_key: str) -> None:
    get_storage().delete(storage_key)


def save_fileobj(fileobj, storage_key: str, content_type: str) -> None:
    get_storage().save(fileobj, storage_key, content_type)
