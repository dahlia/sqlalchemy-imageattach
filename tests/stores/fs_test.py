import functools
import os
import os.path
import re

from pytest import mark, raises
from webob import Request

from sqlalchemy_imageattach.stores.fs import (FileSystemStore,
                                              HttpExposedFileSystemStore,
                                              StaticServerMiddleware,
                                              guess_extension)
from ..conftest import sample_images_dir
from .conftest import TestingImage, utcnow



def test_fs_store(tmpdir):
    fs_store = FileSystemStore(tmpdir.strpath, 'http://mock/img/')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        expected_data = image_file.read()
        image_file.seek(0)
        fs_store.store(image, image_file)
    with fs_store.open(image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_url = 'http://mock/img/testing/234/1/1234.405x640.jpe'
    actual_url = fs_store.locate(image)
    assert expected_url == re.sub(r'\?.*$', '', actual_url)
    fs_store.delete(image)
    with raises(IOError):
        fs_store.open(image)
    tmpdir.remove()


remove_query = functools.partial(re.compile(r'\?.*$').sub, '')


def test_http_fs_store(tmpdir):
    http_fs_store = HttpExposedFileSystemStore(tmpdir.strpath)
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        expected_data = image_file.read()
        image_file.seek(0)
        http_fs_store.store(image, image_file)
    with http_fs_store.open(image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_urls = (
        'http://localhost:80/__images__/testing/234/1/1234.405x640.jpe',
        'http://localhost:80/__images__/testing/234/1/1234.405x640.jpg'
    )
    def app(environ, start_response):
        start_response(
            '200 OK',
            [('Content-Type', 'text/plain; charset=utf-8')]
        )
        yield http_fs_store.locate(image).encode('utf-8')
    app = http_fs_store.wsgi_middleware(app)
    request = Request.blank('/')
    response = request.get_response(app)
    actual_url = response.text
    assert remove_query(actual_url) in expected_urls
    request = Request.blank('/__images__/testing/234/1/1234.405x640.jpe')
    response = request.get_response(app)
    assert response.status_code == 200
    assert response.body == expected_data
    assert response.content_type == 'image/jpeg'
    http_fs_store.delete(image)
    with raises(IOError):
        http_fs_store.open(image)
    tmpdir.remove()


@mark.parametrize('block_size', [None, 8192, 1024, 1024 * 1024])
def test_static_server(block_size):
    def fallback_app(environ, start_response):
        start_response(
            '200 OK',
            [('Content-Type', 'text/plain; charset=utf-8')]
        )
        yield b'fallback: '
        yield environ['PATH_INFO'].encode('utf-8')
    test_dir = os.path.join(os.path.dirname(__file__), '..')
    if block_size:
        app = StaticServerMiddleware(fallback_app, '/static/', test_dir,
                                     block_size)
    else:
        app = StaticServerMiddleware(fallback_app, '/static/', test_dir)
    # 200 OK
    request = Request.blank('/static/context_test.py')
    response = request.get_response(app)
    assert response.status_code == 200
    assert response.content_type == 'text/x-python'
    with open(os.path.join(test_dir, 'context_test.py'), 'rb') as f:
        assert response.body == f.read()
        assert response.content_length == f.tell()
    # 200 OK: subdirectory
    request = Request.blank('/static/stores/fs_test.py')
    response = request.get_response(app)
    assert response.status_code == 200
    assert response.content_type == 'text/x-python'
    with open(os.path.join(test_dir, 'stores', 'fs_test.py'), 'rb') as f:
        assert response.body == f.read()
        assert response.content_length == f.tell()
    # 404 Not Found
    request = Request.blank('/static/not-exist')
    response = request.get_response(app)
    assert response.status_code == 404
    # fallback app
    request = Request.blank('/static-not/')
    response = request.get_response(app)
    assert response.text == 'fallback: /static-not/'


def test_guess_extension():
    assert guess_extension('image/jpeg') == '.jpe'
    assert guess_extension('image/png') == '.png'
    assert guess_extension('image/gif') == '.gif'
