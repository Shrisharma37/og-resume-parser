"""
Deterministic technical skills extractor and categorizer.
Executes sub-5ms tokenization and canonical n-gram matching.
"""

import re
from typing import Dict, List, Set
from src.parsers.skills_constants import CANONICAL_SKILL_MAP, SKILL_TAXONOMY

# Strict token delimiter supporting C++, C#, .NET, Node.js while stripping punctuation
TOKEN_CLEAN_RE = re.compile(r"[^\w+#.]+")
DELIMITER_RE = re.compile(r"[\n,;|•·/–—()\[\]]+")

# Single-character tokens requiring strict case or explicit boundary verification
STRICT_CASE_TOKENS = {"c": "C", "r": "R"}


def _tokenize_text(text: str) -> List[str]:
    """Tokenize text into cleaned words, preserving special tech symbols."""
    if not text:
        return []

    text = text.replace("’", "'").replace("–", " ").replace("—", " ")
    chunks = DELIMITER_RE.split(text)
    tokens: List[str] = []
    for chunk in chunks:
        for match in re.findall(r"[A-Za-z0-9][A-Za-z0-9+#.]*", chunk):
            cleaned = TOKEN_CLEAN_RE.sub("", match).strip(".")
            if cleaned:
                tokens.append(cleaned)
    return tokens


def extract_skills(text: str) -> Dict[str, List[str]]:
    """
    Extract, normalize, and categorize technical skills from resume text.
    Returns:
        Categorized dictionary matching SKILL_TAXONOMY with an additional 'other' bucket.
    """
    if not text:
        return {cat: [] for cat in list(SKILL_TAXONOMY.keys()) + ["other"]}

    tokens = _tokenize_text(text)
    n = len(tokens)
    matched_canonical: Set[str] = set()
    consumed_indices: Set[int] = set()

    # Step 1: Check Trigrams (e.g., "Google Cloud Platform", "Amazon Web Services")
    for i in range(n - 2):
        phrase = f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}".lower()
        if phrase in CANONICAL_SKILL_MAP:
            matched_canonical.add(CANONICAL_SKILL_MAP[phrase])
            consumed_indices.update({i, i + 1, i + 2})

    # Step 2: Check Bigrams (e.g., "Spring Boot", "GitHub Actions")
    for i in range(n - 1):
        if i in consumed_indices or (i + 1) in consumed_indices:
            continue
        phrase = f"{tokens[i]} {tokens[i+1]}".lower()
        if phrase in CANONICAL_SKILL_MAP:
            matched_canonical.add(CANONICAL_SKILL_MAP[phrase])
            consumed_indices.update({i, i + 1})

    # Step 3: Check Unigrams (e.g., "Python", "K8s", "C++", strict "C")
    for i in range(n):
        if i in consumed_indices:
            continue
        token = tokens[i]
        token_lower = token.lower()

        # Handle sensitive single-char tokens (avoid matching 'a', 'i', or lowercase 'c'/'r' in prose)
        if token_lower in STRICT_CASE_TOKENS:
            if token == STRICT_CASE_TOKENS[token_lower]:
                matched_canonical.add(CANONICAL_SKILL_MAP[token_lower])
            continue

        if token_lower in CANONICAL_SKILL_MAP:
            matched_canonical.add(CANONICAL_SKILL_MAP[token_lower])

    # Step 4: Map Canonical Matches to Categories
    categorized: Dict[str, List[str]] = {cat: [] for cat in SKILL_TAXONOMY.keys()}
    categorized["other"] = []

    for skill in matched_canonical:
        assigned = False
        for category, skill_set in SKILL_TAXONOMY.items():
            if skill in skill_set:
                categorized[category].append(skill)
                assigned = True
                break
        if not assigned:
            categorized["other"].append(skill)

    # Sort deterministically for idempotent output
    for cat in categorized:
        categorized[cat].sort()

    return categorized