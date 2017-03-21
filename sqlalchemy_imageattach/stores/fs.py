""":mod:`sqlalchemy_imageattach.stores.fs` --- Filesystem-backed image storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It provides two filesystem-backed image storage implementations:

:class:`FileSystemStore`
   It stores image files into the filesystem of the specified path,
   but :meth:`~.store.Store.locate()` method returns URLs
   of the hard-coded base URL.

:class:`HttpExposedFileSystemStore`
   The mostly same to :class:`FileSystemStore` except it provides
   WSGI middleware (:meth:`~HttpExposedFileSystemStore.wsgi_middleware()`)
   which actually serves image files and its
   :meth:`~.store.Store.locate()` method returns URLs
   based on the actual requested URL.

"""
import mimetypes
import os
import os.path
import shutil

from ..store import Store

__all__ = ('BaseFileSystemStore', 'FileSystemStore',
           'HttpExposedFileSystemStore', 'StaticServerMiddleware',
           'guess_extension')


def guess_extension(mimetype):
    """Finds the right filename extension (e.g. ``'.png'``) for
    the given ``mimetype`` (e.g. :mimetype:`image/png`).

    :param mimetype: mimetype string e.g. ``'image/jpeg'``
    :type mimetype: :class:`str`
    :returns: filename extension for the mimetype
    :rtype: :class:`str`

    """
    if mimetype == 'image/jpeg':
        # mimetypes.guess_extension() had been returned '.jpe' for
        # 'image/jpeg' until Python 3.3, but Python 3.3 has been
        # returned '.jpeg' instead.
        # We stick with '.jpe' to maintain consistency with
        # already stored objects.
        suffix = '.jpe'
    else:
        suffix = mimetypes.guess_extension(mimetype)
    return suffix


class BaseFileSystemStore(Store):
    """Abstract base class of :class:`FileSystemStore` and
    :class:`HttpExposedFileSystemStore`.

    """

    def __init__(self, path):
        self.path = path

    def get_path(self, object_type, object_id, width, height, mimetype):
        id_segment_a = str(object_id % 1000)
        id_segment_b = str(object_id // 1000)
        suffix = guess_extension(mimetype)
        filename = '{0}.{1}x{2}{3}'.format(object_id, width, height, suffix)
        return object_type, id_segment_a, id_segment_b, filename

    def put_file(self, file, object_type, object_id, width, height, mimetype,
                 reproducible):
        path = self.get_path(object_type, object_id, width, height, mimetype)
        for i in range(len(path)):
            d = os.path.join(self.path, *path[:i])
            if not os.path.isdir(d):
                os.mkdir(d)
        path_str = os.path.join(self.path, *path)
        with open(path_str, 'wb') as dst:
            shutil.copyfileobj(file, dst)

    def delete_file(self, *args, **kwargs):
        path = os.path.join(self.path, *self.get_path(*args, **kwargs))
        try:
            os.remove(path)
        except (IOError, OSError):
            pass

    def get_file(self, *args, **kwargs):
        path = os.path.join(self.path, *self.get_path(*args, **kwargs))
        return open(path, 'rb')

    def get_url(self, *args, **kwargs):
        try:
            base_url = self.base_url
        except AttributeError:
            raise NotImplementedError('base_url attribute/property is not '
                                      'implemented')
        path = '/'.join(self.get_path(*args, **kwargs))
        return base_url + path


class FileSystemStore(BaseFileSystemStore):
    """Filesystem-backed storage implementation with hard-coded URL
    routing.

    """

    def __init__(self, path, base_url):
        super(FileSystemStore, self).__init__(path)
        if not base_url.endswith('/'):
            base_url += '/'
        self.base_url = base_url


class HttpExposedFileSystemStore(BaseFileSystemStore):
    """Filesystem-backed storage implementation with WSGI middleware
    which serves actual image files.
    ::

        from flask import Flask
        from sqlalchemy_imageattach.stores.fs import HttpExposedFileSystemStore

        app = Flask(__name__)
        fs_store = HttpExposedFileSystemStore('userimages', 'images/')
        app.wsgi_app = fs_store.wsgi_middleware(app.wsgi_app)

    To determine image urls, the address of server also has to be determined.
    Although it can be automatically detected using :meth:`wsgi_middleware()`,
    WSGI unfortunately is not always there.  For example, Celery tasks aren't
    executed by HTTP requests, so there's no reachable :mailheader:`Host`
    header.

    When its host url is not determined you would get :exc:`RuntimeError`
    if you try locating image urls:

    .. code-block:: pytb

       Traceback (most recent call last):
         ...
         File "/.../sqlalchemy_imageattach/stores/fs.py", line 93, in get_url
           base_url = self.base_url
         File "/.../sqlalchemy_imageattach/stores/fs.py", line 151, in base_url
           type(self)
       RuntimeError: could not determine image url. there are two ways to \
workaround this:
       - set host_url_getter parameter to sqlalchemy_imageattach.stores.fs.\
HttpExposedFileSystemStore
       - use sqlalchemy_imageattach.stores.fs.HttpExposedFileSystemStore.\
wsgi_middleware
       see docs of sqlalchemy_imageattach.stores.fs.\
HttpExposedFileSystemStore for more details

    For such case, you can optionally set ``host_url_getter`` option.
    It takes a callable which takes no arguments and returns a host url string
    like ``'http://servername/'``.  ::

        fs_store = HttpExposedFileSystemStore(
            'userimages', 'images/',
            host_url_getter=lambda:
                'https://{0}/'.format(app.config['SERVER_NAME'])
        )

    :param path: file system path of the directory to store image files
    :type path: :class:`str`
    :param prefix: the prepended path of the url.
                   ``'__images__'`` by default
    :type prefix: :class:`str`
    :param host_url_getter: optional parameter to manually determine host url.
                            it has to be a callable that takes nothing and
                            returns a host url string
    :type host_url_getter: :class:`~typing.Callable`\ [[], :class:`str`]
    :param cors: whether or not to allow the `Cross-Origin Resource Sharing`_
                 for any origin
    :type cors: :class:`bool`

    .. _Cross-Origin Resource Sharing: https://developer.mozilla.org/en-US/\
docs/Web/HTTP/Access_control_CORS

    .. versionadded:: 1.0.0
       Added ``host_url_getter`` option.

    """

    def __init__(self, path, prefix='__images__', host_url_getter=None,
                 cors=False):
        if not (callable(host_url_getter) or host_url_getter is None):
            raise TypeError('host_url_getter must be callable')
        super(HttpExposedFileSystemStore, self).__init__(path)
        if prefix.startswith('/'):
            prefix = prefix[1:]
        if prefix.endswith('/'):
            prefix = prefix[:-1]
        self.prefix = prefix
        self.host_url_getter = host_url_getter
        self.cors = cors

    @property
    def base_url(self):
        if self.host_url_getter is not None:
            host_url = self.host_url_getter()
            if host_url.endswith('/'):
                return '{0}{1}/'.format(host_url, self.prefix)
            return '{0}/{1}/'.format(host_url, self.prefix)
        elif getattr(self, 'host_url', None):
            return self.host_url + self.prefix + '/'
        raise RuntimeError(
            'could not determine image url. '
            'there are two ways to workaround this:\n'
            '- set host_url_getter parameter to {0.__module__}.{0.__name__}\n'
            '- use {0.__module__}.{0.__name__}.wsgi_middleware\n'
            'see docs of {0.__module__}.{0.__name__} for more details'.format(
                type(self)
            )
        )

    def wsgi_middleware(self, app, cors=False):
        """WSGI middlewares that wraps the given ``app`` and serves
        actual image files. ::

            fs_store = HttpExposedFileSystemStore('userimages', 'images/')
            app = fs_store.wsgi_middleware(app)

        :param app: the wsgi app to wrap
        :type app: :class:`~typing.Callable`\ [[],
            :class:`~typing.Iterable`\ [:class:`bytes`]]
        :returns: the another wsgi app that wraps ``app``
        :rtype: :class:`StaticServerMiddleware`

        """
        _app = StaticServerMiddleware(app, '/' + self.prefix, self.path,
                                      cors=self.cors)

        def app(environ, start_response):
            if not hasattr(self, 'host_url'):
                self.host_url = (environ['wsgi.url_scheme'] + '://' +
                                 environ['HTTP_HOST'] + '/')
            return _app(environ, start_response)
        return app

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r}, {2!r}, {3!r})'.format(
            type(self), self.path, self.prefix, self.host_url_getter
        )


class StaticServerMiddleware(object):
    """Simple static server WSGI middleware.

    :param app: the fallback app when the path is not scoped in
                ``url_path``
    :type app: :class:`~typing.Callable`\ [[],
        :class:`~typing.Iterable`\ [:class:`bytes`]]
    :param url_path: the exposed path to url
    :type url_path: :class:`str`
    :param dir_path: the filesystem directory path to serve
    :type dir_path: :class:`str`
    :param block_size: the block size in bytes
    :type block_size: :class:`numbers.Integral`
    :param cors: whether or not to allow the `Cross-Origin Resource Sharing`_
                 for any origin
    :type cors: :class:`bool`

    .. todo::

       - Security considerations (especially about paths)
       - :mailheader:`ETag`
       - :mailheader:`Last-Modified` and :mailheader:`If-Modified-Since`
       - :mailheader:`Cache-Control` and :mailheader:`Expires`

    """

    def __init__(self, app, url_path, dir_path, block_size=8192, cors=False):
        if not url_path.startswith('/'):
            url_path = '/' + url_path
        if not url_path.endswith('/'):
            url_path += '/'
        if not dir_path:
            dir_path = '.'
        elif not dir_path.endswith('/'):
            dir_path += '/'
        self.app = app
        self.url_path = url_path
        self.dir_path = dir_path
        self.block_size = int(block_size)
        self.cors_enabled = cors

    def file_stream(self, path):
        with open(path, 'rb') as f:
            while 1:
                buf = f.read(self.block_size)
                if buf:
                    yield buf
                else:
                    break

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '/')
        if not path.startswith(self.url_path):
            return self.app(environ, start_response)
        file_path = os.path.join(self.dir_path, path[len(self.url_path):])
        try:
            stat = os.stat(file_path)
        except (IOError, OSError):
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return '404 Not Found',
        mimetype, _ = mimetypes.guess_type(file_path)
        mimetype = mimetype or 'application/octet-stream'
        headers = [
            ('Content-Type', mimetype),
            ('Content-Length', str(stat.st_size))
        ]
        if self.cors_enabled:
            headers.append(('Access-Control-Allow-Origin', '*'))
        start_response('200 OK', headers)
        try:
            file_wrapper = environ['wsgi.file_wrapper']
        except KeyError:
            pass
        else:
            if callable(file_wrapper):
                return file_wrapper(open(file_path, 'rb'), self.block_size)
        return self.file_stream(file_path)
