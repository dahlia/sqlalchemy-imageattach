""":mod:`sqlalchemy_imageattach.migration` --- Storage migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.orm.session import Session

from .entity import Image
from .store import Store

__all__ = 'MigrationPlan', 'migrate', 'migrate_class'


def migrate(session, declarative_base, source, destination):
    """Migrate all image data from ``source`` storage to ``destination``
    storage.  All data in ``source`` storage are *not* deleted.

    It does not execute migration by itself alone.  You need to
    :meth:`~MigrationPlan.execute()` the plan it returns::

        migrate(session, Base, source, destination).execute()

    Or iterate it using :keyword:`for` statement::

        for i in migrate(session, Base, source, destination):
            # i is an image just done migration
            print(i)

    :param session: SQLAlchemy session
    :type session: :class:`sqlalchemy.orm.session.Session`
    :param declarative_base:
       declarative base class created by
       :func:`sqlalchemy.ext.declarative.declarative_base`
    :type declarative_base:
       :class:`sqlalchemy.ext.declarative.api.DeclarativeMeta`
    :param source: the storage to copy image data from
    :type source: :class:`~sqlalchemy_imageattach.store.Store`
    :param destination: the storage to copy image data to
    :type destination: :class:`~sqlalchemy_imageattach.store.Store`
    :returns: iterable migration plan which is not executed yet
    :rtype: :class:`MigrationPlan`

    """
    if not isinstance(session, Session):
        raise TypeError('session must be an instance of sqlalchemy.orm.'
                        'session.Session, not ' + repr(session))
    elif not isinstance(declarative_base, DeclarativeMeta):
        raise TypeError('declarative_base must be an instance of sqlalchemy.'
                        'ext.declarative.api.DeclarativeMeta, not ' +
                        repr(declarative_base))
    elif not isinstance(source, Store):
        raise TypeError('source must be an instance of sqlalchemy_imageattach'
                        '.store.Store, not ' + repr(source))
    elif not isinstance(destination, Store):
        raise TypeError('destination must be an instance of '
                        'sqlalchemy_imageattach.store.Store, not ' +
                        repr(source))
    classes = set(
        cls
        for cls in declarative_base._decl_class_registry.values()
        if isinstance(cls, type) and issubclass(cls, Image)
    )

    # FIXME: it's not aware of single table inheritance
    @MigrationPlan
    def result():
        for cls in classes:
            for instance in migrate_class(session, cls, source, destination):
                yield instance
    return result


def migrate_class(session, cls, source, destination):
    """Migrate all image data of ``cls`` from ``source`` storage to
    ``destination`` storage.  All data in ``source`` storage are *not*
    deleted.

    It does not execute migration by itself alone.  You need to
    :meth:`~MigrationPlan.execute()` the plan it returns::

        migrate_class(session, UserPicture, source, destination).execute()

    Or iterate it using :keyword:`for` statement::

        for i in migrate_class(session, UserPicture, source, destination):
            # i is an image just done migration
            print(i)

    :param session: SQLAlchemy session
    :type session: :class:`sqlalchemy.orm.session.Session`
    :param cls: declarative mapper class
    :type cls: :class:`sqlalchemy.ext.declarative.api.DeclarativeMeta`
    :param source: the storage to copy image data from
    :type source: :class:`~sqlalchemy_imageattach.store.Store`
    :param destination: the storage to copy image data to
    :type destination: :class:`~sqlalchemy_imageattach.store.Store`
    :returns: iterable migration plan which is not executed yet
    :rtype: :class:`MigrationPlan`

    """
    if not isinstance(session, Session):
        raise TypeError('session must be an instance of sqlalchemy.orm.'
                        'session.Session, not ' + repr(session))
    elif not isinstance(cls, DeclarativeMeta):
        raise TypeError('cls must be an instance of sqlalchemy.'
                        'ext.declarative.api.DeclarativeMeta, not ' +
                        repr(cls))
    elif not isinstance(source, Store):
        raise TypeError('source must be an instance of sqlalchemy_imageattach'
                        '.store.Store, not ' + repr(source))
    elif not isinstance(destination, Store):
        raise TypeError('destination must be an instance of '
                        'sqlalchemy_imageattach.store.Store, not ' +
                        repr(source))

    @MigrationPlan
    def result():
        for instance in session.query(cls):
            with source.open(instance) as f:
                destination.store(instance, f)
                yield instance
    return result


class MigrationPlan(object):
    """Iterable object that yields migrated images."""

    def __init__(self, function):
        self.function = function

    def __iter__(self):
        return self.function()

    def execute(self, callback=None):
        """Execute the plan.  If optional ``callback`` is present,
        it is invoked with an :class:`~sqlalchemy_imageattach.entity.Image`
        instance for every migrated image.

        :param callback: an optional callback that takes
                         an :class:`~sqlalchemy_imageattach.entity.Image`
                         instance.  it's called zero or more times
        :type callback: :class:`~typing.Callable`\ [[:class:`~.entity.Image`],
                                                     :const:`None`]

        """
        if callback is None:
            for _ in self:
                pass
        elif not callable(callback):
            raise TypeError('callback must be callable, not ' +
                            repr(callback))
        else:
            for instance in self:
                callback(instance)
