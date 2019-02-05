# marshmallow_dataclass
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