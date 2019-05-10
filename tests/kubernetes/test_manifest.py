import pytest
from pathlib import Path
from zelt.kubernetes.manifest import (
    Manifest,
    ResourceType,
    DeploymentRole,
    ManifestsNotFoundException,
)


@pytest.fixture()
def manifest_file(tmp_path: Path) -> Path:
    manifest_file = Path(tmp_path, "a_manifest.yaml")
    with manifest_file.open("w") as f:
        f.write("kind: Ingress")
    return manifest_file


class TestPropertyKind:
    def test_if_fails_given_no_kind(self):
        manifest = Manifest({})
        with pytest.raises(ValueError):
            manifest.kind

    def test_it_handles_unknown_kinds(self):
        manifest = Manifest({"kind": "some_random_type"})
        assert manifest.kind is ResourceType.OTHER

    def test_it_is_case_insensitive(self):
        manifest = Manifest({"kind": "ingress"})
        assert manifest.kind is ResourceType.INGRESS

    def test_it_returns_a_matching_resource_type_given_a_known_kind(self):
        manifest = Manifest({"kind": "Ingress"})
        assert manifest.kind is ResourceType.INGRESS


class TestPropertyName:
    def test_it_fails_given_no_name(self):
        manifest = Manifest({})
        with pytest.raises(ValueError):
            manifest.name

    def test_it_fails_given_an_empty_name(self):
        manifest = Manifest({"metadata": {"name": ""}})
        with pytest.raises(ValueError):
            manifest.name

    def test_it_returns_a_name_given_a_name(self):
        name = "a_name"
        manifest = Manifest({"metadata": {"name": name}})
        assert manifest.name == name


class TestPropertyNamespace:
    def test_it_fails_given_no_namespace(self):
        manifest = Manifest({"kind": "ingress"})
        with pytest.raises(ValueError):
            manifest.namespace

    def test_it_fails_given_an_empty_namespace(self):
        manifest = Manifest({"kind": "Ingress", "metadata": {"namespace": ""}})
        with pytest.raises(ValueError):
            manifest.namespace

    def test_it_returns_a_namespace_given_a_namespaced_resource(self):
        namespace_name = "a_namespace"
        manifest = Manifest(
            {"kind": "Ingress", "metadata": {"namespace": namespace_name}}
        )
        assert manifest.namespace == namespace_name

    def test_it_returns_a_name_given_a_namespace_kind(self):
        namespace_name = "a_namespace"
        manifest = Manifest({"kind": "Namespace", "metadata": {"name": namespace_name}})
        assert manifest.namespace == namespace_name


class TestPropertyLabels:
    def test_it_fails_given_no_labels(self):
        manifest = Manifest({})
        with pytest.raises(ValueError):
            manifest.labels

    def test_it_returns_a_string_of_labels_given_labels(self):
        manifest = Manifest({"metadata": {"labels": {"a": "label"}}})
        assert manifest.labels == "a=label"


class TestPropertyLabelsDict:
    def test_it_returns_an_empty_dict_given_no_labels(self):
        manifest = Manifest({})
        assert manifest.labels_dict == {}

    def test_it_returns_a_dict_of_labels_given_labels(self):
        manifest = Manifest({"metadata": {"labels": {"a": "label"}}})
        assert manifest.labels_dict == {"a": "label"}


class TestPropertyRole:
    def test_it_handles_unknown_roles(self):
        manifest = Manifest({})
        assert manifest.role == DeploymentRole.OTHER

    def test_it_returns_a_matching_role_given_a_role(self):
        manifest = Manifest({"metadata": {"labels": {"role": "controller"}}})
        assert manifest.role == DeploymentRole.CONTROLLER


class TestPropertyHost:
    def test_it_fails_given_no_host(self):
        manifest = Manifest({})
        with pytest.raises(ValueError):
            manifest.host

    def test_it_returns_a_host_given_a_host(self):
        manifest = Manifest({"spec": {"rules": [{"host": "a_host"}]}})
        assert manifest.host == "a_host"


class TestFromFile:
    def test_creates_a_manifest_from_a_file(self, manifest_file: Path):
        manifest = Manifest.from_file(manifest_file)
        assert manifest.kind == ResourceType.INGRESS


class TestAllFromDirectory:
    def test_it_fails_if_no_files_found(self):
        with pytest.raises(ManifestsNotFoundException):
            Manifest.all_from_directory("not_a_path")

    def test_it_creates_manifests_given_a_directory_of_files(
        self, manifest_file: Path, tmp_path
    ):
        manifests = Manifest.all_from_directory(tmp_path)
        assert manifests[0].kind == ResourceType.INGRESS
