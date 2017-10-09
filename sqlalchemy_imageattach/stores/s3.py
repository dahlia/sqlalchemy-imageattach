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
import io
import logging
try:
    from urllib import parse as urlparse
except ImportError:
    import urlparse
try:
    from urllib import request as urllib2
except ImportError:
    import urllib2
import xml.etree.ElementTree

from ..store import Store
from .fs import guess_extension

__all__ = ('BASE_URL_FORMAT', 'DEFAULT_MAX_AGE',
           'AuthMechanismError', 'S3Request', 'S3RequestV2', 'S3RequestV4',
           'S3SandboxStore', 'S3Store')


#: (:class:`numbers.Integral`) The default ``max-age`` seconds of
#: :mailheader:`Cache-Control`.  It's the default value of
#: :attr:`S3Store.max_age` attribute.
DEFAULT_MAX_AGE = 60 * 60 * 24 * 365

#: (:class:`str`) The format string of base url of AWS S3.
#: Contains no trailing slash.
#: Default is ``'https://{0}.s3.amazonaws.com'``.
BASE_URL_FORMAT = 'https://{0}.s3.amazonaws.com'

BASE_REGION_URL_FORMAT = 'https://{0}.s3.{region}.amazonaws.com'


class S3RequestV4(urllib2.Request):
    """HTTP request for S3 REST API which does authentication using
    `Signature Version 4`__ (AWS4Auth).

    .. versionadded:: 1.1.0

    __ \
https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html

    """

    logger = logging.getLogger(__name__ + '.S3RequestV4')

    def __init__(self, url, bucket, region, access_key, secret_key,
                 data=None, headers={}, method=None, content_type=None):
        urllib2.Request.__init__(self, url, data=data, headers=headers)
        self.bucket = bucket
        self.region = region.strip().lower()
        self.access_key = access_key
        self.secret_key = secret_key
        self.method = method
        if self.data is None:
            self.content_type = ''
        else:
            assert content_type
            self.add_header('Content-type', content_type)
            self.content_type = content_type
            self.add_header('Content-length', str(len(self.data)))
        self.content_sha256 = hashlib.sha256(self.data or b'') \
                                     .hexdigest().lower()
        self.add_header('x-amz-content-sha256', self.content_sha256)
        self.add_header('Host', self.host or urlparse.urlparse(url).netloc)
        self.timestamp = datetime.datetime.utcnow()
        self.date = email.utils.formatdate(
            calendar.timegm(self.timestamp.timetuple()),
            usegmt=True
        )
        self.add_header('Date', self.date)
        authorization = self.get_authorization()
        self.logger.debug('get_authorization() = %r', authorization)
        self.add_header('Authorization', authorization)
        self.logger.debug('header_items() = %r', self.header_items())

    def get_method(self):
        return self.method or urllib2.Request.get_method(self) or 'GET'

    def get_path_with_query_string(self):
        url = self.get_full_url()
        path_with_query = url[url.index('/', 8):]
        try:
            q_pos = path_with_query.index('?')
        except ValueError:
            return path_with_query, ''
        return path_with_query[:q_pos], path_with_query[q_pos:]

    def get_authorization(self):
        fmt = 'AWS4-HMAC-SHA256 Credential={0},SignedHeaders={1},Signature={2}'
        credential = '/'.join(self.get_credential())
        signature, signed_headers = self.get_signature()
        return fmt.format(credential, signed_headers, signature)

    def get_credential(self):
        yield self.access_key
        yield self.timestamp.strftime('%Y%m%d')
        yield self.region
        yield 's3'
        yield 'aws4_request'

    def get_signature(self):
        signing_key = self.get_signing_key()
        string_to_sign, signed_headers = self.get_string_to_sign()
        self.logger.getChild('get_signature').debug('string_to_sign = %r',
                                                    string_to_sign)
        digest = hmac.new(signing_key, string_to_sign, hashlib.sha256)
        return digest.hexdigest().lower(), signed_headers

    def get_signing_key(self):
        date_key = self.hmac_sha256(
            b'AWS4' + self.secret_key.encode('ascii'),
            self.timestamp.strftime('%Y%m%d').encode('ascii')
        )
        date_region_key = self.hmac_sha256(
            date_key,
            self.region.encode('ascii')
        )
        date_region_service_key = self.hmac_sha256(date_region_key, b's3')
        signing_key = self.hmac_sha256(date_region_service_key,
                                       b'aws4_request')
        return signing_key

    def get_string_to_sign(self):
        canonical_request_chunks, signed_headers = self.get_canonical_request()

        def generate():
            yield b'AWS4-HMAC-SHA256\n'
            yield self.date.encode('ascii')
            yield b'\n'
            yield self.timestamp.strftime('%Y%m%d/').encode('ascii')
            yield self.region.encode('ascii')
            yield b'/s3/aws4_request'
            yield b'\n'
            canonical_request = b''.join(canonical_request_chunks)
            self.logger.getChild('get_string_to_sign').debug(
                'canonical_request = %r',
                canonical_request
            )
            canonical_request_digest = hashlib.sha256(canonical_request)
            yield canonical_request_digest.hexdigest().lower().encode('ascii')
        return b''.join(generate()), signed_headers

    def get_canonical_request(self):
        canonical_headers, signed_headers = self.get_canonical_headers()

        def generate():
            yield self.get_method().upper().strip().encode('ascii')
            yield b'\n'
            canonical_uri, query_string = self.get_path_with_query_string()
            yield canonical_uri.encode('ascii')
            yield b'\n'
            canonical_query_string = ''.join(
                self.make_canonical_query_string(query_string)
            )
            yield canonical_query_string.encode('ascii')
            yield b'\n'
            yield canonical_headers.encode('utf-8')
            yield b'\n'
            yield signed_headers.encode('utf-8')
            yield b'\n'
            yield self.content_sha256.encode('ascii')
        return generate(), signed_headers

    def make_canonical_query_string(self, query_string):
        parsed = urlparse.parse_qs(query_string, keep_blank_values=True)
        urienc = self.uri_encode
        items = [(urienc(k), urienc(v)) for k, v in parsed.items()]
        items.sort(key=lambda pair: pair[0])
        first = True
        for k, v in items:
            if first:
                first = False
            else:
                yield '&'
            yield k
            yield '='
            yield v

    def get_canonical_headers(self):
        headers = {k.lower(): v.strip() for k, v in self.header_items()}
        assert headers.get('host')
        assert headers.get('x-amz-content-sha256')
        pairs = sorted(headers.items(), key=lambda pair: pair[0])
        line = '{0}:{1}\n'.format
        canonical_headers = ''.join(line(k, v) for k, v in pairs)
        signed_headers = ';'.join(k for k, _ in pairs)
        return canonical_headers, signed_headers

    @staticmethod
    def uri_encode(string, encode_slash=True):
        to_hex = '%{0:02X}'.format
        is_byte_int = type(b'.'[0]) is int

        def to_hex_utf8(char):
            for b in char.encode('utf-8'):
                yield to_hex(b if is_byte_int else ord(b))

        def encode(string, encode_slash):
            for c in string:
                if 'A' <= c <= 'Z' or 'a' <= c <= 'z' or '0' <= c <= '9' or \
                   c in '_-~.':
                    yield c
                elif c == '/':
                    yield '%2F' if encode_slash else c
                else:
                    for byte_repr in to_hex(ord(c)):
                        yield byte_repr

        return ''.join(encode(string, encode_slash))

    @staticmethod
    def hmac_sha256(key, message):
        return hmac.new(key, message, hashlib.sha256).digest()


class S3RequestV2(urllib2.Request):
    """HTTP request for S3 REST API which does authentication using
    `Signature Version 2`__ (AWS2Auth) which has been deprecated since
    January 30, 2014.

    .. versionadded:: 1.1.0

    .. versionchanged:: 1.1.0
       Renamed from :class:`S3Request` (which is now deprecated).

    __ https://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html

    """

    logger = logging.getLogger(__name__ + '.S3RequestV2')

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


class S3Request(S3RequestV2):
    """Remained for backward compatibility.  Use :class:`S3RequestV2`
    (which was renamed) or :class:`S3RequestV4` (which is the current
    standard).

    .. deprecated:: 1.1.0
       Renamed to :class:`S3RequestV2`.

    """


class S3Store(Store):
    """Image storage backend implementation using S3_.  It implements
    :class:`~sqlalchemy_imageattach.store.Store` interface.

    If you'd like to use it with Amazon CloudFront_, pass the base url of
    the distribution to ``public_base_url``.  Note that you should configure
    *Forward Query Strings* to *Yes* when you create the distribution.
    Because SQLAlchemy-ImageAttach will add query strings to public URLs
    to invalidate cache when the image is updated.

    :param bucket: the buckect name
    :type bucket: :class:`str`
    :type access_key: AWS access key for the bucket.
                      it can't be applied if ``name`` isn't string
    :type access_key: :class:`str`
    :type secret_key: AWS secret key for the bucket.
                      it can't be applied if ``name`` isn't string
    :type secret_key: :class:`str`
    :param max_age: the ``max-age`` seconds of :mailheader:`Cache-Control`.
                    default is :const:`DEFAULT_MAX_AGE`
    :type max_age: :class:`numbers.Integral`
    :param prefix: the optional key prefix to logically separate stores
                   with the same bucket.  not used by default
    :type prefix: :class:`str`
    :param public_base_url: an optional url base for public urls.
                            useful when used with cdn
    :type public_base_url: :class:`str`
    :param region: The region code that the ``bucket`` belongs to.
                   If :const:`None` it authenticates using `Signature Version 2
                   <AWS2Auth>`_ (AWS2Auth) which has been deprecated since
                   January 30, 2014.  Because `Signature Version 4 <AWS4Auth>`_
                   (AWS4Auth) requires to determine the region code before
                   signing API requests.
                   Since recent regions don't support Signature Version 2
                   (AWS2Auth) but only Signature Version 4 (AWS4Auth),
                   if you set ``region`` to :const:`None` and
                   ``bucket`` doesn't support Signature Version 2
                   (AWS2Auth) anymore :exc:`AuthMechanismError` would be
                   raised.
                   :const:`None` by default.
    :type region: :class:`str`
    :param max_retry: Retry the given number times if uploading fails.
                      5 by default.
    :type max_retry: :class:`int`
    :raise AuthMechanismError: Raised when the ``bucket`` doesn't support
                               `Signature Version 2 <AWS2Auth>`_ (AWS2Auth)
                               anymore but supports only `Signature Version 4
                               <AWS4Auth>`_ (AWS4Auth).
                               For the most part, it can be resolved by
                               determining ``region`` parameter.

    .. versionadded:: 1.1.0
       The ``region`` and ``max_retry`` parameters.

    .. versionchanged:: 0.8.1
       Added ``public_base_url`` parameter.

    .. _CloudFront: http://aws.amazon.com/cloudfront/
    .. AWS2Auth: \
https://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html
    .. AWS4Auth: \
https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html

    """

    logger = logging.getLogger(__name__ + '.S3Store')

    #: (:class:`str`) The S3 bucket name.
    bucket = None

    #: (:class:`numbers.Integral`) The ``max-age`` seconds of
    #: :mailheader:`Cache-Control`.
    max_age = None

    #: (:class:`str`) The optional key prefix to logically separate
    #: stores with the same bucket.
    prefix = None

    #: (:class:`str`) The optional url base for public urls.
    public_base_url = None

    #: (:class:`str`) The region code that the :attr:`bucket` belongs to.
    #: If :const:`None` it authenticates using Signature Version 2 (AWS2Auth)
    #: which has been deprecated since January 30, 2014.  Because Signature
    #: Version 4 (AWS4Auth) requires to determine the region code before
    #: signing API requests.
    #:
    #: Since recent regions don't support Signature Version 2 (AWS2Auth) but
    #: only Signature Version 4 (AWS4Auth), if you set :attr:`region` to
    #: :const:`None` and :attr:`bucket` doesn't support Signature Version 2
    #: (AWS2Auth) anymore :exc:`AuthMechanismError` would be raised.
    #:
    #: .. versionadded:: 1.1.0
    region = None

    #: (:class:`int`) Retry the given number times if uploading fails.
    #:
    #: .. versionadded:: 1.1.0
    max_retry = None

    def __init__(self, bucket, access_key=None, secret_key=None,
                 max_age=DEFAULT_MAX_AGE, prefix='', public_base_url=None,
                 region=None, max_retry=5):
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        if region is None:
            self.base_url = BASE_URL_FORMAT.format(bucket)
        else:
            self.base_url = BASE_REGION_URL_FORMAT.format(
                bucket,
                region=region
            )
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
        self.max_retry = max_retry

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
        return self.urlopen(request)

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
        if self.region is None:
            cls = S3RequestV2
        else:
            cls = S3RequestV4
            kwargs = dict(kwargs)
            kwargs['region'] = self.region
        return cls(
            url, *args,
            bucket=self.bucket,
            access_key=self.access_key,
            secret_key=self.secret_key,
            **kwargs
        )

    def urlopen(self, *args, **kwargs):
        try:
            return urllib2.urlopen(*args, **kwargs)
        except urllib2.HTTPError as e:
            if e.code == 400 and \
               e.headers.get('content-type') == 'application/xml':
                xml_body = e.read()
                if b'please use aws4-hmac-sha256.' in xml_body.lower():
                    e.close()
                    raise AuthMechanismError(
                        e.filename, e.code, e.msg, e.hdrs,
                        io.BytesIO(xml_body)
                    )
            raise

    def upload_file(self, url, data, content_type, rrs, acl='public-read'):
        headers = {
            'Cache-Control': 'max-age=' + str(self.max_age),
            'x-amz-acl': acl,
            'x-amz-storage-class': 'REDUCED_REDUNDANCY' if rrs else 'STANDARD'
        }
        make_request = lambda url: self.make_request(  # noqa: E731
            url,
            method='PUT',
            data=data,
            content_type=content_type,
            headers=headers
        )
        request = make_request(url)
        trial = 0
        while 1:
            trial += 1
            try:
                self.urlopen(request).read()
            except urllib2.HTTPError as e:
                if trial < self.max_retry and e.code == 307 and \
                   e.headers.get('content-type') == 'application/xml':
                    xml_body = e.read()
                    e.close()
                    try:
                        tree = xml.etree.ElementTree.fromstring(xml_body)
                    except xml.etree.ElementTree.ParseError:
                        self.logger.debug('%s\n%s', e, xml_body)
                        continue
                    endpoint = tree.find('./Endpoint')
                    if tree.tag != 'Error' or endpoint is None:
                        self.logger.debug('%s\n%s', e, xml_body)
                        continue
                    base_url = 'https://' + endpoint.text
                    assert url.startswith(self.base_url)
                    url = base_url + url[len(self.base_url):]
                    request = make_request(url)
                    self.base_url = base_url
                    continue
                elif trial >= self.max_retry or 400 <= e.code < 500:
                    self.logger.exception(e)
                    self.logger.debug(e.read())
                    raise
                self.logger.debug(e)
                continue
            except IOError as e:
                if trial >= self.max_retry:
                    raise
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
        self.urlopen(request).read()


class S3SandboxStore(Store):
    """It stores images into physically two separated S3 buckets while
    these look like logically exist in the same store.  It takes two buckets
    for *read-only* and *overwrite*: ``underlying`` and ``overriding``.

    It's useful for development/testing purpose, because you can use
    the production store in sandbox.

    :param underlying: the name of *underlying* bucket for read-only
    :type underlying: :class:`str`
    :param overriding: the name of *overriding* bucket to record
                       overriding modifications
    :type overriding: :class:`str`
    :type access_key: AWS access key for the buckets.
                      it can't be applied if bucket names are not string
    :type access_key: :class:`str`
    :type secret_key: AWS secret key for the bucket.
                      it can't be applied if bucket names are not string
    :type secret_key: :class:`str`
    :param max_age: the ``max-age`` seconds of :mailheader:`Cache-Control`.
                    default is :const:`DEFAULT_MAX_AGE`
    :type max_age: :class:`numbers.Integral`
    :param overriding_prefix: means the same to :attr:`S3Store.prefix` but
                              it's only applied for ``overriding``
    :type overriding_prefix: :class:`str`
    :param underlying_prefix: means the same to :attr:`S3Store.prefix` but
                              it's only applied for ``underlying``
    :type underlying_prefix: :class:`str`
    :param overriding_region: Means the same to :attr:`S3Store.region` but
                              it's only applied for ``overriding``.
    :type overriding_region: :class:`str`
    :param underlying_region: Means the same to :attr:`S3Store.region` but
                              it's only applied for ``underlying``.
    :type underlying_region: :class:`str`
    :param max_retry: Retry the given number times if uploading fails.
                      5 by default.
    :type max_retry: :class:`int`
    :raise AuthMechanismError: Raised when the ``bucket`` doesn't support
                               `Signature Version 2 <AWS2Auth>`_ (AWS2Auth)
                               anymore but supports only `Signature Version 4
                               <AWS4Auth>`_ (AWS4Auth).
                               For the most part, it can be resolved by
                               determining ``region`` parameter.

    .. versionadded:: 1.1.0
       The ``underlying_region``, ``overriding_region``, and ``max_retry``
       parameters.

    .. AWS2Auth: \
https://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html
    .. AWS4Auth: \
https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html

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
                 underlying_prefix='', overriding_prefix='',
                 underlying_region=None, overriding_region=None,
                 max_retry=5):
        self.underlying = S3Store(underlying,
                                  access_key=access_key, secret_key=secret_key,
                                  max_age=max_age, prefix=underlying_prefix,
                                  region=underlying_region,
                                  max_retry=max_retry)
        self.overriding = S3Store(overriding,
                                  access_key=access_key, secret_key=secret_key,
                                  max_age=max_age, prefix=overriding_prefix,
                                  region=overriding_region,
                                  max_retry=max_retry)

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


class AuthMechanismError(urllib2.HTTPError):
    """Raised when the bucket doesn't support `Signature Version 2 <AWS2Auth>`_
    (AWS2Auth) anymore but supports only `Signature Version 4 <AWS4Auth>`_
    (AWS4Auth).

    For the most part, it can be resolved by determining
    :attr:`S3Store.region`.

    .. seealso::

       `Table of S3 regions and supported signature versions`__

       __ https://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    .. versionadded:: 1.1.0

    .. _CloudFront: http://aws.amazon.com/cloudfront/
    .. AWS2Auth: \
https://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html
    .. AWS4Auth: \
https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html

    """

    def __str__(self):
        return '''HTTPError {0}: {1}
It seems the region and the bucket doesn't support Signature Version 2 \
(AWS2Auth) which has been deprecated since January 30, 2014, but supports \
only Singature Version 4 (AWS4Auth).
In order to use Signature Version 4 (AWS4Auth), specify region= parameter \
of S3Store (or underlying_region=/overriding_region= of S3SandboxStore).
See also: https://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region
'''.format(self.code, self.msg)

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} {1}: {2!r}>'.format(
            type(self), self.code, self.msg
        )
