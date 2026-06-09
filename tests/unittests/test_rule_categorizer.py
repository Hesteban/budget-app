"""
Unit tests for budget/rule_categorizer.py
"""
from __future__ import annotations

import pandas as pd
import pytest

from budget.rule_categorizer import Rule, categorize_description, apply_rules, RULES

class TestRule:
    def test_spotify_match_exact(self):
        r = Rule("spotify", "covered", "Spotify subscription")
        assert r.match("Spotify P42E567947")

    def test_spotify_match_plain(self):
        r = Rule("spotify", "covered", "Spotify subscription")
        assert r.match("spotify")

    def test_spotify_match_uppercase(self):
        r = Rule("spotify", "covered", "Spotify subscription")
        assert r.match("SPOTIFY")

    def test_spotify_match_embedded(self):
        r = Rule("spotify", "covered", "Spotify subscription")
        assert r.match("spotify123")
        assert r.match("myspotifylist")

    def test_case_insensitive_amazon(self):
        r = Rule("amazon", "common", "Amazon purchase")
        assert r.match("AMAZON")
        assert r.match("Amazon")
        assert r.match("amazon")
        assert r.match("WWW.AMAZON*ZQ7HH4QE5")
        assert r.match("AmazonPrime")

    def test_no_match_different_word(self):
        r = Rule("spotify", "covered", "Spotify subscription")
        assert not r.match("Netflix")
        assert not r.match("supermercado")
        assert not r.match("farmacia")


class TestCategorizeDescription:
    def test_returns_covered_for_spotify(self):
        result = categorize_description("Spotify P42E567947")
        assert result is not None
        category, reasoning = result
        assert category == "covered"
        assert "excluded from split" in reasoning

    def test_returns_common_for_amazon(self):
        result = categorize_description("WWW.AMAZON*ZQ7HH4QE5")
        assert result is not None
        category, reasoning = result
        assert category == "common"
        assert "shared household expense" in reasoning

    def test_returns_none_when_no_match(self):
        assert categorize_description("Supermercado") is None
        assert categorize_description("Farmacia") is None
        assert categorize_description("Transferencia") is None
        assert categorize_description("Recibo luz") is None


class TestApplyRules:
    def test_spotify_covered_and_reasoning_set(self):
        df = pd.DataFrame({
            "description": ["Spotify P42E567947", "Farmacia", "Amazon purchase"],
            "category": ["uncategorized"] * 3,
            "reasoning": [""] * 3,
        })
        apply_rules(df)
        assert df.at[0, "category"] == "covered"
        assert "excluded from split" in df.at[0, "reasoning"]
        assert df.at[1, "category"] == "uncategorized"
        assert df.at[1, "reasoning"] == ""
        assert df.at[2, "category"] == "common"
        assert "shared household expense" in df.at[2, "reasoning"]

    def test_all_uncategorized_when_no_rules_match(self):
        df = pd.DataFrame({
            "description": ["Supermercado", "Farmacia", "Restaurante"],
            "category": ["uncategorized"] * 3,
            "reasoning": [""] * 3,
        })
        apply_rules(df)
        assert (df["category"] == "uncategorized").all()
        assert (df["reasoning"] == "").all()

    def test_multiple_rules_same_description(self):
        df = pd.DataFrame({
            "description": ["Spotify"],
            "category": ["uncategorized"],
            "reasoning": [""],
        })
        apply_rules(df)
        assert df.at[0, "category"] == "covered"


class TestRULES:
    def test_spotify_in_rules(self):
        spotify_rules = [r for r in RULES if r.keyword == "spotify"]
        assert len(spotify_rules) == 1
        assert spotify_rules[0].category == "covered"

    def test_amazon_in_rules(self):
        amazon_rules = [r for r in RULES if r.keyword == "amazon"]
        assert len(amazon_rules) == 1
        assert amazon_rules[0].category == "common"

    def test_all_rules_have_valid_category(self):
        for rule in RULES:
            assert rule.category in ("personal", "common", "covered", "uncategorized")

    def test_all_rules_have_non_empty_reasoning(self):
        for rule in RULES:
            assert rule.reasoning != ""