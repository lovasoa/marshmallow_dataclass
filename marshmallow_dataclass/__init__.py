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
from enum import Enum, EnumMeta
import dataclasses
import inspect

import marshmallow
import datetime
import uuid
import decimal
from typing import Dict, Type, List, cast, Tuple, ClassVar, Optional, Any, Mapping, NewType
from enum import Enum, EnumMeta
import typing_inspect
import inspect


__all__ = [
    'dataclass',
    'add_schema',
    'class_schema',
    'field_for_schema'
]

NoneType = type(None)


# _cls should never be specified by keyword, so start it with an
# underscore.  The presence of _cls is used to detect if this
# decorator is being called with parameters or not.
def dataclass(_cls: type = None, *, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False) -> type:
    """
    This decorator does the same as dataclasses.dataclass, but also applies :func:`add_schema`.
    It adds a `.Schema` attribute to the class object

    >>> @dataclass
    ... class Artist:
    ...    name: str
    >>> Artist.Schema
    <class 'marshmallow.schema.Artist'>

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
    dc = dataclasses.dataclass(_cls, repr=repr, eq=eq, order=order, unsafe_hash=unsafe_hash, frozen=frozen)
    return add_schema(dc) if _cls else lambda cls: add_schema(dc(cls))


def add_schema(clazz: type) -> type:
    """
    This decorator adds a marshmallow schema as the 'Schema' attribute in a dataclass.
    It uses :func:`class_schema` internally.

    >>> @add_schema
    ... @dataclasses.dataclass
    ... class Artist:
    ...    names: Tuple[str, str]
    >>> artist = Artist.Schema().loads('{"names": ["Martin", "Ramirez"]}')
    >>> artist
    Artist(names=('Martin', 'Ramirez'))
    """
    clazz.Schema = class_schema(clazz)
    return clazz


def class_schema(clazz: type) -> Type[marshmallow.Schema]:
    """
    Convert a class to a marshmallow schema

    :param clazz: A python class (may be a dataclass)
    :return: A marshmallow Schema corresponding to the dataclass

    .. note::
        All the arguments supported by marshmallow field classes are can
        be passed in the `metadata` dictionary of a field.


    If you want to use a custom marshmallow field
    (one that has no equivalent python type), you can pass it as the
    ``marshmallow_field`` key in the metadata dictionary.

    >>> Meters = NewType('Meters', float)
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
    ...   best_building: Building # Reference to another dataclasses. A schema will be created for it too.
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
    ...   unimportant: int = dataclasses.field(init=False, default=0) # Only fields that are in the __init__ method will be added:
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

    >>> class_schema(None)  # unsupported type
    Traceback (most recent call last):
      ...
    TypeError: None is not a dataclass and cannot be turned into one.
    """

    try:
        # noinspection PyDataclass
        fields: Tuple[dataclasses.Field] = dataclasses.fields(clazz)
    except TypeError:  # Not a dataclass
        try:
            return class_schema(dataclasses.dataclass(clazz))
        except Exception:
            raise TypeError(
                f"{getattr(clazz, '__name__', repr(clazz))} is not a dataclass and cannot be turned into one.")

    # Copy all public members of the dataclass to the schema
    attributes = {k: v for k, v in inspect.getmembers(clazz) if not k.startswith('_')}
    # Update the schema members to contain marshmallow fields instead of dataclass fields
    attributes.update(
        (field.name, field_for_schema(field.type, _get_field_default(field), field.metadata))
        for field in fields if field.init
    )

    schema_class = type(clazz.__name__, (_base_schema(clazz),), attributes)
    return cast(Type[marshmallow.Schema], schema_class)


_native_to_marshmallow: Dict[type, Type[marshmallow.fields.Field]] = {
    int: marshmallow.fields.Integer,
    float: marshmallow.fields.Float,
    str: marshmallow.fields.String,
    bool: marshmallow.fields.Boolean,
    datetime.datetime: marshmallow.fields.DateTime,
    datetime.time: marshmallow.fields.Time,
    datetime.timedelta: marshmallow.fields.TimeDelta,
    datetime.date: marshmallow.fields.Date,
    decimal.Decimal: marshmallow.fields.Decimal,
    uuid.UUID: marshmallow.fields.UUID,
    Any: marshmallow.fields.Raw,
}


def field_for_schema(
        typ: type,
        default=marshmallow.missing,
        metadata: Mapping[str, Any] = None
) -> marshmallow.fields.Field:
    """
    Get a marshmallow Field corresponding to the given python type.
    The metadata of the dataclass field is used as arguments to the marshmallow Field.

    >>> int_field = field_for_schema(int, default=9, metadata=dict(required=True))
    >>> int_field.__class__
    <class 'marshmallow.fields.Integer'>
    
    >>> int_field.default
    9

    >>> int_field.required
    True

    >>> field_for_schema(Dict[str,str]).__class__
    <class 'marshmallow.fields.Dict'>

    >>> field_for_schema(str, metadata={"marshmallow_field": marshmallow.fields.Url()}).__class__
    <class 'marshmallow.fields.Url'>

    >>> field_for_schema(Optional[str]).__class__
    <class 'marshmallow.fields.String'>

    >>> import marshmallow_enum
    >>> field_for_schema(Enum("X", "a b c")).__class__
    <class 'marshmallow_enum.EnumField'>

    >>> import typing
    >>> field_for_schema(typing.Union[int,str]).__class__
    <class 'marshmallow_union.Union'>

    >>> field_for_schema(NewType('UserId', int)).__class__
    <class 'marshmallow.fields.Integer'>

    >>> field_for_schema(NewType('UserId', int), default=0).default
    0

    >>> class Color(Enum):
    ...   red = 1
    >>> field_for_schema(Color).__class__
    <class 'marshmallow_enum.EnumField'>

    >>> field_for_schema(Any).__class__
    <class 'marshmallow.fields.Raw'>
    """

    metadata = {} if metadata is None else dict(metadata)
    if default is not marshmallow.missing:
        metadata.setdefault('default', default)
        if not metadata.get("required"):  # 'missing' must not be set for required fields.
            metadata.setdefault('missing', default)
    else:
        metadata.setdefault('required', True)

    # If the field was already defined by the user
    predefined_field = metadata.get('marshmallow_field')
    if predefined_field:
        return predefined_field

    # Base types
    if typ in _native_to_marshmallow:
        return _native_to_marshmallow[typ](**metadata)

    # Generic types
    origin = typing_inspect.get_origin(typ)
    if origin:
        arguments = typing_inspect.get_args(typ, True)
        if origin in (list, List):
            return marshmallow.fields.List(
                field_for_schema(arguments[0]),
                **metadata
            )
        if origin in (tuple, Tuple):
            return marshmallow.fields.Tuple(
                tuple(field_for_schema(arg) for arg in arguments),
                **metadata
            )
        elif origin in (dict, Dict):
            return marshmallow.fields.Dict(
                keys=field_for_schema(arguments[0]),
                values=field_for_schema(arguments[1]),
                **metadata
            )
        elif typing_inspect.is_optional_type(typ):
            subtyp = next(t for t in arguments if t is not NoneType)
            # Treat optional types as types with a None default
            metadata['default'] = metadata.get('default', None)
            metadata['missing'] = metadata.get('missing', None)
            metadata['required'] = False
            return field_for_schema(subtyp, metadata=metadata)
        elif typing_inspect.is_union_type(typ):
            subfields = [field_for_schema(subtyp, metadata=metadata) for subtyp in arguments]
            import marshmallow_union
            return marshmallow_union.Union(subfields, **metadata)

    # typing.NewType returns a function with a __supertype__ attribute
    newtype_supertype = getattr(typ, '__supertype__', None)
    if newtype_supertype and inspect.isfunction(typ):
        metadata.setdefault('description', typ.__name__)
        return field_for_schema(newtype_supertype, metadata=metadata, default=default)

    # enumerations
    if type(typ) is EnumMeta:
        import marshmallow_enum
        return marshmallow_enum.EnumField(typ, **metadata)

    # Nested dataclasses
    forward_reference = getattr(typ, '__forward_arg__', None)
    nested = forward_reference or class_schema(typ)
    return marshmallow.fields.Nested(nested, **metadata)


def _base_schema(clazz: type) -> Type[marshmallow.Schema]:
    class BaseSchema(marshmallow.Schema):
        @marshmallow.post_load
        def make_data_class(self, data, **_):
            return clazz(**data)

    return BaseSchema


def _get_field_default(field: dataclasses.Field):
    """
    Return a marshmallow default value given a dataclass default value

    >>> _get_field_default(dataclasses.field())
    <marshmallow.missing>
    """
    if field.default_factory is not dataclasses.MISSING:
        return field.default_factory
    elif field.default is dataclasses.MISSING:
        return marshmallow.missing
    return field.default


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
