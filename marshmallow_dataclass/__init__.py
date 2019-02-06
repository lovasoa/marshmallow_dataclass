"""
This library allows the conversion of python 3.7's dataclasses to marshmallow's schemas.
"""

import dataclasses

import marshmallow
import datetime
import uuid
import decimal
from typing import Dict, Type, List, Callable, cast
import collections.abc


def dataclass(clazz: type) -> type:
    """
    This decorator does the same as dataclasses.dataclass, but also applies :func:`add_schema`.
    It adds a `.Schema` attribute to the class object

    >>> @dataclass
    ... class Artist:
    ...    name: str
    >>> Artist.Schema
    <class 'marshmallow.schema.Artist'>
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

    >>> @dataclasses.dataclass()
    ... class Building:
    ...   height: float = dataclasses.field(metadata={'required':True})
    ...   name: str = dataclasses.field(default="anonymous")
    ...
    >>> class_schema(Building) # Returns a marshmallow schema class (not an instance)
    <class 'marshmallow.schema.Building'>

    >>> @dataclasses.dataclass()
    ... class City:
    ...   name: str
    ...   buildings: List[Building] = dataclasses.field(default_factory=lambda: [])
    >>> citySchema = class_schema(City)(strict=True)
    >>> city, _ = citySchema.load({"name": "Paris", "buildings": [{"name": "Eiffel Tower", "height":324}]})
    >>> city
    City(name='Paris', buildings=[Building(height=324.0, name='Eiffel Tower')])

    >>> @dataclasses.dataclass()
    ... class Person:
    ...   name: str
    ...   friends: List['Person'] = dataclasses.field(default_factory=lambda:[]) # Recursive field
    >>> person, _ = class_schema(Person)(strict=True).load({
    ...     "name": "Gérard Bouchard",
    ...     "friends": [{"name": "Roger Boucher"}]
    ... })
    >>> person
    Person(name='Gérard Bouchard', friends=[Person(name='Roger Boucher', friends=[])])
    """

    try:
        fields: Dict[str, dataclasses.Field] = getattr(clazz, '__dataclass_fields__')
    except AttributeError:  # not a dataclass
        try:
            return class_schema(dataclasses.dataclass(clazz))
        except Exception:
            raise TypeError(f"{clazz.__name__} is not a dataclass and cannot be turned into one.")

    attributes = {
        name: field_for_schema(
            field.type,
            _get_field_default(field),
            field.metadata
        )
        for name, field in fields.items()
    }
    schema_class = type(clazz.__name__, (_base_schema(clazz),), attributes)
    return cast(Type[marshmallow.Schema], schema_class)


_native_to_marshmallow: Dict[type, Type[marshmallow.fields.Field]] = {
    int: marshmallow.fields.Int,
    float: marshmallow.fields.Float,
    str: marshmallow.fields.Str,
    bool: marshmallow.fields.Bool,
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
        metadata=None
) -> marshmallow.fields.Field:
    """
    Get a marshmallow Field corresponding to the given python type.
    The metadata of the dataclass field is used as arguments to the marshmallow Field.

    >>> field_for_schema(int, default=9, metadata=dict(required=True))
    <fields.Integer(default=9, attribute=None, validate=None, required=True, load_only=False, dump_only=False, missing=<marshmallow.missing>, allow_none=False, error_messages={'required': 'Missing data for required field.', 'type': 'Invalid input type.', 'null': 'Field may not be null.', 'validator_failed': 'Invalid value.', 'invalid': 'Not a valid integer.'})>

    >>> field_for_schema(Dict[str,str]).__class__
    <class 'marshmallow.fields.Dict'>

    >>> field_for_schema(Callable[[str],str]).__class__
    <class 'marshmallow.fields.Function'>
    """

    if metadata is None:
        metadata = {}

    # Base types
    if typ in _native_to_marshmallow:
        return _native_to_marshmallow[typ](default=default, **metadata)

    # Generic types
    origin: type = getattr(typ, '__origin__', None)
    if origin == list:
        list_elements_type = getattr(typ, '__args__', (None,))[0]
        return marshmallow.fields.List(
            field_for_schema(list_elements_type),
            default=default,
            **metadata
        )
    elif origin == dict:
        key_type, value_type = getattr(typ, '__args__', (None, None))
        return marshmallow.fields.Dict(
            keys=field_for_schema(key_type),
            values=field_for_schema(value_type),
            default=default,
            **metadata
        )
    elif origin == collections.abc.Callable:
        return marshmallow.fields.Function(
            default=default,
            **metadata
        )

    # Nested dataclasses
    forward_reference = getattr(typ, '__forward_arg__', None)
    return marshmallow.fields.Nested(
        nested=forward_reference or class_schema(typ),
        default=default,
        **metadata
    )


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
        return field.default_factory()
    elif field.default is dataclasses.MISSING:
        return marshmallow.missing
    return field.default


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
