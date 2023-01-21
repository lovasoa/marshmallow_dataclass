import inspect
from typing import Callable, Optional, Type

from mypy import nodes
from mypy.plugin import ClassDefContext, DynamicClassDefContext, Plugin
from mypy.plugins import dataclasses
from mypy.plugins.common import add_attribute_to_class
from mypy.types import AnyType, TypeOfAny, TypeType

import marshmallow_dataclass

_NEW_TYPE_SIG = inspect.signature(marshmallow_dataclass.NewType)


def plugin(version: str) -> Type[Plugin]:
    return MarshmallowDataclassPlugin


class MarshmallowDataclassPlugin(Plugin):
    def get_dynamic_class_hook(
        self, fullname: str
    ) -> Optional[Callable[[DynamicClassDefContext], None]]:
        if fullname == "marshmallow_dataclass.NewType":
            return new_type_hook
        return None

    def get_class_decorator_hook(
        self, fullname: str
    ) -> Optional[Callable[[ClassDefContext], None]]:
        if fullname == "marshmallow_dataclass.dataclass":
            return dataclasses.dataclass_tag_callback
        return None

    def get_class_decorator_hook_2(
        self, fullname: str
    ) -> Optional[Callable[[ClassDefContext], bool]]:
        if fullname == "marshmallow_dataclass.dataclass":
            return class_decorator_hook
        return None


def class_decorator_hook(ctx: ClassDefContext) -> bool:
    if not dataclasses.dataclass_class_maker_callback(ctx):
        return False
    any_type = AnyType(TypeOfAny.explicit)
    schema_type = ctx.api.named_type_or_none("marshmallow.Schema") or any_type
    schema_type_type = TypeType.make_normalized(schema_type)
    add_attribute_to_class(ctx.api, ctx.cls, "Schema", schema_type_type)
    return True


def new_type_hook(ctx: DynamicClassDefContext) -> None:
    """
    Dynamic class hook for :func:`marshmallow_dataclass.NewType`.

    Uses the type of the ``typ`` argument.
    """
    typ = _get_arg_by_name(ctx.call, "typ", _NEW_TYPE_SIG)
    if not isinstance(typ, nodes.RefExpr):
        return
    info = typ.node
    if not isinstance(info, nodes.TypeInfo):
        return
    ctx.api.add_symbol_table_node(ctx.name, nodes.SymbolTableNode(nodes.GDEF, info))


def _get_arg_by_name(
    call: nodes.CallExpr, name: str, sig: inspect.Signature
) -> Optional[nodes.Expression]:
    """
    Get value of argument from a call.

    :return: The argument value, or ``None`` if it cannot be found.

    .. warning::
        This probably doesn't yet work for calls with ``*args`` and/or ``*kwargs``.
    """
    args = []
    kwargs = {}
    for arg_name, arg_value in zip(call.arg_names, call.args):
        if arg_name is None:
            args.append(arg_value)
        else:
            kwargs[arg_name] = arg_value
    try:
        bound_args = sig.bind(*args, **kwargs)
    except TypeError:
        return None
    try:
        return bound_args.arguments[name]  # type: ignore[no-any-return]
    except KeyError:
        return None
