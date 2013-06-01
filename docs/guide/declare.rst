Declaring Image Entities
========================

It's easy to use with :mod:`sqlalchemy.ext.declarative`::

    from sqlalchemy import Column, ForeignKey, Integer, Unicode, relationship
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

        user_id = Column(Integer, ForeignKey('User.id'), primary_key=True)
        user = relationship('User')
        __tablename__ = 'user_picture'

In the above example, we declare two entity classes.  ``UserPicture`` which
inherits :class:`~sqlalchemy_imageattach.entity.Image` is an image entity,
and ``User`` owns it.  :func:`~sqlalchemy_imageattach.entity.image_attachment()`
function is a specialized :func:`~sqlalchemy.orm.relationship()` for image
entities.  You can understand it as many-to-many relationship.
