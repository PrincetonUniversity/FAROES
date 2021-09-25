******
FAROES
******

FAROES is "Fusion Analysis, Research, and Optimization for Energy Systems". It is a Python package for optimizing fusion power plants, and especially for optimizing properties like their capital cost or levelized cost of energy. It is built in a modular fashion to allow user-developers to modify or add equations or analyses of their own design.
It uses the OpenMDAO framework (openmdao.org) to provide interfaces to third-party nonlinear solvers and optimizers, especially gradient-based optimizers. The framework has advanced logging features to record solution data and metadata.
This framework also allows users to easily specify the design variables, constraints, and optimization targets, or to define their own.

|forthebadge made-with-python|

|builds|

.. |forthebadge made-with-python| image:: http://ForTheBadge.com/images/badges/made-with-python.svg
   :target: https://www.python.org/

.. |builds| image:: https://github.com/cfe316/FAROES/workflows/pytests/badge.svg
   :target: https://github.com/cfe316/FAROES/workflows/pytests/badge
   :alt: Pytests build status


Requirements
------------
* ``numpy``
* ``scipy``
* ``openmdao == 3.9.0``. Can be installed with ``pip install "openmdao[all]==3.9.0"``.
* ``ruamel >= 0.16``, a yaml parser.
* ``plasmapy`` (https://www.plasmapy.org/).

The latter three can be installed automatically using the ``setup.py`` file.

Installation
------------
Download the repo, ``cd`` to the folder and run ``pip install -e .``. This will download and install requirements and install FAROES in 'editable' mode.

Recommended packages
---------------------
The two below can be installed on linux using the script available here: https://github.com/OpenMDAO/build_pyoptsparse/

* ``pyoptsparse`` (https://github.com/mdolab/pyoptsparse) in order to access the ``pyOptSparseDriver`` which allows use of more powerful optimizers like ``IPOPT``.
* ``IPOPT``. This is optimizer seems to perform a bit better than the implemntations of ``COBYLA`` or ``SLSQP`` which are included with ``scipy``.
