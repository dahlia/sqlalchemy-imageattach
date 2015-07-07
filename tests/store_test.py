import datetime
import io
import os.path

from pytest import mark, raises
from sqlalchemy_imageattach.store import Store

from .conftest import sample_images_dir
from .stores.conftest import TestingImage, utcnow


class EmptyStore(Store):
    """Store subclass that doesn't implement abstract methods."""


@mark.parametrize('store_cls', [EmptyStore, Store])
def miss_put_file(store_cls):
    store = store_cls()
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        with raises(NotImplementedError):
            store.put_file(image_file, 'testing', 1234, 405, 640,
                           'image/jpeg', True)
        image = TestingImage(thing_id=1234, width=405, height=640,
                             mimetype='image/jpeg', original=True,
                             created_at=utcnow())
        with raises(NotImplementedError):
            store.store(image, image_file)


@mark.parametrize('store_cls', [EmptyStore, Store])
def miss_delete_file(store_cls):
    store = store_cls()
    with raises(NotImplementedError):
        store.delete_file('testing', 1234, 405, 640, 'image/jpeg')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with raises(NotImplementedError):
        store.delete(image)


@mark.parametrize('store_cls', [EmptyStore, Store])
def miss_get_file(store_cls):
    store = store_cls()
    with raises(NotImplementedError):
        store.get_file('testing', 1234, 405, 640, 'image/jpeg')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with raises(NotImplementedError):
        store.open(image)


@mark.parametrize('store_cls', [EmptyStore, Store])
def miss_get_url(store_cls):
    store = store_cls()
    with raises(NotImplementedError):
        store.get_url('testing', 1234, 405, 640, 'image/jpeg')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with raises(NotImplementedError):
        store.locate(image)


class FakeStore(Store):
    """Fake store to test Store mixin methods."""

    INCLUDE_QUERY_FOR_URL = 999999

    def __init__(self):
        self.log = []

    def put_file(self, file, object_type, object_id, width, height, mimetype,
                 reproducible, created_at):
        self.log.append(
            (file.read(), object_type, object_id, width, height,
             mimetype, reproducible)
        )

    def delete_file(self, object_type, object_id, width, height, mimetype,
                    created_at):
        self.log = [
            log
            for log in self.log
            if log[1:6] != (object_type, object_id, width, height, mimetype)
        ]

    def get_file(self, object_type, object_id, width, height, mimetype,
                 created_at):
        for log in self.log:
            if log[1:6] == (object_type, object_id, width, height, mimetype):
                return io.BytesIO(log[0])
        raise IOError()

    def get_url(self, object_type, object_id, width, height, mimetype,
                created_at):
        hash_ = hash((object_type, object_id, width, height, mimetype))
        url = 'http://fakeurl.com/' + hex(hash_)
        if object_id == self.INCLUDE_QUERY_FOR_URL:
            return url + '?qs=1&qs=2'
        return url


def test_store():
    store = FakeStore()
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        image = TestingImage(thing_id=1234, width=405, height=640,
                             mimetype='image/jpeg', original=True,
                             created_at=utcnow())
        store.store(image, image_file)
        image_file.seek(0)
        assert (image_file.read(), 'testing', 1234, 405, 640, 'image/jpeg',
                False) in store.log


def test_store_typeerror():
    store = FakeStore()
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        with raises(TypeError):
            store.store(123, image_file)
        with raises(TypeError):
            store.store('abc', image_file)
        with raises(TypeError):
            store.store(None, image_file)
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with raises(TypeError):
        store.store(image, 123)
    with raises(TypeError):
        store.store(image, 'abc')
    with raises(TypeError):
        store.store(image, None)


def test_delete():
    store = FakeStore()
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        image = TestingImage(thing_id=1234, width=405, height=640,
                             mimetype='image/jpeg', original=True,
                             created_at=utcnow())
        store.store(image, image_file)
        assert len(store.log) == 1
        store.delete(image)
    assert not store.log


def test_delete_typeerror():
    store = FakeStore()
    with raises(TypeError):
        store.delete(123)
    with raises(TypeError):
        store.delete('abc')
    with raises(TypeError):
        store.delete(None)


def test_open():
    store = FakeStore()
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with open(image_path, 'rb') as image_file:
        store.store(image, image_file)
        image_file.seek(0)
        with store.open(image) as f:
            assert f.read() == image_file.read()


def test_open_seek():
    store = FakeStore()
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with open(image_path, 'rb') as image_file:
        store.store(image, image_file)
        image_file.seek(0)
        with store.open(image, use_seek=True) as f:
            assert f.read() == image_file.read()
            assert f.tell() == image_file.tell()
            f.seek(0)
            assert f.tell() == 0


def test_open_typerrror():
    store = FakeStore()
    with raises(TypeError):
        store.open(123)
    with raises(TypeError):
        store.open('abc')
    with raises(TypeError):
        store.open(None)
    image = TestingImage(width=405, height=640, mimetype='image/jpeg',
                         original=True, created_at=utcnow())
    with raises(TypeError):
        store.open(image)
    image.thing_id = 'not integer'
    with raises(TypeError):
        store.open(image)


def test_locate():
    store = FakeStore()
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    hash_ = hash(('testing', 1234, 405, 640, 'image/jpeg'))
    expected = 'http://fakeurl.com/' + hex(hash_)
    actual, ts1 = store.locate(image).rsplit('?', 1)
    assert actual == expected
    actual, ts2 = store.locate(image).rsplit('?', 1)
    assert actual == expected
    assert ts1 == ts2
    image.created_at += datetime.timedelta(seconds=1)
    actual, ts3 = store.locate(image).rsplit('?', 1)
    assert actual == expected
    assert ts3 != ts1


def test_locate_qs():
    """Timestamp should be properly inserted even if the original url has
    its own query string.

    """
    store = FakeStore()
    image = TestingImage(thing_id=FakeStore.INCLUDE_QUERY_FOR_URL,
                         width=405, height=640, mimetype='image/jpeg',
                         original=True, created_at=utcnow())
    hash_ = hash(('testing', FakeStore.INCLUDE_QUERY_FOR_URL,
                  405, 640, 'image/jpeg'))
    expected = 'http://fakeurl.com/' + hex(hash_) + '?qs=1&qs=2'
    actual, ts1 = store.locate(image).rsplit('&', 1)
    assert actual == expected
    actual, ts2 = store.locate(image).rsplit('&', 1)
    assert actual == expected
    assert ts1 == ts2
    image.created_at += datetime.timedelta(seconds=1)
    actual, ts3 = store.locate(image).rsplit('&', 1)
    assert actual == expected
    assert ts3 != ts1


def test_locate_typeerror():
    store = FakeStore()
    with raises(TypeError):
        store.locate(123)
    with raises(TypeError):
        store.locate('abc')
    with raises(TypeError):
        store.locate(None)
