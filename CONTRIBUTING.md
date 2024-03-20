# Contributing

To create a development environment and install the development dependencies, run :

```bash
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip setuptools
pip install '.[dev]'
pre-commit install --install-hooks
```

Then you can make your changes, and commit them with

```
git commit # Pre-commit hooks should be run, checking your code
```

Every commit is checked with pre-commit hooks for :
 - style consistency with [flake8](https://flake8.pycqa.org/en/latest/manpage.html)
 - type safety with [mypy](http://mypy-lang.org/)
 - test conformance by running [tests](./tests) with [pytest](https://docs.pytest.org/en/latest/)
   - You can run `pytest` from the command line.
 
 - You can also run `tox` from the command line to test in all supported python versions. Note that this will require you to have all supported python versions installed.