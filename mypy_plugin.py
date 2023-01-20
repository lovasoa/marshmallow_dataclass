"""Shim to load the marshmallow_dataclass.mypy plugin.

This shim is needed when running mypy from pre-commit.

Pre-commit runs mypy from its own venv (into which we do not want
to install marshmallow_dataclass). Because of this, loading the plugin
by module name, e.g.

    [tool.mypy]
    plugins = "marshmallow_dataclass.mypy"

does not work. Mypy also supports specifying a path to the plugin
module source, which would normally get us out of this bind, however,
the fact that our plugin is in a file named "mypy.py" causes issues.

If we set

    [tool.mypy]
    plugins = "marshmallow_dataclass/mypy.py"

mypy `attempts to load`__ the plugin module by temporarily prepending
 ``marshmallow_dataclass`` to ``sys.path`` then importing the ``mypy``
module. Sadly, mypy's ``mypy`` module has already been imported,
so this doesn't end well.

__ https://github.com/python/mypy/blob/914901f14e0e6223077a8433388c367138717451/mypy/build.py#L450


Our solution, here, is to manually load the plugin module (with a better
``sys.path``, and import the ``plugin`` from the real plugin module into this one.

Now we can configure mypy to load this file, by path.

    [tool.mypy]
    plugins = "mypy_plugin.py"

"""
import importlib
import sys
from os import fspath
from pathlib import Path
from typing import Type
from warnings import warn

from mypy.plugin import Plugin


def null_plugin(version: str) -> Type[Plugin]:
    """A fallback do-nothing plugin hook"""
    return Plugin


module_name = "marshmallow_dataclass.mypy"

src = fspath(Path(__file__).parent)
sys.path.insert(0, src)
try:
    plugin_module = importlib.import_module(module_name)
    plugin = plugin_module.plugin
except Exception as exc:
    warn(f"can not load {module_name} plugin: {exc}")
    plugin = null_plugin
finally:
    del sys.path[0]
