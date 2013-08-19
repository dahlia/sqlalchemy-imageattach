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

Note that the responsibility to close files is yours.  Because some file-like
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


Getting image urls
------------------

In web environment, the most case you need just an url of an image, not its
binary content.  So :class:`~sqlalchemy_imageattach.entity.ImageSet` object
provide :meth:`~sqlalchemy_imageattach.entity.ImageSet.locate()` method::

    def user_profile(request, user_id):
        user = session.query(User).get(int(user_id))
        with store_context(store):
            picture_url = user.picture.locate()
        return render_template('user_profile.html',
                               user=user, picture_url=picture_url)

It returns the url of the original image (which is not resized).
Read about :ref:`thumbnail` if you want a thumbnail url.

:class:`~sqlalchemy_imageattach.entity.ImageSet` also implements de facto
standard ``__html__()`` special method, so it can be directly rendered in
the most of template engines like Jinja2_, Mako_.  It's expanded to
``<img>`` tag on templates:

.. code-block:: html+jinja

   <div class="user">
       <a href="{{ url_for('user_profile', user_id=user.id) }}"
          title="{{ user.name }}">{{ user.picture }}</a>
   </div>

.. code-block:: html+mako

   <div class="user">
       <a href="${url_for('user_profile', user_id=user.id)}"
          title="${user.name}">${user.picture}</a>
   </div>

The above template codes are equivalent to:

.. code-block:: html+jinja

   <div class="user">
       <a href="{{ url_for('user_profile', user_id=user.id) }}"
          title="{{ user.name }}"><img src="{{ user.picture.locate() }}"
                                       width="{{ user.picture.width }}"
                                       height="{{ user.picture.height }}"></a>
   </div>

.. code-block:: html+mako

   <div class="user">
       <a href="${url_for('user_profile', user_id=user.id)}"
          title="${user.name}"><img src="${user.picture.locate()}"
                                    width="${user.picture.width}"
                                    height="${user.picture.height}"></a>
   </div>

.. note::

   Template expansion of :class:`~sqlalchemy_imageattach.entity.ImageSet`
   might raise :exc:`~sqlalchemy_imageattach.context.ContextError`.
   You should render the template in the context::

       with store_context(store):
           return render_template('user_profile.html', user=user)

   Or use :ref:`implicit-context`.

.. _Jinja2: http://jinja.pocoo.org/
.. _Mako: http://makotemplates.org/


Getting image files
-------------------

:class:`~sqlalchemy_imageattach.entity.ImageSet` provides :meth:`open_file()
<sqlalchemy_imageattach.entity.ImageSet.open_file>` method.  It returns
a file-like object::

    from shutil import copyfileobj

    with store_context(store):
        with user.picture.open_file() as f:
            copyfileobj(f, dst)

Note that the responsibility to close an opened file is yours.  Recommend to
open it in :keyword:`with` block.


Getting image binary
--------------------

There's a shortcut to read byte string from an opened file.
Use :meth:`~sqlalchemy_imageattach.entity.ImageSet.make_blob()` method.
The following two ways are equivalent::

    # make_blob()
    with store_context(store):
        blob = user.picture.make_blob()

    # open().read()
    with store_context(store):
        with user.picture.open_file() as f:
            blob = f.read()


.. _thumbnail:

Thumbnails
----------

You can make thumbnails and then store them into the store using
:meth:`~sqlalchemy_imageattach.entity.ImageSet.generate_thumbnail()` method.
It takes one of three arguments: ``width``, ``height``, or ``ratio``::

    with store_context(store):
        # Make thumbnails
        width_150 = user.picture.generate_thumbnail(width=150)
        height_300 = user.picture.generate_thumbnail(height=300)
        half = user.picture.generate_thumbnail(ratio=0.5)
        # Get their urls
        width_150_url = width_150.locate()
        height_300_url = width_300.locate()
        half = half.locate()

It returns a made :class:`~sqlalchemy_imageattach.entity.Image` object,
and it shares the most of the same methods to
:class:`~sqlalchemy_imageattach.entity.ImageSet` like
:meth:`~sqlalchemy_imageattach.entity.Image.locate()`,
:meth:`~sqlalchemy_imageattach.entity.Image.open_file()`,
:meth:`~sqlalchemy_imageattach.entity.Image.make_blob()`.

Once made thumbnails can be found using :meth:`find_thumbnail()
<sqlalchemy_imageattach.entity.ImageSet.find_thumbnail>`.  It takes one of
two arguments: ``width`` or ``height`` and returns a found
:class:`~sqlalchemy_imageattach.entity.Image` object::

    with store_context(store):
        # Find thumbnails
        width_150 = user.picture.find_thumbnail(width=150)
        height_300 = user.picture.find_thumbnail(height=300)
        # Get their urls
        width_150_url = width_150.locate()
        height_300_url = width_300.locate()

It raises :exc:`~sqlalchemy.orm.exc.NoResultFound` exception when there's
no such size.

You can implement find-or-create pattern using these two methods::

    def find_or_create(imageset, width=None, height=None):
        assert width is not None or height is not None
        try:
            image = imageset.find_thumbnail(width=width, height=height)
        except NoResultFound:
            image = imageset.generate_thumbnail(width=width, height=height)
        return image

We recommend you to queue generating thumbnails and make it done by backend
workers rather than web applications.  There are several tools for that like
Celery_.

.. _Celery: http://www.celeryproject.org/


Expliciting storage
-------------------

It's so ad-hoc, but there's a way to explicit storage to use without any
context: passing the storage to operations as an argument.  Every methods
that need the context also optionally take ``store`` keyword::

    user.picture.from_file(file_, store=store)
    user.picture.from_blob(blob, store=store)
    user.picture.locate(store=store)
    user.picture.open_file(store=store)
    user.picture.make_blob(store=store)
    user.picture.generate_thumbnail(width=150, store=store)
    user.picture.find_thumbnail(width=150, store=store)

The above calls are all equivalent to the following calls in :keyword:`with`
block::

    with store_context(store):
        user.picture.from_file(file_)
        user.picture.from_blob(blob)
        user.picture.locate()
        user.picture.open_file()
        user.picture.make_blob()
        user.picture.generate_thumbnail(width=150)
        user.picture.find_thumbnail(width=150)


.. _implicit-context:

Implicit contexts
-----------------

If your application already manage some context like request-response lifecycle,
you can make context implicit by utilizing these hooks.  SQLAlchemy-ImageAttach
exposes underlayer functions like :func:`push_store_context()
<sqlalchemy_imageattach.context.push_store_context>` and
:func:`~sqlalchemy_imageattach.context.pop_store_context()` that are used for
implementing :func:`~sqlalchemy_imageattach.context.store_context()`.

For example, use :meth:`~flask.Flask.before_request()` and
:meth:`~flask.Flask.teardown_request()` if you are using Flask_::

    from sqlalchemy_imageattach.context import (pop_store_context,
                                                push_store_context)
    from yourapp import app
    from yourapp.config import store

    @app.before_request
    def start_implicit_store_context():
        push_store_context(store)

    @app.teardown_request
    def stop_implicit_store_context(exception=None):
        pop_store_context()

.. _Flask: http://flask.pocoo.org/
