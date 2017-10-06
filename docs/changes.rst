SQLAlchemy-ImageAttach Changelog
================================

Version 1.1.0
-------------

To be released.

- Dropped Python 3.2 support.
- Now :attr:`~sqlalchemy_imageattach.entity.Image.object_id` has a more
  default implementation for :class:`~uuid.UUID` primary keys.
  If a primary key is not composite and :class:`~uuid.UUID` type,
  :attr:`sqlalchemy_imageattach.entity.Image.object_id` for that doesn't have to
  be implemented.


Version 1.0.0
-------------

Released on June 30, 2016.

- Added :ref:`multiple-image-sets` support.  [:issue:`30` by Jeong YunWon]

  - :func:`~sqlalchemy_imageattach.entity.image_attachment()` function
    now can take ``uselist=True`` option.  It configures to the relationship
    to attach multiple images.
  - :class:`~sqlalchemy_imageattach.entity.ImageSet` became deprecated,
    because it was separated to :class:`SingleImageSet
    <sqlalchemy_imageattach.entity.SingleImageSet>`, and :class:`BaseImageSet
    <sqlalchemy_imageattach.entity.BaseImageSet>` which is a common base
    class for :class:`~sqlalchemy_imageattach.entity.SingleImageSet` and
    :class:`~sqlalchemy_imageattach.entity.MultipleImageSet`.
  - Added :class:`~sqlalchemy_imageattach.entity.MultipleImageSet` and
    :class:`~sqlalchemy_imageattach.entity.ImageSubset`.

- Added ``host_url_getter`` option to :class:`HttpExposedFileSystemStore
  <sqlalchemy_imageattach.stores.fs.HttpExposedFileSystemStore>`.
- Now :meth:`~sqlalchemy_imageattach.entity.BaseImageSet.from_file()` and
  :meth:`~sqlalchemy_imageattach.entity.BaseImageSet.from_blob()` can take
  ``extra_args``/``extra_kwargs`` to be passed to entity model's constructor.
  [:issue:`32`, :issue:`33` by Vahid]
- Added :const:`sqlalchemy_imageattach.version.SQLA_COMPAT_VERSION` and
  :const:`sqlalchemy_imageattach.version.SQLA_COMPAT_VERSION_INFO` constants.


Version 0.9.0
-------------

Released on March 2, 2015.

- Support SVG (:mimetype:`image/svg+xml`) and
  PDF (:mimetype:`application/pdf`).


Version 0.8.2
-------------

Released on July 30, 2014.

- Support Python 3.4.
- Fixed :exc:`UnboundLocalError` of :class:`S3Store
  <sqlalchemy_imageattach.stores.s3.S3Store>`.  [:issue:`20` by Peter Lada]


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

