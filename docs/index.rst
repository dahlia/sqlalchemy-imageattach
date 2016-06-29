SQLAlchemy-ImageAttach
======================

SQLAlchemy-ImageAttach is a SQLAlchemy_ extension for attaching images to
entity objects.  It provides the following features:

Storage backend interface
   You can use file system backend on your local development box,
   and switch it to AWS S3_ when it's deployed to the production box.
   Or you can add a new backend implementation by yourself.

Maintaining multiple image sizes
   Any size of thumbnails can be generated from the original size
   without assuming the fixed set of sizes.  You can generate a thumbnail
   of a particular size if it doesn't exist yet when the size is requested.
   Use RRS_ (Reduced Redundancy Storage) for reproducible thumbnails on S3.

Every image has its URL
   Attached images can be exposed as a URL.

SQLAlchemy transaction aware
   Saved file are removed when the ongoing transaction has been rolled back.

Tested on various environments
   - Python versions: Python 2.6--2.7, 3.2--3.5, PyPy_
   - DBMS: PostgreSQL, MySQL, SQLite
   - SQLAlchemy: 0.8 or higher (tested on 0.8 to 1.1; see CI as well)

.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _S3: https://aws.amazon.com/s3/
.. _RRS: https://aws.amazon.com/s3/reduced-redundancy/
.. _PyPy: http://pypy.org/


Installation
------------

It's already available on PyPI_, so just use :program:`pip`:

.. code-block:: console

   $ pip install SQLAlchemy-ImageAttach

.. image:: https://badge.fury.io/py/SQLAlchemy-ImageAttach.svg
   :target: https://pypi.python.org/pypi/SQLAlchemy-ImageAttach
   :alt: Latest PyPI version

.. _PyPI: https://pypi.python.org/pypi/SQLAlchemy-ImageAttach


User's guide
------------

.. toctree::

   guide/declare
   guide/store
   guide/context
   guide/multiset
   changes


.. module:: sqlalchemy_imageattach

:mod:`sqlalchemy_imageattach` --- API
-------------------------------------

.. toctree::
  :maxdepth: 2

  api/context
  api/entity
  api/file
  api/migration
  api/store
  api/util
  api/version


.. automodule:: sqlalchemy_imageattach.stores
   :members:

   .. toctree::
      :maxdepth: 2

      stores/fs
      stores/s3


Open source
-----------

SQLAlchemy-ImageAttach is an open source software written by `Hong Minhee`_.
The source code is distributed under `MIT license`_, and you can find it
at `GitHub repository`_:

.. code-block:: console

   $ git clone git://github.com/dahlia/sqlalchemy-imageattach.git

If you find any bug, please create an issue to the `issue tracker`_.
Pull requests are also always welcome!

Check out :doc:`changes` as well.

.. image:: https://secure.travis-ci.org/dahlia/sqlalchemy-imageattach.svg
   :alt: Build Status
   :target: https://travis-ci.org/dahlia/sqlalchemy-imageattach

.. image:: https://img.shields.io/coveralls/dahlia/sqlalchemy-imageattach/badge.svg
   :alt: Coverage Status
   :target: https://coveralls.io/r/dahlia/sqlalchemy-imageattach


.. _Hong Minhee: https://hongminhee.org/
.. _MIT license: https://minhee.mit-license.org/
.. _GitHub repository: https://github.com/dahlia/sqlalchemy-imageattach
.. _issue tracker: https://github.com/dahlia/sqlalchemy-imageattach/issues
