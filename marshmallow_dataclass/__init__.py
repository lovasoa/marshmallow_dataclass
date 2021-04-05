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
import warnings
from enum import EnumMeta
from functools import lru_cache
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
    Sequence,
    FrozenSet,
)

import marshmallow
import typing_inspect

__all__ = ["dataclass", "add_schema", "class_schema", "field_for_schema", "NewType"]

NoneType = type(None)
_U = TypeVar("_U")

# Whitelist of dataclass members that will be copied to generated schema.
MEMBERS_WHITELIST: Set[str] = {"Meta"}

# Max number of generated schemas that class_schema keeps of generated schemas. Removes duplicates.
MAX_CLASS_SCHEMA_CACHE_SIZE = 1024


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
) -> Callable[[Type[_U]], Type[_U]]:
    ...


# _cls should never be specified by keyword, so start it with an
# underscore.  The presence of _cls is used to detect if this
# decorator is being called with parameters or not.
def dataclass(
    _cls: Type[_U] = None,
    *,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
) -> Union[Type[_U], Callable[[Type[_U]], Type[_U]]]:
    """
    This decorator does the same as dataclasses.dataclass, but also applies :func:`add_schema`.
    It adds a `.Schema` attribute to the class object

    :param base_schema: marshmallow schema used as a base class when deriving dataclass schema

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
    # dataclass's typing doesn't expect it to be called as a function, so ignore type check
    dc = dataclasses.dataclass(  # type: ignore
        _cls, repr=repr, eq=eq, order=order, unsafe_hash=unsafe_hash, frozen=frozen
    )
    if _cls is None:
        return lambda cls: add_schema(dc(cls), base_schema)
    return add_schema(dc, base_schema)


@overload
def add_schema(_cls: Type[_U]) -> Type[_U]:
    ...


@overload
def add_schema(
    base_schema: Type[marshmallow.Schema] = None,
) -> Callable[[Type[_U]], Type[_U]]:
    ...


@overload
def add_schema(
    _cls: Type[_U], base_schema: Type[marshmallow.Schema] = None
) -> Type[_U]:
    ...


def add_schema(_cls=None, base_schema=None):
    """
    This decorator adds a marshmallow schema as the 'Schema' attribute in a dataclass.
    It uses :func:`class_schema` internally.

    :param type _cls: The dataclass to which a Schema should be added
    :param base_schema: marshmallow schema used as a base class when deriving dataclass schema

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

    def decorator(clazz: Type[_U]) -> Type[_U]:
        # noinspection PyTypeHints
        clazz.Schema = class_schema(clazz, base_schema)  # type: ignore
        return clazz

    return decorator(_cls) if _cls else decorator


def class_schema(
    clazz: type, base_schema: Optional[Type[marshmallow.Schema]] = None
) -> Type[marshmallow.Schema]:
    """
    Convert a class to a marshmallow schema

    :param clazz: A python class (may be a dataclass)
    :param base_schema: marshmallow schema used as a base class when deriving dataclass schema
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
    if not dataclasses.is_dataclass(clazz):
        clazz = dataclasses.dataclass(clazz)
    return _internal_class_schema(clazz, base_schema)


@lru_cache(maxsize=MAX_CLASS_SCHEMA_CACHE_SIZE)
def _internal_class_schema(
    clazz: type, base_schema: Optional[Type[marshmallow.Schema]] = None
) -> Type[marshmallow.Schema]:
    try:
        # noinspection PyDataclass
        fields: Tuple[dataclasses.Field, ...] = dataclasses.fields(clazz)
    except TypeError:  # Not a dataclass
        try:
            warnings.warn(
                "****** WARNING ****** "
                f"marshmallow_dataclass was called on the class {clazz}, which is not a dataclass. "
                "It is going to try and convert the class into a dataclass, which may have "
                "undesirable side effects. To avoid this message, make sure all your classes and "
                "all the classes of their fields are either explicitly supported by "
                "marshmallow_dataclass, or define the schema explicitly using "
                "field(metadata=dict(marshmallow_field=...)). For more information, see "
                "https://github.com/lovasoa/marshmallow_dataclass/issues/51 "
                "****** WARNING ******"
            )
            created_dataclass: type = dataclasses.dataclass(clazz)
            return _internal_class_schema(created_dataclass, base_schema)
        except Exception:
            raise TypeError(
                f"{getattr(clazz, '__name__', repr(clazz))} is not a dataclass and cannot be turned into one."
            )

    # Copy all marshmallow hooks and whitelisted members of the dataclass to the schema.
    attributes = {
        k: v
        for k, v in inspect.getmembers(clazz)
        if hasattr(v, "__marshmallow_hook__") or k in MEMBERS_WHITELIST
    }
    # Update the schema members to contain marshmallow fields instead of dataclass fields
    attributes.update(
        (
            field.name,
            field_for_schema(
                field.type, _get_field_default(field), field.metadata, base_schema
            ),
        )
        for field in fields
        if field.init
    )

    schema_class = type(clazz.__name__, (_base_schema(clazz, base_schema),), attributes)
    return cast(Type[marshmallow.Schema], schema_class)


def _field_by_type(
    typ: Union[type, Any], base_schema: Optional[Type[marshmallow.Schema]]
) -> Optional[Type[marshmallow.fields.Field]]:
    return (
        base_schema and base_schema.TYPE_MAPPING.get(typ)
    ) or marshmallow.Schema.TYPE_MAPPING.get(typ)


def _field_by_supertype(
    typ: Type,
    default: Any,
    newtype_supertype: Type,
    metadata: dict,
    base_schema: Optional[Type[marshmallow.Schema]],
) -> marshmallow.fields.Field:
    """
    Return a new field for fields based on a super field. (Usually spawned from NewType)
    """
    # Add the information coming our custom NewType implementation

    typ_args = getattr(typ, "_marshmallow_args", {})

    # Handle multiple validators from both `typ` and `metadata`.
    # See https://github.com/lovasoa/marshmallow_dataclass/issues/91
    new_validators: List[Callable] = []
    for meta_dict in (typ_args, metadata):
        if "validate" in meta_dict:
            if marshmallow.utils.is_iterable_but_not_string(meta_dict["validate"]):
                new_validators.extend(meta_dict["validate"])
            elif callable(meta_dict["validate"]):
                new_validators.append(meta_dict["validate"])
    metadata["validate"] = new_validators if new_validators else None

    metadata = {**typ_args, **metadata}
    metadata.setdefault("metadata", {}).setdefault("description", typ.__name__)
    field = getattr(typ, "_marshmallow_field", None)
    if field:
        return field(**metadata)
    else:
        return field_for_schema(
            newtype_supertype,
            metadata=metadata,
            default=default,
            base_schema=base_schema,
        )


def _generic_type_add_any(typ: type) -> type:
    """if typ is generic type without arguments, replace them by Any."""
    if typ is list:
        typ = List[Any]
    elif typ is dict:
        typ = Dict[Any, Any]
    elif typ is Mapping:
        typ = Mapping[Any, Any]
    elif typ is Sequence:
        typ = Sequence[Any]
    elif typ is Set:
        typ = Set[Any]
    elif typ is FrozenSet:
        typ = FrozenSet[Any]
    return typ


def _field_for_generic_type(
    typ: type, base_schema: Optional[Type[marshmallow.Schema]], **metadata: Any
) -> Optional[marshmallow.fields.Field]:
    """
    If the type is a generic interface, resolve the arguments and construct the appropriate Field.
    """
    origin = typing_inspect.get_origin(typ)
    if origin:
        arguments = typing_inspect.get_args(typ, True)
        # Override base_schema.TYPE_MAPPING to change the class used for generic types below
        type_mapping = base_schema.TYPE_MAPPING if base_schema else {}

        if origin in (list, List):
            child_type = field_for_schema(arguments[0], base_schema=base_schema)
            list_type = cast(
                Type[marshmallow.fields.List],
                type_mapping.get(List, marshmallow.fields.List),
            )
            return list_type(child_type, **metadata)
        if origin == collections.abc.Sequence:
            from . import collection_field

            child_type = field_for_schema(arguments[0], base_schema=base_schema)
            return collection_field.Sequence(cls_or_instance=child_type, **metadata)
        if origin in (set, Set):
            from . import collection_field

            child_type = field_for_schema(arguments[0], base_schema=base_schema)
            return collection_field.Set(
                cls_or_instance=child_type, frozen=False, **metadata
            )
        if origin in (frozenset, FrozenSet):
            from . import collection_field

            child_type = field_for_schema(arguments[0], base_schema=base_schema)
            return collection_field.Set(
                cls_or_instance=child_type, frozen=True, **metadata
            )
        if origin in (tuple, Tuple):
            children = tuple(
                field_for_schema(arg, base_schema=base_schema) for arg in arguments
            )
            tuple_type = cast(
                Type[marshmallow.fields.Tuple],
                type_mapping.get(  # type:ignore[call-overload]
                    Tuple, marshmallow.fields.Tuple
                ),
            )
            return tuple_type(children, **metadata)
        elif origin in (dict, Dict, collections.abc.Mapping):
            dict_type = type_mapping.get(Dict, marshmallow.fields.Dict)
            return dict_type(
                keys=field_for_schema(arguments[0], base_schema=base_schema),
                values=field_for_schema(arguments[1], base_schema=base_schema),
                **metadata,
            )
        elif typing_inspect.is_union_type(typ):
            if typing_inspect.is_optional_type(typ):
                metadata["allow_none"] = metadata.get("allow_none", True)
                metadata["default"] = metadata.get("default", None)
                metadata["missing"] = metadata.get("missing", None)
                metadata["required"] = False
            subtypes = [t for t in arguments if t is not NoneType]  # type: ignore
            if len(subtypes) == 1:
                return field_for_schema(
                    subtypes[0], metadata=metadata, base_schema=base_schema
                )
            from . import union_field

            return union_field.Union(
                [
                    (
                        subtyp,
                        field_for_schema(
                            subtyp, metadata=metadata, base_schema=base_schema
                        ),
                    )
                    for subtyp in subtypes
                ],
                **metadata,
            )
    return None


def field_for_schema(
    typ: type,
    default=marshmallow.missing,
    metadata: Mapping[str, Any] = None,
    base_schema: Optional[Type[marshmallow.Schema]] = None,
) -> marshmallow.fields.Field:
    """
    Get a marshmallow Field corresponding to the given python type.
    The metadata of the dataclass field is used as arguments to the marshmallow Field.

    :param typ: The type for which a field should be generated
    :param default: value to use for (de)serialization when the field is missing
    :param metadata: Additional parameters to pass to the marshmallow field constructor
    :param base_schema: marshmallow schema used as a base class when deriving dataclass schema

    >>> int_field = field_for_schema(int, default=9, metadata=dict(required=True))
    >>> int_field.__class__
    <class 'marshmallow.fields.Integer'>

    >>> int_field.default
    9

    >>> field_for_schema(str, metadata={"marshmallow_field": marshmallow.fields.Url()}).__class__
    <class 'marshmallow.fields.Url'>
    """

    metadata = {} if metadata is None else dict(metadata)

    if default is not marshmallow.missing:
        metadata.setdefault("default", default)
        # 'missing' must not be set for required fields.
        if not metadata.get("required"):
            metadata.setdefault("missing", default)
    else:
        metadata.setdefault("required", True)

    # If the field was already defined by the user
    predefined_field = metadata.get("marshmallow_field")
    if predefined_field:
        return predefined_field

    # Generic types specified without type arguments
    typ = _generic_type_add_any(typ)

    # Base types
    field = _field_by_type(typ, base_schema)
    if field:
        return field(**metadata)

    if typ is Any:
        metadata.setdefault("allow_none", True)
        return marshmallow.fields.Raw(**metadata)

    if typing_inspect.is_literal_type(typ):
        arguments = typing_inspect.get_args(typ)
        return marshmallow.fields.Raw(
            validate=(
                marshmallow.validate.Equal(arguments[0])
                if len(arguments) == 1
                else marshmallow.validate.OneOf(arguments)
            ),
            **metadata,
        )

    # Generic types
    generic_field = _field_for_generic_type(typ, base_schema, **metadata)
    if generic_field:
        return generic_field

    # typing.NewType returns a function with a __supertype__ attribute
    newtype_supertype = getattr(typ, "__supertype__", None)
    if newtype_supertype and inspect.isfunction(typ):
        return _field_by_supertype(
            typ=typ,
            default=default,
            newtype_supertype=newtype_supertype,
            metadata=metadata,
            base_schema=base_schema,
        )

    # enumerations
    if isinstance(typ, EnumMeta):
        import marshmallow_enum

        return marshmallow_enum.EnumField(typ, **metadata)

    # Nested marshmallow dataclass
    nested_schema = getattr(typ, "Schema", None)

    # Nested dataclasses
    forward_reference = getattr(typ, "__forward_arg__", None)
    nested = (
        nested_schema or forward_reference or _internal_class_schema(typ, base_schema)
    )

    return marshmallow.fields.Nested(nested, **metadata)


def _base_schema(
    clazz: type, base_schema: Optional[Type[marshmallow.Schema]] = None
) -> Type[marshmallow.Schema]:
    """
    Base schema factory that creates a schema for `clazz` derived either from `base_schema`
    or `BaseSchema`
    """

    # Remove `type: ignore` when mypy handles dynamic base classes
    # https://github.com/python/mypy/issues/2813
    class BaseSchema(base_schema or marshmallow.Schema):  # type: ignore
        def load(self, data: Mapping, *, many: bool = None, **kwargs):
            all_loaded = super().load(data, many=many, **kwargs)
            many = self.many if many is None else bool(many)
            if many:
                return [clazz(**loaded) for loaded in all_loaded]
            else:
                return clazz(**all_loaded)

    return BaseSchema


def _get_field_default(field: dataclasses.Field):
    """
    Return a marshmallow default value given a dataclass default value

    >>> _get_field_default(dataclasses.field())
    <marshmallow.missing>
    """
    # Remove `type: ignore` when https://github.com/python/mypy/issues/6910 is fixed
    default_factory = field.default_factory  # type: ignore
    if default_factory is not dataclasses.MISSING:
        return default_factory
    elif field.default is dataclasses.MISSING:
        return marshmallow.missing
    return field.default


def NewType(
    name: str,
    typ: Type[_U],
    field: Optional[Type[marshmallow.fields.Field]] = None,
    **kwargs,
) -> Callable[[_U], _U]:
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

    def new_type(x: _U):
        return x

    new_type.__name__ = name
    # noinspection PyTypeHints
    new_type.__supertype__ = typ  # type: ignore
    # noinspection PyTypeHints
    new_type._marshmallow_field = field  # type: ignore
    # noinspection PyTypeHints
    new_type._marshmallow_args = kwargs  # type: ignore
    return new_type


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
