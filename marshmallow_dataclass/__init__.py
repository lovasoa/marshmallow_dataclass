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
    point_json, err = Point.Schema(strict=True).dumps(point)

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

import dataclasses

import marshmallow
import datetime
import uuid
import decimal
from typing import Dict, Type, List, Callable, cast, Tuple, ClassVar, Optional, Any, Mapping
import collections.abc
import typing_inspect

__all__ = [
    'dataclass',
    'add_schema',
    'class_schema',
    'field_for_schema'
]


def dataclass(clazz: type) -> type:
    """
    This decorator does the same as dataclasses.dataclass, but also applies :func:`add_schema`.
    It adds a `.Schema` attribute to the class object

    >>> @dataclass
    ... class Artist:
    ...    name: str
    >>> Artist.Schema
    <class 'marshmallow.schema.Artist'>

    >>> from marshmallow import Schema
    >>> @dataclass
    ... class Point:
    ...   x:float
    ...   y:float
    ...   Schema: ClassVar[Type[Schema]] = Schema # For the type checker
    ...
    >>> Point.Schema(strict=True).load({'x':0, 'y':0}).data # This line can be statically type checked
    Point(x=0.0, y=0.0)
    """
    return add_schema(dataclasses.dataclass(clazz))


def add_schema(clazz: type) -> type:
    """
    This decorator adds a marshmallow schema as the 'Schema' attribute in a dataclass.
    It uses :func:`class_schema` internally.

    >>> @add_schema
    ... @dataclasses.dataclass
    ... class Artist:
    ...    name: str
    >>> artist, err = Artist.Schema(strict=True).loads('{"name": "Ramirez"}')
    >>> artist
    Artist(name='Ramirez')
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

    >>> @dataclasses.dataclass()
    ... class Building:
    ...   height: Optional[float]
    ...   name: str = dataclasses.field(default="anonymous")
    ...
    >>> class_schema(Building) # Returns a marshmallow schema class (not an instance)
    <class 'marshmallow.schema.Building'>

    >>> @dataclasses.dataclass()
    ... class City:
    ...   name: str = dataclasses.field(metadata={'required':True})
    ...   best_building: Building # Reference to another dataclasses. A schema will be created for it too.
    ...   other_buildings: List[Building] = dataclasses.field(default_factory=lambda: [])
    ...
    >>> citySchema = class_schema(City)(strict=True)
    >>> city, _ = citySchema.load({"name":"Paris", "best_building": {"name": "Eiffel Tower"}})
    >>> city
    City(name='Paris', best_building=Building(height=None, name='Eiffel Tower'), other_buildings=[])

    >>> citySchema.load({"name":"Paris"})
    Traceback (most recent call last):
        ...
    marshmallow.exceptions.ValidationError: {'best_building': ['Missing data for required field.']}

    >>> city_json, _ = citySchema.dump(city)

    >>> @dataclasses.dataclass()
    ... class Person:
    ...   name: str = dataclasses.field(default="Anonymous")
    ...   friends: List['Person'] = dataclasses.field(default_factory=lambda:[]) # Recursive field
    ...
    >>> person, _ = class_schema(Person)(strict=True).load({
    ...     "friends": [{"name": "Roger Boucher"}]
    ... })
    >>> person
    Person(name='Anonymous', friends=[Person(name='Roger Boucher', friends=[])])

    >>> @dataclasses.dataclass()
    ... class C:
    ...   important: int = dataclasses.field(init=True, default=0)
    ...   unimportant: int = dataclasses.field(init=False, default=0) # Only fields that are in the __init__ method will be added:
    ...
    >>> c, _ = class_schema(C)(strict=True).load({
    ...     "important": 9, # This field will be imported
    ...     "unimportant": 9 # This field will NOT be imported
    ... })
    >>> c
    C(important=9, unimportant=0)

    >>> @dataclasses.dataclass
    ... class Website:
    ...  url:str = dataclasses.field(metadata = {
    ...    "marshmallow_field": marshmallow.fields.Url() # Custom marshmallow field
    ...  })
    ...
    >>> class_schema(Website)(strict=True).load({"url": "I am not a good URL !"})
    Traceback (most recent call last):
        ...
    marshmallow.exceptions.ValidationError: {'url': ['Not a valid URL.']}
    """

    try:
        # noinspection PyDataclass
        fields: Tuple[dataclasses.Field] = dataclasses.fields(clazz)
    except TypeError:  # Not a dataclass
        try:
            return class_schema(dataclasses.dataclass(clazz))
        except Exception:
            raise TypeError(f"{clazz.__name__} is not a dataclass and cannot be turned into one.")

    attributes = {
        field.name: field_for_schema(
            field.type,
            _get_field_default(field),
            field.metadata
        )
        for field in fields
        if field.init
    }
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
}


def field_for_schema(
        typ: type,
        default=marshmallow.missing,
        metadata: Mapping[str, Any] = None
) -> marshmallow.fields.Field:
    """
    Get a marshmallow Field corresponding to the given python type.
    The metadata of the dataclass field is used as arguments to the marshmallow Field.

    >>> field_for_schema(int, default=9, metadata=dict(required=True))
    <fields.Integer(default=9, attribute=None, validate=None, required=True, load_only=False, dump_only=False, missing=9, allow_none=False, error_messages={'required': 'Missing data for required field.', 'type': 'Invalid input type.', 'null': 'Field may not be null.', 'validator_failed': 'Invalid value.', 'invalid': 'Not a valid integer.'})>

    >>> field_for_schema(Dict[str,str]).__class__
    <class 'marshmallow.fields.Dict'>

    >>> field_for_schema(Callable[[str],str]).__class__
    <class 'marshmallow.fields.Function'>

    >>> field_for_schema(str, metadata={"marshmallow_field": marshmallow.fields.Url()}).__class__
    <class 'marshmallow.fields.Url'>

    >>> field_for_schema(Optional[str]).__class__
    <class 'marshmallow.fields.String'>
    """

    metadata = {} if metadata is None else dict(metadata)
    metadata.setdefault('required', True)
    if default is not marshmallow.missing:
        metadata.setdefault('default', default)
        metadata.setdefault('missing', default)

    # If the field was already defined by the user
    predefined_field = metadata.get('marshmallow_field')
    if predefined_field:
        return predefined_field

    # Base types
    if typ in _native_to_marshmallow:
        return _native_to_marshmallow[typ](**metadata)

    # Generic types
    origin: type = typing_inspect.get_origin(typ)
    if origin in (list, List):
        list_elements_type = typing_inspect.get_args(typ, True)[0]
        return marshmallow.fields.List(
            field_for_schema(list_elements_type),
            **metadata
        )
    elif origin in (dict, Dict):
        key_type, value_type = typing_inspect.get_args(typ, True)
        return marshmallow.fields.Dict(
            keys=field_for_schema(key_type),
            values=field_for_schema(value_type),
            **metadata
        )
    elif origin in (collections.abc.Callable, Callable):
        return marshmallow.fields.Function(**metadata)
    elif typing_inspect.is_optional_type(typ):
        subtyp = next(t for t in typing_inspect.get_args(typ) if not isinstance(None, t))
        # Treat optional types as types with a None default
        metadata['default'] = metadata.get('default', None)
        metadata['missing'] = metadata.get('missing', None)
        metadata['required'] = False
        return field_for_schema(subtyp, metadata=metadata)

    # Nested dataclasses
    forward_reference = getattr(typ, '__forward_arg__', None)
    nested = forward_reference or class_schema(typ)
    return marshmallow.fields.Nested(nested, **metadata)


def _base_schema(clazz: type) -> Type[marshmallow.Schema]:
    class BaseSchema(marshmallow.Schema):
        @marshmallow.post_load
        def make_data_class(self, data):
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
