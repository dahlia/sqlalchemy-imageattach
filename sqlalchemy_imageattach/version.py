""":mod:`sqlalchemy_imageattach.version` --- Version data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
from __future__ import print_function

__all__ = ('SQLA_COMPAT_VERSION', 'SQLA_COMPAT_VERSION_INFO',
           'VERSION', 'VERSION_INFO')


#: (:class:`tuple`) The triple of version numbers e.g. ``(1, 2, 3)``.
VERSION_INFO = (1, 1, 0)

#: (:class:`str`) The version string e.g. ``'1.2.3'``.
VERSION = '{0}.{1}.{2}'.format(*VERSION_INFO)

#: (:class:`tuple`) The triple of minimum compatible SQLAlchemy version
#: e.g. ``(0, 9, 0)``.
#:
#: .. versionadded:: 1.0.0
SQLA_COMPAT_VERSION_INFO = (0, 9, 0)

#: (:class:`str`) The minimum compatible SQLAlchemy version string
#: e.g. ``'0.9.0'``.
#:
#: .. versionadded:: 1.0.0
SQLA_COMPAT_VERSION = '{0}.{1}.{2}'.format(*SQLA_COMPAT_VERSION_INFO)


if __name__ == '__main__':
    print(VERSION)
