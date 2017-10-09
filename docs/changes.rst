SQLAlchemy-ImageAttach Changelog
================================

Version 1.1.0
-------------

To be released.

- Dropped Python 2.6 and 3.2 support.
- Dropped SQLAlchemy 0.8 support.
- Now became to officially support Python 3.6 (although it already has
  worked well).
- Now :attr:`~sqlalchemy_imageattach.entity.Image.object_id` has a more
  default implementation for :class:`~uuid.UUID` primary keys.
  If a primary key is not composite and :class:`~uuid.UUID` type,
  :attr:`sqlalchemy_imageattach.entity.Image.object_id` for that doesn't have to
  be implemented.
- :meth:`BaseImageSet.generate_thumbnail()` became to strip metadata such as
  all profiles and comments from thumbnail images.  It doesn't affect to
  original images.

- S3 storage backend (:mod:`sqlalchemy_imageattach.stores.s3`) now supports
  `Signature Version 4`__ (AWS4Auth).  Signature Version 4 is used if
  the :attr:`~sqlalchemy_imageattach.stores.s3.S3Store.region` of
  :class:`~sqlalchemy_imageattach.stores.s3.S3Store` is determined.
  Otherwise `Signature Version 2`__ (which is deprecated since January 30, 2014)
  is used as it has been.  [:issue:`34`]

  - Added :attr:`~sqlalchemy_imageattach.stores.s3.S3Store.region` parameter
    to :class:`~sqlalchemy_imageattach.stores.s3.S3Store`.
  - Added
    :attr:`~sqlalchemy_imageattach.stores.s3.S3SandboxStore.underlying_region`
    and
    :attr:`~sqlalchemy_imageattach.stores.s3.S3SandboxStore.overriding_region`
    parameters to :class:`~sqlalchemy_imageattach.stores.s3.S3SandboxStore`.
  - Added :class:`~sqlalchemy_imageattach.stores.s3.S3RequestV4` class.
  - Renamed :class:`~sqlalchemy_imageattach.stores.s3.S3Request` to
    :class:`~sqlalchemy_imageattach.stores.s3.S3RequestV2`.
    The existing :class:`~sqlalchemy_imageattach.stores.s3.S3Request` still
    remains for backward compatibility, but it's deprecated.
  - Added :class:`~sqlalchemy_imageattach.stores.s3.AuthMechanismError`
    exception.

- Added :attr:`~sqlalchemy_imageattach.stores.s3.S3Store.max_retry` parameter
  to :class:`~sqlalchemy_imageattach.stores.s3.S3Store` and
  :class:`~sqlalchemy_imageattach.stores.s3.S3SandboxStore` classes.

__ https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html
__ https://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html


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
- :attr:`Image.object_type <sqlalchemy_imageattach.entity.Image.object_type>`
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

