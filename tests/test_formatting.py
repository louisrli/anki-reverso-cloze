from formatting import strip_punctuation
import unittest

class TestFormatting(unittest.TestCase):

    def test_preserves_apostrophe(self):
        before = "foo'bar"
        self.assertEqual(strip_punctuation(before), "foo'bar")

    def test_strips_punct(self):
        before = "!foo#ba,r"
        self.assertEqual(strip_punctuation(before), "foobar")

    def test_strips_punct_with_apostr(self):
        before = "!foo#'ba,r"
        self.assertEqual(strip_punctuation(before), "foo'bar")


if __name__ == '__main__':
    unittest.main()

