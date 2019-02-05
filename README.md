# marshmallow_dataclass
[![Build Status](https://travis-ci.org/lovasoa/marshmallow_dataclass.svg?branch=master)](https://travis-ci.org/lovasoa/marshmallow_dataclass)

Automatic generation of marshmallow schemas from dataclasses.

## How to use

```python
from dataclasses import field
from marshmallow_dataclass import dataclass # Importing from marshmallow_dataclass instead of dataclasses
from typing import List

@dataclass
class Building:
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
```

## installation
This package [is hosted on pypi](https://pypi.org/project/marshmallow-dataclass/) :

```shell
pipenv install marshmallow-dataclass
```

## Documentation

The project documentation is hosted on github pages:
https://lovasoa.github.io/marshmallow_dataclass/html/marshmallow_dataclass.html.
