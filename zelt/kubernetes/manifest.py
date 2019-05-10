import logging
import os
from enum import Enum
from pathlib import Path
from typing import NamedTuple, List, Dict

import yaml


class ManifestsNotFoundException(Exception):
    pass


class ResourceType(Enum):
    INGRESS = "Ingress"
    SERVICE = "Service"
    NAMESPACE = "Namespace"
    DEPLOYMENT = "Deployment"
    OTHER = ...


class DeploymentRole(Enum):
    CONTROLLER = "controller"
    WORKER = "worker"
    OTHER = ...


class Manifest(NamedTuple):
    body: dict

    def metadata(self, key: str):
        """
        Returns the value of metadata *key*.

        :raise ValueError: If *key* is not a metadata of this manifest.
        """
        try:
            return self.body["metadata"][key]
        except KeyError:
            raise ValueError(f"no metadata {key!r} in manifest") from None

    def nonempty_string_metadata(self, key: str) -> str:
        """
        Returns the non-empty string corresponding to metadata *key*.

        :raise ValueError: If *key* is not a metadata of this manifest, or if
            its value is not a non-empty string.
        """
        v = self.metadata(key)
        _assert_metadata_type(v, str, key)
        if not v:
            raise ValueError(f"unexpectedly empty string for {key!r} metadata")
        return v

    @property
    def kind(self) -> ResourceType:
        try:
            value = self.body["kind"]
        except KeyError:
            raise ValueError("no kind specified in manifest") from None

        try:
            return ResourceType(value.capitalize())
        except ValueError:
            logging.warning(
                "Unsupported resource type %r converted into %s.",
                value,
                ResourceType.OTHER,
            )
            return ResourceType.OTHER

    @property
    def name(self) -> str:
        return self.nonempty_string_metadata("name")

    @property
    def namespace(self) -> str:
        if self.kind is ResourceType.NAMESPACE:
            return self.name
        return self.nonempty_string_metadata("namespace")

    @property
    def labels(self) -> str:
        key = "labels"
        labels = self.metadata(key)
        _assert_metadata_type(labels, dict, key)
        return ",".join(["{}={}".format(k, v) for k, v in labels.items()])

    @property
    def labels_dict(self) -> Dict[str, str]:
        return dict(self.body.get("metadata", {}).get("labels", {}))

    @property
    def role(self) -> DeploymentRole:
        role = self.labels_dict.get("role", "")
        try:
            return DeploymentRole(role.strip().lower())
        except ValueError:
            return DeploymentRole.OTHER

    @property
    def host(self) -> str:
        pretty_key = "spec.rules[0].host"
        try:
            host = self.body["spec"]["rules"][0]["host"]
        except (KeyError, IndexError):
            raise ValueError(f"no {pretty_key} in manifest")
        _assert_type_as(host, str, f"as {pretty_key} in manifest")
        return host

    @classmethod
    def from_file(cls, file: Path) -> "Manifest":
        """
        :raise ValueError: If no manifest can be read from *file*.
        """
        try:
            body = yaml.safe_load(file.read_text())
        except OSError as err:
            raise ValueError(f"can't read manifest from file {file}") from err
        except yaml.YAMLError as err:
            raise ValueError(f"can't read manifest from non-YAML file {file}") from err
        _assert_type_as(body, dict, f"as top-level manifest object in file {file}")
        return Manifest(body=body)

    @classmethod
    def all_from_directory(cls, manifests_path: os.PathLike) -> List["Manifest"]:
        manifests = []
        for path in Path(manifests_path).glob("*"):
            if path.is_file():
                try:
                    manifests.append(Manifest.from_file(path))
                except ValueError as err:
                    logging.warning("Ignoring %s: %s.", path, err)
        if not manifests:
            raise ManifestsNotFoundException(
                f"Could not load any manifest files from {manifests_path}"
            )
        return manifests


def _assert_type_as(value, t: type, as_msg: str) -> None:
    if not isinstance(value, t):
        raise ValueError(f"expected a {t.__qualname__} but got {value!r} {as_msg}")


def _assert_metadata_type(value, t: type, key: str) -> None:
    _assert_type_as(value, t, f"as {key!r} metadata")
