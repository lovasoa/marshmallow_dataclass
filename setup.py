from setuptools import setup, find_packages

VERSION = "7.1.0"

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
    "union": ["marshmallow-union"],
    ':python_version == "3.6"': ["dataclasses"],
    "lint": ["pre-commit~=1.18"],
    "docs": ["sphinx"],
}
EXTRAS_REQUIRE["dev"] = (
    EXTRAS_REQUIRE["enum"]
    + EXTRAS_REQUIRE["union"]
    + EXTRAS_REQUIRE["lint"]
    + EXTRAS_REQUIRE["docs"]
)

setup(
    name="marshmallow_dataclass",
    version=VERSION,
    description="Python library to convert dataclasses into marshmallow schemas.",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
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
