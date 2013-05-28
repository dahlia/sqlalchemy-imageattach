""":mod:`sqlalchemy_imageattach.stores.fs` --- Filesystem-backed image storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It provides two filesystem-backed image storage implementations:

:class:`FileSystemStore`
   It stores image files into the filesystem of the specified path,
   but :meth:`~FileSystemStore.locate()` method returns URLs
   of the hard-coded base URL.

:class:`HttpExposedFileSystemStore`
   The mostly same to :class:`FileSystemStore` except it provides
   WSGI middleware (:meth:`~HttpExposedFileSystemStore.wsgi_middleware()`)
   which actually serves image files and its
   :meth:`~HttpExposedFileSystemStore.locate()` method returns URLs
   based on the actual requested URL.

"""
import mimetypes
import os
import os.path
import shutil

from werkzeug.wsgi import SharedDataMiddleware  # FIXME: remove this dependency

from ..store import Store

__all__ = ('BaseFileSystemStore', 'FileSystemStore',
           'HttpExposedFileSystemStore')


class BaseFileSystemStore(Store):
    """Abstract base class of :class:`FileSystemStore` and
    :class:`HttpExposedFileSystemStore`.

    """

    def __init__(self, path):
        self.path = path

    def get_path(self, object_type, object_id, width, height, mimetype):
        id_segment_a = str(object_id % 1000)
        id_segment_b = str(object_id // 1000)
        suffix = mimetypes.guess_extension(mimetype)
        filename = '{0}.{1}x{2}{3}'.format(object_id, width, height, suffix)
        return object_type, id_segment_a, id_segment_b, filename

    def put_file(self, file, object_type, object_id, width, height, mimetype,
                 reproducible):
        path = self.get_path(object_type, object_id, width, height, mimetype)
        for i in xrange(len(path)):
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

    """

    def __init__(self, path, prefix='x.images'):
        super(HttpExposedFileSystemStore, self).__init__(path)
        if prefix.startswith('/'):
            prefix = prefix[1:]
        if prefix.endswith('/'):
            prefix = prefix[:-1]
        self.prefix = prefix

    @property
    def base_url(self):
        return self.host_url + self.prefix + '/'

    def wsgi_middleware(self, app):
        """WSGI middlewares that wraps the given ``app`` and serves
        actual image files. ::

            fs_store = HttpExposedFileSystemStore('userimages', 'images/')
            app = fs_store.wsgi_middleware(app)

        :param app: the wsgi app to wrap
        :type app: :class:`collections.Callable`
        :returns: the another wsgi app that wraps ``app``
        :rtype: :class:`werkzeug.wsgi.SharedDataMiddleware`

        """
        _app = SharedDataMiddleware(app, {'/' + self.prefix: self.path})
        def app(environ, start_response):
            if not hasattr(self, 'host_url'):
                self.host_url = environ['wsgi.url_scheme'] + '://' + \
                                environ['HTTP_HOST'] + '/'
            return _app(environ, start_response)
        return app
