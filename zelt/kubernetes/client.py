import logging
from typing import List, Optional, Callable

from kubernetes import config
from kubernetes.client import (
    ExtensionsV1beta1Api,
    CoreV1Api,
    V1Namespace,
    ExtensionsV1beta1Deployment,
    V1Pod,
    V1Service,
    V1beta1Ingress,
    V1DeleteOptions,
    V1Status,
    V1ContainerStatus,
)
from kubernetes.client.rest import ApiException
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type

from .manifest import Manifest

KUBE_API_LIST_TIMEOUT = 360
KUBE_API_DELETE_TIMEOUT = 240
KUBE_API_WAIT = 1
STATUS_NOT_FOUND = 404
DEFAULT_DELETE_OPTIONS = V1DeleteOptions(propagation_policy="Foreground")


class PodNotReadyError(RuntimeError):
    pass


class ResourceStillThereError(RuntimeError):
    pass


def read_config():
    try:
        config.load_kube_config()
    except FileNotFoundError:
        logging.error("Kubernetes config. not found!")
        raise


def create_namespace(namespace: Manifest) -> V1Namespace:
    logging.info("Creating Namespace %r...", namespace.name)
    try:
        return CoreV1Api().create_namespace(body=namespace.body)
    except ApiException as err:
        logging.error("Failed to create Namespace %r: %s", namespace.name, err.reason)
        raise


def delete_namespace(name: str) -> Optional[V1Status]:
    logging.info("Deleting Namespace %r...", name)
    try:
        CoreV1Api().delete_namespace(name=name, body=DEFAULT_DELETE_OPTIONS)
    except ApiException as err:
        if err.status == STATUS_NOT_FOUND:
            logging.debug("Skipping Namespace %r deletion: %s", name, err.reason)
            return
        logging.error("Failed to delete Namespace %r: %s", name, err.reason)
        raise
    await_no_resources_found(CoreV1Api().read_namespace, name=name)


def create_deployment(deployment: Manifest) -> ExtensionsV1beta1Deployment:
    logging.info("Creating Deployment %r...", deployment.name)
    try:
        return ExtensionsV1beta1Api().create_namespaced_deployment(
            namespace=deployment.namespace, body=deployment.body
        )
    except ApiException as err:
        logging.error("Failed to create Deployment %r: %s", deployment.name, err.reason)
        raise


def rescale_deployment(
    manifest: Manifest, replicas: int
) -> ExtensionsV1beta1Deployment:
    logging.info("Rescaling Deployment %r to %s Replicas...", manifest.name, replicas)

    if replicas < 0:
        raise ValueError(f"Expected a positive number of Replicas, got {replicas}")

    logging.debug("Fetching existing Deployment %r...", manifest.name)
    try:
        deployment = ExtensionsV1beta1Api().read_namespaced_deployment(
            name=manifest.name, namespace=manifest.namespace
        )
    except ApiException as err:
        logging.error("Failed to fetch Deployment: %s", err.reason)
        raise

    logging.debug(
        "Changing Deployment Replicas from %s to %s...",
        deployment.spec.replicas,
        replicas,
    )
    deployment.spec.replicas = replicas

    logging.debug("Redeploying Deployment %r...", manifest.name)
    try:
        return ExtensionsV1beta1Api().replace_namespaced_deployment(
            name=manifest.name, namespace=manifest.namespace, body=deployment
        )
    except ApiException as err:
        logging.error("Failed to redeploy Deployment %r: %s", manifest.name, err.reason)
        raise


def delete_deployments(namespace: str) -> Optional[V1Status]:
    logging.info("Deleting Deployments in Namespace %r...", namespace)
    try:
        ExtensionsV1beta1Api().delete_collection_namespaced_deployment(
            namespace=namespace
        )
    except ApiException as err:
        if err.status == STATUS_NOT_FOUND:
            logging.debug("Skipping Deployment deletion: %s", err.reason)
            return
        logging.error(
            "Failed to delete Deployments in Namespace %r: %s", namespace, err.reason
        )
        raise
    await_no_resources_found(
        ExtensionsV1beta1Api().list_namespaced_deployment, namespace=namespace
    )


def create_service(service: Manifest) -> V1Service:
    logging.info("Creating Service %r...", service.name)
    try:
        return CoreV1Api().create_namespaced_service(
            namespace=service.namespace, body=service.body
        )
    except ApiException as err:
        logging.error("Failed to create Service %r: %s", service.name, err.reason)
        raise


def delete_service(name: str, namespace: str) -> Optional[V1Status]:
    logging.info("Deleting Service %r...", name)
    try:
        CoreV1Api().delete_namespaced_service(
            name=name, namespace=namespace, body=DEFAULT_DELETE_OPTIONS
        )
    except ApiException as err:
        if err.status == STATUS_NOT_FOUND:
            logging.debug("Skipping Service %r deletion: %s", name, err.reason)
            return
        logging.error("Failed to delete Service %r: %s", name, err.reason)
        raise
    await_no_resources_found(CoreV1Api().list_namespaced_service, namespace=namespace)


def create_ingress(ingress: Manifest) -> V1beta1Ingress:
    logging.info("Creating Ingress %r...", ingress.name)
    try:
        return ExtensionsV1beta1Api().create_namespaced_ingress(
            namespace=ingress.namespace, body=ingress.body
        )
    except ApiException as err:
        logging.error("Failed to create Ingress %r: %s", ingress.name, err.reason)
        raise


def delete_ingress(name: str, namespace: str) -> Optional[V1Status]:
    logging.info("Deleting Ingress %r...", name)
    try:
        ExtensionsV1beta1Api().delete_namespaced_ingress(
            name=name, namespace=namespace, body=DEFAULT_DELETE_OPTIONS
        )
    except ApiException as err:
        if err.status == STATUS_NOT_FOUND:
            logging.debug("Skipping Ingress %r deletion: %s", name, err.reason)
            return
        logging.error("Failed to delete Ingress %r: %s", name, err.reason)
        raise
    await_no_resources_found(
        ExtensionsV1beta1Api().list_namespaced_ingress, namespace=namespace
    )


@retry(
    stop=stop_after_delay(KUBE_API_DELETE_TIMEOUT),
    wait=wait_fixed(KUBE_API_WAIT),
    retry=retry_if_exception_type(ResourceStillThereError),
)
def await_no_resources_found(list_resources: Callable, **kwargs):
    try:
        found = list_resources(**kwargs)
    except ApiException as err:
        if err.status == STATUS_NOT_FOUND:
            return
        raise
    if hasattr(found, "items"):
        found = found.items
    if found:
        raise ResourceStillThereError(f"Resource(s): {found} still found; retrying.")


@retry(
    stop=stop_after_delay(KUBE_API_LIST_TIMEOUT),
    wait=wait_fixed(KUBE_API_WAIT),
    retry=retry_if_exception_type(PodNotReadyError),
)
def wait_until_pod_ready(deployment: Manifest) -> None:
    pod_ready = _pod_status(deployment).ready
    if not pod_ready:
        raise PodNotReadyError()


@retry(stop=stop_after_delay(KUBE_API_LIST_TIMEOUT), wait=wait_fixed(KUBE_API_WAIT))
def _pod_status(deployment: Manifest) -> V1ContainerStatus:
    pod_list = _list_pod(deployment.namespace, deployment.labels)
    return pod_list[0].status.container_statuses[0]


def _list_pod(namespace: str, labels: str) -> List[V1Pod]:
    logging.debug("Listing Pod(s) in Namespace %r with Labels %r...", namespace, labels)
    try:
        return (
            CoreV1Api()
            .list_namespaced_pod(namespace=namespace, label_selector=labels)
            .items
        )
    except ApiException as err:
        logging.error(
            "Failed to list Pod(s) in Namespace %r with Labels %r: %s",
            namespace,
            labels,
            err.reason,
        )
        raise
