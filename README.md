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
from marshmallow_dataclass import dataclass # Importing from marshmallow_dataclass instead of dataclasses
import marshmallow.validate
from typing import List, Optional

@dataclass
class Building:
  # The field metadata is used to instantiate the marshmallow field
  height: float = field(metadata={'validate': marshmallow.validate.Range(min=0)})
  name: str = field(default="anonymous")


@dataclass
class City:
  name: Optional[str]
  buildings: List[Building] = field(default_factory=lambda: [])

# City.Schema contains a marshmallow schema class
city, _ = City.Schema().load({
    "name": "Paris",
    "buildings": [
        {"name": "Eiffel Tower", "height":324}
    ]
})

# Serializing city as a json string
city_json, _ = City.Schema().dumps(city)
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
  x:float
  y:float
  Schema: ClassVar[Type[Schema]] = Schema
```

You can specify the
[`Meta`](https://marshmallow.readthedocs.io/en/3.0/api_reference.html#marshmallow.Schema.Meta)
just as you would in a marshmallow Schema:

```python
from marshmallow_dataclass import dataclass

@dataclass
class Point:
  x:float
  y:float
  class Meta:
    ordered = True
```

## Installation
This package [is hosted on pypi](https://pypi.org/project/marshmallow-dataclass/).

There are two versions, depending on whether you want to use
the latest stable release of marshmallow
(marshmallow 2)
or the newer unstable
marshmallow 3 pre-release:

#### For marshmallow 2
```shell
pipenv install marshmallow-dataclass
```

#### For marshmallow 3
```shell
pipenv install --pre marshmallow-dataclass
```

## Documentation

The project documentation is hosted on github pages:
 - [documentation](https://lovasoa.github.io/marshmallow_dataclass/).

## Usage warning

This library depends on python's standard
[typing](https://docs.python.org/3/library/typing.html)
library, which is
[provisional](https://docs.python.org/3/glossary.html#term-provisional-api).
