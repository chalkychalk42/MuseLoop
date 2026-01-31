"""Tests for BaseAgent JSON parsing."""

from __future__ import annotations

import json

import pytest

from museloop.agents.base import BaseAgent


class TestParseJsonResponse:
    """Test the static _parse_json_response method."""

    def test_direct_json(self):
        data = {"score": 0.8, "pass": True}
        result = BaseAgent._parse_json_response(json.dumps(data))
        assert result == data

    def test_json_in_code_fence(self):
        text = '```json\n{"score": 0.8, "pass": true}\n```'
        result = BaseAgent._parse_json_response(text)
        assert result["score"] == 0.8

    def test_json_in_bare_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = BaseAgent._parse_json_response(text)
        assert result["key"] == "value"

    def test_json_with_surrounding_text(self):
        text = 'Here is my evaluation:\n{"score": 0.5, "feedback": "ok"}\nThat is all.'
        result = BaseAgent._parse_json_response(text)
        assert result["score"] == 0.5

    def test_nested_json(self):
        data = {"outer": {"inner": [1, 2, 3]}, "flag": True}
        result = BaseAgent._parse_json_response(json.dumps(data))
        assert result["outer"]["inner"] == [1, 2, 3]

    def test_json_with_whitespace(self):
        text = '\n\n  {"key": "value"}  \n\n'
        result = BaseAgent._parse_json_response(text)
        assert result["key"] == "value"

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            BaseAgent._parse_json_response("this is not json at all")

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            BaseAgent._parse_json_response("")

    def test_json_array_not_object(self):
        # Arrays parse fine — they're valid JSON
        text = '[{"a": 1}, {"b": 2}]'
        result = BaseAgent._parse_json_response(text)
        assert len(result) == 2

    def test_fence_with_leading_explanation(self):
        text = (
            "I've analyzed the assets. Here's my evaluation:\n\n"
            '```json\n{"score": 0.75, "pass": true, "feedback": "Good work"}\n```\n\n'
            "Let me know if you need more details."
        )
        result = BaseAgent._parse_json_response(text)
        assert result["score"] == 0.75
        assert result["pass"] is True
