from api_helpers import make_cloze
import unittest

class TestApiHelpers(unittest.TestCase):

    def test_make_cloze_one_term(self):
        before = "foo'bar"
        expected = ""
        self.assertEqual(make_cloze(before), expected)

    def test_make_cloze_two_term(self):
        before = "foo'bar"
        expected = ""
        self.assertEqual(make_cloze(before), expected)

if __name__ == '__main__':
    unittest.main()

