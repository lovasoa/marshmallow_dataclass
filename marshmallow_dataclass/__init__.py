"""
This library allows the conversion of python 3.7's :mod:`dataclasses`
to :mod:`marshmallow` schemas.

It takes a python class, and generates a marshmallow schema for it.

Simple example::

    from marshmallow import Schema
    from marshmallow_dataclass import dataclass

    @dataclass
    class Point:
      x:float
      y:float

    point = Point(x=0, y=0)
    point_json = Point.Schema().dumps(point)

Full example::

    from marshmallow import Schema
    from dataclasses import field
    from marshmallow_dataclass import dataclass
    import datetime

    @dataclass
    class User:
      birth: datetime.date = field(metadata= {
        "required": True # A parameter to pass to marshmallow's field
      })
      website:str = field(metadata = {
        "marshmallow_field": marshmallow.fields.Url() # Custom marshmallow field
      })
      Schema: ClassVar[Type[Schema]] = Schema # For the type checker
"""
import collections.abc
import dataclasses
import inspect
import sys
import types
import warnings
from enum import Enum
from functools import partial
from typing import (
    Any,
    Callable,
    ChainMap,
    Dict,
    Generic,
    Hashable,
    Iterable,
    Iterator,
    List,
    Mapping,
    NewType as typing_NewType,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_type_hints,
    overload,
    Sequence,
    FrozenSet,
)

import marshmallow
import typing_inspect

from marshmallow_dataclass.lazy_class_attribute import lazy_class_attribute

__all__ = ["dataclass", "add_schema", "class_schema", "field_for_schema", "NewType"]


if sys.version_info >= (3, 8):
    from typing import get_args
    from typing import get_origin
elif sys.version_info >= (3, 7):
    from typing_extensions import get_args
    from typing_extensions import get_origin
else:

    def get_args(tp):
        return typing_inspect.get_args(tp, evaluate=True)

    def get_origin(tp):
        TYPE_MAP = {
            List: list,
            Sequence: collections.abc.Sequence,
            Set: set,
            FrozenSet: frozenset,
            Tuple: tuple,
            Dict: dict,
            Mapping: collections.abc.Mapping,
            Generic: Generic,
        }

        origin = typing_inspect.get_origin(tp)
        if origin in TYPE_MAP:
            return TYPE_MAP[origin]
        elif origin is not tp:
            return origin
        return None


if sys.version_info >= (3, 7):
    from typing import OrderedDict

    TypeVar_ = TypeVar
else:
    from typing_extensions import OrderedDict

    TypeVar_ = type

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


NoneType = type(None)
_U = TypeVar("_U")
_V = TypeVar("_V")
_Field = TypeVar("_Field", bound=marshmallow.fields.Field)

# Whitelist of dataclass members that will be copied to generated schema.
MEMBERS_WHITELIST: Set[str] = {"Meta"}

# Max number of generated schemas that class_schema keeps of generated schemas. Removes duplicates.
MAX_CLASS_SCHEMA_CACHE_SIZE = 1024


class Error(TypeError):
    """Class passed ``class_schema`` can not be converted to a Marshmallow schema.

    FIXME: Currently this inherits from TypeError for backward compatibility with
    older versions of marshmallow_dataclass which always raised
    TypeError(f"{name} is not a dataclass and cannot be turned into one.")

    """


class InvalidClassError(ValueError, Error):
    """Argument to ``class_schema`` can not be converted to a Marshmallow schema.

    This exception is raised when, while generating a Marshmallow schema for a
    dataclass, a class is encountered for which a Marshmallow Schema can not
    be generated.

    """


class UnrecognizedFieldTypeError(Error):
    """An unrecognized field type spec was encountered.

    This exception is raised when, while generating a Marshmallow schema for a
    dataclass, a field is encountered for which a Marshmallow Field can not
    be generated.

    """


class UnboundTypeVarError(Error):
    """TypeVar instance can not be resolved to a type spec.

    This exception is raised when an unbound TypeVar is encountered.

    """


def _maybe_get_callers_frame(
    cls: type, stacklevel: int = 1
) -> Optional[types.FrameType]:
    """Return the caller's frame, but only if it will help resolve forward type references.

    We sometimes need the caller's frame to get access to the caller's
    local namespace in order to be able to resolve forward type
    references in dataclasses.

    Notes
    -----

    If the caller's locals are the same as the dataclass' module
    globals — this is the case for the common case of dataclasses
    defined at the module top-level — we don't need the locals.
    (Typing.get_type_hints() knows how to check the class module
    globals on its own.)

    In that case, we don't need the caller's frame.  Not holding a
    reference to the frame in our our lazy ``.Scheme`` class attribute
    is a significant win, memory-wise.

    """
    try:
        frame = inspect.currentframe()
        for _ in range(stacklevel + 1):
            if frame is None:
                return None
            frame = frame.f_back

        if frame is None:
            return None

        globalns = getattr(sys.modules.get(cls.__module__), "__dict__", None)
        if frame.f_locals is globalns:
            # Locals are the globals
            return None

        return frame

    finally:
        # Paranoia, per https://docs.python.org/3/library/inspect.html#the-interpreter-stack
        del frame


def _check_decorated_type(cls: object) -> None:
    if typing_inspect.is_generic_type(cls):
        # A .Schema attribute doesn't make sense on a generic type — there's
        # no way for it to know the generic parameters at run time.
        raise TypeError(
            "decorator does not support generic types "
            "(hint: use class_schema directly instead)"
        )
    if not isinstance(cls, type):
        raise TypeError(f"expected a class not {cls!r}")


@overload
def dataclass(
    _cls: Type[_U],
    *,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    cls_frame: Optional[types.FrameType] = None,
) -> Type[_U]:
    ...


@overload
def dataclass(
    *,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    cls_frame: Optional[types.FrameType] = None,
) -> Callable[[Type[_U]], Type[_U]]:
    ...


# _cls should never be specified by keyword, so start it with an
# underscore.  The presence of _cls is used to detect if this
# decorator is being called with parameters or not.
def dataclass(
    _cls: Optional[Type[_U]] = None,
    *,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    cls_frame: Optional[types.FrameType] = None,
    stacklevel: int = 1,
) -> Union[Type[_U], Callable[[Type[_U]], Type[_U]]]:
    """
    This decorator does the same as dataclasses.dataclass, but also applies :func:`add_schema`.
    It adds a `.Schema` attribute to the class object

    :param base_schema: marshmallow schema used as a base class when deriving dataclass schema
    :param cls_frame: frame of cls definition, used to obtain locals with other classes definitions.
        If None is passed the caller frame will be treated as cls_frame

    >>> @dataclass
    ... class Artist:
    ...    name: str
    >>> Artist.Schema
    <class 'marshmallow.schema.Artist'>

    >>> from typing import ClassVar
    >>> from marshmallow import Schema
    >>> @dataclass(order=True) # preserve field order
    ... class Point:
    ...   x:float
    ...   y:float
    ...   Schema: ClassVar[Type[Schema]] = Schema # For the type checker
    ...
    >>> Point.Schema().load({'x':0, 'y':0}) # This line can be statically type checked
    Point(x=0.0, y=0.0)
    """
    dc = dataclasses.dataclass(
        repr=repr, eq=eq, order=order, unsafe_hash=unsafe_hash, frozen=frozen
    )

    def decorator(cls: Type[_U], stacklevel: int = 1) -> Type[_U]:
        _check_decorated_type(cls)
        dc(cls)
        return add_schema(
            cls, base_schema, cls_frame=cls_frame, stacklevel=stacklevel + 1
        )

    if _cls is None:
        return decorator
    return decorator(_cls, stacklevel=stacklevel + 1)


class ClassDecorator(Protocol):
    def __call__(self, cls: Type[_U], stacklevel: int = 1) -> Type[_U]:
        ...


@overload
def add_schema(
    *,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    cls_frame: Optional[types.FrameType] = None,
    stacklevel: int = 1,
) -> ClassDecorator:
    ...


@overload
def add_schema(
    _cls: Type[_U],
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    cls_frame: Optional[types.FrameType] = None,
    stacklevel: int = 1,
) -> Type[_U]:
    ...


def add_schema(
    _cls: Optional[Type[_U]] = None,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    cls_frame: Optional[types.FrameType] = None,
    stacklevel: int = 1,
    attr_name: str = "Schema",
) -> Union[Type[_U], ClassDecorator]:
    """
    This decorator adds a marshmallow schema as the 'Schema' attribute in a dataclass.
    It uses :func:`class_schema` internally.

    :param type _cls: The dataclass to which a Schema should be added
    :param base_schema: marshmallow schema used as a base class when deriving dataclass schema
    :param cls_frame: frame of cls definition

    >>> class BaseSchema(marshmallow.Schema):
    ...   def on_bind_field(self, field_name, field_obj):
    ...     field_obj.data_key = (field_obj.data_key or field_name).upper()

    >>> @add_schema(base_schema=BaseSchema)
    ... @dataclasses.dataclass
    ... class Artist:
    ...    names: Tuple[str, str]
    >>> artist = Artist.Schema().loads('{"NAMES": ["Martin", "Ramirez"]}')
    >>> artist
    Artist(names=('Martin', 'Ramirez'))
    """

    def decorator(cls: Type[_V], stacklevel: int = stacklevel) -> Type[_V]:
        nonlocal cls_frame
        _check_decorated_type(cls)
        if cls_frame is None:
            cls_frame = _maybe_get_callers_frame(cls, stacklevel=stacklevel)
        fget = partial(class_schema, cls, base_schema, cls_frame)
        setattr(cls, attr_name, lazy_class_attribute(fget, attr_name))
        return cls

    if _cls is None:
        return decorator
    return decorator(_cls, stacklevel=stacklevel + 1)


@overload
def class_schema(
    clazz: type,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    *,
    globalns: Optional[Dict[str, Any]] = None,
    localns: Optional[Dict[str, Any]] = None,
) -> Type[marshmallow.Schema]:
    ...


@overload
def class_schema(
    clazz: type,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    clazz_frame: Optional[types.FrameType] = None,
    *,
    globalns: Optional[Dict[str, Any]] = None,
) -> Type[marshmallow.Schema]:
    ...


def class_schema(
    clazz: type,  # FIXME: type | _GenericAlias
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    # FIXME: delete clazz_frame from API?
    clazz_frame: Optional[types.FrameType] = None,
    *,
    globalns: Optional[Dict[str, Any]] = None,
    localns: Optional[Dict[str, Any]] = None,
) -> Type[marshmallow.Schema]:
    """
    Convert a class to a marshmallow schema

    :param clazz: A python class (may be a dataclass)
    :param base_schema: marshmallow schema used as a base class when deriving dataclass schema
    :param clazz_frame: frame of cls definition
    :return: A marshmallow Schema corresponding to the dataclass

    .. note::
        All the arguments supported by marshmallow field classes can
        be passed in the `metadata` dictionary of a field.


    If you want to use a custom marshmallow field
    (one that has no equivalent python type), you can pass it as the
    ``marshmallow_field`` key in the metadata dictionary.

    >>> import typing
    >>> Meters = typing.NewType('Meters', float)
    >>> @dataclasses.dataclass()
    ... class Building:
    ...   height: Optional[Meters]
    ...   name: str = dataclasses.field(default="anonymous")
    ...   class Meta:
    ...     ordered = True
    ...
    >>> class_schema(Building) # Returns a marshmallow schema class (not an instance)
    <class 'marshmallow.schema.Building'>
    >>> @dataclasses.dataclass()
    ... class City:
    ...   name: str = dataclasses.field(metadata={'required':True})
    ...   best_building: Building # Reference to another dataclass. A schema will be created for it too.
    ...   other_buildings: List[Building] = dataclasses.field(default_factory=lambda: [])
    ...
    >>> citySchema = class_schema(City)()
    >>> city = citySchema.load({"name":"Paris", "best_building": {"name": "Eiffel Tower"}})
    >>> city
    City(name='Paris', best_building=Building(height=None, name='Eiffel Tower'), other_buildings=[])

    >>> citySchema.load({"name":"Paris"})
    Traceback (most recent call last):
        ...
    marshmallow.exceptions.ValidationError: {'best_building': ['Missing data for required field.']}

    >>> city_json = citySchema.dump(city)
    >>> city_json['best_building'] # We get an OrderedDict because we specified order = True in the Meta class
    OrderedDict([('height', None), ('name', 'Eiffel Tower')])

    >>> @dataclasses.dataclass()
    ... class Person:
    ...   name: str = dataclasses.field(default="Anonymous")
    ...   friends: List['Person'] = dataclasses.field(default_factory=lambda:[]) # Recursive field
    ...
    >>> person = class_schema(Person)().load({
    ...     "friends": [{"name": "Roger Boucher"}]
    ... })
    >>> person
    Person(name='Anonymous', friends=[Person(name='Roger Boucher', friends=[])])

    >>> @dataclasses.dataclass()
    ... class C:
    ...   important: int = dataclasses.field(init=True, default=0)
    ...    # Only fields that are in the __init__ method will be added:
    ...   unimportant: int = dataclasses.field(init=False, default=0)
    ...
    >>> c = class_schema(C)().load({
    ...     "important": 9, # This field will be imported
    ...     "unimportant": 9 # This field will NOT be imported
    ... }, unknown=marshmallow.EXCLUDE)
    >>> c
    C(important=9, unimportant=0)

    >>> @dataclasses.dataclass
    ... class Website:
    ...  url:str = dataclasses.field(metadata = {
    ...    "marshmallow_field": marshmallow.fields.Url() # Custom marshmallow field
    ...  })
    ...
    >>> class_schema(Website)().load({"url": "I am not a good URL !"})
    Traceback (most recent call last):
        ...
    marshmallow.exceptions.ValidationError: {'url': ['Not a valid URL.']}

    >>> @dataclasses.dataclass
    ... class NeverValid:
    ...     @marshmallow.validates_schema
    ...     def validate(self, data, **_):
    ...         raise marshmallow.ValidationError('never valid')
    ...
    >>> class_schema(NeverValid)().load({})
    Traceback (most recent call last):
        ...
    marshmallow.exceptions.ValidationError: {'_schema': ['never valid']}

    >>> @dataclasses.dataclass
    ... class Anything:
    ...     name: str
    ...     @marshmallow.validates('name')
    ...     def validates(self, value):
    ...         if len(value) > 5: raise marshmallow.ValidationError("Name too long")
    >>> class_schema(Anything)().load({"name": "aaaaaargh"})
    Traceback (most recent call last):
    ...
    marshmallow.exceptions.ValidationError: {'name': ['Name too long']}

    You can use the ``metadata`` argument to override default field behaviour, e.g. the fact that
    ``Optional`` fields allow ``None`` values:

    >>> @dataclasses.dataclass
    ... class Custom:
    ...     name: Optional[str] = dataclasses.field(metadata={"allow_none": False})
    >>> class_schema(Custom)().load({"name": None})
    Traceback (most recent call last):
        ...
    marshmallow.exceptions.ValidationError: {'name': ['Field may not be null.']}
    >>> class_schema(Custom)().load({})
    Custom(name=None)
    """
    if localns is None:
        if clazz_frame is None:
            clazz_frame = _maybe_get_callers_frame(clazz)
        if clazz_frame is not None:
            localns = clazz_frame.f_locals

    if base_schema is None:
        base_schema = marshmallow.Schema

    schema_ctx = _SchemaContext(globalns, localns, base_schema)
    schema = schema_ctx.class_schema(clazz)
    assert not isinstance(schema, _Future)
    return schema


class _LRUDict(OrderedDict[_U, _V]):
    """Limited-length dict which discards LRU entries."""

    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        super().__init__()

    def __setitem__(self, key: _U, value: _V) -> None:
        super().__setitem__(key, value)
        super().move_to_end(key)

        while len(self) > self.maxsize:
            oldkey = next(iter(self))
            super().__delitem__(oldkey)

    def __getitem__(self, key: _U) -> _V:
        val = super().__getitem__(key)
        super().move_to_end(key)
        return val

    _T = TypeVar("_T")

    @overload
    def get(self, key: _U) -> Optional[_V]:
        ...

    @overload
    def get(self, key: _U, default: _T) -> Union[_V, _T]:
        ...

    def get(self, key: _U, default: Any = None) -> Any:
        try:
            return self.__getitem__(key)
        except KeyError:
            return default


_schema_cache = _LRUDict[Hashable, Type[marshmallow.Schema]](
    MAX_CLASS_SCHEMA_CACHE_SIZE
)


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


TypeSpec = typing_NewType("TypeSpec", object)
GenericAliasOfDataclass = typing_NewType("GenericAliasOfDataclass", object)


def _is_generic_alias_of_dataclass(
    cls: object,
) -> TypeGuard[GenericAliasOfDataclass]:
    """
    Check if given class is a generic alias of a dataclass, if the dataclass is
    defined as `class A(Generic[T])`, this method will return true if `A[int]` is passed
    """
    return dataclasses.is_dataclass(get_origin(cls))


def _has_generic_base(cls: type) -> bool:
    """Return True if cls has any generic base classes."""
    return any(typing_inspect.get_parameters(base) for base in cls.__mro__[1:])


class _GenericArgs(Mapping[TypeVar_, TypeSpec], collections.abc.Hashable):
    """A mapping of TypeVars to type specs"""

    def __init__(
        self,
        generic_alias: GenericAliasOfDataclass,
        binding: Optional["_GenericArgs"] = None,
    ):
        origin = typing_inspect.get_origin(generic_alias)
        parameters: Iterable[TypeVar_] = typing_inspect.get_parameters(origin)
        arguments: Iterable[TypeSpec] = get_args(generic_alias)
        if binding is not None:
            arguments = map(binding.resolve, arguments)

        self._args = dict(zip(parameters, arguments))
        self._hashvalue = hash(tuple(self._args.items()))

    _args: Mapping[TypeVar_, TypeSpec]
    _hashvalue: int

    def resolve(self, spec: Union[TypeVar_, TypeSpec]) -> TypeSpec:
        if isinstance(spec, TypeVar):
            try:
                return self._args[spec]
            except KeyError as exc:
                raise UnboundTypeVarError(
                    f"generic type variable {spec.__name__} is not bound"
                ) from exc
        return spec

    def __getitem__(self, param: TypeVar_) -> TypeSpec:
        return self._args[param]

    def __iter__(self) -> Iterator[TypeVar_]:
        return iter(self._args.keys())

    def __len__(self) -> int:
        return len(self._args)

    def __hash__(self) -> int:
        return self._hashvalue


@dataclasses.dataclass
class _SchemaContext:
    """Global context for an invocation of class_schema."""

    globalns: Optional[Dict[str, Any]] = None
    localns: Optional[Dict[str, Any]] = None
    base_schema: Type[marshmallow.Schema] = marshmallow.Schema
    generic_args: Optional[_GenericArgs] = None
    seen_classes: Dict[type, _Future[Type[marshmallow.Schema]]] = dataclasses.field(
        default_factory=dict
    )

    def replace(self, generic_args: Optional[_GenericArgs]) -> "_SchemaContext":
        return dataclasses.replace(self, generic_args=generic_args)

    def get_type_mapping(
        self, use_mro: bool = False
    ) -> Mapping[Any, Type[marshmallow.fields.Field]]:
        """Get base_schema.TYPE_MAPPING.

        If use_mro is true, then merges the TYPE_MAPPINGs from
        all bases in base_schema's MRO.
        """
        base_schema = self.base_schema
        if use_mro:
            return ChainMap(
                *(getattr(cls, "TYPE_MAPPING", {}) for cls in base_schema.__mro__)
            )
        return getattr(base_schema, "TYPE_MAPPING", {})

    def class_schema(
        self, clazz: type
    ) -> Union[Type[marshmallow.Schema], _Future[Type[marshmallow.Schema]]]:
        if clazz in self.seen_classes:
            return self.seen_classes[clazz]

        cache_key = clazz, self.base_schema
        try:
            return _schema_cache[cache_key]
        except KeyError:
            pass

        future: _Future[Type[marshmallow.Schema]] = _Future()
        self.seen_classes[clazz] = future

        constructor: Callable[..., object]

        if self.is_simple_annotated_class(clazz):
            class_name = clazz.__name__
            constructor = _simple_class_constructor(clazz)
            attributes = self.schema_attrs_for_simple_class(clazz)
        elif _is_generic_alias_of_dataclass(clazz):
            origin = get_origin(clazz)
            assert isinstance(origin, type)
            class_name = origin.__name__
            constructor = origin
            ctx = self.replace(generic_args=_GenericArgs(clazz, self.generic_args))
            attributes = ctx.schema_attrs_for_dataclass(origin)
        elif dataclasses.is_dataclass(clazz):
            class_name = clazz.__name__
            constructor = clazz
            attributes = self.schema_attrs_for_dataclass(clazz)
        else:
            raise InvalidClassError(
                f"{clazz} is not a dataclass or a simple annotated class"
            )

        load_to_dict = self.base_schema.load

        def load(
            self: marshmallow.Schema,
            data: Union[Mapping[str, Any], Iterable[Mapping[str, Any]]],
            *,
            many: Optional[bool] = None,
            unknown: Optional[str] = None,
            **kwargs: Any,
        ) -> Any:
            many = self.many if many is None else bool(many)
            loaded = load_to_dict(self, data, many=many, unknown=unknown, **kwargs)
            if many:
                return [constructor(**item) for item in loaded]
            else:
                return constructor(**loaded)

        attributes["load"] = load

        schema_class: Type[marshmallow.Schema] = type(
            f"{class_name}Schema", (self.base_schema,), attributes
        )

        future.set_result(schema_class)
        _schema_cache[cache_key] = schema_class
        return schema_class

    def schema_attrs_for_dataclass(self, clazz: type) -> Dict[str, Any]:
        if _has_generic_base(clazz):
            raise InvalidClassError(
                "class_schema does not support dataclasses with generic base classes"
            )

        type_hints = get_type_hints(clazz, globalns=self.globalns, localns=self.localns)
        attrs = dict(_marshmallow_hooks(clazz))
        for field in dataclasses.fields(clazz):
            if field.init:
                typ = type_hints[field.name]
                default = (
                    field.default_factory
                    if field.default_factory is not dataclasses.MISSING
                    else field.default
                    if field.default is not dataclasses.MISSING
                    else marshmallow.missing
                )
                attrs[field.name] = self.field_for_schema(typ, default, field.metadata)
        return attrs

    def is_simple_annotated_class(self, obj: object) -> bool:
        """Determine whether obj is a "simple annotated class".

        The ```class_schema``` function can generate schemas for
        simple annotated classes (as well as for dataclasses).
        """
        if not isinstance(obj, type):
            return False
        if getattr(obj, "__init__", None) is not object.__init__:
            return False
        if getattr(obj, "__new__", None) is not object.__new__:
            return False

        type_hints = get_type_hints(obj, globalns=self.globalns, localns=self.localns)
        return any(not typing_inspect.is_classvar(th) for th in type_hints.values())

    def schema_attrs_for_simple_class(self, clazz: type) -> Dict[str, Any]:
        type_hints = get_type_hints(clazz, globalns=self.globalns, localns=self.localns)

        attrs = dict(_marshmallow_hooks(clazz))
        for field_name, typ in type_hints.items():
            if not typing_inspect.is_classvar(typ):
                default = getattr(clazz, field_name, marshmallow.missing)
                attrs[field_name] = self.field_for_schema(typ, default)
        return attrs

    def field_for_schema(
        self,
        typ: Union[type, object],
        default: Any = marshmallow.missing,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> marshmallow.fields.Field:
        """
        Get a marshmallow Field corresponding to the given python type.
        The metadata of the dataclass field is used as arguments to the marshmallow Field.

        This is an internal version of field_for_schema.

        :param typ: The type for which a field should be generated
        :param default: value to use for (de)serialization when the field is missing
        :param metadata: Additional parameters to pass to the marshmallow field constructor

        """

        metadata = {} if metadata is None else dict(metadata)

        # If the field was already defined by the user
        predefined_field = metadata.get("marshmallow_field")
        if predefined_field:
            if not isinstance(predefined_field, marshmallow.fields.Field):
                raise TypeError(
                    "metadata['marshmallow_field'] must be set to a Field instance, "
                    f"not {predefined_field}"
                )
            return predefined_field

        if default is not marshmallow.missing:
            metadata.setdefault("dump_default", default)
            # 'missing' must not be set for required fields.
            if not metadata.get("required"):
                metadata.setdefault("load_default", default)
        else:
            metadata.setdefault("required", not typing_inspect.is_optional_type(typ))

        if self.generic_args is not None and isinstance(typ, TypeVar):
            typ = self.generic_args.resolve(typ)

        if _is_builtin_collection_type(typ):
            return self.field_for_builtin_collection_type(typ, metadata)

        # Base types
        type_mapping = self.get_type_mapping(use_mro=True)
        field = type_mapping.get(typ)
        if field is not None:
            return field(**metadata)

        if typ is Any:
            metadata.setdefault("allow_none", True)
            return marshmallow.fields.Raw(**metadata)

        if typing_inspect.is_literal_type(typ):
            return self.field_for_literal_type(typ, metadata)

        if typing_inspect.is_final_type(typ):
            return self.field_for_schema(
                _get_subtype_for_final_type(typ, default),
                default=default,
                metadata=metadata,
            )

        if typing_inspect.is_union_type(typ):
            return self.field_for_union_type(typ, metadata)

        if typing_inspect.is_new_type(typ):
            return self.field_for_new_type(typ, default, metadata)

        # enumerations
        if isinstance(typ, type) and issubclass(typ, Enum):
            return self.field_for_enum(typ, metadata)

        # nested dataclasses
        if (
            dataclasses.is_dataclass(typ)
            or _is_generic_alias_of_dataclass(typ)
            or self.is_simple_annotated_class(typ)
        ):
            nested = self.schema_for_nested(typ)
            # type spec for Nested.__init__ is not correct
            return marshmallow.fields.Nested(nested, **metadata)  # type: ignore[arg-type]

        raise UnrecognizedFieldTypeError(f"can not deduce field type for {typ}")

    def field_for_builtin_collection_type(
        self, typ: object, metadata: Dict[str, Any]
    ) -> marshmallow.fields.Field:
        """
        Handle builtin container types like list, tuple, set, etc.
        """
        origin = get_origin(typ)
        if origin is None:
            origin = typ
            assert len(get_args(typ)) == 0

        args = get_args(typ)

        if origin is tuple and (
            len(args) == 0 or (len(args) == 2 and args[1] is Ellipsis)
        ):
            # Special case: homogeneous tuple — treat as Sequence
            origin = collections.abc.Sequence
            args = args[:1]

        # Override base_schema.TYPE_MAPPING to change the class used for generic types below
        def get_field_type(type_spec: Any, default: Type[_Field]) -> Type[_Field]:
            type_mapping = self.get_type_mapping(use_mro=False)
            return type_mapping.get(type_spec, default)  # type: ignore[return-value]

        def get_field(i: int) -> marshmallow.fields.Field:
            return self.field_for_schema(args[i] if args else Any)

        if origin is tuple:
            tuple_type = get_field_type(Tuple, default=marshmallow.fields.Tuple)
            return tuple_type(tuple(map(self.field_for_schema, args)), **metadata)

        if origin in (dict, collections.abc.Mapping):
            dict_type = get_field_type(Dict, default=marshmallow.fields.Dict)
            return dict_type(keys=get_field(0), values=get_field(1), **metadata)

        if origin is list:
            list_type = get_field_type(List, default=marshmallow.fields.List)
            return list_type(get_field(0), **metadata)

        if origin is collections.abc.Sequence:
            from . import collection_field

            return collection_field.Sequence(get_field(0), **metadata)

        if origin in (set, frozenset):
            from . import collection_field

            frozen = origin is frozenset
            return collection_field.Set(get_field(0), frozen=frozen, **metadata)

        raise ValueError(f"{typ} is not a builtin collection type")

    def field_for_union_type(
        self, typ: object, metadata: Dict[str, Any]
    ) -> marshmallow.fields.Field:
        """
        Construct the appropriate Field for a union or optional type.
        """
        assert typing_inspect.is_union_type(typ)
        subtypes = [t for t in get_args(typ) if t is not NoneType]

        if typing_inspect.is_optional_type(typ):
            metadata = {
                "allow_none": True,
                "dump_default": None,
                **metadata,
            }
            if not metadata.setdefault("required", False):
                metadata.setdefault("load_default", None)

        if len(subtypes) == 1:
            return self.field_for_schema(subtypes[0], metadata=metadata)

        from . import union_field

        return union_field.Union(
            [
                (typ, self.field_for_schema(typ, metadata={"required": True}))
                for typ in subtypes
            ],
            **metadata,
        )

    @staticmethod
    def field_for_literal_type(
        typ: object, metadata: Dict[str, Any]
    ) -> marshmallow.fields.Field:
        """
        Construct the appropriate Field for a Literal type.
        """
        validate: marshmallow.validate.Validator

        assert typing_inspect.is_literal_type(typ)
        arguments = typing_inspect.get_args(typ)
        if len(arguments) == 1:
            validate = marshmallow.validate.Equal(arguments[0])
        else:
            validate = marshmallow.validate.OneOf(arguments)
        return marshmallow.fields.Raw(validate=validate, **metadata)

    def field_for_new_type(
        self, typ: object, default: Any, metadata: Dict[str, Any]
    ) -> marshmallow.fields.Field:
        """
        Return a new field for fields based on a NewType.
        """
        # Add the information coming our custom NewType implementation
        typ_args = getattr(typ, "_marshmallow_args", {})

        # Handle multiple validators from both `typ` and `metadata`.
        # See https://github.com/lovasoa/marshmallow_dataclass/issues/91
        validators: List[Callable[[Any], Any]] = []
        for args in (typ_args, metadata):
            validate = args.get("validate")
            if marshmallow.utils.is_iterable_but_not_string(validate):
                validators.extend(validate)  # type: ignore[arg-type]
            elif validate is not None:
                validators.append(validate)

        metadata = {
            **typ_args,
            **metadata,
            "validate": validators if validators else None,
        }
        type_name = getattr(typ, "__name__", repr(typ))
        metadata.setdefault("metadata", {}).setdefault("description", type_name)

        field: Optional[Type[marshmallow.fields.Field]] = getattr(
            typ, "_marshmallow_field", None
        )
        if field is not None:
            return field(**metadata)
        return self.field_for_schema(
            typ.__supertype__,  # type: ignore[attr-defined]
            default=default,
            metadata=metadata,
        )

    @staticmethod
    def field_for_enum(typ: type, metadata: Dict[str, Any]) -> marshmallow.fields.Field:
        """
        Return a new field for an Enum field.
        """
        if sys.version_info >= (3, 7):
            return marshmallow.fields.Enum(typ, **metadata)
        else:
            # Remove this once support for python 3.6 is dropped.
            import marshmallow_enum

            return marshmallow_enum.EnumField(typ, **metadata)

    def schema_for_nested(
        self, typ: object
    ) -> Union[Type[marshmallow.Schema], Callable[[], Type[marshmallow.Schema]]]:
        """
        Return a marshmallow.Schema for a nested dataclass (or simple annotated class)
        """
        if isinstance(typ, type) and hasattr(typ, "Schema"):
            # marshmallow_dataclass.dataclass
            # Defer evaluation of .Schema attribute, to avoid forward reference issues
            return partial(getattr, typ, "Schema")

        class_schema = self.class_schema(typ)  # type: ignore[arg-type] # FIXME
        if isinstance(class_schema, _Future):
            return class_schema.result
        return class_schema


def _marshmallow_hooks(clazz: type) -> Iterator[Tuple[str, Any]]:
    for name, attr in inspect.getmembers(clazz):
        if hasattr(attr, "__marshmallow_hook__") or name in MEMBERS_WHITELIST:
            yield name, attr


def _simple_class_constructor(clazz: Type[_U]) -> Callable[..., _U]:
    def constructor(**kwargs: Any) -> _U:
        obj = clazz.__new__(clazz)
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    return constructor


def _is_builtin_collection_type(typ: object) -> bool:
    origin = get_origin(typ)
    if origin is None:
        origin = typ

    return origin in {
        list,
        collections.abc.Sequence,
        set,
        frozenset,
        tuple,
        dict,
        collections.abc.Mapping,
    }


def _get_subtype_for_final_type(typ: object, default: Any) -> object:
    """
    Construct the appropriate Field for a Final type.
    """
    assert typing_inspect.is_final_type(typ)
    arguments = typing_inspect.get_args(typ)
    if arguments:
        return arguments[0]
    elif default is marshmallow.missing:
        return Any
    elif callable(default):
        warnings.warn(
            "****** WARNING ****** "
            "marshmallow_dataclass was called on a dataclass with an "
            'attribute that is type-annotated with "Final" and uses '
            "dataclasses.field for specifying a default value using a "
            "factory. The Marshmallow field type cannot be inferred from the "
            "factory and will fall back to a raw field which is equivalent to "
            'the type annotation "Any" and will result in no validation. '
            "Provide a type to Final[...] to ensure accurate validation. "
            "****** WARNING ******"
        )
        return Any
    warnings.warn(
        "****** WARNING ****** "
        "marshmallow_dataclass was called on a dataclass with an "
        'attribute that is type-annotated with "Final" with a default '
        "value from which the Marshmallow field type is inferred. "
        "Support for type inference from a default value is limited and "
        "may result in inaccurate validation. Provide a type to "
        "Final[...] to ensure accurate validation. "
        "****** WARNING ******"
    )
    return type(default)


def field_for_schema(
    typ: type,
    default: Any = marshmallow.missing,
    metadata: Optional[Mapping[str, Any]] = None,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
    # FIXME: delete typ_frame from API?
    typ_frame: Optional[types.FrameType] = None,
) -> marshmallow.fields.Field:
    """
    Get a marshmallow Field corresponding to the given python type.
    The metadata of the dataclass field is used as arguments to the marshmallow Field.

    :param typ: The type for which a field should be generated
    :param default: value to use for (de)serialization when the field is missing
    :param metadata: Additional parameters to pass to the marshmallow field constructor
    :param base_schema: marshmallow schema used as a base class when deriving dataclass schema
    :param typ_frame: frame of type definition

    >>> int_field = field_for_schema(int, default=9, metadata=dict(required=True))
    >>> int_field.__class__
    <class 'marshmallow.fields.Integer'>

    >>> int_field.dump_default
    9

    >>> field_for_schema(str, metadata={"marshmallow_field": marshmallow.fields.Url()}).__class__
    <class 'marshmallow.fields.Url'>
    """
    if base_schema is None:
        base_schema = marshmallow.Schema
    localns = typ_frame.f_locals if typ_frame is not None else None
    schema_ctx = _SchemaContext(localns=localns, base_schema=base_schema)
    return schema_ctx.field_for_schema(typ, default, metadata)


def NewType(
    name: str,
    typ: Type[_U],
    field: Optional[Type[marshmallow.fields.Field]] = None,
    **kwargs: Any,
) -> type:
    """NewType creates simple unique types
    to which you can attach custom marshmallow attributes.
    All the keyword arguments passed to this function will be transmitted
    to the marshmallow field constructor.

    >>> import marshmallow.validate
    >>> IPv4 = NewType('IPv4', str, validate=marshmallow.validate.Regexp(r'^([0-9]{1,3}\\.){3}[0-9]{1,3}$'))
    >>> @dataclass
    ... class MyIps:
    ...   ips: List[IPv4]
    >>> MyIps.Schema().load({"ips": ["0.0.0.0", "grumble grumble"]})
    Traceback (most recent call last):
    ...
    marshmallow.exceptions.ValidationError: {'ips': {1: ['String does not match expected pattern.']}}
    >>> MyIps.Schema().load({"ips": ["127.0.0.1"]})
    MyIps(ips=['127.0.0.1'])

    >>> Email = NewType('Email', str, field=marshmallow.fields.Email)
    >>> @dataclass
    ... class ContactInfo:
    ...   mail: Email = dataclasses.field(default="anonymous@example.org")
    >>> ContactInfo.Schema().load({})
    ContactInfo(mail='anonymous@example.org')
    >>> ContactInfo.Schema().load({"mail": "grumble grumble"})
    Traceback (most recent call last):
    ...
    marshmallow.exceptions.ValidationError: {'mail': ['Not a valid email address.']}
    """

    # noinspection PyTypeHints
    new_type = typing_NewType(name, typ)  # type: ignore
    # noinspection PyTypeHints
    new_type._marshmallow_field = field
    # noinspection PyTypeHints
    new_type._marshmallow_args = kwargs
    return new_type


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
