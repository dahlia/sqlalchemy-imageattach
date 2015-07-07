import io
import os.path

from pytest import fixture

from sqlalchemy_imageattach.context import store_context
from sqlalchemy_imageattach.migration import migrate, migrate_class
from sqlalchemy_imageattach.store import Store
from .conftest import Base, sample_images_dir
from .entity_test import Samething, Something, SomethingCover


class SourceStore(Store):

    def __init__(self):
        self.files = {}

    def put_file(self, file, object_type, object_id, width, height, mimetype,
                 reproducible, created_at):
        key = object_type, object_id, width, height, mimetype
        self.files[key] = file.read(), reproducible

    def get_file(self, object_type, object_id, width, height, mimetype,
                 created_at):
        key = object_type, object_id, width, height, mimetype
        return io.BytesIO(self.files[key][0])


@fixture
def fx_source_store():
    return SourceStore()


@fixture
def fx_migration(fx_session, fx_source_store):
    with store_context(fx_source_store):
        with fx_session.begin():
            a1 = Something(name='a1')
            fx_session.add(a1)
            with open(os.path.join(sample_images_dir, 'iu.jpg'), 'rb') as f:
                a1.cover.from_file(f)
            a1.cover.generate_thumbnail(height=480)
            a1.cover.generate_thumbnail(height=320)
            a1.cover.generate_thumbnail(height=160)
            a2 = Something(name='a2')
            fx_session.add(a2)
            with open(os.path.join(sample_images_dir, 'iu2.jpg'), 'rb') as f:
                a2.cover.from_file(f)
            b1 = Samething(name='b1')
            fx_session.add(b1)
            with open(os.path.join(sample_images_dir, 'asuka.jpg'), 'rb') as f:
                b1.cover.from_file(f)
            b1.cover.generate_thumbnail(height=375)
            b1.cover.generate_thumbnail(height=250)
            b1.cover.generate_thumbnail(height=125)
            b2 = Samething(name='b2')
            fx_session.add(b2)
            with open(os.path.join(sample_images_dir, 'shinji.jpg'),
                      'rb') as f:
                b2.cover.from_file(f)


def test_migrate_class_execute(fx_session, fx_source_store, fx_migration):
    dst = SourceStore()
    plan = migrate_class(fx_session, SomethingCover, fx_source_store, dst)
    assert dst.files == {}
    plan.execute()
    assert dst.files == dict(
        (k, v)
        for k, v in fx_source_store.files.items()
        if k[0] == 'something-cover'
    )


def test_migrate_class_iter(fx_session, fx_source_store, fx_migration):
    dst = SourceStore()
    plan = migrate_class(fx_session, SomethingCover, fx_source_store, dst)
    assert dst.files == {}
    for _ in plan:
        pass
    assert dst.files == dict(
        (k, v)
        for k, v in fx_source_store.files.items()
        if k[0] == 'something-cover'
    )


def test_migrate_execute(fx_session, fx_source_store, fx_migration):
    dst = SourceStore()
    plan = migrate(fx_session, Base, fx_source_store, dst)
    assert dst.files == {}
    plan.execute()
    assert fx_source_store.files == dst.files


def test_migrate_iter(fx_session, fx_source_store, fx_migration):
    dst = SourceStore()
    plan = migrate(fx_session, Base, fx_source_store, dst)
    assert dst.files == {}
    for _ in plan:
        pass
    assert fx_source_store.files == dst.files
