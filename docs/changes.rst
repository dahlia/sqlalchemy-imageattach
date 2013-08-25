SQLAlchemy-ImageAttach Changelog
================================

Version 0.8.1
-------------

Released on August 26, 2013.

- Added :mod:`sqlalchemy_imageattach.migration` module for storage migration.
  See also :ref:`migrate-store` guide.
- Added ``public_base_url`` option to :class:`S3Store
  <sqlalchemy_imageattach.stores.s3.S3Store>`.  It's useful when used with
  CDN e.g. CloudFront_.

.. _CloudFront: http://aws.amazon.com/cloudfront/


Version 0.8.0
-------------

Released on June 20, 2013.

- Support Python 3.2 and 3.3.  (Required minimum version of Wand also becomes
  0.3.0 from 0.2.0.)
- Added manual :func:`~sqlalchemy_imageattach.context.push_store_context()` and
  :func:`~sqlalchemy_imageattach.context.pop_store_context()` API.  It's useful
  when you can't use :keyword:`with` keyword e.g. setup/teardown hooks.
- :attr:`Image.object_type <sqlalchemy_imageattch.entity.Image.object_type>`
  property now has the default value when the primary key is an integer.
- Columns of :class:`~sqlalchemy_imageattach.entity.Image` class become
  able to be used as SQL expressions.
- Added ``block_size`` option to :class:`StaticServerMiddleware
  <sqlalchemy_imageattach.stores.fs.StaticServerMiddleware>`.
- :class:`~sqlalchemy_imageattach.stores.fs.StaticServerMiddleware` now
  supports ``'wsgi.file_wrapper'``.  See also `optional platform-specific
  file handling`__.

__ http://www.python.org/dev/peps/pep-0333/#optional-platform-specific-file-handling


Version 0.8.0.dev-20130531
--------------------------

Initially released on May 31, 2013.

