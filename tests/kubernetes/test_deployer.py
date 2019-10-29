from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from zelt.kubernetes import deployer
from zelt.kubernetes.manifest import Manifest
from zelt.kubernetes.manifest_set import ManifestSet
from zelt.kubernetes.storage.configmap import ConfigmapStorage


@pytest.fixture()
def manifest_set(tmp_path: Path) -> ManifestSet:
    manifest_file = Path(tmp_path, "a_manifest.yaml")
    with manifest_file.open("w") as f:
        f.write(
            """
        apiVersion: apps/v1
        kind: Deployment
        metadata:
            name: a_controller
            namespace: some_namespace
            labels:
                application: some_application
                role: controller
        spec:
            replicas: 1
            selector:
                matchLabels:
                    application: some_application
                    role: controller"""
        )
    return ManifestSet(
        namespace=Manifest.from_file(manifest_file),
        service=Manifest.from_file(manifest_file),
        ingress=Manifest.from_file(manifest_file),
        controller=Manifest.from_file(manifest_file),
        worker=Manifest.from_file(manifest_file),
    )


@pytest.fixture()
def locustfile(tmp_path: Path) -> Path:
    locustfile = Path(tmp_path, "some.py")
    with locustfile.open("w") as f:
        f.write("")
    return locustfile


@pytest.fixture()
def configmap_storage() -> ConfigmapStorage:
    return ConfigmapStorage(namespace="a-namespace", labels={"some": "labels"})


class TestCreateResources:
    @patch("zelt.kubernetes.client.config")
    @patch("zelt.kubernetes.client.CoreV1Api.create_namespace")
    @patch("zelt.kubernetes.client.CoreV1Api.create_namespaced_service")
    @patch("zelt.kubernetes.client.CoreV1Api.create_namespaced_config_map")
    @patch("zelt.kubernetes.client.NetworkingV1beta1Api.create_namespaced_ingress")
    @patch("zelt.kubernetes.client.AppsV1Api.create_namespaced_deployment")
    @patch("zelt.kubernetes.client.wait_until_pod_ready")
    def test_it_deploys_all_given_manifests_and_configmap(
        self,
        wait,
        create_deployment,
        create_ingress,
        create_configmap,
        create_service,
        create_namespace,
        config,
        configmap_storage: ConfigmapStorage,
        locustfile: Path,
        manifest_set: ManifestSet,
    ):
        deployer.create_resources(
            ms=manifest_set, storage=configmap_storage, locustfile=locustfile
        )
        create_namespace.assert_called_once()
        create_service.assert_called_once()
        create_configmap.assert_called_once()
        create_ingress.assert_called_once()
        assert create_deployment.call_count == 2

    @patch("zelt.kubernetes.client.config")
    @patch("zelt.kubernetes.client.CoreV1Api.create_namespace")
    @patch("zelt.kubernetes.client.CoreV1Api.create_namespaced_service")
    @patch("zelt.kubernetes.client.NetworkingV1beta1Api.create_namespaced_ingress")
    @patch("zelt.kubernetes.client.AppsV1Api.create_namespaced_deployment")
    @patch("zelt.kubernetes.client.wait_until_pod_ready")
    def test_it_does_not_deploy_workers_when_given_none(
        self,
        wait,
        create_deployment,
        create_ingress,
        create_service,
        create_namespace,
        config,
        manifest_set: ManifestSet,
    ):
        manifest_set = manifest_set._replace(worker=None)
        deployer.create_resources(
            ms=manifest_set, storage=MagicMock(), locustfile=MagicMock()
        )
        create_namespace.assert_called_once()
        create_service.assert_called_once()
        create_ingress.assert_called_once()
        assert create_deployment.call_count == 1


class TestDeleteResources:
    @patch("zelt.kubernetes.client.config")
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespace")
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespaced_service")
    @patch("zelt.kubernetes.client.CoreV1Api.delete_namespaced_config_map")
    @patch("zelt.kubernetes.client.NetworkingV1beta1Api.delete_namespaced_ingress")
    @patch("zelt.kubernetes.client.await_no_resources_found")
    @patch(
        "zelt.kubernetes.client.AppsV1Api.delete_collection_namespaced_deployment"
    )
    def test_it_deletes_all_given_manifests_and_configmap(
        self,
        delete_deployments,
        wait,
        delete_ingress,
        delete_configmap,
        delete_service,
        delete_namespace,
        config,
        configmap_storage: ConfigmapStorage,
        manifest_set: ManifestSet,
    ):
        deployer.delete_resources(ms=manifest_set, storage=configmap_storage)
        delete_namespace.assert_called_once()
        delete_service.assert_called_once()
        delete_configmap.assert_called_once()
        delete_ingress.assert_called_once()
        delete_deployments.assert_called_once()


class TestUpdateWorkerPods:
    def test_it_does_nothing_if_no_worker_manifest_exists(
        self, manifest_set: ManifestSet
    ):
        manifest_set = manifest_set._replace(worker=None)
        deployer.update_worker_pods(manifest_set, 2)
        assert manifest_set.worker is None

    def test_it_replaces_the_number_of_worker_replicas_in_place(
        self, manifest_set: ManifestSet
    ):
        original_replicas = int(manifest_set.worker.body["spec"]["replicas"])
        expected_replicas = original_replicas + 1

        deployer.update_worker_pods(manifest_set, expected_replicas)

        assert int(manifest_set.worker.body["spec"]["replicas"]) == expected_replicas

    def test_it_only_updates_worker_manifest_replicas(self, manifest_set):
        controller_replicas = int(manifest_set.controller.body["spec"]["replicas"])

        deployer.update_worker_pods(manifest_set, controller_replicas + 1)

        assert (
            int(manifest_set.controller.body["spec"]["replicas"]) == controller_replicas
        )


class TestRescaleWorkerDeployment:
    @patch("zelt.kubernetes.client.AppsV1Api.replace_namespaced_deployment")
    def test_it_does_not_rescale_when_not_given_a_worker_manifest(
        self, rescale, manifest_set: ManifestSet
    ):
        manifest_set = manifest_set._replace(worker=None)
        deployer.rescale_worker_deployment(manifest_set, 0)
        rescale.assert_not_called()

    @patch("zelt.kubernetes.client.config")
    @patch("zelt.kubernetes.client.AppsV1Api.read_namespaced_deployment")
    @patch("zelt.kubernetes.client.AppsV1Api.replace_namespaced_deployment")
    def test_it_rescales_when_given_a_worker_manifest(
        self, rescale, _read, _config, manifest_set: ManifestSet
    ):
        deployer.rescale_worker_deployment(manifest_set, 0)
        rescale.assert_called_once()
