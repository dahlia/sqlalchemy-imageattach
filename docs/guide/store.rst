Storages
========

Choosing the right storage implementation
-----------------------------------------

There are currently only two implementations:

- :mod:`sqlalchemy_imageattach.stores.fs`
- :mod:`sqlalchemy_imageattach.stores.s3`

We recommend you to use :mod:`~sqlalchemy_imageattach.stores.fs` on your local
development box, and switch it to :mod:`~sqlalchemy_imageattach.stores.s3` when
you deploy it to the production system.

If you need to use another storage backend, you can implement the interface
by yourself: :ref:`implement-store`.


Using filesystem on the local development box
---------------------------------------------

The most of computers have a filesystem, so using :mod:`fs
<sqlalchemy_imageattach.stores.fs>` storage is suitable for development.
It works even if you are offline.

Actually there are two kinds of filesystem storages:

:class:`~sqlalchemy_imageattach.stores.fs.FileSystemStore`
   It just stores the images, and simply assumes that you have a separate
   web server for routing static files e.g. Lighttpd_, Nginx_.  For example,
   if you have a sever configuration like this:

   .. code-block:: nginx

      server {
          listen 80;
          server_name images.yourapp.com;
          root /var/local/yourapp/images;
      }

   :class:`~sqlalchemy_imageattach.stores.fs.FileSystemStore` should
   be configured like this::

       sqlalchemy_imageattach.stores.fs.FileSystemStore(
           path='/var/local/yourapp/images',
           base_url='http://images.yourapp.com/'
       )

   .. _Lighttpd: http://www.lighttpd.net/
   .. _Nginx: http://nginx.org/

:class:`~sqlalchemy_imageattach.stores.fs.HttpExposedFileSystemStore`
   In addition to :class:`~sqlalchemy_imageattach.stores.fs.FileSystemStore`'s
   storing features, it does more for you: actually serving files through
   WSGI.  It takes an optional ``prefix`` for url instead of ``base_url``::

       sqlalchemy_imageattach.stores.fs.HttpExposedFileSystemStore(
           path='/var/local/yourapp/images',
           prefix='static/images/'
       )

   The default ``prefix`` is simply ``images/``.

   It provides :meth:`wsgi_middleware()
   <sqlalchemy_imageattach.stores.fs.HttpExposedFileSystemStore.wsgi_middleware>`
   method to inject its own server to your WSGI application.  For example,
   if you are using Flask_::

       from yourapp import app
       app.wsgi_app = store.wsgi_middleware(app.wsgi_app)

   or if Pyramid_::

       app = config.make_wsgi_app()
       app = store.wsgi_middleware(app)

   or if Bottle_::

       app = bottle.app()
       app = store.wsgi_middleware(app)

   .. note::

      The server provided by this isn't production-ready quality, so do not
      use this for your production service.  We recommend you to use
      :class:`~sqlalchemy_imageattach.stores.fs.FileSystemStore` with
      a separate web server like Nginx_ or Lighttpd_ instead.

   .. _Flask: http://flask.pocoo.org/
   .. _Pyramid: http://www.pylonsproject.org/
   .. _Bottle: http://bottlepy.org/


.. _implement-store:

Implementing your own storage
-----------------------------

You can implement a new storage backend if you need.  Every storage has to
inherit :class:`~sqlalchemy_imageattach.store.Store` and implement
the following four methods:

:meth:`~sqlalchemy_imageattach.store.Store.put_file()`
   The method puts a given image to the storage.

   It takes a ``file`` that contains the image blob, four identifier
   values (``object_type``, ``object_id``, ``width``, ``height``) for
   the image, a ``mimetype`` of the image, and a boolean value
   (``reproducible``) which determines whether it can be reproduced or not.

   For example, if it's a filesystem storage, you can make directory/file
   names using ``object_type``, ``object_id``, and size values, and suffix
   using ``mimetype``.  If it's a S3 implementation, it can determine
   whether to use RRS (reduced redundancy storage) or standard storage
   using ``reproducible`` argument.

:meth:`~sqlalchemy_imageattach.store.Store.get_file()`
   The method finds a requested image in the storage.

   It takes four identifier values (``object_type``, ``object_id``,
   ``width``, ``height``) for the image, and a ``mimetype`` of the image.
   The return type must be file-like.

   It should raise :exc:`IOError` or its subtype
   when there's no requested image in the storage.

:meth:`~sqlalchemy_imageattach.store.Store.get_url()`
   The method is similar to :meth:`get_file()
   <sqlalchemy_imageattach.store.Store.get_file>` except it returns
   a URL of the image instead of a file that contains the image blob.

   It doesn't have to raise errors when there's no requested image
   in the storage.  It's okay even if the returned URL is a broken
   link.  Because we assume that it's called only when the requested
   image is sure to be there.  It means you can quickly generate URLs
   by just calculation without any I/O.

   Moreover, you can assume that these URLs are never cached, because
   SQLAlchemy-ImageAttach will automatically appends a query string
   that contains of its updated timestamp for you.

:meth:`~sqlalchemy_imageattach.store.Store.delete_file()`
   The method deletes a requested image in the storage.

   It takes the same arguments to :meth:`get_file()
   <sqlalchemy_imageattach.store.Store.get_file>` and :meth:`get_url()
   <sqlalchemy_imageattach.store.Store.get_url>` methods.

   It must doesn't raise any exception even if there's no requested
   image.

The constructor of it can be anything.  It's not part of the interface.

If you believe your storage implementation could be widely used as well
as for others, please contribute your code by sending a pull request!
We always welcome your contributions.


.. _migrate-store:

Migrating storage
-----------------

SQLAlchemy-ImageAttach provides a simple basic utility to migrate
image data in an old storage to a new storage (although it's not
CLI but API).  In order to migrate storage data you need used
database as well, not only storage.  Because some metadata are only
saved to database.

The following code shows you how to migrate all image data in ``old_store``
to ``new_store``::

    plan = migrate(session, Base, old_store, new_store)
    plan.execute()

In the above code, ``Base`` is declarative base class (which is created by
:func:`sqlalchemy.ext.declarative.declarative_base()`), and ``session`` is
an instance of SQLAlchemy :class:`~sqlalchemy.orm.session.Session`.

If you want to know progress of migration, iterating the result::

    plan = migrate(session, Base, old_store, new_store)
    for image in plan:
        print('Migrated ' + repr(image))

Or pass a ``callback`` function to :meth:`execute()
<sqlalchemy_imageattach.migration.Migration.execute>` method::

    def progress(image):
        print('Migrated ' + repr(image))

    plan = migrate(session, Base, old_store, new_store)
    plan.execute(progress)
