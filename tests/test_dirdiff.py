import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dirdiff  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="dirdiff-")
        self.a = os.path.join(self.root, "a")
        self.b = os.path.join(self.root, "b")
        os.makedirs(self.a)
        os.makedirs(self.b)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, base, rel, data):
        full = os.path.join(base, rel.replace("/", os.sep))
        parent = os.path.dirname(full)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)


class TestScan(Base):
    def test_relative_paths_use_slash(self):
        self.put(self.a, "x/y.txt", b"hi")
        table = dirdiff.scan(self.a, [])
        self.assertIn("x/y.txt", table)

    def test_ignore_exact_name(self):
        self.put(self.a, "keep.txt", b"1")
        self.put(self.a, "node_modules/pkg.js", b"2")
        table = dirdiff.scan(self.a, ["node_modules"])
        self.assertIn("keep.txt", table)
        self.assertNotIn("node_modules/pkg.js", table)


class TestCompare(Base):
    def test_identical(self):
        self.put(self.a, "f.txt", b"same")
        self.put(self.b, "f.txt", b"same")
        ta, tb = dirdiff.scan(self.a, []), dirdiff.scan(self.b, [])
        self.assertEqual(dirdiff.compare(ta, tb, self.a, self.b), [])

    def test_added_and_removed(self):
        self.put(self.a, "gone.txt", b"aaa")
        self.put(self.b, "new.txt", b"bbbb")
        ta, tb = dirdiff.scan(self.a, []), dirdiff.scan(self.b, [])
        diffs = {d.path: d.kind for d in dirdiff.compare(ta, tb, self.a, self.b)}
        self.assertEqual(diffs, {"gone.txt": "removed", "new.txt": "added"})

    def test_changed_same_size_differs(self):
        self.put(self.a, "f.txt", b"abcd")
        self.put(self.b, "f.txt", b"abce")
        ta, tb = dirdiff.scan(self.a, []), dirdiff.scan(self.b, [])
        diffs = dirdiff.compare(ta, tb, self.a, self.b)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].kind, "changed")

    def test_size_change_is_changed(self):
        self.put(self.a, "f.txt", b"a")
        self.put(self.b, "f.txt", b"aaaa")
        ta, tb = dirdiff.scan(self.a, []), dirdiff.scan(self.b, [])
        diffs = dirdiff.compare(ta, tb, self.a, self.b)
        self.assertEqual(diffs[0].kind, "changed")
        self.assertEqual(diffs[0].delta, 3)


class TestMain(Base):
    def test_exit_zero_when_identical(self):
        self.put(self.a, "f", b"z")
        self.put(self.b, "f", b"z")
        self.assertEqual(dirdiff.main([self.a, self.b]), 0)

    def test_exit_one_when_differs(self):
        self.put(self.a, "f", b"z")
        self.put(self.b, "f", b"zz")
        self.assertEqual(dirdiff.main([self.a, self.b]), 1)

    def test_exit_two_when_missing(self):
        missing = os.path.join(self.root, "nope")
        self.assertEqual(dirdiff.main([self.a, missing]), 2)


if __name__ == "__main__":
    unittest.main()
