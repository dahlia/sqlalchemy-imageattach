import shutil
import tempfile
import threading

try:
    import greenlet
except ImportError:
    greenlet = None
try:
    import stackless
except ImportError:
    stackless = None
from pytest import mark, raises

from sqlalchemy_imageattach.context import (ContextError, current_store,
                                            get_current_store, store_context)
from sqlalchemy_imageattach.store import Store
from sqlalchemy_imageattach.stores.fs import FileSystemStore


def test_store_context():
    path = tempfile.mkdtemp()
    store = FileSystemStore(path, 'http://localhost/')
    with raises(ContextError):
        get_current_store()
    with raises(ContextError):
        current_store.get_current_object()
    store2 = Store()
    with store_context(store) as s:
        assert s is store
        assert get_current_store() is store
        assert current_store == store
        with store_context(store2) as s2:
            assert s2 is store2
            assert get_current_store() is store2
            assert current_store == store2
            with store_context(store) as s3:
                assert s3 is store
                assert get_current_store() is store
                assert current_store == store
            assert s2 is store2
            assert get_current_store() is store2
            assert current_store == store2
        assert s is store
        assert get_current_store() is store
        assert current_store == store
    with raises(ContextError):
        get_current_store()
    with raises(ContextError):
        current_store.get_current_object()
    shutil.rmtree(path)


def test_thread_context():
    values = []
    store_1 = Store()
    store_2 = Store()
    def context_1():
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
        with store_context(store_1):
            values.append(get_current_store())
            thread_2.start()
            thread_2.join()
            values.append(get_current_store())
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
    def context_2():
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
        with store_context(store_2):
            values.append(get_current_store())
    thread_1 = threading.Thread(target=context_1)
    thread_2 = threading.Thread(target=context_2)
    thread_1.start()
    thread_1.join()
    assert values == ['error', store_1, 'error', store_2, store_1, 'error']


@mark.skipif('greenlet is None')
def test_greenlet_context():
    values = []
    store_1 = Store()
    store_2 = Store()
    def context_1():
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
        with store_context(store_1):
            values.append(get_current_store())
            greenlet_2.switch()
            values.append(get_current_store())
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
    def context_2():
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
        with store_context(store_2):
            values.append(get_current_store())
            greenlet_1.switch()
    greenlet_1 = greenlet.greenlet(context_1)
    greenlet_2 = greenlet.greenlet(context_2)
    greenlet_1.switch()
    assert values == ['error', store_1, 'error', store_2, store_1, 'error']


@mark.skipif('stackless is None')
def test_stackless_context():
    values = []
    store_1 = Store()
    store_2 = Store()
    def context_1(channel, join_channel):
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
        with store_context(store_1):
            values.append(get_current_store())
            task_2(channel)
            channel.receive()
            values.append(get_current_store())
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
        join_channel.send(None)
    def context_2(channel):
        try:
            s = get_current_store()
        except ContextError:
            values.append('error')
        else:
            values.append(s)
        with store_context(store_2):
            values.append(get_current_store())
            channel.send(None)
    task_1 = stackless.tasklet(context_1)
    task_2 = stackless.tasklet(context_2)
    channel = stackless.channel()
    join_channel = stackless.channel()
    task_1(channel, join_channel)
    join_channel.receive()
    assert values == ['error', store_1, 'error', store_2, store_1, 'error']
