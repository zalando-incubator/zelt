from collections import defaultdict
from os import PathLike
from typing import NamedTuple, List, Dict, Optional

from zelt.kubernetes.manifest import Manifest, ResourceType, DeploymentRole


class ManifestSet(NamedTuple):
    """
    Result of categorizing the user-provided Kubernetes manifests.
    """

    namespace: Manifest
    service: Manifest
    ingress: Manifest
    controller: Manifest
    worker: Optional[Manifest]


# TOOD: Refactor.
def from_directory(dir_path: PathLike) -> ManifestSet:
    categories: Dict[ResourceType, List[Manifest]] = defaultdict(list)
    for m in Manifest.all_from_directory(dir_path):
        categories[m.kind].append(m)

    # Sanity checks for manifests that must be given exactly once.
    unique_resources = (
        ResourceType.NAMESPACE,
        ResourceType.SERVICE,
        ResourceType.INGRESS,
    )
    for kind in unique_resources:
        wanted = f"resource of kind {kind.value!r}"
        try:
            manifests = categories[kind]
        except KeyError:
            raise ValueError(f"Missing required {wanted}.") from None
        if len(manifests) != 1:
            raise ValueError(f"Expected exactly one {wanted} but got {len(manifests)}.")

    # Sanity checks for deployment manifests.
    deploy_rk = f"resource of kind {ResourceType.DEPLOYMENT.value!r}"
    try:
        deployments = categories[ResourceType.DEPLOYMENT]
    except KeyError:
        raise ValueError(f"Missing required {deploy_rk}.") from None
    if len(deployments) > 1:
        actual_roles = {d.role for d in deployments}
        expected_roles = {DeploymentRole.CONTROLLER, DeploymentRole.WORKER}
        if not expected_roles.issubset(actual_roles):
            raise ValueError(
                "Distributed Locust deployments must have roles "
                f"covering {[r.value for r in expected_roles]}, "
                f"got only {[r.value for r in actual_roles]}."
            )

    controllers = [d for d in deployments if d.role is DeploymentRole.CONTROLLER]
    if len(controllers) != 1:
        raise ValueError(
            "Expected exactly one deployment with role "
            f"{DeploymentRole.CONTROLLER.value!r}."
        )

    workers = [d for d in deployments if d.role is DeploymentRole.WORKER]
    if len(workers) > 1:
        raise ValueError(
            f"Expected at most one deployment with role {DeploymentRole.WORKER.value!r}."
        )

    return ManifestSet(
        namespace=categories[ResourceType.NAMESPACE][0],
        service=categories[ResourceType.SERVICE][0],
        ingress=categories[ResourceType.INGRESS][0],
        controller=controllers[0],
        worker=workers[0] if workers else None,
    )
