.. _multiple-image-sets:

Multiple Image Sets
===================

.. versionadded:: 1.0.0

In the :ref:`previous example <declare-image-entities>`, each ``User`` can have
only a single image set of ``UserPicture``.  Although each ``User`` has
multiple sizes of ``UserPicture`` objects, these ``UserPicture`` must be
all the same look except of their width/height.

So, what if we need to attach multiple image sets?  Imagine there are ``Post``
objects, and each ``Post`` can have zero or more attached pictures that have
different looks each other.  (Think of tweets containing multiple images,
or Facebook posts containing multiple photos.)  In these case, you don't need
only an image set, but a set of image sets.  One more dimension should be there.

Fortunately, :func:`~sqlalchemy_imageattach.entity.image_attachement()` provides
``uselist=True`` option.  It configures the relationship to contain multiple
image sets.  For example::

    class Post(Base):
        """Post containing zero or more photos."""

        id = Column(Integer, primary_key=True)
        content = Column(UnicodeText, nullable=False)
        photos = image_attachment('PostPhoto', uselist=True)
        __tablename__ = 'post'

    class PostPhoto(Base, Image):
        """Photo contained by post."""

        post_id = Column(Integer, ForeignKey(Post.id), primary_key=True)
        post = relationship(Post)
        order_index = Column(Integer, primary_key=True)  # least is first
        __tablename__ = 'post_photo'

In the above example, we should pay attention to two things:

- ``uselist=True`` option of ``image_attachment()``
- ``PostPhoto.order_index`` column which is a part of primary key columns.

As previously stated, ``uselist=True`` option configures the ``Post.photos``
relationship to return a set of image sets, rather than an image set.

The subtle thing is ``PostPhoto.order_index`` column.  If the relationship is
configured with ``userlist=True``, the image entity must have *extra
discriminating primary key columns* to group each image set.


Object identifier
-----------------

If the image type need to override :attr:`object_id
<sqlalchemy_imageattach.entity.Image.object_id>` (see also
:ref:`object-identifier`), the returning object identifier also must be possible
discriminated in the same way e.g.::

    @property
    def object_id(self):
        key = '{0},{1}'.format(self.id, self.order_index)
        return int(hashlib.sha1(key).hexdigest(), 16)


Choosing image set to deal with
-------------------------------

Because ``uselist=True`` option adds one more dimension, you need to choose
an image set to deal with before attaching or getting.  The
:meth:`~sqlalchemy_imageattach.entity.MultipleImageSet.get_image_set()`
method is for that::

    post = session.query(Post).get(post_id)
    first_photo = post.photos.get_image_set(order_index=1)
    original_image_url = first_photo.locate()
    thumbnail_url = first_photo.find_thumbnail(width=300).locate()

Note that the method can take criteria unsatisfied by already attached images.
Null image sets returned by such criteria can be used for attaching a new
image set::

    new_photo = post.photos.get_image_set(order_index=9)
    with open(new_image_path, 'rb') as f:
        new_photo.from_file(f)
        # order_index column of the created image set becomes set to 9.

Need to enumerate all attached image sets?  Use :attr:`image_sets
<sqlalchemy_imageattach.entity.MultipleImageSet.image_sets>` property::

    def thumbnail_urls():
        for image_set in post.photos.image_sets:
            yield image_set.find_thumbnail(width=300).locate()
