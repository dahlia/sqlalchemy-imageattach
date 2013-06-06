Attaching Images
================

You've :doc:`declared entities <declare>` and :doc:`choose a storage <store>`,
so then the next step is to actually attach images to objects!  In order to
determine what storage to save images into, you can set the current *context*.


Context
-------

A context knows what storage you are using now, and tell entities the storage
to use.  You can set a context using :func:`store_context()
<sqlalchemy_imageattach.context.store_context>` function in :keyword:`with`
block::

    from sqlalchemy_imageattach.context import store_context

    with store_context(store):
        with open('image_to_attach.jpg') as f:
            entity.picture.from_file(f)

You would face :exc:`~sqlalchemy_imageattach.context.ContextError`
when you try attaching images without any context.


Attaching from file object
--------------------------

A way to attach an image to an object is loading it from a file object using
:class:`~sqlalchemy_imageattach.entity.ImageSet.from_file()` method.
The following example code shows how to attach a profile picture to an user::

    from yourapp.config import session, store

    def set_picture(request, user_id):
        try:
            user = session.query(User).get(int(user_id))
            with store_context(store):
                user.picture.from_file(request.files['picture'])
        except Exception:
            session.rollback()
            raise
        session.commit()

It takes any file-like objects as well e.g.::

    from urllib2 import urlopen

    def set_picture_url(request, user_id):
        try:
            user = session.query(User).get(int(user_id))
            picture_url = request.values['picture_url']
            with store_context(store):
                user.picture.from_file(urlopen(picture_url))
        except Exception:
            session.rollback()
            raise
        session.commit()

Note that the responisibility to close files is yours.  Because some file-like
objects can be reused several times, or don't have to be closed (or some of
them even don't have any ``close()`` method).


Attaching from byte string
--------------------------

Of course you can load images from its byte strings.  Use
:class:`~sqlalchemy_imageattach.entity.ImageSet.from_blob()` method::

    from requests import get

    def set_picture_url(request, user_id):
        try:
            user = session.query(User).get(int(user_id))
            picture_url = request.values['picture_url']
            image_binary = get(picture_url).content
            with store_context(store):
                user.picture.from_blob(image_binary)
        except Exception:
            session.rollback()
            raise
        session.commit()
