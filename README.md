<p align="center"><img src="images/zelt.png"/></div>

## Zalando end-to-end load tester

A **command-line tool** for orchestrating the deployment of [Locust][] in [Kubernetes][].

Use it in conjunction with [Transformer][] to run large-scale end-to-end load testing of your website.

### Prerequistes

- [Python 3.6+][]

### Installation

Install using pip:

```bash
pip install zelt
```

### Usage

Example HAR files, locustfile, and manifests are included in the `examples/` directory, try them out.

**N.B** The cluster to deploy to is determined by your currently configured context. Ensure you are [using the correct cluster][] before using Zelt.

#### Locustfile as input

Zelt can deploy Locust with a locustfile to a cluster:

```bash
zelt from-locustfile PATH_TO_LOCUSTFILE --manifests PATH_TO_MANIFESTS
```

#### HAR files(s) as input

Zelt can transform HAR file(s) into a locustfile and deploy it along with Locust to a cluster:

```bash
zelt from-har PATH_TO_HAR_FILES --manifests PATH_TO_MANIFESTS
```

**N.B** This requires [Transformer][] to be installed. For more information about Transformer, please refer to its [documentation][].

#### Rescale a deployment

Zelt can rescale the number of [workers][] in a deployment it has made to a cluster:

```bash
zelt rescale NUMBER_OF_WORKERS --manifests PATH_TO_MANIFESTS
```

#### Delete a deployment

Zelt can delete deployments it has made from a cluster:

```bash
zelt delete --manifests PATH_TO_MANIFESTS
```

#### Run Locust locally

Zelt can also run Locust locally by providing the `--local/-l` flag to either the `from-har` or `from-locustfile` command e.g.:

```bash
zelt from-locustfile PATH_TO_LOCUSTFILE --local
```

#### Use S3 for locustfile storage

By default, Zelt uses a ConfigMap for storing the locustfile. ConfigMaps have a file-size limitation of ~2MB. If your locustfile is larger than this then you can use an S3 bucket for locustfile storage.

To do so, add the following parameters to your Zelt command:

- `--storage s3`: Switch to S3 storage
- `--s3-bucket`: The name of your S3 bucket
- `--s3-key`: The name of the file as stored in S3

**N.B.** Zelt will _not_ create the S3 bucket for you.

**N.B.** Make sure to update your deployment manifest(s) to download the locustfile file from S3 instead of loading from the ConfigMap volume mount.

#### Use a configuration file for Zelt options

An alternative to specifying Zelt's options on the command-line is to use a configuration file, for example:

```bash
zelt from-har --config examples/config/config.yaml
```

**N.B.** The configuration file's keys are the same as the command-line option names but without the double dash (`--`).

### Documentation

Coming soon...

### Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our process for submitting pull requests to us, and please ensure you follow the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

### Versioning

We use [SemVer][] for versioning.

### Authors

- **Brian Maher** - [@bmaher][]
- **Oliwia Zaremba** - [@tortila][]
- **Thibaut Le Page** - [@thilp][]

See also the list of [contributors](CONTRIBUTORS.md) who participated in this project.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

[Locust]: https://locust.io/
[Kubernetes]: https://kubernetes.io/
[Transformer]: https://github.com/zalando-incubator/transformer
[Python 3.6+]: https://www.python.org/downloads/
[using the correct cluster]: https://kubernetes.io/docs/reference/kubectl/cheatsheet/#kubectl-context-and-configuration
[documentation]: https://transformer.readthedocs.io/
[workers]: https://docs.locust.io/en/stable/running-locust-distributed.html
[@bmaher]: https://github.com/bmaher
[@tortila]: https://github.com/tortila
[@thilp]: https://github.com/thilp
[SemVer]: http://semver.org/
