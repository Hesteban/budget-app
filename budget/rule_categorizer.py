"""
Rule-based transaction categorizer.

Keywords are matched case-insensitively as substrings wrapped in ".*...keyword...*".
Add new rules to the RULES list below.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

ValidCategory = Literal["personal", "common", "covered", "uncategorized"]

@dataclass
class Rule:
    keyword: str
    category: ValidCategory
    reasoning: str

    def match(self, description: str) -> bool:
        pattern = f".*{re.escape(self.keyword)}.*"
        return bool(re.search(pattern, description, re.IGNORECASE))

RULES: list[Rule] = [
    Rule("spotify",          "covered",  "Spotify subscription — excluded from split"),
    Rule("netflix",          "covered",  "Netflix subscription — excluded from split"),
    Rule("amazon",           "common",   "Amazon purchase — shared household expense"),
    Rule("mercadona",        "common",   "Supermarket — shared household expense"),
    Rule("aldi",             "common",   "Supermarket — shared household expense"),
    Rule("dia",              "common",   "Supermarket — shared household expense"),
    Rule("repsol",           "common",   "Fuel — shared household expense"),
    Rule("canal de",         "common",   "Water utility — shared household expense"),
    Rule("pepe energy",      "common",   "Electricity — shared household expense"),
    Rule("casa de ninos",    "common",   "Kindergarten — shared household expense"),
    Rule("carlos rigagorda", "personal", "Hairdresser — personal expense"),
]

def categorize_description(description: str) -> tuple[ValidCategory, str] | None:
    for rule in RULES:
        if rule.match(description):
            return rule.category, rule.reasoning
    return None

def apply_rules(df):
    for i, desc in enumerate(df["description"]):
        result = categorize_description(desc)
        if result:
            df.at[i, "category"] = result[0]
            df.at[i, "reasoning"] = result[1]
    return df