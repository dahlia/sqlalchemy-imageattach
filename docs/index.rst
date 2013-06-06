SQLAlchemy-ImageAttach
======================

SQLAlchemy-ImageAttach is a SQLAlchemy_ extension for attaching images to
entity objects.  It provides the following features:

Storage backend interface
   You can use file system backend on your local development box,
   and switch it to AWS S3_ when it's deployed to the production box.
   Or you can add a new backend implementation by yourself.

Maintaining multple image sizes
   Any size of thumbnails can be generated from the original size
   without assuming the fixed set of sizes.  You can generate a thumbnail
   of a particular size if it doesn't exist yet when the size is requested.
   Use RRS_ (Reduced Redundancy Storage) for reproducible thumbnails on S3.

Every image has its URL
   Attached images can be exposed as a URL.

SQLAlchemy transaction aware
   Saved file are removed when the ongoing transaction has been rolled back.

Tested on various environments
   - Python versions: Python 2.6, 2.7, PyPy
   - DBMS: PostgreSQL, MySQL, SQLite
   - SQLAlchemy: 0.8 or higher

.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _S3: http://aws.amazon.com/s3/
.. _RRS: http://aws.amazon.com/s3/#rss


Installation
------------

It's already available on PyPI_, so just use :program:`pip`:

.. code-block:: console

   $ pip install SQLAlchemy-ImageAttach

.. _PyPI: https://pypi.python.org/pypi/SQLAlchemy-ImageAttach


User's guide
------------

.. toctree::

   guide/declare
   guide/store
   guide/context
   changes


.. module:: sqlalchemy_imageattach

:mod:`sqlalchemy_imageattach` --- API
-------------------------------------

.. toctree::
  :maxdepth: 2

  api/context
  api/entity
  api/file
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

SQLAlchemy-ImageAttach is an open source software written by `Hong Minhee`_
(initially written for Crosspop_).  The source code is distributed under
`MIT license`_ and you can find it at `GitHub repository`_.  Check out now:

.. code-block:: console

   $ git clone git://github.com/crosspop/sqlalchemy-imageattach.git

If you find any bug, please create an issue to the `issue tracker`_.
Pull requests are also always welcome!

Check out :doc:`changes` as well.

.. image:: https://secure.travis-ci.org/crosspop/sqlalchemy-imageattach.png
   :alt: Build Status
   :target: http://travis-ci.org/crosspop/sqlalchemy-imageattach

.. image:: https://coveralls.io/repos/crosspop/sqlalchemy-imageattach/badge.png
   :alt: Coverage Status
   :target: https://coveralls.io/r/crosspop/sqlalchemy-imageattach


.. _Hong Minhee: http://dahlia.kr/
.. _Crosspop: http://crosspop.in/
.. _MIT license: http://minhee.mit-license.org/
.. _GitHub repository: https://github.com/crosspop/sqlalchemy-imageattach
.. _issue tracker: https://github.com/crosspop/sqlalchemy-imageattach/issues
