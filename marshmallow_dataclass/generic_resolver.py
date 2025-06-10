import copy
import dataclasses
import sys
from typing import (
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)
import typing_inspect
import warnings

if sys.version_info >= (3, 9):
    from typing import Annotated, get_args, get_origin
    from types import GenericAlias
else:
    from typing_extensions import Annotated, get_args, get_origin

    GenericAlias = type(list)


if sys.version_info >= (3, 13):
    from typing import NoDefault
else:
    from typing import final

    @final
    class NoDefault:
        pass


_U = TypeVar("_U")


class UnboundTypeVarError(TypeError):
    """TypeVar instance can not be resolved to a type spec.

    This exception is raised when an unbound TypeVar is encountered.
    """


class InvalidTypeVarDefaultError(TypeError):
    """TypeVar default can not be resolved to a type spec.

    This exception is raised when an invalid TypeVar default is encountered.
    This is most likely a scoping error: https://peps.python.org/pep-0696/#scoping-rules
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
    _default: Union[_U, "_Future[_U]"]

    def __init__(self, default=NoDefault) -> None:
        self._done = False
        self._default = default

    def done(self) -> bool:
        """Return ``True`` if the value is available"""
        return self._done

    def result(self) -> _U:
        """Return the deferred value.

        Raises ``InvalidStateError`` if the value has not been set.
        """
        if self.done():
            return self._result

        if self._default is not NoDefault:
            if isinstance(self._default, _Future):
                return self._default.result()

            return self._default

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
    is_generic = typing_inspect.is_generic_type(clazz)
    type_arguments = get_args(clazz)
    return is_generic and len(type_arguments) > 0


def may_contain_typevars(clazz: type) -> bool:
    """
    Check if the class can contain typevars. This includes Special Forms.

    Different from typing_inspect.is_generic_type as that explicitly ignores Union and Tuple.

    We still need to resolve typevars for Union and Tuple
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
                        default = getattr(potential_type, "__default__", NoDefault)
                        if default is not None:
                            future._default = default
                    else:
                        future.set_result(potential_type)

                args_by_class[subclass] = tuple(subclass_generic_params_to_args)

            else:
                # PEP-696: Typevar's may be used as defaults, but T1 must be used before T2
                # https://peps.python.org/pep-0696/#scoping-rules
                seen_type_args: Dict[TypeVar, _Future] = {}
                for arg in args:
                    default = getattr(arg, "__default__", NoDefault)
                    if default is not None:
                        if isinstance(default, TypeVar):
                            if default in seen_type_args:
                                # We've already seen this TypeVar, Set the default to it's _Future
                                default = seen_type_args[default]

                            else:
                                # We haven't seen this yet, according to PEP-696 this is invalid.
                                raise InvalidTypeVarDefaultError(
                                    f"{subclass.__name__} has an invalid TypeVar default for field {arg}"
                                )

                    seen_type_args[arg] = _Future(default=default)

                args_by_class[subclass] = tuple(seen_type_args.items())

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
    if not resolved_generics or not may_contain_typevars(clazz):
        return clazz

    new_args = tuple(
        (
            _replace_typevars(arg, resolved_generics)
            if may_contain_typevars(arg)
            else (resolved_generics[arg].result() if arg in resolved_generics else arg)
        )
        for arg in get_args(clazz)
    )
    # i.e.: typing.List, typing.Dict, but not list, and dict
    if hasattr(clazz, "copy_with"):
        return clazz.copy_with(new_args)
    # i.e.: list, dict - inspired by typing._strip_annotations
    if sys.version_info >= (3, 9) and isinstance(clazz, GenericAlias):
        return GenericAlias(clazz.__origin__, new_args)  # type:ignore[return-value]

    # I'm not sure how we'd end up here. But raise a warnings so people can create an issue
    warnings.warn(f"Unable to replace typevars in {clazz}")
    return clazz


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
                field_type: type = field.type  # type: ignore[assignment]
                if may_contain_typevars(field_type):
                    new_field = copy.copy(field)
                    new_field.type = _replace_typevars(
                        field_type, resolved_typevars[subclass]
                    )
                elif isinstance(field_type, TypeVar):
                    new_field = copy.copy(field)
                    new_field.type = resolved_typevars[subclass][field_type].result()

                fields[field.name] = (field, new_field)
            except InvalidStateError:
                unbound_fields.add(field.name)

    if unbound_fields:
        raise UnboundTypeVarError(
            f"{clazz.__name__} has unbound fields: {', '.join(unbound_fields)}"
        )

    return tuple(v[1] for v in fields.values())
