""":mod:`sqlalchemy_imageattach.context` --- Scoped context of image storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scoped context makes other modules able to vertically take an image
store object without explicit parameter for it.  It's similar to
Flask_'s design decision and Werkzeug_'s context locals.
Context locals are workaround to use dynamic scoping in
programming languages that doesn't provide it (like Python).

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

.. _Flask: http://flask.pocoo.org/
.. _Werkzeug: http://werkzeug.pocoo.org/

"""
import contextlib
import sys
if sys.version_info >= (3,):
    try:
        import _thread
    except ImportError:
        import _dummy_thread as _thread
else:
    try:
        import thread as _thread
    except ImportError:
        import dummy_thread as _thread

try:
    import greenlet
except ImportError:
    greenlet = None
try:
    import stackless
except ImportError:
    stackless = None

from .store import Store  # noqa

__all__ = ('ContextError', 'LocalProxyStore', 'context_stacks',
           'current_store', 'get_current_context_id', 'get_current_store',
           'pop_store_context', 'push_store_context', 'store_context')


def get_current_context_id():
    """Identifis which context it is (greenlet, stackless, or thread).

    :returns: the identifier of the current context.

    """
    global get_current_context_id
    if greenlet is not None:
        if stackless is None:
            get_current_context_id = greenlet.getcurrent
            return greenlet.getcurrent()
        return greenlet.getcurrent(), stackless.getcurrent()
    elif stackless is not None:
        get_current_context_id = stackless.getcurrent
        return stackless.getcurrent()
    get_current_context_id = _thread.get_ident
    return _thread.get_ident()


#: (:class:`dict`) The dictionary of concurrent contexts to their stacks.
context_stacks = {}


def push_store_context(store):
    """Manually pushes a store to the current stack.

    Although :func:`store_context()` and :keyword:`with` keyword are
    preferred than using it, it's useful when you have to push and pop
    the current stack on different hook functions like setup/teardown.

    :param store: the image store to set to the :data:`current_store`
    :type store: :class:`~sqlalchemy_imageattach.store.Store`

    """
    context_stacks.setdefault(get_current_context_id(), []).append(store)


def pop_store_context():
    """Manually pops the current store from the stack.

    Although :func:`store_context()` and :keyword:`with` keyword are
    preferred than using it, it's useful when you have to push and pop
    the current stack on different hook functions like setup/teardown.

    :returns: the current image store
    :rtype: :class:`~sqlalchemy_imageattach.store.Store`

    """
    return context_stacks.setdefault(get_current_context_id(), []).pop()


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
    push_store_context(store)
    yield store
    pop_store_context()


def get_current_store():
    """The lower-level function of :data:`current_store`.  It returns
    the **actual** store instance while :data:`current_store` is a just
    proxy of it.

    :returns: the actual object of the currently set image store
    :rtype: :class:`~sqlalchemy_imageattach.store.Store`

    """
    try:
        store = context_stacks.setdefault(get_current_context_id(), [])[-1]
    except IndexError:
        raise ContextError('not in store_context; use sqlalchemy_imageattach.'
                           'entity.store_context()')
    return store


class LocalProxyStore(Store):
    """Proxy of another image storage.

    :param get_current_object: a function that returns "current" store
    :type get_current_object: :class:`typing.Callable`\ [[],
                                                         :class:`.store.Store`]
    :param repr_string: an optional string for :func:`repr()`
    :type repr_string: :class:`str`

    """

    def __init__(self, get_current_object, repr_string=None):
        if not callable(get_current_object):
            raise TypeError('expected callable')
        self.get_current_object = get_current_object
        self.repr_string = repr_string

    def put_file(self, file, object_type, object_id, width, height,
                 mimetype, reproducible):
        self.get_current_object().put_file(
            file, object_type, object_id, width, height,
            mimetype, reproducible
        )

    def delete_file(self, object_type, object_id, width, height, mimetype):
        self.get_current_object().delete_file(
            object_type, object_id, width, height, mimetype
        )

    def get_file(self, object_type, object_id, width, height, mimetype):
        return self.get_current_object().get_file(
            object_type, object_id, width, height, mimetype
        )

    def get_url(self, object_type, object_id, width, height, mimetype):
        return self.get_current_object().get_url(
            object_type, object_id, width, height, mimetype
        )

    def __eq__(self, other):
        return self.get_current_object() == other

    def __ne__(self, other):
        return self.get_current_object() != other

    def __hash__(self):
        return hash(self.get_current_object())

    def __repr__(self):
        if self.repr_string is None:
            try:
                current_store = self.get_current_object()
            except ContextError:
                return '<Unbound {0}.{1}>'.format(self.__module__,
                                                  self.__name__)
            return repr(current_store)
        return self.repr_string


#: (:class:`LocalProxyStore`) The currently set context of the image store
#: backend.  It can be set using :func:`store_context()`.
current_store = LocalProxyStore(get_current_store,
                                __name__ + '.current_store')


class ContextError(Exception):
    """The exception which rises when the :data:`current_store` is required
    but there's no currently set store context.

    """
