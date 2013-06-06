""":mod:`sqlalchemy_imageattach.version` --- Version data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
from __future__ import print_function

#: (:class:`tuple`) The triple of version numbers e.g. ``(1, 2, 3)``.
VERSION_INFO = (0, 8, 0)

#: (:class:`str`) The version string e.g. ``'1.2.3'``.
VERSION = '{0}.{1}.{2}'.format(*VERSION_INFO)


if __name__ == '__main__':
    print(VERSION)
