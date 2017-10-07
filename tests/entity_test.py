from __future__ import absolute_import, print_function, with_statement

import contextlib
import hashlib
import os.path
import uuid

from pytest import fixture, raises
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, String
from sqlalchemy_utils.types.uuid import UUIDType
from wand.image import Image as WandImage

from .conftest import Base, sample_images_dir
from sqlalchemy_imageattach.context import store_context
from sqlalchemy_imageattach.entity import Image, NoopContext, image_attachment
from sqlalchemy_imageattach.stores.fs import FileSystemStore


class ExpectedException(Exception):
    """Exception to be expected to rise."""


@fixture
def tmp_store(tmpdir):
    yield FileSystemStore(tmpdir.strpath, 'http://localhost/')
    tmpdir.remove()


class Something(Base):

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    cover = image_attachment('SomethingCover')

    __tablename__ = 'something'


class SomethingCover(Base, Image):

    something_id = Column(Integer, ForeignKey(Something.id), primary_key=True)
    something = relationship(Something)

    __tablename__ = 'something_cover'

    def __repr__(self):
        return '<SomethingCover something_id={0!r} {1!r}x{2!r}{3}>'.format(
            self.something_id, self.width, self.height,
            ' original' if self.original else ''
        )


def test_from_raw_file(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    something = Something(name='some name')
    with open(filepath, 'rb') as f:
        expected = f.read()
        f.seek(0)
        img = something.cover.from_raw_file(f, tmp_store, original=True)
        assert something.cover.original is img
        with fx_session.begin():
            fx_session.add(something)
            assert something.cover.original is img
    assert something.cover.count() == 1
    assert img is something.cover.original
    with something.cover.open_file(tmp_store) as f:
        actual = f.read()
    assert actual == expected
    # overwriting
    something.cover.generate_thumbnail(ratio=0.5, store=tmp_store)
    assert something.cover.count() == 2
    with open(os.path.join(sample_images_dir, 'iu2.jpg'), 'rb') as f:
        expected = f.read()
        f.seek(0)
        img2 = something.cover.from_raw_file(f, tmp_store, original=True)
        assert something.cover.original is img2
        with fx_session.begin():
            fx_session.add(something)
            assert something.cover.original is img2
    assert something.cover.count() == 1
    assert img2 is something.cover.original
    with something.cover.open_file(tmp_store) as f:
        actual = f.read()
    assert actual == expected
    # overwriting + thumbnail generation
    something.cover.generate_thumbnail(ratio=0.5, store=tmp_store)
    assert something.cover.count() == 2
    with open(filepath, 'rb') as f:
        expected = f.read()
        f.seek(0)
        img3 = something.cover.from_raw_file(f, tmp_store, original=True)
        something.cover.generate_thumbnail(width=10, store=tmp_store)
        something.cover.generate_thumbnail(width=20, store=tmp_store)
        assert something.cover.original is img3
        with fx_session.begin():
            fx_session.add(something)
            assert something.cover.original is img3
    assert something.cover.count() == 3
    assert frozenset(img.width for img in something.cover) == frozenset([
        10, 20, img3.width
    ])
    assert img3 is something.cover.original
    with something.cover.open_file(tmp_store) as f:
        actual = f.read()
    assert actual == expected
    if mimetype == 'image/svg+xml':
        # Skip the rest tests for SVG images
        return
    with something.cover.find_thumbnail(width=10).open_file(tmp_store) as f:
        with WandImage(file=f) as wand:
            assert wand.width == 10
    with something.cover.find_thumbnail(width=20).open_file(tmp_store) as f:
        with WandImage(file=f) as wand:
            assert wand.width == 20


class ObjectIdOverriddenImage(Base, Image):

    id = Column(Integer, primary_key=True)

    __tablename__ = 'object_id_overridden_image'

    @property
    def object_id(self):
        return self.id * 2


class UuidKeyImage(Base, Image):

    id = Column(UUIDType, primary_key=True)

    __tablename__ = 'uuid_key_image'


class StringKeyImage(Base, Image):

    id = Column(String(255), primary_key=True)

    __tablename__ = 'string_key_image'


class CompositeKeyImage(Base, Image):

    id_a = Column(Integer, primary_key=True)
    id_b = Column(Integer, primary_key=True)

    __tablename__ = 'composite_key_image'


def test_default_object_id():
    """If the primary key is integer or UUID, object_id is automatically
    filled.

    """
    o = SomethingCover(something_id=12345)
    assert o.object_id == o.something_id
    u = UuidKeyImage(id=uuid.UUID('76fdc405-9120-4ffc-a7a1-3c35409c595f'))
    assert u.object_id == 158166530401166902469325588563807197535


def test_overridden_object_id():
    """object_id can be overridden."""
    o = ObjectIdOverriddenImage(id=12345)
    assert o.object_id == 12345 * 2


def test_string_key_object_id():
    """If the primary key is not integer, object_id cannot be
    automatically implemented.

    """
    o = StringKeyImage(id='string_key')
    with raises(NotImplementedError):
        o.object_id


def test_composite_key_object_id():
    """If the primary key is composite key, object_id cannot be
    automatically implemented.

    """
    o = CompositeKeyImage(id_a=123, id_b=456)
    with raises(NotImplementedError):
        o.object_id


def test_from_raw_file_implicitly(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with open(filepath, 'rb') as f:
            expected = f.read()
            f.seek(0)
            img = something.cover.from_raw_file(f, original=True)
            assert something.cover.original is img
            with fx_session.begin():
                fx_session.add(something)
                assert something.cover.original is img
    assert something.cover.count() == 1
    assert img is something.cover.original
    with store_context(tmp_store):
        with something.cover.open_file() as f:
            actual = f.read()
    assert actual == expected


def test_from_blob(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    something = Something(name='some name')
    with open(filepath, 'rb') as f:
        expected = f.read()
        img = something.cover.from_blob(expected, tmp_store)
        assert something.cover.original is img
        with fx_session.begin():
            fx_session.add(something)
            assert something.cover.original is img
    assert something.cover.count() == 1
    assert img is something.cover.original
    assert something.cover.make_blob(tmp_store) == expected
    # overwriting
    something.cover.generate_thumbnail(ratio=0.5, store=tmp_store)
    assert something.cover.count() == 2
    with open(os.path.join(sample_images_dir, 'iu2.jpg'), 'rb') as f:
        expected = f.read()
        img2 = something.cover.from_blob(expected, tmp_store)
        assert something.cover.original is img2
        with fx_session.begin():
            fx_session.add(something)
            assert something.cover.original is img2
    assert something.cover.count() == 1
    assert img2 is something.cover.original
    assert something.cover.make_blob(tmp_store) == expected


def test_from_blob_implicitly(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with open(filepath, 'rb') as f:
            expected = f.read()
            img = something.cover.from_blob(expected)
            assert something.cover.original is img
            with fx_session.begin():
                fx_session.add(something)
                assert something.cover.original is img
    assert something.cover.count() == 1
    assert img is something.cover.original
    with store_context(tmp_store):
        assert something.cover.make_blob() == expected


def test_rollback_from_raw_file(fx_session, fx_sample_image, tmp_store):
    """When the transaction fails, file shoud not be stored."""
    filepath, mimetype, (width, height) = fx_sample_image
    something = Something(name='some name')
    with fx_session.begin():
        fx_session.add(something)
    with open(filepath, 'rb') as f:
        with raises(ExpectedException):
            with fx_session.begin():
                image = something.cover.from_raw_file(f, tmp_store,
                                                      original=True)
                assert something.cover.original is image
                fx_session.flush()
                assert something.cover.original is image
                args = (image.object_type, image.object_id, image.width,
                        image.height, image.mimetype)
                raise ExpectedException()
    assert something.cover.count() == 0
    assert something.cover.original is None
    with raises(IOError):
        print(tmp_store.get_file(*args))


def test_rollback_from_raw_file_implitcitly(fx_session, fx_sample_image,
                                            tmp_store):
    """When the transaction fails, file shoud not be stored."""
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with fx_session.begin():
            fx_session.add(something)
        with open(filepath, 'rb') as f:
            with raises(ExpectedException):
                with fx_session.begin():
                    image = something.cover.from_raw_file(f, original=True)
                    assert something.cover.original is image
                    fx_session.flush()
                    assert something.cover.original is image
                    args = (image.object_type, image.object_id, image.width,
                            image.height, image.mimetype)
                    raise ExpectedException()
    assert something.cover.count() == 0
    assert something.cover.original is None
    with raises(IOError):
        print(tmp_store.get_file(*args))


def test_delete(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with open(filepath, 'rb') as f:
            image = something.cover.from_file(f)
            assert something.cover.original is image
            with fx_session.begin():
                fx_session.add(something)
                assert something.cover.original is image
            args = (image.object_type, image.object_id, image.width,
                    image.height, image.mimetype)
        with fx_session.begin():
            fx_session.delete(image)
        assert something.cover.original is None
        with raises(IOError):
            tmp_store.get_file(*args)


def test_rollback_from_delete(fx_session, fx_sample_image, tmp_store):
    """When the transaction fails, file should not be deleted."""
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with open(filepath, 'rb') as f:
            expected = f.read()
        image = something.cover.from_blob(expected)
        assert something.cover.original is image
        with fx_session.begin():
            fx_session.add(something)
            assert something.cover.original is image
        with raises(ExpectedException):
            with fx_session.begin():
                assert something.cover.original is image
                fx_session.delete(image)
                raise ExpectedException()
        with tmp_store.open(image) as f:
            actual = f.read()
    assert something.cover.original is image
    assert actual == expected


def test_delete_parent(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with open(filepath, 'rb') as f:
            image = something.cover.from_file(f)
            assert something.cover.original is image
            with fx_session.begin():
                fx_session.add(something)
            assert something.cover.original is image
            args = (image.object_type, image.object_id, image.width,
                    image.height, image.mimetype)
        with fx_session.begin():
            assert something.cover.original is image
            fx_session.delete(something)
        assert something.cover.original is None
        with raises(IOError):
            tmp_store.get_file(*args)


class Samething(Base):
    """Not S'o'mething, but s'a'mething."""

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    cover = image_attachment('SamethingCover')

    __tablename__ = 'samething'


class SamethingCover(Base, Image):

    samething_id = Column(Integer, ForeignKey(Samething.id), primary_key=True)
    samething = relationship(Samething)

    __tablename__ = 'samething_cover'


def test_delete_from_persistence(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with open(filepath, 'rb') as f:
            image = something.cover.from_file(f)
            assert something.cover.original is image
            with fx_session.begin():
                fx_session.add(something)
            assert something.cover.original is image
            args = ('samething-cover', image.object_id, image.width,
                    image.height, image.mimetype)
            fx_session.execute('INSERT INTO samething '
                               'SELECT * FROM something')
            fx_session.execute('INSERT INTO samething_cover '
                               'SELECT * FROM something_cover')
            f.seek(0)
            tmp_store.put_file(f, *(args + (False,)))
        cover = fx_session.query(SamethingCover) \
                          .filter_by(samething_id=something.id) \
                          .one()
        with fx_session.begin():
            fx_session.delete(cover)
        samething = fx_session.query(Samething) \
                              .filter_by(id=something.id) \
                              .one()
        assert samething.cover.original is None
        with raises(IOError):
            print(tmp_store.get_file(*args))


def test_delete_parent_from_persistence(fx_session, fx_sample_image,
                                        tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with open(filepath, 'rb') as f:
            image = something.cover.from_file(f)
            assert something.cover.original is image
            with fx_session.begin():
                fx_session.add(something)
            assert something.cover.original is image
            args = ('samething-cover', image.object_id, image.width,
                    image.height, image.mimetype)
            fx_session.execute('INSERT INTO samething '
                               'SELECT * FROM something')
            fx_session.execute('INSERT INTO samething_cover '
                               'SELECT * FROM something_cover')
            f.seek(0)
            tmp_store.put_file(f, *(args + (False,)))
        samething = fx_session.query(Samething) \
                              .filter_by(id=something.id) \
                              .one()
        with fx_session.begin():
            fx_session.delete(samething)
        assert samething.cover.original is None
        with raises(IOError):
            print(tmp_store.get_file(*args))


def test_rollback_from_delete_parent(fx_session, fx_sample_image, tmp_store):
    """When the transaction fails, file should not be deleted."""
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with open(filepath, 'rb') as f:
            expected = f.read()
        image = something.cover.from_blob(expected)
        assert something.cover.original is image
        with fx_session.begin():
            fx_session.add(something)
            assert something.cover.original is image
        with raises(ExpectedException):
            with fx_session.begin():
                assert something.cover.original is image
                fx_session.delete(something)
                raise ExpectedException()
        with tmp_store.open(image) as f:
            actual = f.read()
    assert actual == expected
    assert something.cover.original is image


def test_generate_thumbnail(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    something = Something(name='some name')
    with raises(IOError):
        something.cover.generate_thumbnail(ratio=0.5, store=tmp_store)
    with open(filepath, 'rb') as f:
        original = something.cover.from_file(f, tmp_store)
        assert something.cover.original is original
        double = something.cover.generate_thumbnail(ratio=2, store=tmp_store)
        thumbnail = something.cover.generate_thumbnail(height=height // 2,
                                                       store=tmp_store)
        assert (something.cover.generate_thumbnail(width=width * 2,
                                                   store=tmp_store)
                is double)
        with fx_session.begin():
            fx_session.add(something)
            assert something.cover.original is original
    assert something.cover.count() == 3
    assert original is something.cover.original
    assert double.size == (width * 2, height * 2)
    half_width = width // 2
    assert thumbnail.height == height // 2
    # workaround off-by-one error
    assert thumbnail.width in (half_width - 1, half_width, half_width + 1)
    half_width = thumbnail.width
    assert (something.cover.generate_thumbnail(width=half_width,
                                               store=tmp_store)
            is thumbnail)
    with fx_session.begin():
        x3 = something.cover.generate_thumbnail(width=width * 3,
                                                store=tmp_store)
    assert something.cover.count() == 4
    x3.size == (width * 3, height * 3)
    thumbnail_sizes = [
        (width, height),
        (width * 2, height * 2),
        (half_width, height // 2)
    ]
    for size in thumbnail_sizes:
        fail_hint = 'size = {0!r}, sizes = {1!r}'.format(
            size, [i.size for i in something.cover]
        )
        assert something.cover.find_thumbnail(width=size[0]) \
                        .size == size, fail_hint
        assert something.cover.find_thumbnail(height=size[1]) \
                        .size == size, fail_hint
        assert something.cover.find_thumbnail(*size).size == size, fail_hint
    with raises(NoResultFound):
        something.cover.find_thumbnail(270)
    with raises(NoResultFound):
        something.cover.find_thumbnail(height=426)
    with raises(NoResultFound):
        something.cover.find_thumbnail(270, 426)


def test_generate_thumbnail_implicitly(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    with store_context(tmp_store):
        something = Something(name='some name')
        with raises(IOError):
            something.cover.generate_thumbnail(ratio=0.5)
        with open(filepath, 'rb') as f:
            original = something.cover.from_file(f)
            assert something.cover.original is original
            double = something.cover.generate_thumbnail(ratio=2)
            thumbnail = something.cover.generate_thumbnail(height=height // 2)
            assert something.cover \
                            .generate_thumbnail(width=width * 2) is double
            with fx_session.begin():
                fx_session.add(something)
                assert something.cover.original is original
        assert something.cover.count() == 3
        assert original is something.cover.original
        assert double.size == (width * 2, height * 2)
        assert thumbnail.height == height // 2
        half_width = width // 2
        # workaround off-by-one error
        assert thumbnail.width in (half_width - 1, half_width, half_width + 1)
        half_width = thumbnail.width
        assert something.cover \
                        .generate_thumbnail(width=half_width) is thumbnail
        with fx_session.begin():
            x3 = something.cover.generate_thumbnail(width=width * 3)
        assert something.cover.count() == 4
        x3.size == (width * 3, height * 3)


def test_imageset_should_be_cleared(fx_session, tmp_store):
    """All previously existing images should be removed even if
    there are already same sizes of thumbnails.

    """
    with store_context(tmp_store):
        with fx_session.begin():
            some = Something(name='Issue 13')
            with open(os.path.join(sample_images_dir, 'shinji.jpg'),
                      'rb') as shinji:
                some.cover.from_file(shinji)
            some.cover.generate_thumbnail(width=100)
            some.cover.generate_thumbnail(width=50)
            fx_session.add(some)
        shinji_500 = hashlib.md5(some.cover.original.make_blob()).digest()
        shinji_100 = hashlib.md5(
            some.cover.find_thumbnail(width=100).make_blob()
        ).digest()
        shinji_50 = hashlib.md5(
            some.cover.find_thumbnail(width=50).make_blob()
        ).digest()
        with fx_session.begin():
            with open(os.path.join(sample_images_dir, 'asuka.jpg'),
                      'rb') as asuka:
                some.cover.from_file(asuka)
            with raises(NoResultFound):
                some.cover.find_thumbnail(width=100)
            some.cover.generate_thumbnail(width=100)
            some.cover.generate_thumbnail(width=50)
            fx_session.add(some)
        asuka_500 = hashlib.md5(some.cover.original.make_blob()).digest()
        asuka_100 = hashlib.md5(
            some.cover.find_thumbnail(width=100).make_blob()
        ).digest()
        asuka_50 = hashlib.md5(
            some.cover.find_thumbnail(width=50).make_blob()
        ).digest()
    assert shinji_500 != asuka_500
    assert shinji_100 != asuka_100
    assert shinji_50 != asuka_50


def test_compile_image_columns(fx_session):
    """These queries should be able to be compiled."""
    query = fx_session.query(SomethingCover)
    query.order_by(Image.width).all()
    query.order_by(Image.height).all()
    query.order_by(Image.mimetype).all()
    query.order_by(Image.original).all()
    query.order_by(Image.created_at).all()


def test_noop_context():
    counter = [0]

    @contextlib.contextmanager
    def object_():
        counter[0] += 1
        yield ()
        counter[0] += 1
    obj = object_()
    assert counter[0] == 0
    with NoopContext(obj) as o:
        assert counter[0] == 0
        assert o is obj
    assert counter[0] == 0


class Manything(Base):

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    covers = image_attachment('ManythingCover', uselist=True)

    __tablename__ = 'manything'


class ManythingCover(Base, Image):

    manything_id = Column(Integer, ForeignKey(Manything.id), primary_key=True)
    cover_id = Column(Integer, primary_key=True)
    manything = relationship(Manything)

    __tablename__ = 'manything_cover'

    @property
    def object_id(self):
        return (self.manything_id + self.cover_id) ** 2 + self.manything_id

    def __repr__(self):
        return '<ManythingCover manything_id={0!r} {1!r}x{2!r}{3}>'.format(
            self.manything_id, self.width, self.height,
            ' original' if self.original else ''
        )


def test_many_images(fx_session, fx_sample_image, tmp_store):
    filepath, mimetype, (width, height) = fx_sample_image
    manything = Manything(name='many name')
    imageset0 = manything.covers.get_image_set(cover_id=0)
    with open(filepath, 'rb') as f:
        expected = f.read()
        f.seek(0)
        img = imageset0.from_raw_file(f, tmp_store, original=True)
        assert imageset0.original is img
        with fx_session.begin():
            fx_session.add(manything)
            assert imageset0.original is img
    assert manything.covers.count() == 1
    assert imageset0.count() == 1
    assert len(list(manything.covers.image_sets)) == 1
    assert img is imageset0.original
    with imageset0.open_file(tmp_store) as f:
        actual = f.read()
    assert actual == expected

    imageset0.generate_thumbnail(ratio=0.5, store=tmp_store)
    assert manything.covers.count() == 2
    assert imageset0.count() == 2
    assert len(list(manything.covers.image_sets)) == 1

    imageset1 = manything.covers.get_image_set(cover_id=1)
    with open(filepath, 'rb') as f:
        expected = f.read()
        f.seek(0)
        img = imageset1.from_raw_file(f, tmp_store, original=True)
        assert imageset1.original is img
        with fx_session.begin():
            fx_session.add(manything)
            assert imageset1.original is img
    assert manything.covers.count() == 3
    assert imageset1.count() == 1
    assert len(list(manything.covers.image_sets)) == 2
    assert img is imageset1.original
    with imageset1.open_file(tmp_store) as f:
        actual = f.read()
    assert actual == expected

    with open(filepath, 'rb') as f:
        imageset0.from_raw_file(f, tmp_store, original=True)
        with fx_session.begin():
            fx_session.add(manything)
    assert manything.covers.count() == 2
    assert imageset0.count() == 1
    assert imageset1.count() == 1
    assert len(list(manything.covers.image_sets)) == 2
