import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import CONFIG
from core.mcp_client import call_tool, get_tools

SERVER = str(Path(__file__).resolve().parent.parent / "core" / "mcp_server.py")
EXTERNAL = {"mcp": {"command": sys.executable, "args": [SERVER]}}
DOCS = Path(__file__).resolve().parent.parent / "knowledge" / "documents"
THIRD_PARTY = {"mcp": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", str(DOCS)]}}


class ExternalServer(unittest.TestCase):
    @patch.dict(CONFIG, EXTERNAL)
    def test_lists_its_tools(self):
        names = [tool["function"]["name"] for tool in get_tools()]
        self.assertIn("web_search", names)

    @patch.dict(CONFIG, EXTERNAL)
    def test_calls_an_existing_tool(self):
        # without the key web_search fails before any network call: the error proves the round trip
        with patch.dict(os.environ):
            os.environ.pop("LANGSEARCH_API_KEY", None)
            with self.assertRaisesRegex(RuntimeError, "LANGSEARCH_API_KEY is not set"):
                call_tool("web_search", {"query": "test"})

    @patch.dict(CONFIG, {"mcp": {"command": "no-such-mcp-server", "args": []}})
    def test_configured_command_is_the_one_started(self):
        with self.assertRaises(Exception):
            get_tools()


@unittest.skipUnless(shutil.which("npx"), "npx is not installed")
class ThirdPartyServer(unittest.TestCase):
    @patch.dict(CONFIG, THIRD_PARTY)
    def test_lists_its_tools(self):
        names = [tool["function"]["name"] for tool in get_tools()]
        self.assertIn("list_directory", names)

    @patch.dict(CONFIG, THIRD_PARTY)
    def test_calls_a_tool(self):
        self.assertIn("sensia_guide.md", call_tool("list_directory", {"path": str(DOCS)}))

    @patch.dict(CONFIG, THIRD_PARTY)
    def test_tool_error_is_raised(self):
        with self.assertRaisesRegex(RuntimeError, "(?i)access denied"):
            call_tool("list_directory", {"path": str(DOCS.parent.parent)})


if __name__ == "__main__":
    unittest.main()
