SQLAlchemy-ImageAttach
======================

**SQLAlchemy-ImageAttach** is a SQLAlchemy_ extension for attaching images to
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
   - Python versions: Python 2.6, 2.7, PyPy.
   - DBMS: PostgreSQL, MySQL, SQLite

.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _S3: http://aws.amazon.com/s3/
.. _RRS: http://aws.amazon.com/s3/#rss


Links
-----

Docs
   https://sqlalchemy-imageattach.readthedocs.org/

GitHub
   https://github.com/crosspop/sqlalchemy-imageattach

Continuous Integration (Travis CI)
   http://travis-ci.org/crosspop/sqlalchemy-imageattach

   .. image:: https://secure.travis-ci.org/crosspop/sqlalchemy-imageattach.png
      :alt: Build Status
      :target: http://travis-ci.org/crosspop/sqlalchemy-imageattach

Code Coverage
   https://coveralls.io/r/crosspop/sqlalchemy-imageattach

   .. image:: https://coveralls.io/repos/crosspop/sqlalchemy-imageattach/badge.png
      :alt: Coverage Status
      :target: https://coveralls.io/r/crosspop/sqlalchemy-imageattach

Author Website
   http://dahlia.kr/
