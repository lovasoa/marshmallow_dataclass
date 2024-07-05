import copy
import dataclasses
import inspect
import sys
from typing import (
    Any,
    Dict,
    ForwardRef,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
)

import typing_inspect

if sys.version_info >= (3, 9):
    from typing import Annotated, get_args, get_origin

    def eval_forward_ref(t: ForwardRef, globalns, localns, recursive_guard=frozenset()):
        return t._evaluate(globalns, localns, recursive_guard)

else:
    from typing_extensions import Annotated, get_args, get_origin

    def eval_forward_ref(t: ForwardRef, globalns, localns):
        return t._evaluate(globalns, localns)


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


def _get_namespaces(
    clazz: type,
    globalns: Optional[Dict[str, Any]] = None,
    localns: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    # region - Copied from typing.get_type_hints
    if globalns is None:
        base_globals = getattr(sys.modules.get(clazz.__module__, None), "__dict__", {})
    else:
        base_globals = globalns
    base_locals = dict(vars(clazz)) if localns is None else localns
    if localns is None and globalns is None:
        # This is surprising, but required.  Before Python 3.10,
        # get_type_hints only evaluated the globalns of
        # a class.  To maintain backwards compatibility, we reverse
        # the globalns and localns order so that eval() looks into
        # *base_globals* first rather than *base_locals*.
        # This only affects ForwardRefs.
        base_globals, base_locals = base_locals, base_globals
    # endregion - Copied from typing.get_type_hints

    return base_globals, base_locals


def _resolve_typevars(
    clazz: type,
    globalns: Optional[Dict[str, Any]] = None,
    localns: Optional[Dict[str, Any]] = None,
) -> Dict[type, Dict[TypeVar, _Future]]:
    """
    Attemps to resolves all TypeVars in the class bases. Allows us to resolve inherited and aliased generics.

    Returns a dict of each base class and the resolved generics.
    """
    # Use Tuples so can zip (order matters)
    args_by_class: Dict[type, Tuple[Tuple[TypeVar, _Future], ...]] = {}
    parent_class: Optional[type] = None
    # Loop in reversed order and iteratively resolve types
    for subclass in reversed(clazz.mro()):
        base_globals, base_locals = _get_namespaces(subclass, globalns, localns)
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
                        future.set_result(
                            eval_forward_ref(
                                potential_type,
                                globalns=base_globals,
                                localns=base_locals,
                            )
                            if isinstance(potential_type, ForwardRef)
                            else potential_type
                        )

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
                future.set_result(
                    eval_forward_ref(potential_type, globalns=globalns, localns=localns)
                    if isinstance(potential_type, ForwardRef)
                    else potential_type
                )

    # Convert to nested dict for easier lookup
    return {k: {typ: fut for typ, fut in args} for k, args in args_by_class.items()}


def _replace_typevars(
    clazz: type, resolved_generics: Optional[Dict[TypeVar, _Future]] = None
) -> type:
    if (
        not resolved_generics
        or inspect.isclass(clazz)
        or not may_contain_typevars(clazz)
    ):
        return clazz

    return clazz.copy_with(  # type: ignore
        tuple(
            (
                _replace_typevars(arg, resolved_generics)
                if may_contain_typevars(arg)
                else (
                    resolved_generics[arg].result() if arg in resolved_generics else arg
                )
            )
            for arg in get_args(clazz)
        )
    )


def get_resolved_dataclass_fields(
    clazz: type,
    globalns: Optional[Dict[str, Any]] = None,
    localns: Optional[Dict[str, Any]] = None,
) -> Tuple[dataclasses.Field, ...]:
    unbound_fields = set()
    # Need to manually resolve fields because `dataclasses.fields` doesn't handle generics and
    # looses the source class. Thus I don't know how to resolve this at later on.
    # Instead we recreate the type but with all known TypeVars resolved to their actual types.
    resolved_typevars = _resolve_typevars(clazz, globalns=globalns, localns=localns)
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
                if not inspect.isclass(field.type) and may_contain_typevars(field.type):
                    new_field = copy.copy(field)
                    new_field.type = _replace_typevars(
                        field.type, resolved_typevars.get(subclass)
                    )
                elif isinstance(field.type, TypeVar):
                    new_field = copy.copy(field)
                    new_field.type = resolved_typevars[subclass][field.type].result()
                elif isinstance(field.type, ForwardRef):
                    base_globals, base_locals = _get_namespaces(
                        subclass, globalns, localns
                    )
                    new_field = copy.copy(field)
                    new_field.type = eval_forward_ref(
                        field.type, globalns=base_globals, localns=base_locals
                    )
                elif isinstance(field.type, str):
                    base_globals, base_locals = _get_namespaces(
                        subclass, globalns, localns
                    )
                    new_field = copy.copy(field)
                    new_field.type = eval_forward_ref(
                        ForwardRef(field.type, is_argument=False, is_class=True)
                        if sys.version_info >= (3, 9)
                        else ForwardRef(field.type, is_argument=False),
                        globalns=base_globals,
                        localns=base_locals,
                    )

                fields[field.name] = (field, new_field)
            except (InvalidStateError, KeyError):
                unbound_fields.add(field.name)

    if unbound_fields:
        raise UnboundTypeVarError(
            f"{clazz.__name__} has unbound fields: {', '.join(unbound_fields)}"
        )

    return tuple(v[1] for v in fields.values())
