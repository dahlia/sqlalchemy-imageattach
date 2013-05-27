import io

from sqlalchemy_imageattach.file import ReusableFileProxy


def test_reusable_file_proxy():
    buffer_ = io.BytesIO('abcde' * 100)
    buffer_.seek(20)
    with ReusableFileProxy(buffer_) as proxy:
        assert proxy.tell() == 0
        assert proxy.read() == 'abcde' * 100
        assert proxy.tell() == 500
    assert buffer_.tell() == 20
    assert buffer_.read() == 'abcde' * 96
    buffer_.close()
