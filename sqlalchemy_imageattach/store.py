""":mod:`sqlalchemy_imageattach.store` --- Image storage backend interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module declares a common interface for physically agnostic storage
backends.  Whatever a way to implement a storage, it needs only common
operations of the interface.  This consists of some basic operations
like writing, reading, deletion, and finding urls.

Modules that implement the storage interface inside
:mod:`sqlalchemy_imageattach.storages` package might help to implement
a new storage backend.

"""
import io
import numbers
import shutil

from .file import FileProxy, SeekableFileProxy

__all__ = 'Store',


class Store(object):
    """The interface of image storage backends.  Every image storage
    backend implementation has to implement this.

    """

    def put_file(self, file, object_type, object_id, width, height, mimetype,
                 reproducible):
        """Puts the ``file`` of the image.

        :param file: the image file to put
        :type file: file-like object, :class:`file`
        :param object_type: the object type of the image to put
                            e.g. ``'comics.cover'``
        :type object_type: :class:`str`
        :param object_id: the object identifier number of the image to put
        :type object_id: :class:`numbers.Integral`
        :param width: the width of the image to put
        :type width: :class:`numbers.Integral`
        :param height: the height of the image to put
        :type height: :class:`numbers.Integral`
        :param mimetype: the mimetype of the image to put
                         e.g. ``'image/jpeg'``
        :type mimetype: :class:`str`
        :param reproducible: :const:`True` only if it's reproducible by
                             computing e.g. resized thumbnails.
                             :const:`False` if it cannot be reproduced
                             e.g. original images
        :type reproducible: :class:`bool`

        .. note::

           This is an abstract method which has to be implemented
           (overridden) by subclasses.

           It's not for consumers but implementations, so consumers
           should use :meth:`store()` method instead of this.

        """
        raise NotImplementedError('put_file() has to be implemented')

    def delete_file(self, object_type, object_id, width, height, mimetype):
        """Deletes all reproducible files related to the image.
        It doesn't raise any exception even if there's no such file.

        :param object_type: the object type of the image to put
                            e.g. ``'comics.cover'``
        :type object_type: :class:`str`
        :param object_id: the object identifier number of the image to put
        :type object_id: :class:`numbers.Integral`
        :param width: the width of the image to delete
        :type width: :class:`numbers.Integral`
        :param height: the height of the image to delete
        :type height: :class:`numbers.Integral`
        :param mimetype: the mimetype of the image to delete
                         e.g. ``'image/jpeg'``
        :type mimetype: :class:`str`

        """
        raise NotImplementedError('delete_file() has to be implemented')

    def get_file(self, object_type, object_id, width, height, mimetype):
        """Gets the file-like object of the given criteria.

        :param object_type: the object type of the image to find
                            e.g. ``'comics.cover'``
        :type object_type: :class:`str`
        :param object_id: the object identifier number of the image to find
        :type object_id: :class:`numbers.Integral`
        :param width: the width of the image to find
        :type width: :class:`numbers.Integral`
        :param height: the height of the image to find
        :type height: :class:`numbers.Integral`
        :param mimetype: the mimetype of the image to find
                         e.g. ``'image/jpeg'``
        :type mimetype: :class:`str`
        :returns: the file of the image
        :rtype: file-like object, :class:`file`
        :raise IOError: when such file doesn't exist

        .. note::

           This is an abstract method which has to be implemented
           (overridden) by subclasses.

           It's not for consumers but implementations, so consumers
           should use :meth:`open()` method instead of this.

        """
        raise NotImplementedError('get_file() has to be implemented')

    def get_url(self, object_type, object_id, width, height, mimetype):
        """Gets the file-like object of the given criteria.

        :param object_type: the object type of the image to find
                            e.g. ``'comics.cover'``
        :type object_type: :class:`str`
        :param object_id: the object identifier number of the image to find
        :type object_id: :class:`numbers.Integral`
        :param width: the width of the image to find
        :type width: :class:`numbers.Integral`
        :param height: the height of the image to find
        :type height: :class:`numbers.Integral`
        :param mimetype: the mimetype of the image to find
                         e.g. ``'image/jpeg'``
        :type mimetype: :class:`str`
        :returns: the url locating the image
        :rtype: :class:`str`

        .. note::

           This is an abstract method which has to be implemented
           (overridden) by subclasses.

           It's not for consumers but implementations, so consumers
           should use :meth:`locate()` method instead of this.

        """
        raise NotImplementedError('get_url() has to be implemented')

    def store(self, image, file):
        """Stores the actual data ``file`` of the given ``image``.
        ::

            with open(imagefile, 'rb') as f:
                store.store(image, f)

        :param image: the image to store its actual data file
        :type image: :class:`sqlalchemy_imageattach.entity.Image`
        :param file: the image file to put
        :type file: file-like object, :class:`file`

        """
        from .entity import Image
        if not isinstance(image, Image):
            raise TypeError('image must be a sqlalchemy_imageattach.entity.'
                            'Image instance, not ' + repr(image))
        elif not callable(getattr(file, 'read', None)):
            raise TypeError('file must be a readable file-like object that '
                            'implements read() method, not ' + repr(file))
        self.put_file(file, image.object_type, image.object_id,
                      image.width, image.height, image.mimetype,
                      not image.original)

    def delete(self, image):
        """Delete the file of the given ``image``.

        :param image: the image to delete
        :type image: :class:`sqlalchemy_imageattach.entity.Image`

        """
        from .entity import Image
        if not isinstance(image, Image):
            raise TypeError('image must be a sqlalchemy_imageattach.entity.'
                            'Image instance, not ' + repr(image))
        self.delete_file(image.object_type, image.object_id,
                         image.width, image.height, image.mimetype)

    def open(self, image, use_seek=False):
        """Opens the file-like object of the given ``image``.
        Returned file-like object guarantees:

        - context manager protocol
        - :class:`collections.abc.Iterable` protocol
        - :class:`collections.abc.Iterator` protocol
        - :meth:`~io.RawIOBase.read()` method
        - :meth:`~io.IOBase.readline()` method
        - :meth:`~io.IOBase.readlines()` method

        To sum up: you definitely can read the file, in :keyword:`with`
        statement and :keyword:`for` loop.

        Plus, if ``use_seek`` option is :const:`True`:

        - :meth:`~io.IOBase.seek()` method
        - :meth:`~io.IOBase.tell()` method

        For example, if you want to make a local copy of
        the image::

            import shutil

            with store.open(image) as src:
                with open(filename, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

        :param image: the image to get its file
        :type image: :class:`sqlalchemy_imageattach.entity.Image`
        :param use_seek: whether the file should seekable.
                         if :const:`True` it maybe buffered in the memory.
                         default is :const:`False`
        :type use_seek: :class:`bool`
        :returns: the file-like object of the image, which is a context
                  manager (plus, also seekable only if ``use_seek``
                  is :const:`True`)
        :rtype: :class:`file`, :class:`~sqlalchemy_imageattach.file.FileProxy`,
                file-like object
        :raise IOError: when such file doesn't exist

        """
        from .entity import Image
        if not isinstance(image, Image):
            raise TypeError('image must be a sqlalchemy_imageattach.entity.'
                            'Image instance, not ' + repr(image))
        elif image.object_id is None:
            raise TypeError('image.object_id must be set; it is currently '
                            'None however')
        elif not isinstance(image.object_id, numbers.Integral):
            raise TypeError('image.object_id must be integer, not ' +
                            repr(image.object_id))
        f = self.get_file(image.object_type, image.object_id,
                          image.width, image.height, image.mimetype)
        for method in 'read', 'readline', 'readlines':
            if not callable(getattr(f, method, None)):
                raise TypeError(
                    '{0!r}.get_file() must return file-like object which '
                    'has {1}() method, not {2!r}'.format(self, method, f)
                )
        ctxt = (callable(getattr(f, '__enter__', None)) and
                callable(getattr(f, '__exit__', None)))
        if use_seek:
            if not callable(getattr(f, 'seek', None)):
                f2 = io.BytesIO()
                shutil.copyfileobj(f, f2)
                f2.seek(0)
                return f2
            if ctxt:
                return f
            return SeekableFileProxy(f)
        if ctxt:
            return f
        return FileProxy(f)

    def locate(self, image):
        """Gets the URL of the given ``image``.

        :param image: the image to get its url
        :type image: :class:`sqlalchemy_imageattach.entity.Image`
        :returns: the url of the image
        :rtype: :class:`str`

        """
        from .entity import Image
        if not isinstance(image, Image):
            raise TypeError('image must be a sqlalchemy_imageattach.entity.'
                            'Image instance, not ' + repr(image))
        url = self.get_url(image.object_type, image.object_id,
                           image.width, image.height, image.mimetype)
        if '?' in url:
            fmt = '{0}&_ts={1}'
        else:
            fmt = '{0}?_ts={1}'
        return fmt.format(url, image.created_at.strftime('%Y%m%d%H%M%S%f'))
