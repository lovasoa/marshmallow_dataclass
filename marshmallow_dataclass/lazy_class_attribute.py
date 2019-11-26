from typing import Any, Callable


__all__ = ("lazy_class_attribute",)


# todo: could be moved to separate library
class LazyClassAttribute:
    """Descriptor decorator implementing a class-level, read-only
    property, which caches its results on the class(es) on which it
    operates.
    """

    __slots__ = ("func", "name", "called")

    def __init__(self, func: Callable[[type], Any], name: str = None):
        self.func = func
        self.name = name
        self.called = False

    def __get__(self, instance, cls=None):
        if not cls:
            cls = type(instance)

        # avoid recursion when get_type_hints is called on the class
        if self.called:
            return

        self.called = True

        setattr(cls, self.name, self.func(cls))

        # "getattr" is used to handle bounded methods
        return getattr(cls, self.name)

    def __set_name__(self, owner, name):
        self.name = self.name or name


lazy_class_attribute = LazyClassAttribute
