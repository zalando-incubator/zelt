import pytest

from pathlib import Path

from zelt.kubernetes.manifest_set import from_directory


@pytest.fixture()
def unique_manifests(tmp_path: Path) -> None:
    kinds = ["namespace", "service", "ingress"]
    for kind in kinds:
        manifest_file = Path(tmp_path, f"{kind}.yaml")
        with manifest_file.open("w") as f:
            f.write(f"kind: {kind}\nname: {kind}")


@pytest.fixture()
def controller_deployment(tmp_path: Path) -> None:
    controller_deployment = Path(tmp_path, "controller_deployment.yaml")
    with controller_deployment.open("w") as f:
        f.write(
            "kind: deployment\nname: controller_deployment\nmetadata:\n  labels:\n    role: controller"
        )


@pytest.fixture()
def worker_deployment(tmp_path: Path) -> None:
    worker_deployment = Path(tmp_path, "worker_deployment.yaml")
    with worker_deployment.open("w") as f:
        f.write(
            "kind: deployment\nname: worker_deployment\nmetadata:\n  labels:\n    role: worker"
        )


class TestFromDirectory:
    def test_it_fails_when_not_given_all_required_manifests(self, tmp_path):
        manifest_file = Path(tmp_path, "namespace.yaml")
        with manifest_file.open("w") as f:
            f.write("kind: namespace\nname: a_namespace")

        with pytest.raises(ValueError, match="got 0"):
            from_directory(tmp_path)

    def test_it_fails_when_given_more_than_one_of_the_uniquely_required_manifests(
        self, unique_manifests, tmp_path
    ):
        manifest_file_duplicate = Path(tmp_path, "duplicate_namespace.yaml")
        with manifest_file_duplicate.open("w") as f:
            f.write("kind: namespace\nname: a_namespace")

        with pytest.raises(ValueError, match="got 2"):
            from_directory(tmp_path)

    def test_it_fails_when_given_only_a_worker_deployment(
        self, unique_manifests, worker_deployment, tmp_path
    ):
        with pytest.raises(ValueError, match="controller"):
            from_directory(tmp_path)

    def test_it_fails_when_given_deployment_manifests_without_all_required_roles(
        self, unique_manifests, worker_deployment, tmp_path
    ):
        duplicate_deployment = Path(tmp_path, "duplicate_deployment.yaml")
        with duplicate_deployment.open("w") as f:
            f.write(
                "kind: deployment\nname: duplicate\nmetadata:\n  labels:\n    role: worker"
            )

        with pytest.raises(ValueError, match="roles covering"):
            from_directory(tmp_path)

    def test_it_fails_when_given_more_than_one_controller_deployment(
        self, unique_manifests, controller_deployment, worker_deployment, tmp_path
    ):
        duplicate_deployment = Path(tmp_path, "duplicate_deployment.yaml")
        with duplicate_deployment.open("w") as f:
            f.write(
                "kind: deployment\nname: duplicate\nmetadata:\n  labels:\n    role: controller"
            )
        with pytest.raises(ValueError, match="controller"):
            from_directory(tmp_path)

    def test_it_fails_when_given_more_than_one_worker_deployment(
        self, unique_manifests, controller_deployment, worker_deployment, tmp_path
    ):
        duplicate_deployment = Path(tmp_path, "duplicate_deployment.yaml")
        with duplicate_deployment.open("w") as f:
            f.write(
                "kind: deployment\nname: duplicate\nmetadata:\n  labels:\n    role: worker"
            )
        with pytest.raises(ValueError, match="worker"):
            from_directory(tmp_path)

    def test_it_returns_a_set_of_manifests_given_a_directory_of_all_manifest_types(
        self, unique_manifests, controller_deployment, worker_deployment, tmp_path
    ):
        manifest_set = from_directory(tmp_path)
        assert manifest_set.namespace is not None
        assert manifest_set.service is not None
        assert manifest_set.ingress is not None
        assert manifest_set.controller is not None
        assert manifest_set.worker is not None

    def test_it_returns_a_set_of_manifests_given_a_directory_of_manifest_files_without_a_worker_deployment(
        self, unique_manifests, controller_deployment, tmp_path
    ):
        manifest_set = from_directory(tmp_path)
        assert manifest_set.namespace is not None
        assert manifest_set.service is not None
        assert manifest_set.ingress is not None
        assert manifest_set.controller is not None
        assert manifest_set.worker is None
