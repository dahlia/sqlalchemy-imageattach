from __future__ import absolute_import

from sqlalchemy_imageattach.util import (append_docstring, classproperty,
                                         get_minimum_indent)


def test_minimum_indent():
    assert get_minimum_indent('Hello') == ''
    assert get_minimum_indent('''Hello
    world

    ''') == '    '
    assert get_minimum_indent('''Hello
    world::

        code

    asdf

    ''') == '    '
    assert get_minimum_indent('''\
    Hello
    world::

        code

    asdf

    ''', 0) == '    '


def test_append_docstring():
    def test_func():
        """Hello.

        :returns: any integer
        :rtype: :class:`numbers.Integral`

        -"""
        return 123
    assert append_docstring(
        test_func.__doc__,
        '.. note::',
        '',
        '   Appended docstring!'
    ) == '''Hello.

        :returns: any integer
        :rtype: :class:`numbers.Integral`

        -
        .. note::

           Appended docstring!
    '''.rstrip()


def test_classproperty():

    class Foo(object):
        @classproperty
        def bar(cls):
            return 'baz'

    assert Foo.bar == 'baz'
    assert Foo().bar == 'baz'
