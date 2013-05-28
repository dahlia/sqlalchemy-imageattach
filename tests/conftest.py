import os
import os.path

from pytest import fixture
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

try:
    from psycopg2cffi.compat import register
except ImportError:
    pass
else:
    register()


DEFAULT_DATABASE_URL = 'sqlite://'

sample_images_dir = os.path.join(os.path.dirname(__file__), 'images')

cmd_options_intiailized = False


def pytest_addoption(parser):
    global cmd_options_intiailized 
    if cmd_options_intiailized:
        return
    env = os.environ.get
    parser.addoption('--database-url', type='string',
                     default=env('IMAGEATTACH_TEST_DATABASE_URL',
                                 DEFAULT_DATABASE_URL),
                     help='Database URL for testing. [default: %default]')
    parser.addoption('--echo-sql', action='store_true', default=False,
                     help='Print all executed queries for failed tests')
    parser.addoption('--s3-name', type='string',
                     default=env('IMAGEATTACH_TEST_S3_NAME'),
                     help='AWS S3 bucket name for testing purpose '
                          '[default: %default]')
    parser.addoption('--s3-access-key', type='string',
                     default=env('IMAGEATTACH_TEST_S3_ACCESS_KEY'),
                     help='AWS credential to access the testing bucket '
                          '[default: %default]')
    parser.addoption('--s3-secret-key', type='string',
                     default=env('IMAGEATTACH_TEST_S3_SECRET_KEY'),
                     help='AWS credential to access the testing bucket '
                          '[default: %default]')
    parser.addoption('--s3-sandbox-name', type='string',
                     default=env('IMAGEATTACH_TEST_S3_SANDBOX_NAME'),
                     help='AWS S3 secondary bucket name for testing purpose '
                          '[default: %default]')
    cmd_options_intiailized = True


Base = declarative_base()
Session = sessionmaker()


@fixture
def fx_session(request):
    try:
        database_url = request.config.getoption('--database-url')
    except ValueError:
        database_url = None
    try:
        echo_sql = request.config.getoption('--echo-sql')
    except ValueError:
        echo_sql = False
    connect_args = {}
    options = {'connect_args': connect_args, 'poolclass': NullPool}
    if database_url == DEFAULT_DATABASE_URL:
        # We have to use SQLite :memory: database across multiple threads
        # for testing.  http://bit.ly/sqlalchemy-sqlite-memory-multithread
        connect_args['check_same_thread'] = False
        options['poolclass'] = StaticPool
    engine = create_engine(database_url, echo=echo_sql, **options)
    metadata = Base.metadata
    metadata.drop_all(bind=engine)
    metadata.create_all(bind=engine)
    session = Session(bind=engine, autocommit=True)
    @request.addfinalizer
    def finalize_session():
        session.rollback()
        metadata.drop_all(bind=engine)
        engine.dispose()
    return session
