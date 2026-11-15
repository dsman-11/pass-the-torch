"""Explicit aliases only; suffixes on unrelated courses remain significant."""
COURSE_ALIASES = {"CSCI455": "CSCI455X"}


def canonical(code):
    return COURSE_ALIASES.get(code, code)
