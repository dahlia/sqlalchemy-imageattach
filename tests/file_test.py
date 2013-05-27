from __future__ import unicode_literals

import io

from sqlalchemy_imageattach.file import ReusableFileProxy


def test_reusable_file_proxy():
    buffer_ = io.BytesIO(b'abcde' * 100)
    buffer_.seek(20)
    with ReusableFileProxy(buffer_) as proxy:
        assert proxy.tell() == 0
        assert proxy.read() == b'abcde' * 100
        assert proxy.tell() == 500
    assert buffer_.tell() == 20
    assert buffer_.read() == b'abcde' * 96
    buffer_.close()
