import os.path

from setuptools import find_packages, setup

from sqlalchemy_imageattach.version import VERSION


def readme():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
            return f.read()
    except (IOError, OSError):
        pass


install_requires = [
    'SQLAlchemy >= 0.9.0',
    'Wand >= 0.3.0'
]


setup(
    name='SQLAlchemy-ImageAttach',
    version=VERSION,
    description='SQLAlchemy extension for attaching images to entity objects',
    long_description=readme(),
    url='https://github.com/dahlia/sqlalchemy-imageattach',
    author='Hong Minhee',
    author_email='hong.minhee' '@' 'gmail.com',
    license='MIT License',
    packages=find_packages(exclude=['tests', 'tests.stores']),
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: Stackless',
        'Topic :: Database :: Front-Ends',
        'Topic :: Multimedia :: Graphics'
    ]
)
