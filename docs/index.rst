.. include:: ../README.rst

User's guide
------------

.. toctree::

   guide/declare
   guide/store
   guide/context
   guide/multiset
   changes


.. module:: sqlalchemy_imageattach

:mod:`sqlalchemy_imageattach` --- API
-------------------------------------

.. toctree::
  :maxdepth: 2

  api/context
  api/entity
  api/file
  api/migration
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

SQLAlchemy-ImageAttach is an open source software written by `Hong Minhee`_.
The source code is distributed under `MIT license`_, and you can find it
at `GitHub repository`_:

.. code-block:: console

   $ git clone git://github.com/dahlia/sqlalchemy-imageattach.git

If you find any bug, please create an issue to the `issue tracker`_.
Pull requests are also always welcome!

Check out :doc:`Changelog <changes>` as well.


.. _Hong Minhee: https://hongminhee.org/
.. _MIT license: https://minhee.mit-license.org/
.. _GitHub repository: https://github.com/dahlia/sqlalchemy-imageattach
.. _issue tracker: https://github.com/dahlia/sqlalchemy-imageattach/issues
