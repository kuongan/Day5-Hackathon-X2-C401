import importlib.util
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "backend" / "agent" / "chat-agent" / "tools.py"
spec = importlib.util.spec_from_file_location("chat_agent_tools", MODULE_PATH)
assert spec is not None and spec.loader is not None
chat_agent_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chat_agent_tools)


class RetrieveDiseaseInfoToolTest(unittest.TestCase):
    def test_returns_warning_when_database_is_missing(self):
        missing_db = Path(self._testMethodName)
        original_db_path = chat_agent_tools.DB_PATH
        chat_agent_tools.DB_PATH = missing_db
        try:
            payload = json.loads(chat_agent_tools.retrieve_disease_info.invoke({"query": "sot xuat huyet", "top_k": 1}))
        finally:
            chat_agent_tools.DB_PATH = original_db_path

        self.assertEqual(payload["query"], "sot xuat huyet")
        self.assertEqual(payload["total_hits"], 0)
        self.assertEqual(payload["articles"], [])
        self.assertIn("Database not found", payload["warning"])


if __name__ == "__main__":
    unittest.main()
