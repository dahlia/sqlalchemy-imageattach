import shutil
import tempfile

from pytest import raises

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
        str(current_store)
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
        str(current_store)
    shutil.rmtree(path)
