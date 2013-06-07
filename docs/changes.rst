SQLAlchemy-ImageAttach Changelog
================================

Version 0.8.0
-------------

To be released.

- Support Python 3.2 and 3.3.
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

