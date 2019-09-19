# marshmallow_dataclass
[![Build Status](https://travis-ci.org/lovasoa/marshmallow_dataclass.svg?branch=master)](https://travis-ci.org/lovasoa/marshmallow_dataclass)
[![PyPI version](https://badge.fury.io/py/marshmallow-dataclass.svg)](https://badge.fury.io/py/marshmallow-dataclass)

Automatic generation of [marshmallow](https://marshmallow.readthedocs.io/) schemas from dataclasses.

Specifying a schema to which your data should conform is very useful, both for (de)serialization and for documentation.
However, using schemas in python often means having both a class to represent your data and a class to represent its schema, which means duplicated code that could fall out of sync. With the new features of python 3.6, types can be defined for class members, and that allows libraries like this one to generate schemas automatically.

An use case would be to document APIs (with [flasgger](https://github.com/rochacbruno/flasgger#flasgger), for instance) in a way that allows you to statically check that the code matches the documentation.

## How to use

You simply import
[`marshmallow_dataclass.dataclass`](https://lovasoa.github.io/marshmallow_dataclass/html/marshmallow_dataclass.html#marshmallow_dataclass.dataclass)
instead of
[`dataclasses.dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass).
It adds a `Schema` property to the generated class,
containing a marshmallow
[Schema](https://marshmallow.readthedocs.io/en/2.x-line/api_reference.html#marshmallow.Schema)
class.

If you need to specify custom properties on your marshmallow fields
(such as `attribute`, `error`, `validate`, `required`, `dump_only`, `error_messages`, `description` ...)
you can add them using the `metadata` argument of the
[`field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field)
function.

```python
from dataclasses import field
from marshmallow_dataclass import (
    dataclass,
)  # Importing from marshmallow_dataclass instead of dataclasses
import marshmallow.validate
from typing import List, Optional


@dataclass
class Building:
    # The field metadata is used to instantiate the marshmallow field
    height: float = field(metadata={"validate": marshmallow.validate.Range(min=0)})
    name: str = field(default="anonymous")


@dataclass
class City:
    name: Optional[str]
    buildings: List[Building] = field(default_factory=lambda: [])


# City.Schema contains a marshmallow schema class
city = City.Schema().load(
    {"name": "Paris", "buildings": [{"name": "Eiffel Tower", "height": 324}]}
)

# Serializing city as a json string
city_json = City.Schema().dumps(city)
```

The previous  syntax is very convenient, as the only change
you have to apply to your existing code is update the
`dataclass` import.

However, as the `.Schema` property is added dynamically,
it can confuse type checkers.
If you want to avoid that, you can also use the standard
`dataclass` decorator, and generate the schema manually
using
[`class_schema`](https://lovasoa.github.io/marshmallow_dataclass/html/marshmallow_dataclass.html#marshmallow_dataclass.class_schema)
:

```python
from dataclasses import dataclass
from datetime import datetime
import marshmallow_dataclass


@dataclass
class Person:
    name: str
    birth: datetime


PersonSchema = marshmallow_dataclass.class_schema(Person)
```

You can also declare the schema as a
[`ClassVar`](https://docs.python.org/3/library/typing.html#typing.ClassVar):

```python
from marshmallow_dataclass import dataclass
from marshmallow import Schema
from typing import ClassVar, Type


@dataclass
class Point:
    x: float
    y: float
    Schema: ClassVar[Type[Schema]] = Schema
```

### Custom base Schema class

It is also possible to derive all schemas from your own 
base Schema class
(see [marshmallow's documentation about extending `Schema`](https://marshmallow.readthedocs.io/en/stable/extending.html)).
This allows you to implement custom (de)serialization
behavior, for instance renaming fields:

```python
import marshmallow
import marshmallow_dataclass


class BaseSchema(marshmallow.Schema):
    def on_bind_field(self, field_name, field_obj):
        field_obj.data_key = (field_obj.data_key or field_name).upper()


@marshmallow_dataclass.dataclass(base_schema=BaseSchema)
class Sample:
    my_text: str
    my_int: int


Sample.Schema().dump(Sample(my_text="warm words", my_int=1))
# -> {"MY_TEXT": "warm words", "MY_INT": 1}
```

### Custom NewType declarations

> This feature is currently only available
> in the latest pre-release, `6.1.0rc1`.
> Please try it, and open an issue if you have
> some feedback to give about it.

This library exports a `NewType` function
to create new python types with a custom
(de)serialization logic.

All the additional keyword arguments to
`NewType` are passed to the marshmallow
field initializer:

```python
import marshmallow.validate
from marshmallow_dataclass import NewType

IPv4 = NewType(
    "IPv4", str, validate=marshmallow.validate.Regexp(r"^([0-9]{1,3}\\.){3}[0-9]{1,3}$")
)
```

You can also set a predefined marshmallow field
for your new type:

```python
import marshmallow
from marshmallow_dataclass import NewType

Email = NewType("Email", str, field=marshmallow.fields.Email)
```

This feature allows you to implement a custom 
serialization and deserialization logic using
[custom marshmallow fields](https://marshmallow.readthedocs.io/en/stable/custom_fields.html#creating-a-field-class).

### Using marshmallow's `Meta`
You can specify the
[`Meta`](https://marshmallow.readthedocs.io/en/3.0/api_reference.html#marshmallow.Schema.Meta)
just as you would in a marshmallow Schema:

```python
from marshmallow_dataclass import dataclass


@dataclass
class Point:
    x: float
    y: float

    class Meta:
        ordered = True
```

## Installation
This package [is hosted on pypi](https://pypi.org/project/marshmallow-dataclass/).
You can install it with a simple :

```shell
pip3 install marshmallow-dataclass
```

This package also has the following optional features:
 - `enum`, for translating python enums to 
[marshmallow-enum](https://github.com/justanr/marshmallow_enum).
 - `union`, for translating python
 [`Union` types](https://docs.python.org/3/library/typing.html#typing.Union)
 into [`marshmallow-union`](https://pypi.org/project/marshmallow-union/)
 fields.
 
You can install these features with:

```shell 
pip3 install marshmallow-dataclass[enum,union]
```

#### For marshmallow 2
`marshmallow-dataclass` does not support the old
marshmallow 2 anymore.
You can install a version before `6.0`
if you want marshmallow 2 support.

## Documentation

The project documentation is hosted on github pages:
 - [documentation](https://lovasoa.github.io/marshmallow_dataclass/).

## Usage warning

This library depends on python's standard
[typing](https://docs.python.org/3/library/typing.html)
library, which is
[provisional](https://docs.python.org/3/glossary.html#term-provisional-api).
