import unittest

from tools.internet_search import internet_search


class InternetSearchTest(unittest.TestCase):
    def test_api_returns_results(self):
        results = internet_search("donne moi du code python pour faire du visuel web")

        self.assertIsInstance(results, str)
        self.assertGreater(len(results), 0)


if __name__ == "__main__":
    unittest.main()
