""":mod:`sqlalchemy_imageattach.util` --- Utilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides some utility functions to manipulate
docstrings at runtime.  It's useful for adjusting the docs
built by Sphinx without making the code ugly.

"""
import re
import textwrap

__all__ = ('append_docstring', 'append_docstring_attributes',
           'get_minimum_indent')


def get_minimum_indent(docstring, ignore_before=1):
    r"""Gets the minimum indent string from the ``docstring``:

    >>> get_minimum_indent('Hello')
    ''
    >>> get_minimum_indent('Hello\n    world::\n        yeah')
    '    '

    :param docstring: the docstring to find its minimum indent
    :type docstring: :class:`str`
    :param ignore_before: ignore lines before this line.
                          usually docstrings which follow :pep:`8`
                          have no indent for the first line,
                          so its default value is 1
    :type ignore_before: :class:`numbers.Integral`
    :returns: the minimum indent string which consists of only
              whitespaces (tabs and/or spaces)
    :rtype: :class:`str`

    """
    indent_re = re.compile(r'^\s*')
    indents = [indent_re.match(line).group(0)
               for line in docstring.splitlines()[ignore_before:]
               if line.strip()]
    return min(indents, key=len) if indents else ''


def append_docstring(docstring, *lines):
    """Appends the ``docstring`` with given ``lines``::

        function.__doc__ = append_docstring(
            function.__doc__,
            '.. note::'
            '',
            '   Appended docstring!'
        )

    :param docstring: a docstring to be appended
    :param \*lines: lines of trailing docstring
    :returns: new docstring which is appended
    :rtype: :class:`str`

    """
    shallowest = get_minimum_indent(docstring)
    appender = []
    for line in lines:
        appender.append('\n')
        if line.strip():
            appender.append(shallowest)
            appender.append(line)
    return docstring + ''.join(appender)


def append_docstring_attributes(docstring, locals):
    """Manually appends class' ``docstring`` with its attribute docstrings.
    For example::

        class Entity(object):
            # ...

            __doc__ = append_docstring_attributes(
                __doc__,
                dict((k, v) for k, v in locals()
                            if isinstance(v, MyDescriptor))
            )

    :param docstring: class docstring to be appended
    :type docstring: :class:`str`
    :param locals: attributes dict
    :type locals: :class:`~typing.Mapping`\ [:class:`str`, :class:`object`]
    :returns: appended docstring
    :rtype: :class:`str`

    """
    docstring = docstring or ''
    for attr, val in locals.items():
        doc = val.__doc__
        if not doc:
            continue
        doc = get_minimum_indent(doc) + doc
        lines = ['   ' + l for l in textwrap.dedent(doc).splitlines()]
        docstring = append_docstring(
            docstring,
            '',
            '.. attribute:: ' + attr,
            '',
            *lines
        )
    return docstring
