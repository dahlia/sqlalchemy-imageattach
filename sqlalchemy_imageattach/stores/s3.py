""":mod:`sqlalchemy_imageattach.stores.s3` --- AWS S3_ backend storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The backend storage implementation for `Simple Storage Service <S3>`_
provided by `Amazon Web Services <AWS>`_.

.. _S3: http://aws.amazon.com/s3/
.. _AWS: http://aws.amazon.com/

"""
import base64
import calendar
import datetime
import email.utils
import hashlib
import hmac
import logging
try:
    from urllib import request as urllib2
except ImportError:
    import urllib2

from ..store import Store
from .fs import guess_extension

__all__ = ('BASE_URL_FORMAT', 'DEFAULT_MAX_AGE',
           'S3Request', 'S3SandboxStore', 'S3Store')


#: (:class:`numbers.Integral`) The default ``max-age`` seconds of
#: :mailheader:`Cache-Control`.  It's the default value of
#: :attr:`S3Store.max_age` attribute.
DEFAULT_MAX_AGE = 60 * 60 * 24 * 365

#: (:class:`str`) The format string of base url of AWS S3.
#: Contains no trailing slash.
#: Default is ``'https://{0}.s3.amazonaws.com'``.
BASE_URL_FORMAT = 'https://{0}.s3.amazonaws.com'


class S3Request(urllib2.Request):
    """HTTP request for S3 REST API which does authentication."""

    logger = logging.getLogger(__name__ + '.S3Request')

    def __init__(self, url, bucket, access_key, secret_key,
                 data=None, headers={}, method=None, content_type=None):
        urllib2.Request.__init__(self, url, data=data, headers=headers)
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.method = method
        if self.data is None:
            self.content_md5 = ''
            self.content_type = ''
        else:
            assert content_type
            self.content_md5 = base64.b64encode(
                hashlib.md5(self.data).digest()
            ).decode('ascii')
            self.content_type = content_type
            self.add_header('Content-md5', self.content_md5)
            self.add_header('Content-type', content_type)
            self.add_header('Content-length', len(self.data))
        self.date = email.utils.formatdate(
            calendar.timegm(datetime.datetime.utcnow().timetuple()),
            usegmt=True
        )
        self.add_header('Date', self.date)
        authorization = self.get_authorization()
        self.logger.debug('get_authorization() = %r', authorization)
        self.add_header('Authorization', authorization)

    def get_method(self):
        return self.method or urllib2.Request.get_method(self) or 'GET'

    def get_path_with_query(self):
        url = self.get_full_url()
        return url[url.index('/', 8):]

    def get_authorization(self):
        return 'AWS {0}:{1}'.format(
            self.access_key,
            self.get_signature().decode('utf-8')
        )

    def get_signature(self):
        sign = self.sign()
        self.logger.debug('sign() = %r', sign)
        d = hmac.new(
            self.secret_key.encode('utf-8'),
            sign.encode('utf-8'),
            hashlib.sha1
        )
        return base64.b64encode(d.digest())

    def sign(self):
        return '\n'.join([
            self.get_method().upper(),
            self.content_md5,
            self.content_type,
            self.date,
            self.canonicalize_headers() + self.canonicalize_resource()
        ])

    def canonicalize_headers(self):
        pairs = [(k.lower(), v)
                 for k, v in self.header_items()
                 if k.lower().startswith('x-amz-')]
        pairs.sort(key=lambda pair: pair[0])
        line = '{0}:{1}\n'.format
        return ''.join(line(k, v) for k, v in pairs)

    def canonicalize_resource(self):
        # FIXME: query should be lexicographically sorted if multiple
        return '/' + self.bucket + self.get_path_with_query()


class S3Store(Store):
    """Image storage backend implementation using S3_.  It implements
    :class:`~sqlalchemy_imageattach.store.Store` interface.

    If you'd like to use it with Amazon CloudFront_, pass the base url of
    the distribution to ``public_base_url``.  Note that you should configure
    *Forward Query Strings* to *Yes* when you create the distribution.
    Because SQLAlchemy-ImageAttach will add query strings to public URLs
    to invalidate cache when the image is updated.

    :param bucket: the buckect name
    :type bucket: :class:`basestring`
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
    :param public_base_url: an optional url base for public urls.
                            useful when used with cdn
    :type public_base_url: :class:`basestring`

    .. versionchanged:: 0.8.1
       Added ``public_base_url`` parameter.

    .. _CloudFront: http://aws.amazon.com/cloudfront/

    """

    logger = logging.getLogger(__name__ + '.S3Store')

    #: (:class:`basestring`) The S3 bucket name.
    bucket = None

    #: (:class:`numbers.Integral`) The ``max-age`` seconds of
    #: :mailheader:`Cache-Control`.
    max_age = None

    #: (:class:`basestring`) The optional key prefix to logically separate
    #: stores with the same bucket.
    prefix = None

    #: (:class:`basestring`) The optional url base for public urls.
    public_base_url = None

    def __init__(self, bucket, access_key=None, secret_key=None,
                 max_age=DEFAULT_MAX_AGE, prefix='', public_base_url=None):
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = BASE_URL_FORMAT.format(bucket)
        self.max_age = max_age
        self.prefix = prefix.strip()
        if self.prefix.endswith('/'):
            self.prefix = self.prefix.rstrip('/')
        if public_base_url is None:
            self.public_base_url = self.base_url
        elif public_base_url.endswith('/'):
            self.public_base_url = public_base_url.rstrip('/')
        else:
            self.public_base_url = public_base_url

    def get_key(self, object_type, object_id, width, height, mimetype):
        key = '{0}/{1}/{2}x{3}{4}'.format(
            object_type, object_id, width, height,
            guess_extension(mimetype)
        )
        if self.prefix:
            return '{0}/{1}'.format(self.prefix, key)
        return key

    def get_file(self, *args, **kwargs):
        url = self.get_s3_url(*args, **kwargs)
        request = self.make_request(url)
        return urllib2.urlopen(request)

    def get_s3_url(self, *args, **kwargs):
        return '{0}/{1}'.format(
            self.base_url,
            self.get_key(*args, **kwargs)
        )

    def get_url(self, *args, **kwargs):
        return '{0}/{1}'.format(
            self.public_base_url,
            self.get_key(*args, **kwargs)
        )

    def make_request(self, url, *args, **kwargs):
        return S3Request(url, *args,
                         bucket=self.bucket,
                         access_key=self.access_key,
                         secret_key=self.secret_key,
                         **kwargs)

    def upload_file(self, url, data, content_type, rrs, acl='public-read'):
        headers = {
            'Cache-Control': 'max-age=' + str(self.max_age),
            'x-amz-acl': acl,
            'x-amz-storage-class': 'REDUCED_REDUNDANCY' if rrs else 'STANDARD'
        }
        request = self.make_request(
            url,
            method='PUT',
            data=data,
            content_type=content_type,
            headers=headers
        )
        while 1:
            try:
                urllib2.urlopen(request).read()
            except urllib2.HTTPError as e:
                if 400 <= e.code < 500:
                    self.logger.exception(e)
                    self.logger.debug(e.read())
                    raise
                self.logger.debug(e)
                continue
            except IOError as e:
                self.logger.debug(e)
                continue
            else:
                break

    def put_file(self, file, object_type, object_id, width, height, mimetype,
                 reproducible):
        url = self.get_s3_url(object_type, object_id, width, height, mimetype)
        self.upload_file(url, file.read(), mimetype, rrs=reproducible)

    def delete_file(self, *args, **kwargs):
        url = self.get_s3_url(*args, **kwargs)
        request = self.make_request(url, method='DELETE')
        urllib2.urlopen(request).read()


class S3SandboxStore(Store):
    """It stores images into physically two separated S3 buckets while
    these look like logically exist in the same store.  It takes two buckets
    for *read-only* and *overwrite*: ``underlying`` and ``overriding``.

    It's useful for development/testing purpose, because you can use
    the production store in sandbox.

    :param underlying: the name of *underlying* bucket for read-only
    :type underlying: :class:`basestring`
    :param overriding: the name of *overriding* bucket to record
                       overriding modifications
    :type overriding: :class:`basestring`
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

    logger = logging.getLogger(__name__ + '.S3SandboxStore')

    #: All keys marked as "deleted" have this mimetype as
    #: its :mailheader:`Content-Type` header.
    DELETED_MARK_MIMETYPE = \
        'application/x-sqlalchemy-imageattach-sandbox-deleted'

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
        try:
            file_ = self.overriding.get_file(*args, **kwargs)
        except IOError:
            return self.underlying.get_file(*args, **kwargs)
        if file_.info().get('Content-Type') == self.DELETED_MARK_MIMETYPE:
            raise IOError('deleted')
        return file_

    def get_url(self, *args, **kwargs):
        request = self.overriding.make_request(
            self.overriding.get_url(*args, **kwargs),
            method='HEAD'
        )
        store = self.overriding
        try:
            urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            if e.code == 404:
                store = self.underlying
        return store.get_url(*args, **kwargs)

    def put_file(self, *args, **kwargs):
        self.overriding.put_file(*args, **kwargs)

    def delete_file(self, object_type, object_id, width, height, mimetype):
        args = object_type, object_id, width, height, mimetype
        self.overriding.delete_file(*args)
        url = self.overriding.get_s3_url(*args)
        self.overriding.upload_file(
            url,
            data=b'',
            content_type=self.DELETED_MARK_MIMETYPE,
            rrs=True,
            acl='private'
        )
