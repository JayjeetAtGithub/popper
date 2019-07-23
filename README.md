# <img src="https://raw.githubusercontent.com/systemslab/popper/57f7a89bed6ff3e4d62ea2a5683ae28e3251931e/docs/figures/popper_logo_just_jug.png" width="64" valign="middle" alt="Popper"/> Popper

[![Downloads](https://pepy.tech/badge/popper)](https://pepy.tech/project/popper)
[![Build Status](https://travis-ci.org/systemslab/popper.svg?branch=master)](https://travis-ci.org/systemslab/popper)
[![codecov](https://codecov.io/gh/systemslab/popper/branch/master/graph/badge.svg)](https://codecov.io/gh/systemslab/popper)
[![Join the chat at https://gitter.im/systemslab/popper](https://badges.gitter.im/systemslab/popper.svg)](https://gitter.im/falsifiable-us/popper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![PyPI version](https://badge.fury.io/py/popper.svg)](https://badge.fury.io/py/popper)
[![GitHub license](https://img.shields.io/github/license/systemslab/popper.svg)](https://github.com/systemslab/popper/blob/master/LICENSE)

<p align="center">
  <img src="docs/figures/demo.gif" width="800">
</p>

Popper is a [Github Actions](https://github.com/features/actions) 
(GHA) workflow execution engine that allows you to execute GHA 
workflows locally on your machine and CI services. In addition to 
running a GHA workflow locally, the goal of this project is to provide 
the following functionality:

  * **Continuous integration**. Generate configuration files for 
    distinct CI services, allowing users to execute Github Action 
    workflows on these services (Travis, Jenkins, Gitlab and Circle 
    supported). [See here for 
    more](https://medium.com/getpopper/waiting-for-your-github-actions-invite-wait-no-longer-cf310b8c630c).
  * **Other Runtimes**. We are working in adding support for 
    transparently running workflows in other runtimes such as 
    [Vagrant](https://www.vagrantup.com/), 
    [Singularity](https://sylabs.io/), [cri-o](https://cri-o.io) and 
    others (see [this 
    project](https://github.com/systemslab/popper/projects/12) for 
    more).
  * **Action and workflow search**. Provide with a searchable catalog 
    of publicly available actions (and workflows) so that you do not 
    need to re-invent the wheel.
  * **Scaffolding**. Aid in the implementation of new actions and 
    workflows.
  * **Action library**. As part of our efforts, we maintain a list of 
    actions available at <https://github.com/popperized>.

-----

This repository contains:

  * [`cli/`](cli/). The codebase of the CLI tool.
  * [`docs/`](docs/). General 
    [documentation](https://popper.readthedocs.io/en/latest/) 
    containing guides, CLI documentation and pointers to other 
    resources.
  * [`gh-pages`](https://github.com/systemslab/popper/tree/gh-pages) 
    branch. Contents of our [landing page](http://falsifiable.us).

## Installation

We have a [`pip`](https://pypi.python.org/pypi) package available. To
install:

```bash
pip install popper
```

Once installed, you can get an overview and list of available 
commands:

```bash
popper --help
```

For a quickstart guide on how to use the CLI, look 
[here](https://popper.readthedocs.io/en/latest/sections/getting_started.html).

## Contributing

Anyone is welcome to contribute to Popper! To get started, take a look 
at our [contributing guidelines](CONTRIBUTING.md), then dive in with 
our [list of good first 
issues](https://github.com/systemslab/popper/issues?utf8=%E2%9C%93&q=is%3Aissue+label%3A%22good+first+issue%22+is%3Aopen) 
and [open projects](https://github.com/systemslab/popper/projects).

## Participation Guidelines

Popper adheres to the code of conduct [posted in this 
repository](CODE_OF_CONDUCT.md). By participating or contributing to 
Popper, you're expected to uphold this code. If you encounter 
unacceptable behavior, please immediately [email 
us](mailto:ivo@cs.ucsc.edu).
