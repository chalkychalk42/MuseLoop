"""Tests for graph routing functions."""

from __future__ import annotations

from museloop.core.graph import after_critic, after_director, should_research


class TestShouldResearch:
    def test_first_iteration_always_researches(self):
        state = {"iteration": 1, "memory": {}}
        assert should_research(state) == "research"

    def test_second_iteration_with_empty_memory_researches(self):
        state = {"iteration": 2, "memory": {}}
        assert should_research(state) == "research"

    def test_second_iteration_with_full_memory_skips(self):
        state = {
            "iteration": 2,
            "memory": {
                "style_keywords": ["neon", "dark"],
                "recommendations": ["Use high contrast"],
            },
        }
        assert should_research(state) == "script"

    def test_partial_memory_still_researches(self):
        state = {
            "iteration": 2,
            "memory": {"style_keywords": ["neon"]},
        }
        assert should_research(state) == "research"

    def test_missing_memory_key(self):
        state = {"iteration": 3}
        assert should_research(state) == "research"


class TestAfterDirector:
    def test_has_assets_goes_to_critic(self):
        state = {"assets": [{"type": "image"}], "director_retries": 0}
        assert after_director(state) == "critic"

    def test_no_assets_zero_retries_goes_to_critic(self):
        """retries=0 means director hasn't failed yet; no retry."""
        state = {"assets": [], "director_retries": 0}
        assert after_director(state) == "critic"

    def test_no_assets_first_failure_retries(self):
        """retries=1 means first attempt failed; retry once."""
        state = {"assets": [], "director_retries": 1}
        assert after_director(state) == "director"

    def test_no_assets_second_failure_goes_to_critic(self):
        """retries=2 means already retried; give up."""
        state = {"assets": [], "director_retries": 2}
        assert after_director(state) == "critic"

    def test_missing_retries_defaults_to_critic(self):
        """Missing retries defaults to 0; no retry."""
        state = {"assets": []}
        assert after_director(state) == "critic"


class TestAfterCritic:
    def test_high_score_goes_to_end(self):
        state = {"critique": {"score": 0.95}, "human_approval": None}
        assert after_critic(state) == "__end__"

    def test_low_score_goes_to_end(self):
        state = {"critique": {"score": 0.3}, "human_approval": None}
        assert after_critic(state) == "__end__"

    def test_borderline_score_goes_to_approval(self):
        state = {"critique": {"score": 0.75}, "human_approval": None}
        assert after_critic(state) == "human_approval"

    def test_already_approved_goes_to_end(self):
        state = {
            "critique": {"score": 0.75},
            "human_approval": {"approved": True},
        }
        assert after_critic(state) == "__end__"

    def test_missing_critique_goes_to_end(self):
        state = {"human_approval": None}
        assert after_critic(state) == "__end__"
