# pylint: skip-file
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from kubernetes.client.rest import ApiException

import zelt
from zelt.kubernetes.storage.configmap import ConfigmapStorage
from zelt.kubernetes.storage.s3 import S3Storage
from zelt.zelt import StorageMethod, HARFilesNotFoundException


class TestDeploy:
    def test_it_exits_when_not_given_manifests(self):
        with pytest.raises(ValueError, match="[Mm]issing required"):
            zelt.deploy(
                locustfile="a_locustfile",
                worker_pods=0,
                manifests_path=None,
                clean=False,
                storage_method=StorageMethod.CONFIGMAP,
                local=False,
            )

    @patch("subprocess.run")
    def test_it_deploys_locust_locally_when_given_local_option_and_no_manifests(
        self, subprocess
    ):
        zelt.deploy(
            locustfile="a_locustfile",
            worker_pods=0,
            manifests_path=None,
            clean=False,
            storage_method=StorageMethod.CONFIGMAP,
            local=True,
        )
        subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_it_defaults_to_deploying_locally_when_given_manifest_and_local_options(
        self, subprocess
    ):
        zelt.deploy(
            locustfile="a_locustfile",
            worker_pods=0,
            manifests_path="some_manifests",
            clean=False,
            storage_method=StorageMethod.CONFIGMAP,
            local=True,
        )
        subprocess.assert_called_once()

    @patch("zelt.zelt._deploy_in_kubernetes")
    def test_it_deploys_locust_in_kubernetes_when_given_manifests(
        self, deploy_in_kubernetes
    ):
        zelt.deploy(
            locustfile="a_locustfile",
            worker_pods=0,
            manifests_path="some_manifests",
            clean=False,
            storage_method=StorageMethod.CONFIGMAP,
            local=False,
        )
        deploy_in_kubernetes.assert_called_once()

    def test_it_errors_when_given_a_negative_number_of_worker_pods(self):
        with pytest.raises(ValueError, match="positive number of pods"):
            zelt.deploy(
                locustfile="a_locustfile",
                worker_pods=-1,
                manifests_path="some_manifests",
                clean=False,
                storage_method=StorageMethod.CONFIGMAP,
                local=False,
            )

    @patch("zelt.kubernetes.deployer.create_resources")
    @patch("zelt.kubernetes.deployer.delete_resources")
    @patch("zelt.kubernetes.manifest_set.from_directory")
    @patch(
        "zelt.kubernetes.storage.configmap.ConfigmapStorage.__init__", return_value=None
    )
    def test_it_does_not_clean_before_deployment_when_not_given_clean_option(
        self, _cm_init, _from_dir, delete, create
    ):
        zelt.deploy(
            locustfile="a_locustfile",
            worker_pods=0,
            manifests_path="some_manifests",
            clean=False,
            storage_method=StorageMethod.CONFIGMAP,
            local=False,
        )
        delete.assert_not_called()
        create.assert_called_once()

    @patch("zelt.kubernetes.deployer.create_resources")
    @patch("zelt.kubernetes.deployer.delete_resources")
    @patch("zelt.kubernetes.manifest_set.from_directory")
    @patch(
        "zelt.kubernetes.storage.configmap.ConfigmapStorage.__init__", return_value=None
    )
    def test_it_cleans_before_deployment_when_given_clean_option(
        self, _cm_init, _from_dir, delete, create
    ):
        zelt.deploy(
            locustfile="a_locustfile",
            worker_pods=0,
            manifests_path="some_manifests",
            clean=True,
            storage_method=StorageMethod.CONFIGMAP,
            local=False,
        )
        delete.assert_called_once()
        create.assert_called_once()


class TestRescale:
    def test_it_exits_when_not_given_manifests(self):
        with pytest.raises(ValueError, match="[Mm]issing required"):
            zelt.rescale(manifests_path=None, worker_pods=0)

    def test_it_exits_when_given_a_negative_number_of_worker_pods(self):
        with pytest.raises(ValueError, match="positive number of pods"):
            zelt.rescale(manifests_path="some_manifests", worker_pods=-1)

    @patch("zelt.kubernetes.deployer.rescale_worker_deployment")
    @patch("zelt.kubernetes.manifest_set.from_directory")
    def test_it_calls_rescale_worker_deployment_when_given_a_positive_number_of_worker_pods(
        self, rescale_worker_deployment, _from_dir
    ):
        zelt.rescale(manifests_path="some_manifests", worker_pods=0)
        rescale_worker_deployment.assert_called_once()


class TestDelete:
    def test_it_exits_when_not_given_manifests(self):
        with pytest.raises(ValueError, match="[Mm]issing required"):
            zelt.delete(manifests_path=None, storage_method=StorageMethod.CONFIGMAP)

    @patch("zelt.kubernetes.deployer.delete_resources")
    @patch("zelt.kubernetes.manifest_set.from_directory")
    def test_it_calls_delete_resources(self, delete_resources, _from_dir):
        zelt.delete(
            manifests_path="some_manifests", storage_method=StorageMethod.CONFIGMAP
        )
        delete_resources.assert_called_once()


class TestInvokeTransformer:
    @patch("pathlib.Path.open")
    def test_it_exits_when_not_given_har_files(self, open):
        with pytest.raises(HARFilesNotFoundException, match="(C|c)ould not load"):
            zelt.invoke_transformer("NOT_A_PATH", MagicMock())

    @patch("pathlib.Path.open")
    @patch("transformer.dump")
    def test_it_calls_transformer(self, transformer, _open, tmp_path):
        zelt.invoke_transformer([tmp_path], MagicMock())
        transformer.assert_called_once()


class TestStorageMethod:
    class TestFromStorageArg:
        def test_it_fails_when_given_unknown_argument(self):
            with pytest.raises(ValueError, match="unknown"):
                StorageMethod.from_storage_arg("bob")

        @pytest.mark.parametrize("arg", ("s3", "S3"))
        def test_it_returns_s3_when_given_s3(self, arg):
            assert StorageMethod.from_storage_arg(arg) is StorageMethod.S3

        @pytest.mark.parametrize("arg", ("configmap", "cm", "ConfigMap", "CM"))
        def test_it_returns_configmap_when_given_configmap_or_cm(self, arg):
            assert StorageMethod.from_storage_arg(arg) is StorageMethod.CONFIGMAP

    class TestBuildStorage:
        @pytest.mark.parametrize(
            "kwargs",
            (
                {"s3_bucket": None, "s3_key": None},
                {"s3_bucket": "a", "s3_key": None},
                {"s3_bucket": None, "s3_key": "a"},
            ),
        )
        def test_it_fails_when_given_s3_but_not_required_args(self, kwargs):
            with pytest.raises(ValueError, match="[Mm]issing required"):
                StorageMethod.S3.build_storage(manifests=MagicMock(), **kwargs)

        @pytest.mark.parametrize(
            "kwargs",
            (
                {"s3_bucket": "a", "s3_key": "b"},
                {"s3_bucket": "a", "s3_key": None},
                {"s3_bucket": None, "s3_key": "a"},
            ),
        )
        def test_it_fails_when_not_given_s3_but_given_s3_args(self, kwargs):
            with pytest.raises(ValueError, match="[uU]nexpected"):
                StorageMethod.CONFIGMAP.build_storage(manifests=MagicMock(), **kwargs)

        def test_it_returns_an_s3storage_when_given_s3_and_s3_args(self):
            assert isinstance(
                StorageMethod.S3.build_storage(
                    manifests=MagicMock(), s3_bucket="a", s3_key="b"
                ),
                S3Storage,
            )

        def test_it_returns_a_configmapstorage_when_given_configmap(self):
            assert isinstance(
                StorageMethod.CONFIGMAP.build_storage(manifests=MagicMock()),
                ConfigmapStorage,
            )
