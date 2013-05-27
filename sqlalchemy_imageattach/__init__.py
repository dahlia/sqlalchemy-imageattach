""":mod:`sqlalchemy_imageattach` --- SQLAlchemy-ImageAttach
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This package provides a simple way to attach images to the other
object-relationally mapped entities and store these into the physically
agnostic backend storages.

For example, you can simply store image files into the filesystem, and
then deploy your application into the production, make the production to
use AWS S3 instead.  The common backend interface concists of only
essential operations, so you can easily implement a new storage backend.

"""
