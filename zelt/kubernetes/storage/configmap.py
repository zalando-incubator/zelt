import logging
import os
from pathlib import Path

from kubernetes.client import V1ConfigMap, CoreV1Api, V1DeleteOptions
from kubernetes.client.rest import ApiException

import zelt.kubernetes.client as client
from zelt.kubernetes.storage.protocol import LocustfileStorage

CONFIGMAP_NAME = "zelt-locustfile"
CONFIGMAP_KEY = "locustfile.py"


class ConfigmapStorage(LocustfileStorage):
    def __init__(self, namespace: str, labels: dict) -> None:
        super().__init__()
        self.namespace = namespace
        self.labels = dict(labels)

    def upload(self, locustfile: os.PathLike) -> None:
        logging.info("Creating ConfigMap %r...", CONFIGMAP_NAME)
        config_map = V1ConfigMap(
            data={CONFIGMAP_KEY: Path(locustfile).read_text()},
            metadata={"name": CONFIGMAP_NAME, "labels": self.labels},
        )
        try:
            logging.debug("Creating ConfigMap %r...", CONFIGMAP_NAME)
            CoreV1Api().create_namespaced_config_map(
                namespace=self.namespace, body=config_map
            )
            logging.debug("ConfigMap %r created.", CONFIGMAP_NAME)
        except ApiException as err:
            logging.error(
                "Failed to create ConfigMap %r: %s", CONFIGMAP_NAME, err.reason
            )
            raise

    def delete(self) -> None:
        try:
            logging.info("Deleting ConfigMap %r...", CONFIGMAP_NAME)
            CoreV1Api().delete_namespaced_config_map(
                name=CONFIGMAP_NAME,
                namespace=self.namespace,
                body=V1DeleteOptions(propagation_policy="Foreground"),
            )
            logging.debug("Waiting for ConfigMap %r to be deleted...", CONFIGMAP_NAME)
            client.await_no_resources_found(
                CoreV1Api().list_namespaced_config_map, namespace=self.namespace
            )
            logging.debug("ConfigMap %r deleted.", CONFIGMAP_NAME)
        except ApiException as err:
            if err.status == 404:
                logging.debug(
                    "Skipping ConfigMap %r deletion: %s", CONFIGMAP_NAME, err.reason
                )
                return
            logging.error(
                "Failed to delete ConfigMap %r: %s", CONFIGMAP_NAME, err.reason
            )
            raise
