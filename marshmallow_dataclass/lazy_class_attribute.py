import threading
from typing import Callable, Generic, Optional, TypeVar


__all__ = ("lazy_class_attribute",)


_T_co = TypeVar("_T_co", covariant=True)


class LazyClassAttribute(Generic[_T_co]):
    """Descriptor implementing a cached class property."""

    __slots__ = ("fget", "attr_name", "rlock", "called_from")

    def __init__(self, fget: Callable[[], _T_co], attr_name: str):
        self.fget = fget
        self.attr_name = attr_name
        self.rlock = threading.RLock()
        self.called_from: Optional[threading.Thread] = None

    def __get__(self, instance: object, cls: Optional[type] = None) -> _T_co:
        if not cls:
            cls = type(instance)

        with self.rlock:
            if self.called_from is not None:
                if self.called_from is not threading.current_thread():
                    return getattr(cls, self.attr_name)  # type: ignore[no-any-return]
                raise AttributeError(
                    f"recursive evaluation of {cls.__name__}.{self.attr_name}"
                )
            self.called_from = threading.current_thread()
            value = self.fget()
            setattr(cls, self.attr_name, value)
            return value


lazy_class_attribute = LazyClassAttribute
