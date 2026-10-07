import unittest

from tools.internet_search import internet_search


class InternetSearchTest(unittest.TestCase):
    def test_api_returns_results(self):
        results = internet_search("latest Python release")

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn("name", results[0])
        self.assertIn("url", results[0])


if __name__ == "__main__":
    unittest.main()
