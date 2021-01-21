from setuptools import setup, find_packages

VERSION = "8.3.1"

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries",
]

EXTRAS_REQUIRE = {
    "enum": ["marshmallow-enum"],
    "union": ["typeguard"],
    ':python_version == "3.6"': ["dataclasses"],
    "lint": ["pre-commit~=1.18"],
    "docs": ["sphinx"],
    "tests": [
        "pytest>=5.4",
        # re: pypy: typed-ast (a dependency of mypy) fails to install on pypy
        # https://github.com/python/typed_ast/issues/111
        "pytest-mypy-plugins>=1.2.0; implementation_name != 'pypy'",
        # `Literal` was introduced in:
        # - Python 3.8 (https://www.python.org/dev/peps/pep-0586)
        # - typing-extensions 3.7.2 (https://github.com/python/typing/pull/591)
        "typing-extensions~=3.7.2; python_version < '3.8'",
    ],
}
EXTRAS_REQUIRE["dev"] = (
    EXTRAS_REQUIRE["enum"]
    + EXTRAS_REQUIRE["union"]
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
    python_requires=">=3.6",
    install_requires=["marshmallow>=3.0.0,<4.0", "typing-inspect"],
    extras_require=EXTRAS_REQUIRE,
    package_data={"marshmallow_dataclass": ["py.typed"]},
)
