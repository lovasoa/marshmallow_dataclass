import tempfile
import textwrap
import os
import unittest

mypy_installed = True
try:
    import mypy.api
except ImportError:
    # mypy not installed on pypy (see setup.py)
    mypy_installed = False

MYPY_INI = """\
[mypy]
follow_imports = silent
plugins = marshmallow_dataclass.mypy
"""


@unittest.skipUnless(mypy_installed, "mypy required")
class TestMypyPlugin(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        """
        Prepare a clean temporary test directory.
        Also cd into it for the duration of the test to get simple filenames in mypy output.
        """
        self.testdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.testdir)

    def tearDown(self):
        os.chdir(self.old_cwd)

    def assert_mypy_output(self, contents: str, expected: str):
        """
        Run mypy and assert output matches ``expected``.

        The file with ``contents`` is always named ``main.py``.
        """
        config_path = os.path.join(self.testdir, "mypy.ini")
        script_path = os.path.join(self.testdir, "main.py")
        with open(config_path, "w") as f:
            f.write(MYPY_INI)
        with open(script_path, "w") as f:
            f.write(textwrap.dedent(contents).strip())
        command = [script_path, "--config-file", config_path, "--no-error-summary"]
        out, err, returncode = mypy.api.run(command)
        err_msg = "\n".join(
            ["", f"returncode: {returncode}", "stdout:", out, "stderr:", err]
        )
        self.assertEqual(out.strip(), textwrap.dedent(expected).strip(), err_msg)

    def test_basic(self):
        self.assert_mypy_output(
            """
            from dataclasses import dataclass
            import marshmallow as ma
            from marshmallow_dataclass import NewType

            Email = NewType("Email", str, validate=ma.validate.Email)
            UserID = NewType("UserID", validate=ma.validate.Length(equal=32), typ=str)

            @dataclass
            class User:
                id: UserID
                email: Email

            user = User(id="a"*32, email="user@email.com")
            reveal_type(user.id)
            reveal_type(user.email)

            User(id=42, email="user@email.com")
            User(id="a"*32, email=["not", "a", "string"])
            """,
            """
            main.py:14: note: Revealed type is 'builtins.str'
            main.py:15: note: Revealed type is 'builtins.str'
            main.py:17: error: Argument "id" to "User" has incompatible type "int"; expected "str"
            main.py:18: error: Argument "email" to "User" has incompatible type "List[str]"; expected "str"
            """,
        )


if __name__ == "__main__":
    unittest.main()
