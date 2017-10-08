SQLAlchemy-ImageAttach
======================

.. image:: https://img.shields.io/pypi/v/SQLAlchemy-ImageAttach.svg
   :target: https://pypi.org/project/SQLAlchemy-ImageAttach/
   :alt: PyPI

.. image:: https://readthedocs.org/projects/sqlalchemy-imageattach/badge/?version=stable
   :target: https://sqlalchemy-imageattach.readthedocs.io/
   :alt: Read the Docs

.. image:: https://travis-ci.org/dahlia/sqlalchemy-imageattach.svg?branch=master
   :alt: Build Status
   :target: https://travis-ci.org/dahlia/sqlalchemy-imageattach

.. image:: https://img.shields.io/coveralls/dahlia/sqlalchemy-imageattach/badge.svg?
   :alt: Coverage Status
   :target: https://coveralls.io/r/dahlia/sqlalchemy-imageattach

**SQLAlchemy-ImageAttach** is a SQLAlchemy_ extension for attaching images to
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
   - Python versions: Python 2.7, 3.3 or higher, PyPy_
   - DBMS: PostgreSQL, MySQL, SQLite
   - SQLAlchemy: 0.9 or higher (tested on 0.9 to 1.1; see CI as well)

.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _S3: https://aws.amazon.com/s3/
.. _RRS: https://aws.amazon.com/s3/reduced-redundancy/
.. _PyPy: http://pypy.org/


Installation
------------

It's available on PyPI_:

.. code-block:: console

   $ pip install SQLAlchemy-ImageAttach

.. _PyPI: https://pypi.org/project/SQLAlchemy-ImageAttach/
