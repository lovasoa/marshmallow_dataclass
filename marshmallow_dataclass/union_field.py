import copy
from typing import Dict, List, Tuple, Any, Optional, Type

import typeguard
from marshmallow import fields, Schema, ValidationError
from abc import ABC, abstractmethod

SERIALIZATION_STRATEGY_KEY = "serialization_strategy"

class SerializationStrategy(ABC):

    def __init__(self):
        self._union_fields = []
        self._required = False

    def set_union_fields(self, union_fields):
        self._union_fields = union_fields

    def set_required(self, required):
        self._required = required

    @abstractmethod
    def serialize(self, value: Any, attr: str, obj, **kwargs) -> Any:
        pass

    @abstractmethod
    def deserialize(self, value: Any, attr: Optional[str], data, **kwargs) -> Any:
        pass


class FallbackSerializationStrategy(SerializationStrategy):

    def serialize(self, value: Any, attr: str, obj, **kwargs) -> Any:
        errors = []
        if value is None and not self._required:
            return value
        for typ, field in self._union_fields:
            try:
                typeguard.check_type(attr, value, typ)
                return field._serialize(value, attr, obj, **kwargs)
            except TypeError as e:
                errors.append(e)
        raise TypeError(
            f"Unable to serialize value with any of the fields in the union: {errors}"
        )

    def deserialize(self, value: Any, attr: Optional[str], data, **kwargs) -> Any:
        errors = []
        for typ, field in self._union_fields:
            try:
                result = field.deserialize(value, **kwargs)
                typeguard.check_type(attr or "anonymous", result, typ)
                return result
            except (TypeError, ValidationError) as e:
                errors.append(e)

        raise ValidationError(errors)


class NamedTypeSerializationStrategy(SerializationStrategy):

    def __init__(self, type_to_name_map: Optional[Dict[Type, str]] = None, type_key="__type__", value_key="__value__"):
        super().__init__()
        self._type_to_name_map = type_to_name_map
        self._type_key = type_key
        self._value_key = value_key

    def _get_field(self, type):
        return next(f for t, f in self._union_fields if t == type)

    def _compute_name_to_type_map(self):
        self._name_to_type_map = None if self._type_to_name_map is None else {
            n: (t, self._get_field(t)) for t, n in self._type_to_name_map.items()}

    def set_union_fields(self, union_fields):
        super().set_union_fields(union_fields)
        if self._type_to_name_map is None:
            self._type_to_name_map = {t: t.__name__ for t, _ in union_fields}
        self._compute_name_to_type_map()

    def serialize(self, value: Any, attr: str, obj, **kwargs) -> Any:
        errors = []
        if value is None and not self._required:
            return value
        for typ, field in self._union_fields:
            try:
                typeguard.check_type(attr, value, typ)
                serialized = field._serialize(value, attr, obj, **kwargs)
                if isinstance(serialized, dict):
                    serialized[self._type_key] = self._type_to_name_map[typ]
                else:
                    serialized = {
                        self._value_key: serialized,
                        self._type_key: self._type_to_name_map[typ]
                    }
                return serialized
            except TypeError as e:
                errors.append(e)
        raise TypeError(
            f"Unable to serialize value with any of the fields in the union: {errors}"
        )

    def _validate(self, value: Any) -> Tuple[Type[Any], fields.Field]:
        if not isinstance(value, dict):
            raise TypeError("Expected value to be a dict")
        if self._type_key not in value:
            raise RuntimeError(f"Can't get object type, {self._type_key} not found")

        typ_name = value[self._type_key]

        if typ_name not in self._name_to_type_map:
            raise RuntimeError(f"Unknown type {typ_name}")

        return self._name_to_type_map[typ_name]

    def deserialize(self, value: Any, attr: Optional[str], data, **kwargs) -> Any:
        typ, field = self._validate(value)
        value = copy.copy(value)
        del value[self._type_key]

        errors = []

        try:
            result = field.deserialize(value, **kwargs)
            typeguard.check_type(attr or "anonymous", result, typ)
            return result
        except (TypeError, ValidationError) as e:
            errors.append(e)

        try:
            result = field.deserialize(value[self._value_key], **kwargs)
            typeguard.check_type(attr or "anonymous", result, typ)
            return result
        except (TypeError, ValidationError, KeyError) as e:
            errors.append(e)

        raise ValidationError(errors)


class Union(fields.Field):
    """A union field, composed other `Field` classes or instances.
    This field serializes elements based on their type, with one of its child fields.

    Example: ::

        number_or_string = UnionField([
                    (float, fields.Float()),
                    (str, fields.Str())
                ])

    :param union_fields: A list of types and their associated field instance.
    :param kwargs: The same keyword arguments that :class:`Field` receives.
    """

    def __init__(self, union_fields: List[Tuple[type, fields.Field]], **kwargs):
        kwargs = copy.deepcopy(kwargs)
        self._serialization_strategy = self.__extract_serialization_strategy(kwargs)
        super().__init__(**kwargs)
        self._serialization_strategy.set_union_fields(union_fields)
        self._serialization_strategy.set_required(self.required)
        self.union_fields = union_fields

    def __extract_serialization_strategy(self, metadata: dict):
        serialization_strategy: SerializationStrategy = FallbackSerializationStrategy()
        if SERIALIZATION_STRATEGY_KEY in metadata:
            serialization_strategy = metadata[SERIALIZATION_STRATEGY_KEY]
        return serialization_strategy

    def _bind_to_schema(self, field_name: str, schema: Schema) -> None:
        super()._bind_to_schema(field_name, schema)
        new_union_fields = []
        for typ, field in self.union_fields:
            field = copy.deepcopy(field)
            field._bind_to_schema(field_name, self)
            new_union_fields.append((typ, field))

        self.union_fields = new_union_fields

    def _serialize(self, value: Any, attr: str, obj, **kwargs) -> Any:
        return self._serialization_strategy.serialize(value, attr, obj, **kwargs)

    def _deserialize(self, value: Any, attr: Optional[str], data, **kwargs) -> Any:
        return self._serialization_strategy.deserialize(value, attr, data, **kwargs)
