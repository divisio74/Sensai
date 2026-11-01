import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

# by path: for the test runner, `main` is tests/main.py
_spec = importlib.util.spec_from_file_location("sensia_main", Path(__file__).resolve().parent.parent / "main.py")
main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(main)

FAST_CALL = {"function": {"name": "fast", "arguments": {"seconds": 40, "task": "reverse a string"}}}
REPLIES = [("", [FAST_CALL]), ("Done.", [])]


def send(answer, persona="dev", replies=REPLIES):
    with patch.object(main, "chat_with_tools", side_effect=list(replies)) as chat, \
            patch("builtins.input", return_value=answer), \
            patch.object(main, "run_fast", return_value=None) as run:
        main.u_send_message_a("hello", [{"role": "system", "content": ""}], "model", "url", persona)
    return chat, run


class ModelRequestsFast(unittest.TestCase):
    def test_runs_after_yes(self):
        _, run = send("y")
        run.assert_called_once_with("reverse a string", 40.0, "model", "url", "dev")

    def test_never_runs_without_yes(self):
        _, run = send("n")
        run.assert_not_called()

    def test_invalid_arguments_do_not_run(self):
        bad = {"function": {"name": "fast", "arguments": {"seconds": "soon", "task": "x"}}}
        _, run = send("y", replies=[("", [bad]), ("Done.", [])])
        run.assert_not_called()

    def test_only_one_run_per_message(self):
        _, run = send("y", replies=[("", [FAST_CALL]), ("", [FAST_CALL]), ("Done.", [])])
        self.assertEqual(run.call_count, 1)

    def test_tool_is_only_offered_to_the_dev_persona(self):
        names = lambda chat: [t["function"]["name"] for t in chat.call_args_list[0].args[3]]
        self.assertIn("fast", names(send("n")[0]))
        self.assertNotIn("fast", names(send("n", persona="sensia", replies=[("Hi.", [])])[0]))


if __name__ == "__main__":
    unittest.main()
