import os.path

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
from setuptools.command.test import test

from sqlalchemy_imageattach.version import VERSION


def readme():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
            return f.read()
    except (IOError, OSError):
        return ''


class pytest(test):

    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        from pytest import main
        errno = main(self.test_args)
        raise SystemExit(errno)


install_requires = [
    'SQLAlchemy >= 0.8.0',
    'Wand >= 0.3.0'
]

tests_require = [
    'pytest >= 2.6.0',
    'WebOb'
]


setup(
    name='SQLAlchemy-ImageAttach',
    version=VERSION,
    description='SQLAlchemy extension for attaching images to entity objects',
    long_description=readme(),
    url='https://github.com/dahlia/sqlalchemy-imageattach',
    author='Hong Minhee',
    author_email='hongminhee' '@' 'member.fsf.org',
    license='MIT License',
    packages=find_packages(exclude=['tests', 'tests.stores']),
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={'tests': tests_require},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: Stackless',
        'Topic :: Database :: Front-Ends',
        'Topic :: Multimedia :: Graphics'
    ],
    cmdclass={'test': pytest}
)
