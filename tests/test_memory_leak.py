import gc
import inspect
import sys
import unittest
import weakref
from dataclasses import dataclass

import marshmallow
import marshmallow_dataclass as md


class Referenceable:
    pass


class TestMemoryLeak(unittest.TestCase):
    """Test for memory leaks as decribed in `#198`_.

    .. _#198: https://github.com/lovasoa/marshmallow_dataclass/issues/198
    """

    def setUp(self):
        gc.collect()
        gc.disable()
        self.frame_collected = False

    def tearDown(self):
        gc.enable()

    def trackFrame(self):
        """Create a tracked local variable in the callers frame.

        We track these locals in the WeakSet self.livingLocals.

        When the callers frame is freed, the locals will be GCed as well.
        In this way we can check that the callers frame has been collected.
        """
        local = Referenceable()
        weakref.finalize(local, self._set_frame_collected)
        try:
            frame = inspect.currentframe()
            frame.f_back.f_locals["local_variable"] = local
        finally:
            del frame

    def _set_frame_collected(self):
        self.frame_collected = True

    def assertFrameCollected(self):
        """Check that all locals created by makeLocal have been GCed"""
        if not hasattr(sys, "getrefcount"):
            # pypy does not do reference counting
            gc.collect(0)
        self.assertTrue(self.frame_collected)

    def test_sanity(self):
        """Test that our scheme for detecting leaked frames works."""
        frames = []

        def f():
            frames.append(inspect.currentframe())
            self.trackFrame()

        f()

        gc.collect(0)
        self.assertFalse(
            self.frame_collected
        )  # with frame leaked, f's locals are still alive
        frames.clear()
        self.assertFrameCollected()

    def test_class_schema(self):
        def f():
            @dataclass
            class Foo:
                value: int

            md.class_schema(Foo)

            self.trackFrame()

        f()
        self.assertFrameCollected()

    def test_md_dataclass_lazy_schema(self):
        def f():
            @md.dataclass
            class Foo:
                value: int

            self.trackFrame()

        f()
        # NB: The "lazy" Foo.Schema attribute descriptor holds a reference to f's frame,
        # which, in turn, holds a reference to class Foo, thereby creating ref cycle.
        # So, a gc pass is required to clean that up.
        gc.collect(0)
        self.assertFrameCollected()

    def test_md_dataclass(self):
        def f():
            @md.dataclass
            class Foo:
                value: int

            self.assertIsInstance(Foo.Schema(), marshmallow.Schema)
            self.trackFrame()

        f()
        self.assertFrameCollected()
