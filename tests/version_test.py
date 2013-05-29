import collections
import numbers
import os

from sqlalchemy import __version__
from sqlalchemy_imageattach.version import VERSION, VERSION_INFO


def test_version_info():
    assert isinstance(VERSION_INFO, collections.Sequence)
    assert len(VERSION_INFO) == 3
    assert isinstance(VERSION_INFO[0], numbers.Integral)
    assert isinstance(VERSION_INFO[1], numbers.Integral)
    assert isinstance(VERSION_INFO[2], numbers.Integral)


def test_sqlalchemy_version():
    assert map(int, __version__.split('.')[:2]) == list(VERSION_INFO[:2])
    assert __version__.split('.')[:2] == VERSION.split('.')[:2]


def test_version():
    assert isinstance(VERSION, str)
    assert map(int, VERSION.split('.')) == list(VERSION_INFO)


def test_print():
    with os.popen('python -m sqlalchemy_imageattach.version') as pipe:
        printed_version = pipe.read().strip()
        assert printed_version == VERSION
