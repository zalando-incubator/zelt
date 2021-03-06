Contributing
================

**Thank you for your interest in Zelt!
Your contributions are highly welcome.**

There are multiple ways to get involved:

.. contents::
   :local:

Make sure you always follow our simple `code of conduct`_.
If you need help, please reach out to us by `opening an issue`_.

.. _code of conduct: https://github.com/zalando-incubator/zelt/blob/master/CODE_OF_CONDUCT.md
.. _opening an issue: https://github.com/zalando-incubator/zelt/issues/new/choose

Report a bug
------------

Reporting bugs is one of the best ways to contribute.
Before creating a bug report, please check that an issue_ reporting the same
problem **does not already exist**.
If there is such an issue, show your interest with an emoji reaction on the
issue's description, and add the results of your investigation (if any) in a
comment.

.. _issue: https://github.com/zalando-incubator/zelt/issues

To report a **new bug**, `open a bug report`_ describing the problem.

.. _open a bug report: https://github.com/zalando-incubator/zelt/issues
   /new?labels=bug&template=bug_report.md

If you want to provide a fix along with your bug report, that's great!
In that case, please send us a **pull request** as described below in the
:ref:`contribute-code` section.

Suggest a feature
-----------------

To propose a new feature for Zelt, `open a feature request`_ and
summarize the desired functionality and the problem you're trying to solve.

.. _open a feature request: https://github.com/zalando-incubator/zelt
   /issues/new?template=feature_request.md&labels=enhancement

.. _contribute-code:

Contribute code
---------------

.. _set-up-dev:

Set up a dev environment
''''''''''''''''''''''''

The only required dependency for local deployment is Poetry_.

.. _Poetry: https://poetry.eustace.io/docs/#installation

Once you have Poetry, you can simply call ``make install`` to install all
necessary dependencies.
This mimics what happens in our continuous integration pipeline, so you won't
get surprised.

.. _project-conventions:

Conventions
'''''''''''

- All source code is formatted using black_.

- All non-private functions are reasonably covered by unit tests runnable
  with Pytest_ (via ``make test``).

- All user-facing APIs are clearly documented using Sphinx_ in docstrings
  (for developers) and in reST files in the :file:`docs/` directory (for
  users).
  See :ref:`documentation` for details.

- All user-facing changes are reported in :ref:`changelog`, along with a
  reference to the relevant pull request or issue identifiers.

.. _black: https://black.readthedocs.io/
.. _Pytest: https://docs.pytest.org/
.. _Sphinx: https://www.sphinx-doc.org/

Suggested workflow
''''''''''''''''''

.. highlight:: bash

1. Check the list of `open issues`_.
   Either **assign yourself to an existing issue**, or `create a new one`_ that
   you would like to work on.
   Describe the problem you're trying to solve, and your ideas for solving it.

   It is always best to **discuss your plans** beforehand: it ensures that your
   contribution is in line with the goals of the project.

.. _open issues: https://github.com/zalando-incubator/zelt/issues
.. _create a new one: https://github.com/zalando-incubator/zelt/issues/new/choose

2. **Fork** the `repository on GitHub`_ and clone your fork::

      $ git clone https://github.com/my-pseudo/zelt.git

.. _repository on GitHub: https://github.com/zalando-incubator/zelt

3. Create a **feature branch**, for example ``my-feature``, starting from the
   ``master`` branch::

      $ git checkout -b my-feature

   Push that branch on your fork::

      $ git push -u origin my-feature

4. Open a `new pull request`_ in `draft mode`_, and explain what you are doing:
   which issue_ are you solving and how?

   Using the **draft mode** prevents from immediately sending a request for
   code review to all maintainers, so it's useful when you don't yet have all
   your code ready.

.. _new pull request: https://github.com/zalando-incubator/zelt/compare
.. _draft mode: https://help.github.com/en/articles/creating-a-pull-request-from-a-fork

5. Get the necessary tools: :ref:`set-up-dev`.

6. Make commits of **small, logical units of work**.
   We should be able to use `git bisect`_ to find the origin of bugs.
   Make sure you :ref:`sign-off <sign-your-work>` on all your commits::

      $ git commit -s

   And finally, please write :ref:`clear commit messages <commit-messages>`!

.. _git bisect: https://git-scm.com/docs/git-bisect

7. Check that all **tests** (including your *new* ones) succeed::

      $ make test

   If this fails on your local machine, there is a good risk that it will also
   fail on Travis, preventing your pull request from being merged.

8. `Project maintainers`_ may **comment on your work** as you progress.
   If they don't and you would like some feedback, feel free to mention_ one of
   them in your pull request.

.. _project maintainers: https://github.com/zalando-incubator/zelt/blob/master/MAINTAINERS
.. _mention: https://github.blog/2011-03-23-mention-somebody-they-re-notified/

9. As explained in the :ref:`release-process` section, in Zelt, **each
   pull request merged** in the ``master`` branch becomes a **new release** on
   PyPI.
   Therefore, a few files need to be updated with a **new version number**, and
   :file:`docs/Changelog.rst` should probably contain a description of your
   contributions.
   **Everything is explained** in :ref:`release-process`.

10. You are welcome to add your name in our :ref:`contributors` file
    (:file:`docs/Contributors.rst`).
    This is of course optional, but we would be happy to remember and showcase
    the help you provided!

11. When you are done, mark your draft pull request as `Ready for review`_.
    This will automatically request a **code review** from all `project
    maintainers`_.

    Make sure your contributions respect :ref:`Zelt's conventions
    <project-conventions>` before that!

.. _ready for review: https://help.github.com/en/articles/changing-the-stage-of-a-pull-request

12. Your pull request must be approved 👍 by two `project maintainers`_ before
    it can be merged.

**Thank you** for your contributions!

.. _documentation:

Documentation
-------------

It is important that *all* features of Zelt are **documented**:

- **user-facing features**, such as new command-line options:
  if our users don't know these features exist, they will not use them and
  Zelt will be less useful to them;

- **contributor-facing features**, like internal APIs, design decisions, and
  contribution workflows: if our potential contributors struggle finding the
  right place to contribute, or cannot get a working development environment,
  the barrier of entry will be too high and the project will not benefit from
  their valuable contributions.

Zelt uses Sphinx_ to make the documentation accessible and readable to
anyone with a web browser.
It also makes it easy to link user documentation (in :file:`docs/*.rst`) and
contributor documentation (as docstrings_ in Zelt's Python source files)
when appropriate.

.. _docstrings: https://en.wikipedia.org/wiki/Docstring

Sphinx is automatically installed during the :ref:`set-up-dev` step.
**You can easily build the documentation** on your own machine by running
``make docs`` at the root of the repository.
This converts the reST files under the :file:`docs/` directory into HTML files
under :file:`docs/_build/html/`, so you can do something like::

   $ firefox docs/_build/html/index.html

to start browsing the documentation locally.

.. note::

   Be careful not to track these generated HTML files with git.
   The reST files and docstrings are the only source of truth.

.. _commit-messages:

Commit messages
---------------

Ideally, your commit messages answer two questions:
**what changed** and **why?**

The message's first line should describe the "what".
The rest of the message (separated from the first line by an empty line)
should explain the "why".

.. _sign-your-work:

Sign your work / DCO
--------------------

All contributions to Zelt (including pull requests) must agree to the
`Developer Certificate of Origin (DCO) version 1.1`__.
This is exactly the same one created and used by the Linux kernel developers:
a certification by a developer that they have the right to submit their
contribution to the project.

__ http://developercertificate.org/

Simply submitting a contribution (commits) implies this agreement.
However, **please include a "Signed-off-by" line** in every commit -- that line
is a conventional way to confirm that you agree with the DCO.
You can do that easily with git's ``-s`` option::

   $ git commit -s

You can automate this with a `git hook`_.

.. _git hook: https://stackoverflow.com/questions/15015894
   /git-add-signed-off-by-line-using-format-signoff-not-working

.. centered:: Have fun, and happy hacking!
