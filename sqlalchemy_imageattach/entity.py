""":mod:`sqlalchemy_imageattach.entity` --- Image entities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides a short way to attach resizable images
to other object-relationally mapped entity classes.

For example, imagine there's a fictional entity named
:class:`User` and it has its :attr:`~User.picture` and
:attr:`~User.front_cover`.  So there should be two
image entities that subclass :class:`Image` mixin::

    class UserPicture(Base, Image):
        '''User's profile picture.'''

        user_id = Column(Integer, ForeignKey('User.id'), primary_key=True)
        user = relationship('User')

        __tablename__ = 'user_picture'

You have to also inherit your own :func:`declarative_base()
<sqlalchemy.ext.declarative.declarative_base>` class (``Base`` in the example).

Assume there's also :class:`UserFrontCover` in the same way.

Note that the class can override :attr:`~Image.object_id` property.
Backend storages utilize this to identify images e.g. filename, S3 key.
If the primary key of the image entity is integer, :attr:`~Image.object_id`
automatically uses the primary key value by default, but it can be
overridden if needed, and must be implemented if the primary key is not
integer or composite key.

There's also :attr:`~Image.object_type` property.  :class:`Image` provides
the default value for it as well.  It uses the class name (underscores
will be replaced by hyphens) by default, but you can override it.

These :class:`Image` subclasses can be related to the their
'parent' entity using :func:`image_attachment()` function.
It's a specialized version of SQLAlchemy's built-in
:func:`~sqlalchemy.orm.relationship()` function, so you can pass
the same options as :func:`~sqlalchemy.orm.relationship()` takes::

    class User(Base):
        '''Users have their profile picture and front cover.'''

        id = Column(Integer, primary_key=True)
        picture = image_attachment('UserPicture')
        front_cover = image_attachment('UserFrontCover')

        __tablename__ = 'user'

It's done, you can store the actual image files using
:meth:`ImageSet.from_file()` or :meth:`ImageSet.from_blob()`
method::

    with store_context(store):
        user = User()
        with open('picture.jpg', 'rb') as f:
            user.picture.from_blob(f.read())
        with open('front_cover.jpg', 'rb') as f:
            user.front_cover.from_file(f)
        with session.begin():
            session.add(user)

Or you can resize the image to make thumbnails using
:meth:`ImageSet.generate_thumbnail()` method::

    with store_context(store):
        user.picture.generate_thumbnail(ratio=0.5)
        user.picture.generate_thumbnail(height=100)
        user.front_cover.generate_thumbnail(width=500)

"""
from __future__ import division

import cgi
import io
import numbers
import shutil

from sqlalchemy import Column
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.instrumentation import instance_state
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import exists, tuple_
from sqlalchemy.sql.functions import now
from sqlalchemy.types import Boolean, DateTime, Integer, String
from wand.image import Image as WandImage

from .context import current_store, get_current_store, store_context
from .file import ReusableFileProxy
from .store import Store
from .util import append_docstring_attributes

__all__ = 'Image', 'ImageSet', 'image_attachment'


def image_attachment(*args, **kwargs):
    """The helper function, decorates raw
    :func:`~sqlalchemy.orm.relationship()` function, sepcialized for
    relationships between :class:`Image` subtypes.

    It takes the same parameters as :func:`~sqlalchemy.orm.relationship()`.

    :param \*args: the same arguments as
                   :func:`~sqlalchemy.orm.relationship()`
    :param \*\*kwargs: the same keyword arguments as
                       :func:`~sqlalchemy.orm.relationship()`
    :returns: the relationship property
    :rtype: :class:`sqlalchemy.orm.properties.RelationshipProperty`

    .. todo::

       It currently doesn't support population (eager loading) on
       :func:`image_attachment()` relationships yet.

       We seem to need to work something on attribute instrumental
       implementation.

    """
    kwargs.setdefault('lazy', 'dynamic')
    kwargs.setdefault('query_class', ImageSet)
    kwargs.setdefault('uselist', True)
    kwargs.setdefault('cascade', 'all, delete-orphan')
    return relationship(*args, **kwargs)


class Image(object):
    """The image of the particular size.

    Note that it implements :meth:`__html__()` method, a de facto
    standard special method for HTML templating.  So you can simply use
    it in HTML templates like:

    .. sourcecode:: jinja

       {{ user.profile.find_thumbnail(120) }}

    The above template is equivalent to:

    .. sourcecode:: html+jinja

       {% with thumbnail = user.profile.find_thumbnail(120) %}
           <img src="{{ thumbnail.locate() }}"
                width="{{ thumbnail.width }}"
                height="{{ thumbnail.height }}">
       {% endwith %}

    """

    @declared_attr
    def object_type(cls):
        """(:class:`basestring`) The identifier string of the image type.
        It uses :attr:`__tablename__` (which replaces underscores with
        hyphens) by default, but can be overridden.

        """
        try:
            name = cls.__tablename__
        except AttributeError:
            raise NotImplementedError('object_type property has to be '
                                      'implemented')
        return name.replace('_', '-')

    @property
    def object_id(self):
        """(:class:`numbers.Integral`) The identifier number of the image.
        It uses the primary key if it's integer, but can be overridden,
        and must be implemented when the primary key is not integer or
        composite key.

        """
        key_columns = inspect(type(self)).primary_key
        pk = [c.name for c in key_columns if c.name not in ('width', 'height')]
        if len(pk) == 1:
            pk_value = getattr(self, pk[0])
            if isinstance(pk_value, numbers.Integral):
                return pk_value
        raise NotImplementedError('object_id property has to be implemented')

    #: (:class:`numbers.Integral`) The image's width.
    width = Column('width', Integer, primary_key=True)

    #: (:class:`numbers.Integral`) The image's height."""
    height = Column('height', Integer, primary_key=True)

    #: (:class:`basestring`) The mimetype of the image
    #: e.g. ``'image/jpeg'``, ``'image/png'``.
    mimetype = Column('mimetype', String(255), nullable=False)

    #: (:class:`bool`) Whether it is original or resized.
    original = Column('original', Boolean, nullable=False, default=False)

    #: (:class:`datetime.datetime`) The created time.
    created_at = Column('created_at',
                        DateTime(timezone=True), nullable=False, default=now())

    @hybrid_property
    def size(self):
        """(:class:`tuple`) The same to the pair of (:attr:`width`,
        :attr:`height`).

        """
        return self.width, self.height

    @size.expression
    def size(cls):
        return tuple_(cls.width, cls.height)

    @size.setter
    def size(self, size):
        self.width, self.height = size

    def make_blob(self, store=current_store):
        """Gets the byte string of the image from the ``store``.

        :param store: the storage which contains the image.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the binary data of the image
        :rtype: :class:`str`

        """
        with self.open_file(store) as f:
            return f.read()

    def open_file(self, store=current_store, use_seek=False):
        """Opens the file-like object which is a context manager
        (that means it can used for :keyword:`with` statement).

        If ``use_seek`` is ``True`` (though ``False`` by default)
        it guarentees the returned file-like object is also seekable
        (provides :meth:`~file.seek()` method).

        :param store: the storage which contains image files.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the file-like object of the image, which is a context
                  manager (plus, also seekable only if ``use_seek``
                  is ``True``)
        :rtype: :class:`file`,
                :class:`~sqlalchemy_imageattach.file.FileProxy`,
                file-like object

        """
        if not isinstance(store, Store):
            raise TypeError('store must be an instance of '
                            'sqlalchemy_imageattach.store.Store, not ' +
                            repr(store))
        return store.open(self, use_seek)

    def locate(self, store=current_store):
        """Gets the URL of the image from the ``store``.

        :param store: the storage which contains the image.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the url of the image
        :rtype: :class:`basestring`

        """
        if not isinstance(store, Store):
            raise TypeError('store must be an instance of '
                            'sqlalchemy_imageattach.store.Store, not ' +
                            repr(store))
        return store.locate(self)

    def __html__(self):
        u = cgi.escape(self.locate())
        return '<img src="{0}" width="{1}" height="{2}">'.format(u, *self.size)

    __doc__ = append_docstring_attributes(
        __doc__,
        dict((k, v) for k, v in locals().items()
                    if isinstance(v, declared_attr))
    )


class ImageSet(Query):
    """The subtype of :class:`~sqlalchemy.orm.query.Query` specialized
    for :class:`Image`.  It provides more methods and properties over
    :class:`~sqlalchemy.orm.query.Query`.

    Note that it implements :meth:`__html__()` method, a de facto
    standard special method for HTML templating.  So you can simply use
    it in Jinja2 like:

    .. sourcecode:: jinja

       {{ user.profile }}

    instead of:

    .. sourcecode:: html+jinja

       <img src="{{ user.profile|permalink }}"
            width="{{ user.profile.original.width }}"
            height="{{ user.profile.original.height }}">

    """

    #: (:class:`collections.MutableSet`) The set of instances that their
    #: image files are stored but the ongoing transaction isn't committed.
    #: When the transaction might fail and rollback, image files in the
    #: set are deleted back in the storage.
    _stored_images = set()

    #: (:class:`collections.MutableSet`) The set of instanced marked
    #: as deleted.  If the ongoing transaction is successfully committed
    #: the actual files in the storages will be deleted as well.
    #: When the transaction might fail and rollback, image files won't
    #: deleted and the set will be empty.
    _deleted_images = set()

    @classmethod
    def _mark_image_file_stored(cls, mapper, connection, target):
        """When the session flushes, stores actual image files into
        the storage.  Note that these files could be deleted back
        if the ongoing transaction has done rollback.  See also
        :meth:`_delete_image_file()`.

        """
        try:
            file_ = target.file
        except AttributeError:
            raise TypeError('sqlalchemy_imageattach.entity.Image which is '
                            'to be inserted must have file to store')
        try:
            try:
                store = target.store
            except AttributeError:
                raise TypeError('sqlalchemy_imageattach.entity.Image which is '
                                'to be inserted must have store for the file')
            store.store(target, file_)
            cls._stored_images.add((target, store))
            del target.file, target.store
        finally:
            file_.close()

    @classmethod
    def _mark_image_file_deleted(cls, mapper, connection, target):
        """When the session flushes, marks images as deleted.
        The files of this marked images will be actually deleted
        in the image storage when the ongoing transaction succeeds.
        If it fails the :attr:`_deleted_images` queue will be just
        empty.

        """
        cls._deleted_images.add((target, get_current_store()))

    @classmethod
    def _images_failed(cls, session, previous_transaction):
        """Deletes the files of :attr:`_stored_images` back and clears
        the :attr:`_stored_images` and :attr:`_deleted_images` set
        when the ongoing transaction has done rollback.

        """
        for image, store in cls._stored_images:
            store.delete(image)
        cls._stored_images.clear()
        cls._deleted_images.clear()

    @classmethod
    def _images_succeeded(cls, session):
        """Clears the :attr:`_stored_images` set and deletes actual
        files that are marked as deleted in the storage
        if the ongoing transaction has committed.

        """
        for image, store in cls._deleted_images:
            for stored_image, _ in cls._stored_images:
                if (stored_image.object_type == image.object_type and
                    stored_image.object_id == image.object_id and
                    stored_image.width == image.width and
                    stored_image.height == image.height and
                    stored_image.mimetype == image.mimetype):
                    break
            else:
                store.delete(image)
        cls._stored_images.clear()
        cls._deleted_images.clear()

    def from_raw_file(self, raw_file, store=current_store, size=None,
                      mimetype=None, original=True):
        """Similar to :meth:`from_file()` except it's lower than that.
        It assumes that ``raw_file`` is readable and seekable while
        :meth:`from_file()` only assumes the file is readable.
        Also it doesn't make any in-memory buffer while
        :meth:`from_file()` always makes an in-memory buffer and copy
        the file into the buffer.

        If ``size`` and ``mimetype`` are passed, it won't try to read
        image and will use these values instead.

        It's used for implementing :meth:`from_file()` and
        :meth:`from_blob()` methods that are higher than it.

        :param raw_file: the seekable and readable file of the image
        :type raw_file: file-like object, :class:`file`
        :param store: the storage to store the file.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :param size: an optional size of the image.
                     automatically detected if it's omitted
        :type size: :class:`tuple`
        :param mimetype: an optional mimetype of the image.
                         automatically detected if it's omitted
        :type mimetype: :class:`basestring`
        :param original: an optional flag which represents whether
                         it is an original image or not.
                         defualt is ``True`` (meaning original)
        :type original: :class:`bool`
        :returns: the created image instance
        :rtype: :class:`Image`

        """
        cls = self.column_descriptions[0]['type']
        if not (isinstance(cls, type) and issubclass(cls, Image)):
            raise TypeError('the first entity must be a subtype of '
                            'sqlalchemy_imageattach.entity.Image')
        if original and self.session:
            if store is current_store:
                for existing in self:
                    self.remove(existing)
                self.session.flush()
            else:
                with store_context(store):
                    for existing in self:
                        self.remove(existing)
                    self.session.flush()
        if size is None or mimetype is None:
            with WandImage(file=raw_file) as wand:
                size = size or wand.size
                mimetype = mimetype or wand.mimetype
        if mimetype.startswith('image/x-'):
            mimetype = 'image/' + mimetype[8:]
        image = cls(size=size, mimetype=mimetype, original=original)
        raw_file.seek(0)
        image.file = raw_file
        image.store = store
        self.append(image)
        return image

    def from_blob(self, blob, store=current_store):
        """Stores the ``blob`` (byte string) for the image
        into the ``store``.

        :param blob: the byte string for the image
        :type blob: :class:`str`
        :param store: the storage to store the image data.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the created image instance
        :rtype: :class:`Image`

        """
        data = io.BytesIO(blob)
        return self.from_raw_file(data, store, original=True)

    def from_file(self, file, store=current_store):
        """Stores the ``file`` for the image into the ``store``.

        :param file: the readable file of the image
        :type file: file-like object, :class:`file`
        :param store: the storage to store the file.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the created image instance
        :rtype: :class:`Image`

        """
        data = io.BytesIO()
        shutil.copyfileobj(file, data)
        data.seek(0)
        return self.from_raw_file(data, store, original=True)

    @property
    def original(self):
        """(:class:`Image`) The original image.  It could be ``None``
        if there are no stored images yet.

        """
        if Session.object_session(self.instance) is None:
            for image, store in self._stored_images:
                if image.original:
                    return image
            state = instance_state(self.instance)
            try:
                added = state.committed_state[self.attr.key].added_items
            except KeyError:
                pass
            else:
                for image in added:
                    if image.original:
                        return image
            if self.session:
                for image in self.session.new:
                    if image.original:
                        return image
            return
        query = self.filter_by(original=True)
        try:
            return query.one()
        except NoResultFound:
            pass

    def require_original(self):
        """Returns the :attr:`original` image or just raise
        :exc:`~exceptions.IOError` (instead of returning ``None``).
        That means it guarantees the return value is never ``None``
        but always :class:`Image`.

        :returns: the :attr:`original` image
        :rtype: :class:`Image`
        :raises exceptions.IOError: when there's no :attr:`original`
                                    image yet

        """
        original = self.original
        if original is None:
            raise IOError('there is no original image yet')
        return original

    def find_thumbnail(self, width=None, height=None):
        """Finds the thumbnail of the image with the given ``width``
        and/or ``height``.

        :param width: the thumbnail width
        :type width: :class:`numbers.Integral`
        :param height: the thumbnail height
        :type height: :class:`numbers.Integral`
        :returns: the thumbnail image
        :rtype: :class:`Image`
        :raises sqlalchemy.orm.exc.NoResultFound:
           when there's no image of such size

        """
        if width is None and height is None:
            raise TypeError('required width and/or height')
        q = self
        if width is not None:
            q = q.filter_by(width=width)
        if height is not None:
            q = q.filter_by(height=height)
        try:
            return q.one()
        except NoResultFound:
            if width is not None and height is not None:
                msg = 'size: ' + repr((width, height))
            elif width is not None:
                msg = 'width: ' + repr(width)
            else:
                msg = 'height: ' + repr(height)
            raise NoResultFound('no thumbnail image of such ' + msg)

    def generate_thumbnail(self, ratio=None, width=None, height=None,
                           filter='undefined', store=current_store,
                           _preprocess_image=None, _postprocess_image=None):
        """Resizes the :attr:`original` (scales up or down) and
        then store the resized thumbnail into the ``store``.

        :param ratio: resize by its ratio.  if it's greater than 1
                      it scales up, and if it's less than 1 it scales
                      down.  exclusive for ``width`` and ``height``
                      parameters
        :type ratio: :class:`numbers.Real`
        :param width: resize by its width.  exclusive for ``ratio``
                      and ``height`` parameters
        :type width: :class:`numbers.Integral`
        :param height: resize by its height.  exclusive for ``ratio``
                       and ``width`` parameters
        :type height: :class:`numbers.Integral`
        :param filter: a filter type to use for resizing.  choose one in
                       :const:`wand.image.FILTER_TYPES`.  default is
                       ``'undefined'`` which means ImageMagick will try
                       to guess best one to use
        :type filter: :class:`basestring`, :class:`numbers.Integral`
        :param store: the storage to store the resized image file.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :param _preprocess_image: internal-use only option for preprocessing
                                  original image before resizing.
                                  it has to be callable which takes
                                  a :class:`wand.image.Image` object
                                  and returns a new :class:`wand.image.Image`
                                  object
        :type _preprocess_image: :class:`collections.Callable`
        :param _postprocess_image: internal-use only option for preprocessing
                                   original image before resizing.
                                   it has to be callable which takes
                                   a :class:`wand.image.Image` object
                                   and returns a new :class:`wand.image.Image`
                                   object
        :type _postprocess_image: :class:`collections.Callable`
        :returns: the resized thumbnail image.  it might be an already
                  existing image if the same size already exists
        :rtype: :class:`Image`
        :raises exceptions.IOError: when there's no :attr:`original`
                                    image yet

        """
        params = ratio, width, height
        param_count = sum(p is not None for p in params)
        if not param_count:
            raise TypeError('pass an argument ratio, width, or height')
        elif param_count > 1:
            raise TypeError('pass only one argument in ratio, width, or '
                            'height; these parameters are exclusive for '
                            'each other')
        transient = Session.object_session(self.instance) is None
        state = instance_state(self.instance)
        try:
            added = state.committed_state[self.attr.key].added_items
        except KeyError:
            added = []
        if width is not None:
            if not isinstance(width, numbers.Integral):
                raise TypeError('width must be integer, not ' + repr(width))
            elif width < 1:
                raise ValueError('width must be natural number, not ' +
                                 repr(width))
            # find the same-but-already-generated thumbnail
            for image in added:
                if image.width == width:
                    return image
            if not transient:
                query = self.filter_by(width=width)
                try:
                    return query.one()
                except NoResultFound:
                    pass
            height = lambda sz: sz[1] * (width / sz[0])
        elif height is not None:
            if not isinstance(height, numbers.Integral):
                raise TypeError('height must be integer, not ' + repr(height))
            elif height < 1:
                raise ValueError('height must be natural number, not ' +
                                 repr(height))
            # find the same-but-already-generated thumbnail
            for image in added:
                if image.height == height:
                    return image
            if not transient:
                query = self.filter_by(height=height)
                try:
                    return query.one()
                except NoResultFound:
                    pass
            width = lambda sz: sz[0] * (height / sz[1])
        elif ratio is not None:
            if not isinstance(ratio, numbers.Real):
                raise TypeError('ratio must be an instance of numbers.Real, '
                                'not ' + repr(ratio))
            width = lambda sz: sz[0] * ratio
            height = lambda sz: sz[1] * ratio
        data = io.BytesIO()
        with self.open_file(store=store) as f:
            if _preprocess_image is None:
                img = WandImage(file=f)
            else:
                with WandImage(file=f) as img:
                    img = _preprocess_image(img)
            with img:
                original_size = img.size
                if callable(width):
                    width = width(original_size)
                if callable(height):
                    height = height(original_size)
                width = int(width)
                height = int(height)
                # find the same-but-already-generated thumbnail
                for image in added:
                    if image.width == width and image.height == height:
                        return image
                if not transient:
                    query = self.filter_by(width=width, height=height)
                    try:
                        return query.one()
                    except NoResultFound:
                        pass
                img.resize(width, height, filter=filter)
                if _postprocess_image is None:
                    mimetype = img.mimetype
                    img.save(file=data)
                else:
                    with _postprocess_image(img) as img:
                        mimetype = img.mimetype
                        img.save(file=data)
        return self.from_raw_file(data, store,
                                  size=(width, height),
                                  mimetype=mimetype,
                                  original=False)

    def open_file(self, store=current_store, use_seek=False):
        """The shorthand of :meth:`~Image.open_file()` for
        the :attr:`original`.

        :param store: the storage which contains the image files
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :param use_seek: whether the file should seekable.
                         if ``True`` it maybe buffered in the memory.
                         default is ``False``
        :type use_seek: :class:`bool`
        :returns: the file-like object of the image, which is a context
                  manager (plus, also seekable only if ``use_seek``
                  is ``True``)
        :rtype: :class:`file`,
                :class:`~sqlalchemy_imageattach.file.FileProxy`,
                file-like object

        """
        original = self.require_original()
        if Session.object_session(self.instance) is None:
            try:
                file = original.file
            except AttributeError:
                raise IOError('no stored original image file')
            return ReusableFileProxy(file)
        return original.open_file(store, use_seek)

    def make_blob(self, store=current_store):
        """The shorthand of :meth:`~Image.make_blob()` for
        the :attr:`original`.

        :param store: the storage which contains the image files.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the byte string of the :attr:`original` image
        :rtype: :class:`str`

        """
        return self.require_original().make_blob(store)

    def locate(self, store=current_store):
        """The shorthand of :meth:`~Image.locate()` for
        the :attr:`original`.

        :param store: the storage which contains the image files.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the url of the :attr:`original` image
        :rtype: :class:`basestring`

        """
        return self.require_original().locate(store)

    def __nonzero__(self):
        session = Session.object_session(self.instance)
        if session is None:
            return bool(self.count())
        for v, in session.query(exists(self.as_scalar())):
            return bool(v)
        return False

    def __html__(self):
        if not self:
            return ''
        url = cgi.escape(self.locate())
        size = self.require_original().size
        return '<img src="{0}" width="{1}" height="{2}">'.format(url, *size)


listen(Session, 'after_soft_rollback', ImageSet._images_failed)
listen(Session, 'after_commit', ImageSet._images_succeeded)
listen(Image, 'after_insert', ImageSet._mark_image_file_stored, propagate=True)
listen(Image, 'after_delete', ImageSet._mark_image_file_deleted, propagate=True)
