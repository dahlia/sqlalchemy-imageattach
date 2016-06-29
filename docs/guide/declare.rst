.. _declare-image-entities:

Declaring Image Entities
========================

It's easy to use with :mod:`sqlalchemy.ext.declarative`::

    from sqlalchemy import Column, ForeignKey, Integer, Unicode
    from sqlalchemy.orm import relationship
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy_imageattach.entity import Image, image_attachment


    Base = declarative_base()


    class User(Base):
        """User model."""

        id = Column(Integer, primary_key=True)
        name = Column(Unicode, nullable=False)
        picture = image_attachment('UserPicture')
        __tablename__ = 'user'


    class UserPicture(Base, Image):
        """User picture model."""

        user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
        user = relationship('User')
        __tablename__ = 'user_picture'

In the above example, we declare two entity classes.  ``UserPicture`` which
inherits :class:`~sqlalchemy_imageattach.entity.Image` is an image entity,
and ``User`` owns it.  :func:`~sqlalchemy_imageattach.entity.image_attachment()`
function is a specialized :func:`~sqlalchemy.orm.relationship()` for image
entities.  You can understand it as one-to-many relationship.


Object type
-----------

Every image class has :attr:`~sqlalchemy_imageattach.entity.Image.object_type`
string, which is used by the storage.

``UserPicture`` in the above example omits :attr:`object_type
<sqlalchemy_imageattach.entity.Image.object_type>` property,
but it can be overridden if needed.  Its default value is the table name
(underscores will be replaced by hyphens).


When would you need to override :attr:`object_type
<sqlalchemy_imageattach.entity.Image.object_type>`?  The most common case
is when you changed the table name.  Identifiers like path names that
are internally used by the stoage won't be automatically renamed even if
you change the table name in the relational database.  So you need to
maintain the same :attr:`~sqlalchemy_imageattach.entity.Image.object_type`
value.


.. _object-identifier:

Object identifier
-----------------

Every image instance has :attr:`~sqlalchemy_imageattach.entity.Image.object_id`
number, which is used by the storage.  A pair of (:attr:`object_type
<~sqlalchemy_imageattach.entity.Image.object_type>`, :attr:`object_id
<~sqlalchemy_imageattach.entity.Image.object_id>` is an unique key for an image.

``UserPicture`` in the above example omits :attr:`object_id
<sqlalchemy_imageattach.entity.Image.object_id>` property, because it
provides the default value when the primary key is integer.  It has to be
explicitly implemented when the primary key is not integer or composite key.

For example, the most simple and easiest (although naive) way to implement
:attr:`~sqlalchemy_imageattach.entity.Image.object_id` for the string primary
key is hashing it::

    @property
    def object_id(self):
        return int(hashlib.sha1(self.id).hexdigest(), 16)

If the primary key is a pair, encode a pair into an integer::

    @property
    def object_id(self):
        a = self.id_a
        b = self.id_b
        return (a + b) * (a + b) + a

If the primary key is composite of three or more columns, encode a tuple
into a linked list of pairs first, and then encode the pair into an integer.
It's just a way to encode, and there are many other ways to do the same.
