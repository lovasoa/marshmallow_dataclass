from setuptools import setup, find_packages

VERSION = "8.6.1"

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Operating System :: OS Independent",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries",
]

EXTRAS_REQUIRE = {
    "union": ["typeguard>=2.4.1,<4.0.0"],
    "lint": ["pre-commit~=2.17"],
    "docs": ["sphinx"],
    "tests": [
        "pytest>=5.4",
        # re: pypy: typed-ast (a dependency of mypy) fails to install on pypy
        # https://github.com/python/typed_ast/issues/111
        "pytest-mypy-plugins>=1.2.0; implementation_name != 'pypy'",
    ],
}
EXTRAS_REQUIRE["dev"] = (
    EXTRAS_REQUIRE["union"]
    + EXTRAS_REQUIRE["lint"]
    + EXTRAS_REQUIRE["docs"]
    + EXTRAS_REQUIRE["tests"]
)

setup(
    name="marshmallow_dataclass",
    version=VERSION,
    description="Python library to convert dataclasses into marshmallow schemas.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(
        include=["marshmallow_dataclass", "marshmallow_dataclass.*"]
    ),
    author="Ophir LOJKINE",
    author_email="pere.jobs@gmail.com",
    url="https://github.com/lovasoa/marshmallow_dataclass",
    keywords=["marshmallow", "dataclass", "serialization"],
    classifiers=CLASSIFIERS,
    license="MIT",
    python_requires=">=3.9",
    install_requires=[
        "marshmallow>=3.18.0,<4.0",
        "typing-inspect>=0.8.0,<1.0",
        # Need `dataclass_transform(field_specifiers)`
        "typing-extensions>=4.2.0; python_version<'3.11' and python_version>='3.7'",
    ],
    extras_require=EXTRAS_REQUIRE,
    package_data={"marshmallow_dataclass": ["py.typed"]},
)
