"""main 主流程的离线集成测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

import main


class MainTests(unittest.TestCase):
    @patch("main._print_analysis")
    @patch("main._print_email")
    @patch("main.analyze_email")
    @patch("main.parse_email")
    @patch("main.fetch_recent_emails")
    @patch("main.load_config")
    def test_main_analyzes_only_first_successful_email(
        self,
        mock_load_config: object,
        mock_fetch: object,
        mock_parse: object,
        mock_analyze: object,
        mock_print_email: object,
        mock_print_analysis: object,
    ) -> None:
        config = object()
        messages = [object(), object()]
        first = {"uid": "1", "body": "第一封"}
        second = {"uid": "2", "body": "第二封"}
        analysis = {
            "summary": "摘要",
            "category": "其他",
            "importance": "低",
            "todos": [],
            "deadline": None,
        }
        mock_load_config.return_value = config  # type: ignore[attr-defined]
        mock_fetch.return_value = messages  # type: ignore[attr-defined]
        mock_parse.side_effect = [first, second]  # type: ignore[attr-defined]
        mock_analyze.return_value = analysis  # type: ignore[attr-defined]

        self.assertEqual(main.main(), 0)
        mock_analyze.assert_called_once_with(first, config)  # type: ignore[attr-defined]
        mock_print_analysis.assert_called_once_with(analysis)  # type: ignore[attr-defined]
        self.assertEqual(mock_print_email.call_count, 2)  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
