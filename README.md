# marshmallow_dataclass
[![Build Status](https://travis-ci.org/lovasoa/marshmallow_dataclass.svg?branch=master)](https://travis-ci.org/lovasoa/marshmallow_dataclass)

Automatic generation of marshmallow schemas from dataclasses.

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
from typing import List

@dataclass
class Building:
  # The field metadata is used to instantiate the marshmallow field
  height: float = field(metadata={'required':True})
  name: str = field(default="anonymous")


@dataclass
class City:
  name: str
  buildings: List[Building] = field(default_factory=lambda: [])

# City.Schema contains a marshmallow schema class
city, _ = City.Schema().load({
    "name": "Paris",
    "buildings": [
        {"name": "Eiffel Tower", "height":324}
    ]
})

# Example string dump of City Schema
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

## installation
This package [is hosted on pypi](https://pypi.org/project/marshmallow-dataclass/) :

```shell
pipenv install marshmallow-dataclass
```

## Documentation

The project documentation is hosted on github pages:
 - [documentation](https://lovasoa.github.io/marshmallow_dataclass/).

## Usage warning

This library depends on python's standard
[typing](https://docs.python.org/3/library/typing.html)
library, which is
[provisional](https://docs.python.org/3/glossary.html#term-provisional-api).