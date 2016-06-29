SQLAlchemy-ImageAttach
======================

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
   - Python versions: Python 2.6--2.7, 3.2--3.5, PyPy_
   - DBMS: PostgreSQL, MySQL, SQLite
   - SQLAlchemy: 0.8 or higher

.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _S3: http://aws.amazon.com/s3/
.. _RRS: http://aws.amazon.com/s3/#rss
.. _PyPy: http://pypy.org/


Links
-----

Docs
   https://sqlalchemy-imageattach.readthedocs.io/

   .. image:: https://readthedocs.org/projects/sqlalchemy-imageattach/badge/
      :target: https://sqlalchemy-imageattach.readthedocs.io/
      :alt: Documentation Status

Package Index (Cheeseshop)
   https://pypi.python.org/pypi/SQLAlchemy-ImageAttach

   .. image:: https://badge.fury.io/py/SQLAlchemy-ImageAttach.svg?
      :target: https://pypi.python.org/pypi/SQLAlchemy-ImageAttach
      :alt: Latest PyPI version

GitHub
   https://github.com/dahlia/sqlalchemy-imageattach

Continuous Integration (Travis CI)
   http://travis-ci.org/dahlia/sqlalchemy-imageattach

   .. image:: https://secure.travis-ci.org/dahlia/sqlalchemy-imageattach.svg?
      :alt: Build Status
      :target: https://travis-ci.org/dahlia/sqlalchemy-imageattach

Code Coverage
   https://coveralls.io/r/dahlia/sqlalchemy-imageattach

   .. image:: https://img.shields.io/coveralls/dahlia/sqlalchemy-imageattach/badge.svg?
      :alt: Coverage Status
      :target: https://coveralls.io/r/dahlia/sqlalchemy-imageattach

Author Website
   https://hongminhee.org/
