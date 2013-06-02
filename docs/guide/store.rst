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


Implementing your own storage
-----------------------------

You can implement a new storage backend if you need.  Every stoage has to
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

   It should raise :exc:`~exceptions.IOError` or its subtype
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
