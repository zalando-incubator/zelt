import logging
import os
from tenacity import RetryError

import zelt.kubernetes.client as kube
from zelt.kubernetes.manifest_set import ManifestSet
from zelt.kubernetes.storage.protocol import LocustfileStorage


def create_resources(
    ms: ManifestSet, storage: LocustfileStorage, locustfile: os.PathLike
) -> None:
    try:
        kube.read_config()
        kube.create_namespace(ms.namespace)

        storage.upload(locustfile)

        kube.create_deployment(ms.controller)
        kube.wait_until_pod_ready(ms.controller)

        if ms.worker:
            kube.create_deployment(ms.worker)

        kube.create_service(ms.service)
        kube.create_ingress(ms.ingress)
    except (kube.ApiException, RetryError) as err:
        logging.error("Kubernetes operation failed: %s", err.reason)


def delete_resources(ms: ManifestSet, storage: LocustfileStorage) -> None:
    logging.info("Deleting resources...")
    try:
        kube.read_config()
        namespace = ms.namespace.name

        storage.delete()
        kube.delete_ingress(ms.ingress.name, namespace)
        kube.delete_service(ms.service.name, namespace)
        kube.delete_deployments(namespace)
        kube.delete_namespace(namespace)
    except (kube.ApiException, RetryError) as err:
        logging.error("Kubernetes operation failed: %s", err.reason)


def update_worker_pods(ms: ManifestSet, worker_replicas: int) -> None:
    if ms.worker is not None:
        ms.worker.body["spec"]["replicas"] = worker_replicas


def rescale_worker_deployment(ms: ManifestSet, replicas: int) -> None:
    if not ms.worker:
        logging.error(
            "Missing worker manifest. Only worker deployments can be rescaled."
        )
        return

    try:
        kube.read_config()
        kube.rescale_deployment(ms.worker, replicas)
    except kube.ApiException as err:
        logging.error("Kubernetes operation failed: %s", err.reason)
