## Minikube

These manifests presume the following setup with a local installation of [Minikube](https://kubernetes.io/docs/setup/minikube/):

### Ingress

Ingress has been installed in Minikube:

`minikube addons enable ingress`

A hostname has been configured locally:

```echo `minikube ip` zelt.minikube | sudo tee -a /etc/hosts```
