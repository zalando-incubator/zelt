import enum
import logging
import os
import subprocess
from pathlib import Path
from time import time
from typing import Optional, Sequence
from zlib import adler32

from zelt.kubernetes import deployer, manifest_set
from zelt.kubernetes.manifest_set import ManifestSet
from zelt.kubernetes.storage.configmap import ConfigmapStorage
from zelt.kubernetes.storage.protocol import LocustfileStorage
from zelt.kubernetes.storage.s3 import S3Storage

try:
    import transformer

    TRANSFORMER_NOT_FOUND = False
except ImportError:
    TRANSFORMER_NOT_FOUND = True


class HARFilesNotFoundException(Exception):
    pass


class StorageMethod(enum.Enum):
    CONFIGMAP = enum.auto()
    S3 = enum.auto()

    @classmethod
    def from_storage_arg(cls, arg: str) -> "StorageMethod":
        if arg.lower() == "s3":
            return cls.S3
        if arg.lower() in ("cm", "configmap"):
            return cls.CONFIGMAP
        raise ValueError(f"unknown {cls.__qualname__} {arg!r}")

    def build_storage(
        self,
        manifests: ManifestSet,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
    ) -> LocustfileStorage:
        if self is StorageMethod.S3 and (not (s3_bucket and s3_key)):
            raise ValueError(
                "Missing required 's3-bucket' and/or 's3-key' options "
                "for 'storage=s3' option."
            )

        if self is not StorageMethod.S3 and (s3_bucket or s3_key):
            raise ValueError(
                "Unexpected 's3-bucket' or 's3-key' options "
                "without 'storage=s3' option."
            )

        if self is StorageMethod.S3:
            return S3Storage(bucket=s3_bucket, key=s3_key)

        return ConfigmapStorage(
            namespace=manifests.namespace.name, labels=manifests.namespace.labels_dict
        )


def deploy(
    locustfile: os.PathLike,
    worker_pods: int,
    manifests_path: Optional[os.PathLike],
    clean: bool,
    storage_method: StorageMethod,
    local: bool,
    s3_bucket: Optional[str] = None,
    s3_key: Optional[str] = None,
) -> None:
    if local:
        if manifests_path:
            logging.warning(
                "Mutually incompatible options 'local' and 'manifests' specified. Defaulting to running locally."
            )
        return _deploy_locally(locustfile)

    if not manifests_path:
        raise ValueError("Missing required 'manifests' option.")

    _deploy_in_kubernetes(
        locustfile,
        worker_pods,
        manifests_path=manifests_path,
        clean_deployment=clean,
        storage_method=storage_method,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )


def rescale(manifests_path, worker_pods: int) -> None:
    if not manifests_path:
        raise ValueError("Missing required 'manifests' option.")

    if worker_pods < 0:
        raise ValueError(f"Expected a positive number of pods, got {worker_pods}.")

    manifests = manifest_set.from_directory(manifests_path)
    deployer.update_worker_pods(manifests, worker_pods)
    deployer.rescale_worker_deployment(manifests, worker_pods)
    logging.info("Rescaling complete.")


def delete(
    manifests_path: os.PathLike,
    storage_method: StorageMethod,
    s3_bucket: Optional[str] = None,
    s3_key: Optional[str] = None,
) -> None:
    if not manifests_path:
        raise ValueError("Missing required 'manifests' option.")

    manifests = manifest_set.from_directory(manifests_path)
    storage = storage_method.build_storage(manifests, s3_bucket, s3_key)
    deployer.delete_resources(manifests, storage)
    logging.info("Deletion complete.")


def invoke_transformer(
    paths: Sequence[os.PathLike], plugin_names: Sequence[str]
) -> Path:
    if TRANSFORMER_NOT_FOUND:
        raise ImportError(
            "Transformer not found. It is required for calls to 'from-har'. "
            "It can be installed with 'pip install har-transformer'."
        )

    har_files = []
    for path in paths:
        if os.path.exists(path):
            har_files.append(Path(path))
    if not har_files:
        raise HARFilesNotFoundException(f"Could not load any HAR files from {paths}")

    locustfile = Path(f"locustfile-{adler32(str(paths).encode(encoding='utf-8'))}.py")
    with locustfile.open("w") as f:
        transformer.dump(f, har_files, plugin_names)
    logging.info("%s created from %s.", locustfile, har_files)
    return locustfile


def _deploy_locally(locustfile: os.PathLike) -> None:
    logging.info("Deploying Locust locally with locustfile %s...", locustfile)
    logging.info("\n\nOpen http://localhost:8089/ to access the Locust dashboard.\n\n")

    # The host value is unused when full URLs are used in the locustfile.
    subprocess.run(["locust", "-f", os.fspath(locustfile), "--host=unused"], check=True)


def _deploy_in_kubernetes(
    locustfile: os.PathLike,
    worker_pods: int,
    manifests_path: os.PathLike,
    clean_deployment: bool,
    storage_method: StorageMethod,
    s3_bucket: Optional[str],
    s3_key: Optional[str],
) -> None:
    if worker_pods < 0:
        raise ValueError(f"Expected a positive number of pods, got {worker_pods}.")

    logging.info(
        "Deploying Locust in Kubernetes with locustfile %s and %s worker pods...",
        locustfile,
        worker_pods,
    )

    manifests = manifest_set.from_directory(manifests_path)

    storage = storage_method.build_storage(manifests, s3_bucket, s3_key)

    if clean_deployment:
        deployer.delete_resources(manifests, storage)

    deployer.update_worker_pods(manifests, worker_pods)
    deployer.create_resources(manifests, storage, locustfile)

    logging.info(
        "\n\nOpen %s to access the Locust dashboard.\n\n", manifests.ingress.host
    )
