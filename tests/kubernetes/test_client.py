from unittest.mock import MagicMock, patch

import pytest
from kubernetes.client import (
    ExtensionsV1beta1Deployment,
    V1Namespace,
    V1Service,
    V1beta1Ingress,
    ExtensionsV1beta1DeploymentSpec,
    V1ObjectMeta,
)
from kubernetes.client.rest import ApiException
from tenacity import wait_none, RetryError, stop_after_attempt

from zelt.kubernetes.client import (
    DEFAULT_DELETE_OPTIONS,
    STATUS_NOT_FOUND,
    create_namespace,
    create_deployment,
    _list_pod,
    create_ingress,
    create_service,
    read_config,
    delete_namespace,
    delete_service,
    delete_ingress,
    delete_deployments,
    await_no_resources_found,
    rescale_deployment,
)
from zelt.kubernetes.manifest import Manifest


class TestReadConfig:
    @patch("kubernetes.config.load_kube_config")
    def test_it_calls_kubernetes_config(self, config):
        read_config()
        config.assert_called_once()

    @patch("kubernetes.config.load_kube_config")
    def test_it_throws_error_when_file_not_found(self, config, caplog):
        config.side_effect = FileNotFoundError()
        with pytest.raises(FileNotFoundError):
            read_config()
        assert any(
            r.levelname == "ERROR" for r in caplog.records
        ), "an error should be logged"


class TestCreateNamespace:
    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CoreV1Api")
    def test_it_calls_kubernetes_api(self, core_api, *_):
        data = {"metadata": {"name": "some_manifest"}}
        create_namespace(Manifest(body=data))
        core_api().create_namespace.assert_called_with(body=data)

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CoreV1Api")
    def test_it_raises_exception(self, core_api, *_):
        core_api().create_namespace.side_effect = ApiException(MagicMock())
        with pytest.raises(ApiException):
            create_namespace(Manifest(body={"metadata": {"name": "some_manifest"}}))


class TestDeleteNamespace:
    @patch("zelt.kubernetes.client.CoreV1Api.read_namespace", return_value=None)
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespace")
    def test_it_calls_kubernetes_api(self, delete, *_):
        namespace_name = "a_namespace"
        delete_namespace(namespace_name)
        delete.assert_called_once_with(name=namespace_name, body=DEFAULT_DELETE_OPTIONS)

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespace")
    def test_it_skips_deletion_when_namespace_not_found(self, delete, waiting):
        delete.side_effect = ApiException(status=STATUS_NOT_FOUND)

        result = delete_namespace("a_namespace")

        delete.assert_called_once()
        waiting.assert_not_called()
        assert result is None

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespace")
    def test_it_raises_exception(self, delete, waiting):
        delete.side_effect = ApiException()

        with pytest.raises(ApiException):
            delete_namespace("a_namespace")

        delete.assert_called_once()
        waiting.assert_not_called()

    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespace")
    @patch(
        "zelt.kubernetes.client.CoreV1Api.read_namespace", return_value=V1Namespace()
    )
    def test_it_raises_exception_when_timeout_reached(self, *_):
        await_no_resources_found.retry.wait = wait_none()
        await_no_resources_found.retry.stop = stop_after_attempt(1)

        with pytest.raises(RetryError):
            delete_namespace("a_namespace")


class TestCreateDeployment:
    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api")
    def test_it_calls_kubernetes_api(self, extensions_api, *_):
        data = {
            "kind": "deployment",
            "metadata": {"namespace": "a_namespace", "name": "a_deployment"},
        }
        manifest = Manifest(body=data)
        create_deployment(manifest)
        extensions_api().create_namespaced_deployment.assert_called_with(
            namespace=manifest.namespace, body=data
        )

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api")
    def test_it_raises_exception(self, extensions_api, *_):
        extensions_api().create_namespaced_deployment.side_effect = ApiException(
            MagicMock()
        )
        with pytest.raises(ApiException):
            create_deployment(
                Manifest(
                    body={
                        "kind": "deployment",
                        "metadata": {
                            "namespace": "a_namespace",
                            "name": "a_deployment",
                        },
                    }
                )
            )


class TestRescaleDeployment:
    def test_it_raises_error_when_given_a_negative_number_of_replicas(self):
        with pytest.raises(ValueError, match="positive number of (r|R)eplicas"):
            rescale_deployment(MagicMock(), -2)

    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api.read_namespaced_deployment")
    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api.replace_namespaced_deployment")
    def test_it_redeploys_when_given_a_positive_number_of_replicas(self, replace, read):
        manifest = MagicMock()
        rescale_deployment(manifest, 2)
        read.assert_called_once()
        replace.assert_called_once()


class TestDeleteDeployments:
    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch(
        "zelt.kubernetes.client.ExtensionsV1beta1Api.delete_collection_namespaced_deployment"
    )
    def test_it_calls_kubernetes_api(self, delete, waiting, *_):
        namespace_name = "some_deployments"
        delete_deployments(namespace_name)

        delete.assert_called_once_with(namespace=namespace_name)
        waiting.assert_called_once()

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch(
        "zelt.kubernetes.client.ExtensionsV1beta1Api.delete_collection_namespaced_deployment"
    )
    def test_it_raises_exception(self, delete, waiting):
        delete.side_effect = ApiException()

        with pytest.raises(ApiException):
            delete_deployments("some_deployments")

        delete.assert_called_once()
        waiting.assert_not_called()

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch(
        "zelt.kubernetes.client.ExtensionsV1beta1Api.delete_collection_namespaced_deployment"
    )
    def test_it_skips_deletion_when_deployments_not_found(self, delete, waiting):
        delete.side_effect = ApiException(status=STATUS_NOT_FOUND)

        result = delete_deployments("some_deployments")

        delete.assert_called_once()
        waiting.assert_not_called()
        assert result is None


class TestListControllerPod:
    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CoreV1Api")
    def test_it_calls_kubernetes_api(self, core_api, *_):
        manifest = Manifest(
            body={
                "kind": "deployment",
                "metadata": {
                    "name": "a_deployment",
                    "namespace": "a_namespace",
                    "labels": {"role": "controller", "application": "an_application"},
                },
            }
        )
        _list_pod(manifest.namespace, manifest.labels)
        core_api().list_namespaced_pod.assert_called_with(
            namespace=manifest.namespace, label_selector=manifest.labels
        )

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CoreV1Api")
    def test_it_raises_exception(self, core_api, *_):
        manifest = Manifest(
            body={
                "kind": "deployment",
                "metadata": {
                    "name": "a_deployment",
                    "namespace": "a_namespace",
                    "labels": {"role": "controller", "application": "an_application"},
                },
            }
        )
        core_api().list_namespaced_pod.side_effect = ApiException(MagicMock())
        with pytest.raises(ApiException):
            _list_pod(manifest.namespace, manifest.labels)


class TestCreateService:
    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CoreV1Api")
    def test_it_calls_kubernetes_api(self, core_api, *_):
        manifest = Manifest(
            body={
                "kind": "service",
                "metadata": {
                    "name": "a_service",
                    "namespace": "a_namespace",
                    "labels": {"application": "an_application"},
                },
            }
        )
        create_service(manifest)
        core_api().create_namespaced_service.assert_called_with(
            namespace=manifest.namespace, body=manifest.body
        )

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CoreV1Api")
    def test_it_raises_exception(self, core_api, *_):
        manifest = Manifest(
            body={
                "kind": "service",
                "metadata": {
                    "name": "a_service",
                    "namespace": "a_namespace",
                    "labels": {"application": "an_application"},
                },
            }
        )
        core_api().create_namespaced_service.side_effect = ApiException(MagicMock())
        with pytest.raises(ApiException):
            create_service(manifest)


class TestDeleteService:
    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespaced_service")
    def test_it_calls_kubernetes_api(self, delete, waiting):
        service_name = "a_service"
        namespace_name = "a_namespace"
        delete_service(service_name, namespace_name)
        delete.assert_called_once_with(
            name=service_name, namespace=namespace_name, body=DEFAULT_DELETE_OPTIONS
        )
        waiting.assert_called_once()

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespaced_service")
    def test_it_skips_deletion_when_service_not_found(self, delete, waiting):
        delete.side_effect = ApiException(status=STATUS_NOT_FOUND)

        result = delete_service("a_service", "a_namespace")

        delete.assert_called_once()
        waiting.assert_not_called()
        assert result is None

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespaced_service")
    def test_it_raises_exception(self, delete, waiting):
        delete.side_effect = ApiException()

        with pytest.raises(ApiException):
            delete_service("a_service", "a_namespace")

        delete.assert_called_once()
        waiting.assert_not_called()


class TestCreateIngress:
    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api")
    def test_it_calls_kubernetes_api(self, extensions_api, *_):
        manifest = Manifest(
            body={
                "kind": "ingress",
                "metadata": {
                    "name": "an_ingress",
                    "namespace": "a_namespace",
                    "labels": {"application": "an_application"},
                },
            }
        )
        create_ingress(manifest)
        extensions_api().create_namespaced_ingress.assert_called_with(
            namespace=manifest.namespace, body=manifest.body
        )

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api")
    def test_it_raises_exception(self, extensions_api, *_):
        extensions_api().create_namespaced_ingress.side_effect = ApiException(
            MagicMock()
        )
        manifest = Manifest(
            body={
                "kind": "ingress",
                "metadata": {
                    "name": "an_ingress",
                    "namespace": "a_namespace",
                    "labels": {"application": "an_application"},
                },
            }
        )
        with pytest.raises(ApiException):
            create_ingress(manifest)


class TestDeleteIngress:
    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api.delete_namespaced_ingress")
    def test_it_calls_kubernetes_api(self, delete, waiting):
        ingress_name = "an_ingress"
        namespace_name = "a_namespace"
        delete_ingress(ingress_name, namespace_name)
        delete.assert_called_once_with(
            name=ingress_name, namespace=namespace_name, body=DEFAULT_DELETE_OPTIONS
        )
        waiting.assert_called_once()

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api.delete_namespaced_ingress")
    def test_it_skips_deletion_when_ingress_not_found(self, delete, waiting):
        delete.side_effect = ApiException(status=STATUS_NOT_FOUND)

        result = delete_ingress("an_ingress", "a_namespace")

        delete.assert_called_once()
        waiting.assert_not_called()
        assert result is None

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.ExtensionsV1beta1Api.delete_namespaced_ingress")
    def test_it_raises_exception(self, delete, waiting):
        delete.side_effect = ApiException()

        with pytest.raises(ApiException):
            delete_ingress("an_ingress", "a_namespace")

        delete.assert_called_once()
        waiting.assert_not_called()
