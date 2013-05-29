""":mod:`sqlalchemy_imageattach.stores.s3` --- AWS S3_ backed image storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Amazon Web Services <AWS>`_ offers `Simple Storage Service <S3>`_.
It provides several features we really need:

Accessible via HTTP(S)
   Comic images should be accessibile from web browser.
   S3 objects can have their own public URL if they are set to enough ACL.

Reliability
   Comic images shouldn't be lost.

Redundancy control
   - Reduced Redundancy: resized images could be reproducible by computing.
   - Standard: original images cannot be reproducible,
     so it shouldn't be lost.

Low cost
   We have no enough money.

In here we depend on :mod:`simples3` to deal with S3 buckets and objects.

.. _S3: http://aws.amazon.com/s3/
.. _AWS: http://aws.amazon.com/

"""
import mimetypes
import re

from simples3.bucket import S3Bucket, S3Error

from ..store import Store

__all__ = 'BASE_URL_FORMAT', 'DEFAULT_MAX_AGE', 'S3SandboxStore', 'S3Store'


#: (:class:`numbers.Integral`) The default ``max-age`` seconds of
#: :mailheader:`Cache-Control`.  It's the default value of
#: :attr:`S3Store.max_age` attribute.
DEFAULT_MAX_AGE = 60 * 60 * 24 * 365

#: (:class:`str`) The format string of base url of AWS S3.
#: Contains no trailing slash.
#: Default is ``'https://{0}.s3.amazonaws.com'``.
BASE_URL_FORMAT = 'https://{0}.s3.amazonaws.com'



class S3Store(Store):
    """Image storage backend implementation using S3_.  It implements
    :class:`~sqlalchemy_imageattach.store.Store` interface.

    :param name: the buckect name, or bucket object provided by :mod:`simples3`
    :type name: :class:`basestring`, :class:`simples3.bucket.S3Bucket`
    :type access_key: AWS access key for the bucket.
                      it can't be applied if ``name`` isn't string
    :type access_key: :class:`basestring`
    :type secret_key: AWS secret key for the bucket.
                      it can't be applied if ``name`` isn't string
    :type secret_key: :class:`basestring`
    :param max_age: the ``max-age`` seconds of :mailheader:`Cache-Control`.
                    default is :const:`DEFAULT_MAX_AGE`
    :type max_age: :class:`numbers.Integral`
    :param prefix: the optional key prefix to logically separate stores
                   with the same bucket.  not used by default
    :type prefix: :class:`basestring`

    """

    #: (:class:`simples3.bucket.S3Bucket`) The S3 bucket object.
    bucket = None

    #: (:class:`numbers.Integral`) The ``max-age`` seconds of
    #: :mailheader:`Cache-Control`.
    max_age = None

    #: (:class:`basestring`) The optional key prefix to logically separate
    #: stores with the same bucket.
    prefix = None

    def __init__(self, name, access_key=None, secret_key=None,
                 max_age=DEFAULT_MAX_AGE, prefix=''):
        if isinstance(name, S3Bucket):
            if access_key or secret_key:
                raise TypeError('cannot appliable access_key, nor secret_key '
                                'with simples3.bucket.S3Bucket argument')
            self.bucket = name
        else:
            base_url = BASE_URL_FORMAT.format(name)
            self.bucket = S3Bucket(
                name,
                access_key=access_key,
                secret_key=secret_key,
                base_url=base_url
            )
        self.max_age = max_age
        self.prefix = prefix.strip()
        if self.prefix.endswith('/'):
            self.prefix = self.prfix[:-1]

    def get_key(self, object_type, object_id, width, height, mimetype):
        key = '{0}/{1}/{2}x{3}{4}'.format(
            object_type, object_id, width, height,
            mimetypes.guess_extension(mimetype)
        )
        if self.prefix:
            return '{0}/{1}'.format(self.prefix, key)
        return key

    def get_file(self, *args, **kwargs):
        key = self.get_key(*args, **kwargs)
        try:
            return self.bucket.get(key)
        except (KeyError, S3Error) as e:
            raise IOError(str(e))

    def get_url(self, *args, **kwargs):
        key = self.get_key(*args, **kwargs)
        url = self.bucket.make_url(key)
        return re.sub(r'\?.*$', '', url)

    def put_file(self, file, object_type, object_id, width, height, mimetype,
                 reproducible):
        key = self.get_key(object_type, object_id, width, height, mimetype)
        rrs = 'REDUCED_REDUNDANCY' if reproducible else 'STANDARD'
        self.bucket.put(
            key,
            file.read(),
            acl='public-read',
            mimetype=mimetype,
            headers={
                'Cache-Control': 'max-age=' + str(self.max_age),
                'x-amz-storage-class': rrs
            }
        )

    def delete_file(self, *args, **kwargs):
        key = self.get_key(*args, **kwargs)
        self.bucket.delete(key)


class S3SandboxStore(Store):
    """It stores images into physically two separated S3 buckets while
    these look like logically exist in the same store.  It takes two buckets
    for *read-only* and *overwrite*: ``underlying`` and ``overriding``.

    It's useful for development/testing purpose, because you can use
    the production store in sandbox.

    :param underlying: the name (or object provided by :mod:`simples3`) of
                       *underlying* bucket for read-only
    :type underlying: :class:`basestring`, :class:`simples3.bucket.S3Bucket`
    :param overriding: the name (or object provided by :mod:`simples3`) of
                       *overriding* bucket to record overriding modifications
    :type overriding: :class:`basestring`, :class:`simples3.bucket.S3Bucket`
    :type access_key: AWS access key for the buckets.
                      it can't be applied if bucket names are not string
    :type access_key: :class:`basestring`
    :type secret_key: AWS secret key for the bucket.
                      it can't be applied if bucket names are not string
    :type secret_key: :class:`basestring`
    :param max_age: the ``max-age`` seconds of :mailheader:`Cache-Control`.
                    default is :const:`DEFAULT_MAX_AGE`
    :type max_age: :class:`numbers.Integral`
    :param overriding_prefix: means the same to :attr:`S3Store.prefix` but
                              it's only applied for ``overriding``
    :type overriding_prefix: :class:`basestring`
    :param underlying_prefix: means the same to :attr:`S3Store.prefix` but
                              it's only applied for ``underlying``
    :type underlying_prefix: :class:`basestring`

    """

    #: All keys marked as "deleted" have this mimetype as
    #: its :mailheader:`Content-Type` header.
    DELETED_MARK_MIMETYPE = 'application/x-pop-sandbox-deleted'

    #: (:class:`S3Store`) The *underlying* store for read-only.
    underlying = None

    #: (:class:`S3Store`) The *overriding* store to record overriding
    #: modification.
    overriding = None

    def __init__(self, underlying, overriding,
                 access_key=None, secret_key=None, max_age=DEFAULT_MAX_AGE,
                 underlying_prefix='', overriding_prefix=''):
        self.underlying = S3Store(underlying,
                                  access_key=access_key, secret_key=secret_key,
                                  max_age=max_age, prefix=underlying_prefix)
        self.overriding = S3Store(overriding,
                                  access_key=access_key, secret_key=secret_key,
                                  max_age=max_age, prefix=overriding_prefix)

    def get_file(self, *args, **kwargs):
        key = self.overriding.get_key(*args, **kwargs)
        try:
            file_ = self.overriding.bucket.get(key)
        except (KeyError, S3Error):
            return self.underlying.get_file(*args, **kwargs)
        if file_.s3_info.get('mimetype') == self.DELETED_MARK_MIMETYPE:
            raise IOError('deleted')
        return file_

    def get_url(self, *args, **kwargs):
        key = self.overriding.get_key(*args, **kwargs)
        try:
            self.overriding.bucket.info(key)
        except (KeyError, S3Error):
            store = self.underlying
        else:
            store = self.overriding
        return store.get_url(*args, **kwargs)

    def put_file(self, *args, **kwargs):
        self.overriding.put_file(*args, **kwargs)

    def delete_file(self, *args, **kwargs):
        key = self.overriding.get_key(*args, **kwargs)
        self.overriding.bucket.delete(key)
        self.overriding.bucket.put(
            key, '',
            acl='private',
            mimetype=self.DELETED_MARK_MIMETYPE,
            headers={ 'x-amz-storage-class': 'REDUCED_REDUNDANCY'}
        )
