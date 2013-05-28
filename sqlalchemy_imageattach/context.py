""":mod:`sqlalchemy_imageattach.context` --- Scoped context of image storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scoped context makes other modules able to vertically take an image
store object without explicit parameter for it.  It's similar to
:pypi:`Flask`'s design decision and actually implemented using
:pypi:`Werkzeug`'s context locals.  Context locals are poor man's
way to use dynamic scoping in programming languages that doesn't
provide it (like Python).

For example, a function can take an image store to use as its parameter::

    def func(store):
        url = store.locate(image)
        # ...

    func(fs_store)

But, what if for various reasions it can't take an image store
as parameter?  You should vertically take it using scoped context::

    def func():
        current_store.locate(image)

    with store_context(fs_store):
        func()

What if you have to pass the another store to other subroutine?::

    def func(store):
        decorated_store = DecoratedStore(store)
        func2(decorated_store)

    def func2(store):
        url = store.locate(image)
        # ...

    func(fs_store)

The above code can be rewritten using scoped context::

    def func():
        decorated_store = DecoratedStore(current_store)
        with store_context(decorated_store):
            func2()

    def func2():
        url = current_store.locate(image)
        # ...

    with store_context(fs_store):
        func()

"""
import contextlib

from werkzeug.local import LocalProxy, LocalStack

from .store import Store

__all__ = ('current_store', 'current_store_stack', 'get_current_store',
           'store_context')


#: (:class:`werkzeug.local.LocalStack`) The context local stack to maintain
#: internal state of nested contexts.
current_store_stack = LocalStack()


@contextlib.contextmanager
def store_context(store):
    """Sets the new (nested) context of the current image storage::

        with store_context(store):
            print current_store

    It could be set nestedly as well::

        with store_context(store1):
            print current_store  # store1
            with store_context(store2):
                print current_store  # store2
            print current_store  # store1 back

    :param store: the image store to set to the :data:`current_store`
    :type store: :class:`~sqlalchemy_imageattach.store.Store`

    """
    if not isinstance(store, Store):
        raise TypeError('store must be an instance of sqlalchemy_imageattach.'
                        'store.Store, not ' + repr(store))
    current_store_stack.push(store)
    yield store
    current_store_stack.pop()


def get_current_store():
    """The lower-level function of :data:`current_store`.  It returns
    the **actual** store instance while :data:`current_store` is a just
    proxy of it.

    :returns: the actual object of the currently set image store
    :rtype: :class:`~sqlalchemy_imageattach.store.Store`

    """
    store = current_store_stack.top
    if store is None:
        raise ContextError('not in store_context; use sqlalchemy_imageattach.'
                           'entity.store_context()')
    return store


class LocalProxyStore(Store, LocalProxy):
    """The subtype of :class:`~sqlalchemy_imageattach.store.Store` and
    :class:`werkzeug.local.LocalProxy`.  It's a proxy of another
    image storage which doesn't fail on instance type checking
    for :class:`~sqlalchemy_imageattach.store.Store` interface::

        from sqlalchemy_imageattach.store import Store
        from werkzeug.local import LocalProxy

        local_proxy_store = LocalProxyStore(get_current_storage)
        local_proxy = LocalProxy(get_current_storage)

        assert isinstance(local_proxy_store, Store), \
               'LocalProxyStore instance passes on instance type checking'
        assert not isinstance(local_proxy, Store), \
               'while LocalProxy fails'

    The constructor takes the same parameters to
    :class:`~werkzeug.local.LocalProxy`'s one.

    """

    def put_file(self, file, object_type, object_id, width, height,
                 mimetype, reproducible):
        self._get_current_object().put_file(
            file, object_type, object_id, width, height,
            mimetype, reproducible
        )

    def delete_file(self, object_type, object_id, width, height, mimetype):
        self._get_current_object().delete_file(
            object_type, object_id, width, height, mimetype
        )

    def get_file(self, object_type, object_id, width, height, mimetype):
        return self._get_current_object().get_file(
            object_type, object_id, width, height, mimetype
        )

    def get_url(self, object_type, object_id, width, height, mimetype):
        return self._get_current_object().get_url(
            object_type, object_id, width, height, mimetype
        )

    def __repr__(self):
        try:
            return super(LocalProxyStore, self).__repr__()
        except ContextError:
            return '("unbound", {0}.current_store)[1]'.format(__name__)


#: (:class:`LocalProxyStore`) The currently set context of the image store
#: backend.  It can be set using :func:`store_context()`.
current_store = LocalProxyStore(get_current_store, 'current_store')


class ContextError(Exception):
    """The exception which rises when the :data:`current_store` is required
    but there's no currently set store context.

    """
