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

Zelt was born from a need in Zalando to ensure our stack would hold-up
to the `load expected during Black Friday 2018`_. In addition to
component-level load testing, we performed system-level end-to-end load tests;
hence the name 'Zalando end-to-end load tester' or Zelt for short.
Despite the name, Zelt can be used for any form of load testing that requires
the use of Locust and Kubernetes.

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
.. _`load expected during Black Friday 2018`: https://jobs.zalando.com/tech/blog/end-to-end-load-testing-zalandos-production-website/
