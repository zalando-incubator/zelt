.. title:: Zelt - documentation

.. image:: _static/zelt.png
    :alt: Zelt logo
    :align: center

**Welcome to Zelt's documentation!**

Zelt's jobs is to deploy Locust_ in Kubernetes_. The main use-case for
deploying Locust in Kubernetes is when you want to generate an
amount of load that is greater than can be generated from one machine.
Kubernetes allows you to easily achieve this scale, Zelt ensures
the deployment is equally as easy.

Getting Started
---------------

See `our README`_ for basic information like:

.. _our README: https://github.com/zalando-incubator/zelt/blob/master/README.rst

- how to **install** Zelt,
- how to use the ``zelt`` **command-line tool**

How to ...
----------

.. toctree::
   :maxdepth: 1

   Run a load test using Zelt <Run-a-load-test>
   Contribute to Zelt <Contributing>

.. _Locust: https://locust.io
.. _Kubernetes: https://kubernetes.io/
