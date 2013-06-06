import functools
import os.path
import re
try:
    from urllib import request as urllib2
except ImportError:
    import urllib2
import uuid

from pytest import fixture, mark, raises, skip

from sqlalchemy_imageattach.stores import s3
from sqlalchemy_imageattach.stores.s3 import S3SandboxStore, S3Store
from ..conftest import sample_images_dir
from .conftest import TestingImage, utcnow


remove_query = functools.partial(re.compile(r'\?.*$').sub, '')

# Don't use HTTPS for unit testing (to utilize fakes3)
s3.BASE_URL_FORMAT = 'http://{0}.s3.amazonaws.com'

# Set debuglevel=1 of urllib2 to debug
handler = urllib2.HTTPHandler(debuglevel=1)
urllib2.install_opener(urllib2.build_opener(handler))


@fixture
def s3_store_getter(request):
    try:
        name = request.config.getoption('--s3-name')
    except ValueError:
        name = None
    if name is None:
        skip('--s3-{name,access-key,secret-key} options (and IMAGEATTACH_TEST'
             '_S3_{NAME,ACCESS_KEY,SECRET_KEY} envvars) were not provided')
        return
    try:
        access_key = request.config.getoption('--s3-access-key')
    except ValueError:
        access_key = None
    try:
        secret_key = request.config.getoption('--s3-secret-key')
    except ValueError:
        secret_key = None
    return functools.partial(S3Store, name,
                             access_key=access_key,
                             secret_key=secret_key)


@fixture
def s3_sandbox_store_getter(request):
    try:
        name = request.config.getoption('--s3-name')
        sandbox_name = request.config.getoption('--s3-sandbox-name')
    except ValueError:
        name = None
    if name is None:
        skip('--s3-{name,sandbox-name,access-key,secret-key} options '
             '(and POPTESTS_S3_{NAME,SANDBOX_NAME,ACCESS_KEY,SECRET_KEY} '
             'envvars) were not provided')
        return
    try:
        access_key = request.config.getoption('--s3-access-key')
    except ValueError:
        access_key = None
    try:
        secret_key = request.config.getoption('--s3-secret-key')
    except ValueError:
        secret_key = None
    return functools.partial(S3SandboxStore,
                             underlying=name,
                             overriding=sandbox_name,
                             access_key=access_key,
                             secret_key=secret_key)


@mark.parametrize('prefix', ['', 'prefixtest'])
def test_s3_store(prefix, s3_store_getter):
    s3 = s3_store_getter(prefix=prefix)
    thing_id = uuid.uuid1().int
    image = TestingImage(thing_id=thing_id, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        expected_data = image_file.read()
        image_file.seek(0)
        s3.store(image, image_file)
    with s3.open(image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_url = s3.get_url('testing', thing_id, 405, 640, 'image/jpeg')
    actual_url = s3.locate(image)
    assert remove_query(expected_url) == remove_query(actual_url)
    if prefix:
        no_prefix = s3_store_getter()
        with raises(IOError):
            no_prefix.open(image)
    s3.delete(image)
    with raises(IOError):
        s3.open(image)


@mark.parametrize(('underlying_prefix', 'overriding_prefix'), [
    ('under', 'over'),
    ('', '')
])
@mark.slow
def test_s3_sandbox_store(underlying_prefix, overriding_prefix,
                          s3_sandbox_store_getter):
    s3 = s3_sandbox_store_getter(underlying_prefix=underlying_prefix,
                                 overriding_prefix=overriding_prefix)
    under = s3.underlying
    over = s3.overriding
    id_offset = uuid.uuid1().int
    if id_offset % 2:  # id_offset is always even
        id_offset -= 1
    if not underlying_prefix:
        id_offset *= -1
    # Store a fixture image for underlying store
    under_id = id_offset + 1
    under_image = TestingImage(thing_id=under_id, width=405, height=640,
                               mimetype='image/jpeg', original=True,
                               created_at=utcnow())
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        expected_data = image_file.read()
        image_file.seek(0)
        under.store(under_image, image_file)
    # Underlying images have to be logically shown through sandbox
    with s3.open(under_image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_url = under.get_url('testing', under_id, 405, 640, 'image/jpeg')
    actual_url = s3.locate(under_image)
    assert remove_query(expected_url) == remove_query(actual_url)
    # Store an image to sandbox store
    over_id = id_offset + 2
    image = TestingImage(thing_id=over_id, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        s3.store(image, image_file)
    # Image has to be logically stored
    with s3.open(image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_url = over.get_url('testing', over_id, 405, 640, 'image/jpeg')
    actual_url = s3.locate(image)
    assert remove_query(expected_url) == remove_query(actual_url)
    # Image has to be physically stored into the overriding store
    with over.open(image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_url = over.get_url('testing', over_id, 405, 640, 'image/jpeg')
    actual_url = s3.locate(image)
    assert remove_query(expected_url) == remove_query(actual_url)
    # Images must not be physically stored into the underlying store
    with raises(IOError):
        under.open(image)
    # Deletion must not touch underlying
    s3.delete(under_image)
    with raises(IOError):
        s3.open(under_image)
    with under.open(under_image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_url = over.get_url('testing', under_id, 405, 640, 'image/jpeg')
    actual_url = s3.locate(under_image)
    assert remove_query(expected_url) == remove_query(actual_url)
    # Clean up fixtures
    if underlying_prefix and overriding_prefix:
        no_prefix = s3_sandbox_store_getter()
        with raises(IOError):
            no_prefix.open(image)
    under.delete(under_image)
