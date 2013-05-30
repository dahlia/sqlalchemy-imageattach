SQLAlchemy-ImageAttach
======================

SQLAlchemy-ImageAttach is a SQLAlchemy extension for attaching images to
enities.  It's easy to use with :mod:`sqlalchemy.ext.declarative`::

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


.. module:: sqlalchemy_imageattach

:mod:`sqlalchemy_imageattach` --- API
-------------------------------------

.. toctree::
  :maxdepth: 2

  api/context
  api/entity
  api/file
  api/store
  api/util
  api/version


.. automodule:: sqlalchemy_imageattach.stores
   :members:

   .. toctree::
      :maxdepth: 2

      stores/fs
      stores/s3


Open source
-----------

SQLAlchemy-ImageAttach is an open source software written by `Hong Minhee`_
(initially written for Crosspop_).  The source code is distributed under
`MIT license`_ and you can find it at `GitHub repository`_.  Check out now:

.. code-block:: console

   $ git clone git://github.com/crosspop/sqlalchemy-imageattach.git

If you find any bug, please create an issue to the `issue tracker`_.
Pull requests are also always welcome!

.. image:: https://secure.travis-ci.org/crosspop/sqlalchemy-imageattach.png
   :alt: Build Status
   :target: http://travis-ci.org/crosspop/sqlalchemy-imageattach

.. image:: https://coveralls.io/repos/crosspop/sqlalchemy-imageattach/badge.png
   :alt: Coverage Status
   :target: https://coveralls.io/r/crosspop/sqlalchemy-imageattach


.. _Hong Minhee: http://dahlia.kr/
.. _Crosspop: http://crosspop.in/
.. _MIT license: http://minhee.mit-license.org/
.. _GitHub repository: https://github.com/crosspop/sqlalchemy-imageattach
.. _issue tracker: https://github.com/crosspop/sqlalchemy-imageattach/issues
