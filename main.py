"""
Zelt: Orchestrate Locust deployments in Kubernetes.

Usage:
    zelt from-har <har-files>... -m <manifests>
                                 [-w <pods>]
                                 [--storage <method>]
                                 [--s3-bucket <name> --s3-key <name>]
                                 [-p <plugin-name>]...
                                 [--clean]
                                 [--logging <level>]
    zelt from-har <har-files>... --local
                                 [-p <plugin-name>]...
                                 [--logging <level>]
    zelt from-har --config <file>
                  [--local]
                  [--clean]
                  [--logging <level>]
    zelt from-locustfile <locustfile> -m <manifests>
                                      [-w <pods>]
                                      [--storage <method>]
                                      [--s3-bucket <name> --s3-key <name>]
                                      [--clean]
                                      [--logging <level>]
    zelt from-locustfile <locustfile> --local
                                      [--logging <level>]
    zelt from-locustfile --config <file>
                         [--local]
                         [--clean]
                         [--logging <level>]
    zelt rescale <required-pods> -m <manifests>
                                 [--logging <level>]
    zelt rescale <required-pods> --config <file>
                                 [--logging <level>]
    zelt delete -m <manifests> [--storage <method>]
                               [--s3-bucket <name> --s3-key <name>]
                               [--logging <level>]
    zelt delete --config <file>
                [--logging <level>]
    zelt --help
    zelt --version

Options:
    -h, --help                               Show this screen.
    -v, --version                            Show version.
    -p, --transformer-plugins=<plugin-name>  Module name of Transformer plugin (repeatable).
    -m, --manifests=<manifests>              Path to manifest files.
    -w, --worker-pods=<pods>                 Number of worker pods to deploy [default: 1].
    -s, --storage=<method>                   Remote locustfile storage method (S3 or ConfigMap)
                                               [default: ConfigMap].
    --s3-bucket=<name>                       Name of S3 bucket for remote locustfile storage.
    --s3-key=<name>                          Name of S3 key for remote locustfile storage.
    -c, --clean                              Delete and redeploy remote resources.
    -l, --local                              Run Locust locally.
    --logging=<level>                        Set logging level (INFO, DEBUG, or ERROR) [default: INFO].
    --config=<file>                          Optional configuration file specifying options.
"""


import logging
import os
import pkg_resources
import sys
import yaml
from docopt import docopt
from pathlib import Path
from typing import NamedTuple, Sequence

import zelt
from zelt.zelt import StorageMethod


class Config(NamedTuple):

    from_har: bool
    from_locustfile: bool
    rescale: bool
    delete: bool
    har_files: Sequence[os.PathLike]
    locustfile: os.PathLike
    transformer_plugins: Sequence[str]
    manifests: os.PathLike
    worker_pods: int
    required_pods: int
    storage: str
    s3_bucket: str
    s3_key: str
    clean: bool
    local: bool
    logging: str


def cli():
    """
    Entrypoint for Zelt.
    """

    # Disable deprecation warning coming from Kubernetes client's YAML loading.
    # See https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation
    yaml.warnings({"YAMLLoadWarning": False})

    config = _load_config(docopt(__doc__, version=_version()))

    logging.basicConfig(level=config.logging)

    if config.from_har:
        config = config._replace(
            locustfile=zelt.invoke_transformer(
                paths=config.har_files, plugin_names=config.transformer_plugins
            )
        )
        _deploy(config)

    if config.from_locustfile:
        _deploy(config)

    if config.rescale:
        _rescale(config)

    if config.delete:
        _delete(config)


def _version() -> str:
    return pkg_resources.get_distribution("zelt").version


def _deploy(config: Config) -> None:
    """
    Deploys Locust.
    """
    try:
        zelt.deploy(
            config.locustfile,
            int(config.worker_pods),
            config.manifests,
            config.clean,
            StorageMethod.from_storage_arg(config.storage),
            config.local,
            config.s3_bucket,
            config.s3_key,
        )
    except Exception as e:
        logging.fatal("Error: %s", e)
        exit(1)


def _rescale(config: Config) -> None:
    """
    Rescales a worker deployment.
    """
    try:
        zelt.rescale(config.manifests, int(config.required_pods))
    except Exception as e:
        logging.fatal("Error: %s", e)
        exit(1)


def _delete(config: Config) -> None:
    """
    Deletes a deployment.
    """
    try:
        zelt.delete(
            config.manifests,
            StorageMethod.from_storage_arg(config.storage),
            config.s3_bucket,
            config.s3_key,
        )
    except Exception as e:
        logging.fatal("Error: %s", e)
        exit(1)


def _load_config(config: dict) -> Config:
    """
    Loads config from command-line or file.
    """
    config = _normalise_config(config)

    if config["config"]:
        config = {**config, **yaml.safe_load(Path(config["config"]).read_text())}

    return Config(
        from_har=config["from-har"],
        from_locustfile=config["from-locustfile"],
        rescale=config["rescale"],
        delete=config["delete"],
        har_files=config.get("har-files", []),
        locustfile=config["locustfile"],
        transformer_plugins=config.get("transformer-plugins", []),
        manifests=config["manifests"],
        worker_pods=config["worker-pods"],
        required_pods=config["required-pods"],
        storage=config["storage"],
        s3_bucket=config["s3-bucket"],
        s3_key=config["s3-key"],
        clean=config["clean"],
        local=config["local"],
        logging=config["logging"],
    )


def _normalise_config(config: dict) -> dict:
    """
    Removes special characters from config keys.
    """
    normalised_config = {}
    for k in config:
        normalised_config[
            k.replace("--", "").replace("<", "").replace(">", "")
        ] = config[k]
    return normalised_config
