import copy
import dataclasses
import inspect
import sys
from typing import (
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
)

import typing_inspect

if sys.version_info >= (3, 9):
    from typing import Annotated, get_args, get_origin
else:
    from typing_extensions import Annotated, get_args, get_origin

_U = TypeVar("_U")


class UnboundTypeVarError(TypeError):
    """TypeVar instance can not be resolved to a type spec.

    This exception is raised when an unbound TypeVar is encountered.

    """


class InvalidStateError(Exception):
    """Raised when an operation is performed on a future that is not
    allowed in the current state.
    """


class _Future(Generic[_U]):
    """The _Future class allows deferred access to a result that is not
    yet available.
    """

    _done: bool
    _result: _U

    def __init__(self) -> None:
        self._done = False

    def done(self) -> bool:
        """Return ``True`` if the value is available"""
        return self._done

    def result(self) -> _U:
        """Return the deferred value.

        Raises ``InvalidStateError`` if the value has not been set.
        """
        if self.done():
            return self._result
        raise InvalidStateError("result has not been set")

    def set_result(self, result: _U) -> None:
        if self.done():
            raise InvalidStateError("result has already been set")
        self._result = result
        self._done = True


def is_generic_alias(clazz: type) -> bool:
    """
    Check if given object is a Generic Alias.

    A `generic alias`__ is a generic type bound to generic parameters.

    E.g., given

        class A(Generic[T]):
            pass

    ``A[int]`` is a _generic alias_ (while ``A`` is a *generic type*, but not a *generic alias*).
    """
    is_generic = is_generic_type(clazz)
    type_arguments = get_args(clazz)
    return is_generic and len(type_arguments) > 0


def is_generic_type(clazz: type) -> bool:
    """
    typing_inspect.is_generic_type explicitly ignores Union and Tuple
    """
    origin = get_origin(clazz)
    return origin is not Annotated and (
        (isinstance(clazz, type) and issubclass(clazz, Generic))  # type: ignore[arg-type]
        or isinstance(clazz, typing_inspect.typingGenericAlias)
    )


def _resolve_typevars(clazz: type) -> Dict[type, Dict[TypeVar, _Future]]:
    """
    Attemps to resolves all TypeVars in the class bases. Allows us to resolve inherited and aliased generics.

    Returns a dict of each base class and the resolved generics.
    """
    # Use Tuples so can zip (order matters)
    args_by_class: Dict[type, Tuple[Tuple[TypeVar, _Future], ...]] = {}
    parent_class: Optional[type] = None
    # Loop in reversed order and iteratively resolve types
    for subclass in reversed(clazz.mro()):
        if issubclass(subclass, Generic) and hasattr(subclass, "__orig_bases__"):  # type: ignore[arg-type]
            args = get_args(subclass.__orig_bases__[0])

            if parent_class and args_by_class.get(parent_class):
                subclass_generic_params_to_args: List[Tuple[TypeVar, _Future]] = []
                for (_arg, future), potential_type in zip(
                    args_by_class[parent_class], args
                ):
                    if isinstance(potential_type, TypeVar):
                        subclass_generic_params_to_args.append((potential_type, future))
                    else:
                        future.set_result(potential_type)

                args_by_class[subclass] = tuple(subclass_generic_params_to_args)

            else:
                args_by_class[subclass] = tuple((arg, _Future()) for arg in args)

            parent_class = subclass

    # clazz itself is a generic alias i.e.: A[int]. So it hold the last types.
    if is_generic_alias(clazz):
        origin = get_origin(clazz)
        args = get_args(clazz)
        for (_arg, future), potential_type in zip(args_by_class[origin], args):  # type: ignore[index]
            if not isinstance(potential_type, TypeVar):
                future.set_result(potential_type)

    # Convert to nested dict for easier lookup
    return {k: {typ: fut for typ, fut in args} for k, args in args_by_class.items()}


def _replace_typevars(
    clazz: type, resolved_generics: Optional[Dict[TypeVar, _Future]] = None
) -> type:
    if not resolved_generics or inspect.isclass(clazz) or not is_generic_type(clazz):
        return clazz

    return clazz.copy_with(  # type: ignore
        tuple(
            (
                _replace_typevars(arg, resolved_generics)
                if is_generic_type(arg)
                else (
                    resolved_generics[arg].result() if arg in resolved_generics else arg
                )
            )
            for arg in get_args(clazz)
        )
    )


def get_generic_dataclass_fields(clazz: type) -> Tuple[dataclasses.Field, ...]:
    unbound_fields = set()
    # Need to manually resolve fields because `dataclasses.fields` doesn't handle generics and
    # looses the source class. Thus I don't know how to resolve this at later on.
    # Instead we recreate the type but with all known TypeVars resolved to their actual types.
    resolved_typevars = _resolve_typevars(clazz)
    # Dict[field_name, Tuple[original_field, resolved_field]]
    fields: Dict[str, Tuple[dataclasses.Field, dataclasses.Field]] = {}

    for subclass in reversed(clazz.mro()):
        if not dataclasses.is_dataclass(subclass):
            continue

        for field in dataclasses.fields(subclass):
            try:
                if field.name in fields and fields[field.name][0] == field:
                    continue  # identical, so already resolved.

                # Either the first time we see this field, or it got overridden
                # If it's a class we handle it later as a Nested. Nothing to resolve now.
                new_field = field
                if not inspect.isclass(field.type) and is_generic_type(field.type):
                    new_field = copy.copy(field)
                    new_field.type = _replace_typevars(
                        field.type, resolved_typevars[subclass]
                    )
                elif isinstance(field.type, TypeVar):
                    new_field = copy.copy(field)
                    new_field.type = resolved_typevars[subclass][field.type].result()

                fields[field.name] = (field, new_field)
            except InvalidStateError:
                unbound_fields.add(field.name)

    if unbound_fields:
        raise UnboundTypeVarError(
            f"{clazz.__name__} has unbound fields: {', '.join(unbound_fields)}"
        )

    return tuple(v[1] for v in fields.values())
