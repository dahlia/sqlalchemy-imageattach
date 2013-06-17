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


setup(
    name='SQLAlchemy-ImageAttach',
    version=VERSION,
    description='SQLAlchemy extension for attaching images to entity objects',
    long_description=readme(),
    url='https://github.com/crosspop/sqlalchemy-imageattach',
    author='Hong Minhee',
    author_email='minhee' '@' 'dahlia.kr',
    license='MIT License',
    packages=find_packages(exclude=['tests']),
    install_requires=install_requires,
    tests_require=['pytest >= 2.3.0', 'WebOb'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: Stackless',
        'Topic :: Database :: Front-Ends',
        'Topic :: Multimedia :: Graphics'
    ],
    cmdclass={'test': pytest}
)
