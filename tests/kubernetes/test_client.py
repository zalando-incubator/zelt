from typing import List
from unittest.mock import MagicMock, patch

import pytest
from kubernetes.client import V1Namespace
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
    try_creating_custom_objects,
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
    @patch("zelt.kubernetes.client.AppsV1Api")
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
    @patch("zelt.kubernetes.client.AppsV1Api")
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

    @patch("zelt.kubernetes.client.AppsV1Api.read_namespaced_deployment")
    @patch("zelt.kubernetes.client.AppsV1Api.replace_namespaced_deployment")
    def test_it_redeploys_when_given_a_positive_number_of_replicas(self, replace, read):
        manifest = MagicMock()
        rescale_deployment(manifest, 2)
        read.assert_called_once()
        replace.assert_called_once()


class TestDeleteDeployments:
    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.AppsV1Api.delete_collection_namespaced_deployment")
    def test_it_calls_kubernetes_api(self, delete, waiting, *_):
        namespace_name = "some_deployments"
        delete_deployments(namespace_name)

        delete.assert_called_once_with(namespace=namespace_name)
        waiting.assert_called_once()

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.AppsV1Api.delete_collection_namespaced_deployment")
    def test_it_raises_exception(self, delete, waiting):
        delete.side_effect = ApiException()

        with pytest.raises(ApiException):
            delete_deployments("some_deployments")

        delete.assert_called_once()
        waiting.assert_not_called()

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.AppsV1Api.delete_collection_namespaced_deployment")
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
    @patch("zelt.kubernetes.client.NetworkingV1beta1Api")
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
    @patch("zelt.kubernetes.client.NetworkingV1beta1Api")
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
    @patch("zelt.kubernetes.client.NetworkingV1beta1Api.delete_namespaced_ingress")
    def test_it_calls_kubernetes_api(self, delete, waiting):
        ingress_name = "an_ingress"
        namespace_name = "a_namespace"
        delete_ingress(ingress_name, namespace_name)
        delete.assert_called_once_with(
            name=ingress_name, namespace=namespace_name, body=DEFAULT_DELETE_OPTIONS
        )
        waiting.assert_called_once()

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.NetworkingV1beta1Api.delete_namespaced_ingress")
    def test_it_skips_deletion_when_ingress_not_found(self, delete, waiting):
        delete.side_effect = ApiException(status=STATUS_NOT_FOUND)

        result = delete_ingress("an_ingress", "a_namespace")

        delete.assert_called_once()
        waiting.assert_not_called()
        assert result is None

    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch("zelt.kubernetes.client.NetworkingV1beta1Api.delete_namespaced_ingress")
    def test_it_raises_exception(self, delete, waiting):
        delete.side_effect = ApiException()

        with pytest.raises(ApiException):
            delete_ingress("an_ingress", "a_namespace")

        delete.assert_called_once()
        waiting.assert_not_called()


class TestCreateCustomResources:
    @pytest.fixture()
    def manifests(self) -> List[Manifest]:
        manifest_a = Manifest(
            body={
                "apiVersion": "zalando.org/v1",
                "kind": "ZalandoCustomResource",
                "metadata": {
                    "name": "a_surprise",
                    "namespace": "a_namespace",
                    "labels": {"application": "an_application"},
                },
            }
        )
        manifest_b = Manifest(
            body={
                "apiVersion": "example.com/v2",
                "kind": "ExampleCustomResource",
                "metadata": {
                    "name": "a_surprise",
                    "namespace": "a_namespace",
                    "labels": {"application": "an_application"},
                },
            }
        )
        manifest_c = Manifest(
            body={
                "apiVersion": "example.com/v2",
                "kind": "ClusterCustomResource",
                "metadata": {
                    "name": "a_surprise",
                    "labels": {"application": "an_application"},
                },
            }
        )
        return [manifest_a, manifest_b, manifest_c]

    @pytest.fixture()
    def crds(self) -> List[MagicMock]:
        crd_manifest_a = MagicMock()
        crd_manifest_a.spec.names.kind = "ZalandoCustomResource"
        crd_manifest_a.spec.names.plural = "zalandocustomresources"
        crd_manifest_a.spec.scope = "Namespaced"

        crd_manifest_b = MagicMock()
        crd_manifest_b.spec.names.kind = "ExampleCustomResource"
        crd_manifest_b.spec.names.plural = "examplecustomresources"
        crd_manifest_b.spec.scope = "Namespaced"

        crd_cluster_manifest = MagicMock()
        crd_cluster_manifest.spec.names.kind = "ClusterCustomResource"
        crd_cluster_manifest.spec.names.plural = "clustercustomresources"
        crd_cluster_manifest.spec.scope = "Cluster"

        return [crd_manifest_a, crd_manifest_b, crd_cluster_manifest]

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CustomObjectsApi.create_namespaced_custom_object")
    @patch(
        "zelt.kubernetes.client.ApiextensionsV1beta1Api.list_custom_resource_definition"
    )
    def test_it_fetches_available_crds_once(
        self, list_crds, create_custom_objects, config, manifests, crds
    ):
        try_creating_custom_objects(manifests)
        list_crds.assert_called_once()

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CustomObjectsApi")
    @patch(
        "zelt.kubernetes.client.ApiextensionsV1beta1Api.list_custom_resource_definition"
    )
    def test_it_creates_supported_custom_resources(
        self,
        list_crds,
        custom_objects_api,
        config,
        manifests: List[Manifest],
        crds: List[MagicMock],
    ):
        # All 3 CRDs are available in the cluster
        list_crds.return_value = MagicMock(items=crds)
        # Zelt tries to deploy only the namespaced ones
        # (without a CustomClusterResource)
        try_creating_custom_objects(manifests[:2])

        custom_objects_api().create_namespaced_custom_object.assert_any_call(
            namespace=manifests[0].namespace,
            body=manifests[0].body,
            group="zalando.org",
            version="v1",
            plural="zalandocustomresources",
        )
        custom_objects_api().create_namespaced_custom_object.assert_any_call(
            namespace=manifests[1].namespace,
            body=manifests[1].body,
            group="example.com",
            version="v2",
            plural="examplecustomresources",
        )

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CustomObjectsApi")
    @patch(
        "zelt.kubernetes.client.ApiextensionsV1beta1Api.list_custom_resource_definition"
    )
    def test_it_ignores_unsupported_resources(
        self, list_crds, custom_objects_api, config, manifests, crds, caplog
    ):
        # ZalandoCustomResource is the only available CRD in the cluster
        list_crds.return_value = MagicMock(items=[crds[0]])
        # Zelt tries to deploy ZalandoCustomResource and ExampleCustomResource
        try_creating_custom_objects(manifests)

        custom_objects_api().create_namespaced_custom_object.assert_called_once()
        custom_objects_api().create_namespaced_custom_object.assert_called_with(
            namespace=manifests[0].namespace,
            body=manifests[0].body,
            group="zalando.org",
            version="v1",
            plural="zalandocustomresources",
        )
        assert any(
            "Unsupported custom manifest" in r.msg for r in caplog.records
        ), "an error should be logged"

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CustomObjectsApi")
    @patch(
        "zelt.kubernetes.client.ApiextensionsV1beta1Api.list_custom_resource_definition"
    )
    def test_it_ignores_non_namespaced_crds(
        self, list_crds, custom_objects_api, config, manifests, crds, caplog
    ):
        # All 3 CRDs are available in the cluster
        list_crds.return_value = MagicMock(items=crds)
        # Zelt tries to deploy a ClusterCustomResource
        try_creating_custom_objects([manifests[2]])

        custom_objects_api().create_namespaced_custom_object.assert_not_called()
        assert any(
            "Non-namespaced resources are not supported" in r.msg
            for r in caplog.records
        ), "an error should be logged"

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CustomObjectsApi")
    @patch(
        "zelt.kubernetes.client.ApiextensionsV1beta1Api.list_custom_resource_definition"
    )
    def test_it_raises_exception_on_fetching_crds(
        self, list_crds, custom_objects_api, config, manifests
    ):
        list_crds.side_effect = ApiException()

        with pytest.raises(ApiException):
            try_creating_custom_objects(manifests)

        list_crds.assert_called_once()
        custom_objects_api().create_namespaced_custom_object.assert_not_called()

    @patch("kubernetes.config.load_kube_config")
    @patch("zelt.kubernetes.client.CustomObjectsApi")
    @patch(
        "zelt.kubernetes.client.ApiextensionsV1beta1Api.list_custom_resource_definition"
    )
    def test_it_raises_exception_on_creating_resources(
        self, list_crds, custom_objects_api, config, manifests, crds
    ):
        list_crds.return_value = MagicMock(items=crds)
        custom_objects_api().create_namespaced_custom_object.side_effect = (
            ApiException()
        )

        with pytest.raises(ApiException):
            try_creating_custom_objects(manifests)

        list_crds.assert_called_once()
