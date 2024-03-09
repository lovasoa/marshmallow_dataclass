from typing import Annotated

import marshmallow.fields

Url = Annotated[str, marshmallow.fields.Url]
Email = Annotated[str, marshmallow.fields.Email]

# Aliases
URL = Url
