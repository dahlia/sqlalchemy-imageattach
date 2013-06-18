import os.path

from pytest import raises
from sqlalchemy_imageattach.store import Store

from .conftest import sample_images_dir
from .stores.conftest import TestingImage, utcnow


class EmptyStore(Store):
    """Store subclass that doesn't implement abstract methods."""


def miss_put_file():
    store = EmptyStore()
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


def miss_delete_file():
    store = EmptyStore()
    with raises(NotImplementedError):
        store.delete_file('testing', 1234, 405, 640, 'image/jpeg')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with raises(NotImplementedError):
        store.delete(image)


def miss_get_file():
    store = EmptyStore()
    with raises(NotImplementedError):
        store.get_file('testing', 1234, 405, 640, 'image/jpeg')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with raises(NotImplementedError):
        store.open(image)


def miss_get_url():
    store = EmptyStore()
    with raises(NotImplementedError):
        store.get_url('testing', 1234, 405, 640, 'image/jpeg')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    with raises(NotImplementedError):
        store.locate(image)
