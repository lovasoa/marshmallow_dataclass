from setuptools import setup, find_packages

VERSION = '0.5.3'

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3.7',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries'
]

setup(
    name='marshmallow_dataclass',
    version=VERSION,
    description='Python library to convert dataclasses into marshmallow schemas.',
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    author='Ophir LOJKINE',
    author_email='pere.jobs@gmail.com',
    url='https://github.com/lovasoa/marshmallow_dataclass',
    keywords=['marshmallow', 'dataclass', 'serialization'],
    classifiers=CLASSIFIERS,
    install_requires=['marshmallow>=2.0,<3.0', 'typing-inspect']
)
