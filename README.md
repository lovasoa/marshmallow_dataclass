# marshmallow-dataclass

[![Build Status](https://travis-ci.org/lovasoa/marshmallow_dataclass.svg?branch=master)](https://travis-ci.org/lovasoa/marshmallow_dataclass)
[![PyPI version](https://badge.fury.io/py/marshmallow-dataclass.svg)](https://badge.fury.io/py/marshmallow-dataclass)
[![marshmallow 3 compatible](https://badgen.net/badge/marshmallow/3)](https://marshmallow.readthedocs.io/en/latest/upgrading.html)

Automatic generation of [marshmallow](https://marshmallow.readthedocs.io/) schemas from dataclasses.

```python
from dataclasses import dataclass, field
from typing import List, Optional

import marshmallow
import marshmallow_dataclass


@dataclass
class Building:
    # field metadata is used to instantiate the marshmallow field
    height: float = field(metadata={"validate": marshmallow.validate.Range(min=0)})
    name: str = field(default="anonymous")


@dataclass
class City:
    name: Optional[str]
    buildings: List[Building] = field(default_factory=list)


CitySchema = marshmallow_dataclass.class_schema(City)

# Deserialize dict to an object
city = CitySchema().load(
    {"name": "Paris", "buildings": [{"name": "Eiffel Tower", "height": 324}]}
)
# => City(name='Paris', buildings=[Building(height=324.0, name='Eiffel Tower')])

# Serializing object to a dict
city_dict = CitySchema().dump(city)
# => {'name': 'Paris', 'buildings': [{'name': 'Eiffel Tower', 'height': 324.0}]}
```

## Why

Using schemas in Python often means having both a class to represent your data and a class to represent its schema, which results in duplicated code that could fall out of sync.
As of Python 3.6, types can be defined for class members, which allows libraries to generate schemas automatically.

Therefore, you can document your APIs in a way that allows you to statically check that the code matches the documentation.

## Installation

This package [is hosted on PyPI](https://pypi.org/project/marshmallow-dataclass/).

```shell
pip3 install marshmallow-dataclass
```

You may optionally install the following extras:

- `enum`, for translating python enums to [marshmallow-enum](https://github.com/justanr/marshmallow_enum).
- `union`, for translating python [`Union` types](https://docs.python.org/3/library/typing.html#typing.Union) into [`marshmallow-union`](https://pypi.org/project/marshmallow-union/) fields.

```shell
pip3 install marshmallow-dataclass[enum,union]
```

### marshmallow 2 support

`marshmallow-dataclass` no longer supports marshmallow 2.
Install `marshmallow_dataclass<6.0` if you need marshmallow 2 compatibility.

## Usage

Use the [`class_schema`](https://lovasoa.github.io/marshmallow_dataclass/html/marshmallow_dataclass.html#marshmallow_dataclass.class_schema) function to generate a marshmallow [Schema](https://marshmallow.readthedocs.io/en/latest/api_reference.html#marshmallow.Schema) class from a [`dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass).

```python
from dataclasses import dataclass
from datetime import date

import marshmallow_dataclass


@dataclass
class Person:
    name: str
    birth: date


PersonSchema = marshmallow_dataclass.class_schema(Person)
```

### Customizing generated fields

To pass arguments to the generated marshmallow fields (e.g., `validate`, `load_only`, `dump_only`, etc.), pass them to the `metadata` argument of the [`field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field) function.

```python
from dataclasses import dataclass, field
from typing import List, Optional

import marshmallow.validate


@dataclass
class Building:
    height: float = field(metadata={"validate": marshmallow.validate.Range(min=0)})
    name: str = field(default="anonymous")


@dataclass
class City:
    name: Optional[str]
    buildings: List[Building] = field(default_factory=list)


CitySchema = marshmallow_dataclass.class_schema(City)
```

### `@dataclass` shortcut

`marshmallow_dataclass` provides a `@dataclass` decorator that behaves like the standard library's `@dataclasses.dataclass` and adds a `Schema` attribute with the generated marshmallow [Schema](https://marshmallow.readthedocs.io/en/2.x-line/api_reference.html#marshmallow.Schema).

```python
from dataclasses import field
from typing import List, Optional

# Use marshmallow_dataclass's @dataclass shortcut
from marshmallow_dataclass import dataclass
import marshmallow.validate


@dataclass
class Building:
    height: float = field(metadata={"validate": marshmallow.validate.Range(min=0)})
    name: str = field(default="anonymous")


@dataclass
class City:
    name: Optional[str]
    buildings: List[Building] = field(default_factory=list)


# City.Schema contains a marshmallow schema class
city = City.Schema().load(
    {"name": "Paris", "buildings": [{"name": "Eiffel Tower", "height": 324}]}
)
```

Note: Since the `.Schema` property is added dynamically, it can confuse type checkers.
To avoid that, you can declare `Schema` as a [`ClassVar`](https://docs.python.org/3/library/typing.html#typing.ClassVar).

```python
from typing import ClassVar, Type

from marshmallow_dataclass import dataclass
from marshmallow import Schema


@dataclass
class Point:
    x: float
    y: float
    Schema: ClassVar[Type[Schema]] = Schema
```

### Customizing the base Schema

To customize the base `Schema` class, pass the `base_schema` argument.
This allows you to implement custom (de)serialization behavior.

```python
import marshmallow
import marshmallow_dataclass


class UppercaseSchema(marshmallow.Schema):
    """A Schema that marshals data with uppercased keys."""

    def on_bind_field(self, field_name, field_obj):
        field_obj.data_key = (field_obj.data_key or field_name).upper()


class Sample:
    my_text: str
    my_int: int


SampleSchema = marshmallow_dataclass.class_schema(Sample, base_schema=UppercaseSchema)

Sample.Schema().dump(Sample(my_text="warm words", my_int=1))
# -> {"MY_TEXT": "warm words", "MY_INT": 1}
```

You can also pass `base_schema` to `marshmallow_dataclass.dataclass`.

```python
@marshmallow_dataclass.dataclass(base_schema=UppercaseSchema)
class Sample:
    my_text: str
    my_int: int
```

See [marshmallow's documentation about extending `Schema`](https://marshmallow.readthedocs.io/en/stable/extending.html).

### Custom NewType declarations

> This feature is currently only available
> in the latest pre-release, `6.1.0rc1`.
> Please try it, and open an issue if you have
> some feedback to give about it.

This library exports a `NewType` function to create types that generate [customized marshmallow fields](https://marshmallow.readthedocs.io/en/stable/custom_fields.html#creating-a-field-class).

Keyword arguments to `NewType` are passed to the marshmallow field constructor.

```python
import marshmallow.validate
from marshmallow_dataclass import NewType

IPv4 = NewType(
    "IPv4", str, validate=marshmallow.validate.Regexp(r"^([0-9]{1,3}\\.){3}[0-9]{1,3}$")
)
```

You can also pass a marshmallow field `NewType`.

```python
import marshmallow
from marshmallow_dataclass import NewType

Email = NewType("Email", str, field=marshmallow.fields.Email)
```

### `Meta` options

[`Meta` options](https://marshmallow.readthedocs.io/en/3.0/api_reference.html#marshmallow.Schema.Meta) are set the same way as a marshmallow `Schema`.

```python
from marshmallow_dataclass import dataclass


@dataclass
class Point:
    x: float
    y: float

    class Meta:
        ordered = True
```

## Documentation

The project documentation is hosted on GitHub Pages: https://lovasoa.github.io/marshmallow_dataclass/

## Usage warning

This library depends on python's standard [typing](https://docs.python.org/3/library/typing.html) library, which is [provisional](https://docs.python.org/3/glossary.html#term-provisional-api).
