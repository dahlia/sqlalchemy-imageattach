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
:meth:`~BaseImageSet.from_file()` or :meth:`~BaseImageSet.from_blob()`
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
:meth:`~BaseImageSet.generate_thumbnail()` method::

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
import uuid

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

__all__ = ('VECTOR_TYPES', 'BaseImageSet', 'BaseImageQuery', 'Image',
           'ImageSet', 'ImageSubset', 'MultipleImageSet', 'SingleImageSet',
           'image_attachment')


#: (:class:`typing.AbstractSet`\ [:class:`str`]) The set of vector image types.
VECTOR_TYPES = frozenset(['image/svg+xml', 'application/pdf'])


def image_attachment(*args, **kwargs):
    """The helper function, decorates raw
    :func:`~sqlalchemy.orm.relationship()` function, sepcialized for
    relationships between :class:`Image` subtypes.

    It takes the same parameters as :func:`~sqlalchemy.orm.relationship()`.

    If ``uselist`` is :const:`True`, it becomes possible to attach multiple
    image sets.  In order to attach multiple image sets, image entity types
    must have extra discriminating primary key columns to group each image set.

    If ``uselist`` is :const:`False` (which is default), it becomes
    possible to attach only a single image.

    :param \*args: the same arguments as
                   :func:`~sqlalchemy.orm.relationship()`
    :param \*\*kwargs: the same keyword arguments as
                       :func:`~sqlalchemy.orm.relationship()`
    :returns: the relationship property
    :rtype: :class:`sqlalchemy.orm.properties.RelationshipProperty`

    .. versionadded:: 1.0.0
       The ``uselist`` parameter.

    .. todo::

       It currently doesn't support population (eager loading) on
       :func:`image_attachment()` relationships yet.

       We seem to need to work something on attribute instrumental
       implementation.

    """
    if kwargs.get('uselist', False):
        kwargs.setdefault('query_class', MultipleImageSet)
    else:
        kwargs.setdefault('query_class', SingleImageSet)
    kwargs['uselist'] = True
    kwargs.setdefault('lazy', 'dynamic')
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
        """(:class:`str`) The identifier string of the image type.
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

        .. versionchanged:: 1.1.0
           Since 1.1.0, it provides a more default implementation for
           :class:`~uuid.UUID` primary keys.  If a primary key is not
           composite and :class:`~uuid.UUID` type, :attr:`object_id
           <sqlalchemy_imageattach.entity.Image.object_id>` for that doesn't
           have to be implemented.

        """
        pk = self.identity_attributes()
        if len(pk) == 1:
            pk_value = getattr(self, pk[0])
            if isinstance(pk_value, numbers.Integral):
                return pk_value
            elif isinstance(pk_value, uuid.UUID):
                return pk_value.int
        raise NotImplementedError('object_id property has to be implemented')

    @classmethod
    def identity_attributes(cls):
        """A list of the names of primary key fields.

        :returns: A list of the names of primary key fields
        :rtype: :class:`typing.Sequence`\ [:class:`str`]

        .. versionadded:: 1.0.0

        """
        columns = inspect(cls).primary_key
        names = [c.name for c in columns if c.name not in ('width', 'height')]
        return names

    @property
    def identity_map(self):
        """(:class:`typing.Mapping`\ [:class:`str`, :class:`object`])
        A dictionary of the values of primary key fields with their names.

        .. versionadded:: 1.0.0

        """
        pk = self.identity_attributes()
        values = {}
        for name in pk:
            values[name] = getattr(self, name)
        return values

    #: (:class:`numbers.Integral`) The image's width.
    width = Column('width', Integer, primary_key=True)

    #: (:class:`numbers.Integral`) The image's height."""
    height = Column('height', Integer, primary_key=True)

    #: (:class:`str`) The mimetype of the image
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

        If ``use_seek`` is :const:`True` (though :const:`False` by default)
        it guarentees the returned file-like object is also seekable
        (provides :meth:`~file.seek()` method).

        :param store: the storage which contains image files.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the file-like object of the image, which is a context
                  manager (plus, also seekable only if ``use_seek``
                  is :const:`True`)
        :rtype: :class:`file`,
                :class:`~sqlalchemy_imageattach.file.FileProxy`,
                file-like object

        """
        if not isinstance(store, Store):
            raise TypeError('store must be an instance of '
                            'sqlalchemy_imageattach.store.Store, not ' +
                            repr(store))

        if Session.object_session(self) is None:
            try:
                file = self.file
            except AttributeError:
                raise IOError('no stored original image file')
            return ReusableFileProxy(file)

        return store.open(self, use_seek)

    def locate(self, store=current_store):
        """Gets the URL of the image from the ``store``.

        :param store: the storage which contains the image.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :returns: the url of the image
        :rtype: :class:`str`

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
        dict(
            (k, v) for k, v in locals().items() if isinstance(v, declared_attr)
        )
    )


class NoopContext(object):
    """Null context manager that does nothing."""

    __slots__ = 'object_',

    def __init__(self, object_):
        self.object_ = object_

    def __enter__(self, *args, **kwargs):
        return self.object_

    def __exit__(self, *args, **kwargs):
        pass


class BaseImageQuery(Query):
    """The subtype of :class:`~sqlalchemy.orm.query.Query` specialized
    for :class:`Image`.  It provides more methods and properties over
    :class:`~sqlalchemy.orm.query.Query`.

    .. versionadded:: 1.0.0

    """

    #: (:class:`collections.abc.MutableSet`) The set of instances that their
    #: image files are stored but the ongoing transaction isn't committed.
    #: When the transaction might fail and rollback, image files in the
    #: set are deleted back in the storage.
    _stored_images = set()

    #: (:class:`collections.abc.MutableSet`) The set of instanced marked
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
                if stored_image.object_type == image.object_type and \
                   stored_image.object_id == image.object_id and \
                   stored_image.width == image.width and \
                   stored_image.height == image.height and \
                   stored_image.mimetype == image.mimetype:
                    break
            else:
                store.delete(image)
        cls._stored_images.clear()
        cls._deleted_images.clear()

    def _original_images(self, **kwargs):
        """A list of the original images.

        :returns: A list of the original images.
        :rtype: :class:`typing.Sequence`\ [:class:`Image`]
        """

        def test(image):
            if not image.original:
                return False
            for filter, value in kwargs.items():
                if getattr(image, filter) != value:
                    return False
            return True

        if Session.object_session(self.instance) is None:
            images = []
            for image, store in self._stored_images:
                if test(image):
                    images.append(image)

            state = instance_state(self.instance)
            try:
                added = state.committed_state[self.attr.key].added_items
            except KeyError:
                pass
            else:
                for image in added:
                    if test(image):
                        images.append(image)
            if self.session:
                for image in self.session.new:
                    if test(image):
                        images.append(image)
        else:
            query = self.filter_by(original=True, **kwargs)
            images = query.all()
        return images


class BaseImageSet(object):
    """The abstract class of the following two image set types:

    - :class:`SingleImageSet`
    - :class:`ImageSubset`

    The common things about them, abstracted by :class:`BaseImageSet`, are:

    - It always has an :attr:`original` image, and has only one
      :attr:`original` image.
    - It consists of zero or more thumbnails generated from :attr:`original`
      image.
    - Thumbnails can be generated using :func:`generate_thumbnail()` method.
    - Generated thumbnails can be found using :func:`find_thumbnail()` method.

    You can think image set of an abstract image hiding its size details.
    It actually encapsulates physical images of different sizes but having
    all the same look.  So only its :attr:`original` image is canon, and other
    thumbnails are replica of it.

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

    def from_raw_file(self, raw_file, store=current_store, size=None,
                      mimetype=None, original=True, extra_args=None,
                      extra_kwargs=None):
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
        :type mimetype: :class:`str`
        :param original: an optional flag which represents whether
                         it is an original image or not.
                         defualt is :const:`True` (meaning original)
        :type original: :class:`bool`
        :param extra_args: additional arguments to pass to the model's
                           constructor.
        :type extra_args: :class:`collections.abc.Sequence`
        :param extra_kwargs: additional keyword arguments to pass to the
                             model's constructor.
        :type extra_kwargs: :class:`typing.Mapping`\ [:class:`str`,
                                                      :class:`object`]
        :returns: the created image instance
        :rtype: :class:`Image`

        .. versionadded:: 1.0.0
           The ``extra_args`` and ``extra_kwargs`` options.

        """
        query = self.query
        cls = query.column_descriptions[0]['type']
        if not (isinstance(cls, type) and issubclass(cls, Image)):
            raise TypeError('the first entity must be a subtype of '
                            'sqlalchemy_imageattach.entity.Image')

        if original and query.session:
            if store is current_store:
                for existing in query:
                    test_data = existing.identity_map.copy()
                    test_data.update(self.identity_map)
                    if existing.identity_map == test_data:
                        query.remove(existing)
                query.session.flush()
            else:
                with store_context(store):
                    for existing in query:
                        test_data = existing.identity_map.copy()
                        test_data.update(self.identity_map)
                        if existing.identity_map == test_data:
                            query.remove(existing)
                    query.session.flush()
        if size is None or mimetype is None:
            with WandImage(file=raw_file) as wand:
                size = size or wand.size
                mimetype = mimetype or wand.mimetype
        if mimetype.startswith('image/x-'):
            mimetype = 'image/' + mimetype[8:]

        if extra_kwargs is None:
            extra_kwargs = {}
        extra_kwargs.update(self.identity_map)

        if extra_args is None:
            extra_args = ()

        image = cls(size=size, mimetype=mimetype, original=original,
                    *extra_args, **extra_kwargs)
        raw_file.seek(0)
        image.file = raw_file
        image.store = store
        query.append(image)
        return image

    def from_blob(self, blob, store=current_store,
                  extra_args=None, extra_kwargs=None):
        """Stores the ``blob`` (byte string) for the image
        into the ``store``.

        :param blob: the byte string for the image
        :type blob: :class:`str`
        :param store: the storage to store the image data.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :param extra_args: additional arguments to pass to the model's
                           constructor.
        :type extra_args: :class:`collections.abc.Sequence`
        :param extra_kwargs: additional keyword arguments to pass to the
                             model's constructor.
        :type extra_kwargs: :class:`typing.Mapping`\ [:class:`str`,
                                                      :class:`object`]
        :returns: the created image instance
        :rtype: :class:`Image`

        .. versionadded:: 1.0.0
           The ``extra_args`` and ``extra_kwargs`` options.

        """
        data = io.BytesIO(blob)
        return self.from_raw_file(data, store, original=True,
                                  extra_args=extra_args,
                                  extra_kwargs=extra_kwargs)

    def from_file(self, file, store=current_store,
                  extra_args=None, extra_kwargs=None):
        """Stores the ``file`` for the image into the ``store``.

        :param file: the readable file of the image
        :type file: file-like object, :class:`file`
        :param store: the storage to store the file.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :param extra_args: additional arguments to pass to the model's
                           constructor.
        :type extra_args: :class:`collections.abc.Sequence`
        :param extra_kwargs: additional keyword arguments to pass to the
                             model's constructor.
        :type extra_kwargs: :class:`typing.Mapping`\ [:class:`str`,
                                                      :class:`object`]
        :returns: the created image instance
        :rtype: :class:`Image`

        .. versionadded:: 1.0.0
           The ``extra_args`` and ``extra_kwargs`` options.

        """

        if isinstance(file, cgi.FieldStorage):
            file = file.file

        data = io.BytesIO()
        shutil.copyfileobj(file, data)
        data.seek(0)
        return self.from_raw_file(data, store, original=True,
                                  extra_args=extra_args,
                                  extra_kwargs=extra_kwargs)

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
        :type filter: :class:`str`, :class:`numbers.Integral`
        :param store: the storage to store the resized image file.
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :param _preprocess_image: internal-use only option for preprocessing
                                  original image before resizing
        :type _preprocess_image:
            :class:`typing.Callable`\ [[:class:`wand.image.Image`],
                                        :class:`wand.image.Image`]
        :param _postprocess_image: internal-use only option for preprocessing
                                   original image before resizing
        :type _postprocess_image:
            :class:`typing.Callable`\ [[:class:`wand.image.Image`],
                                        :class:`wand.image.Image`]
        :returns: the resized thumbnail image.  it might be an already
                  existing image if the same size already exists
        :rtype: :class:`Image`
        :raise IOError: when there's no :attr:`original` image yet

        """
        params = ratio, width, height
        param_count = sum(p is not None for p in params)
        if not param_count:
            raise TypeError('pass an argument ratio, width, or height')
        elif param_count > 1:
            raise TypeError('pass only one argument in ratio, width, or '
                            'height; these parameters are exclusive for '
                            'each other')

        query = self.query
        transient = Session.object_session(query.instance) is None
        state = instance_state(query.instance)
        try:
            added = state.committed_state[query.attr.key].added_items
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
                q = query.filter_by(width=width)
                try:
                    return q.one()
                except NoResultFound:
                    pass

            def height(sz):
                return sz[1] * (width / sz[0])
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
                q = query.filter_by(height=height)
                try:
                    return q.one()
                except NoResultFound:
                    pass

            def width(sz):
                return sz[0] * (height / sz[1])
        elif ratio is not None:
            if not isinstance(ratio, numbers.Real):
                raise TypeError('ratio must be an instance of numbers.Real, '
                                'not ' + repr(ratio))

            def width(sz):
                return sz[0] * ratio

            def height(sz):
                return sz[1] * ratio
        data = io.BytesIO()
        image = self.require_original()
        with image.open_file(store=store) as f:
            if _preprocess_image is None:
                img = WandImage(file=f)
            else:
                with WandImage(file=f) as img:
                    img = _preprocess_image(img)
            with img:
                if img.mimetype in VECTOR_TYPES:
                    img.format = 'png'
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
                    q = query.filter_by(width=width, height=height)
                    try:
                        return q.one()
                    except NoResultFound:
                        pass
                if len(img.sequence) > 1:
                    img_ctx = img.sequence[0].clone()
                    img_ctx.resize(width, height, filter=filter)
                    img_ctx.strip()
                else:
                    img_ctx = NoopContext(img)
                with img_ctx as single_img:
                    single_img.resize(width, height, filter=filter)
                    single_img.strip()
                    if _postprocess_image is None:
                        mimetype = img.mimetype
                        single_img.save(file=data)
                    else:
                        with _postprocess_image(img) as img:
                            mimetype = img.mimetype
                            single_img.save(file=data)
        return self.from_raw_file(data, store,
                                  size=(width, height),
                                  mimetype=mimetype,
                                  original=False)

    @property
    def original(self):
        """(:class:`Image`) The original image.  It could be :const:`None`
        if there are no stored images yet.

        """
        images = self.query._original_images(**self.identity_map)
        if images:
            return images[0]

    def require_original(self):
        """Returns the :attr:`original` image or just raise
        :exc:`IOError` (instead of returning :const:`None`).
        That means it guarantees the return value is never :const:`None`
        but always :class:`Image`.

        :returns: the :attr:`original` image
        :rtype: :class:`Image`
        :raise IOError: when there's no :attr:`original` image yet

        """
        image = self.original
        if not image:
            raise IOError('there is no original image yet')
        return image

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

    def open_file(self, store=current_store, use_seek=False):
        """The shorthand of :meth:`~Image.open_file()` for
        the :attr:`original`.

        :param store: the storage which contains the image files
                      :data:`~sqlalchemy_imageattach.context.current_store`
                      by default
        :type store: :class:`~sqlalchemy_imageattach.store.Store`
        :param use_seek: whether the file should seekable.
                         if :const:`True` it maybe buffered in the memory.
                         default is :const:`False`
        :type use_seek: :class:`bool`
        :returns: the file-like object of the image, which is a context
                  manager (plus, also seekable only if ``use_seek``
                  is :const:`True`)
        :rtype: :class:`file`,
                :class:`~sqlalchemy_imageattach.file.FileProxy`,
                file-like object

        """
        original = self.require_original()
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
        :rtype: :class:`str`

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


class SingleImageSet(BaseImageQuery, BaseImageSet):
    """Used for :func:`image_attachment()` is congirued ``uselist=False``
    option (which is default).

    It contains one canonical :attr:`~BaseImageSet.original` image and
    its thumbnails, as it's a subtype of :class:`BaseImageSet`.

    .. versionadded:: 1.0.0
       Renamed from :class:`ImageSet`.

    """

    @property
    def identity_map(self):
        return {}

    @property
    def query(self):
        return self


#: Alias of :class:`SingleImageSet`.
#:
#: .. deprecated:: Use :class:`SingleImageSet` to distinguish from
#:                 :class:`MultipleImageSet`.
#:
#: .. versionchanged:: 1.0.0
#:    Renamed to :class:`SingleImageSet`, and this remains only for backward
#:    compatibility.  It will be completely removed in the future.
ImageSet = SingleImageSet  # backward compatibility


class MultipleImageSet(BaseImageQuery):
    """Used for :func:`image_attachment()` is congirued with ``uselist=True``
    option.

    Like :class:`SingleImageSet`, it is a subtype of :class:`BaseImageQuery`.
    It can be filtered using :func:`~sqlalchemy.orm.query.Query.filter()`
    method or sorted using :func:`~sqlalchemy.orm.query.Query.order()` method.

    Unlike :class:`SingleImageSet`, it is not a subtype of
    :class:`BaseImageSet`, as it can contain multiple image sets.
    That means, it's not image set, but set of image sets.
    Its elements are :class:`ImageSubset` objects, that are image sets.

    .. versionadded:: 1.0.0

    """

    def get_image_set(self, **pk):
        """Choose a single image set to deal with.  It takes criteria through
        keyword arguments.  The given criteria doesn't have to be satisfied by
        any already attached images.  Null image sets returned by such criteria
        can be used for attaching a new image set.

        :param \*\*pk: keyword arguments of extra discriminating primary key
                       column names to its values
        :return: a single image set
        :rtype: :class:`ImageSubset`

        """
        return ImageSubset(self, **pk)

    @property
    def image_sets(self):
        """(:class:`typing.Iterable`\ [:class:`ImageSubset`]) The set of
        attached image sets.

        """
        images = self._original_images()
        for image in images:
            yield ImageSubset(self, **image.identity_map)


class ImageSubset(BaseImageSet):
    """Image set which is contained by :class:`MultipleImageSet`.

    It contains one canonical :attr:`~BaseImageSet.original` image and
    its thumbnails, as it's also a subtype of :class:`BaseImageSet`
    like :class:`SingleImageSet`.

    .. versionadded:: 1.0.0

    """

    def __init__(self, _query, **identity_map):
        self.query = _query
        cls = _query.column_descriptions[0]['type']
        if set(identity_map.keys()) > set(cls.identity_attributes()):
            raise TypeError(
                'identity_map got unexpected key {0!r}. it must be one'
                'of the primary key columns {1!r}.'.format(
                    tuple(identity_map.keys()),
                    tuple(cls.identity_attributes())
                )
            )
        self.identity_map = identity_map

    def count(self):
        return self.query.filter_by(**self.identity_map).count()


listen(Session, 'after_soft_rollback', BaseImageQuery._images_failed)
listen(Session, 'after_commit', BaseImageQuery._images_succeeded)
listen(Image, 'after_insert', BaseImageQuery._mark_image_file_stored,
       propagate=True)
listen(Image, 'after_delete', BaseImageQuery._mark_image_file_deleted,
       propagate=True)
