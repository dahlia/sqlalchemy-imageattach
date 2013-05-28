import datetime

from sqlalchemy.schema import Column
from sqlalchemy.types import Integer

from sqlalchemy_imageattach.entity import Image
from ..conftest import Base


class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return datetime.timedelta(0)


def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=UTC())


class TestingImage(Base, Image):

    thing_id = Column(Integer, primary_key=True)

    @property
    def object_id(self):
        return self.thing_id

    __tablename__ = 'testing'
