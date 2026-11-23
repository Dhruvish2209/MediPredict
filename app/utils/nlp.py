"""
Free-text -> canonical symptoms.

Pipeline
  1. normalise text, split into clauses
  2. longest-phrase-first regex matching (word boundaries, optional plural) against
     the synonym dictionary + humanised canonical names
  3. negation detection  ("no fever", "without cough or headache", "don't have chills")
  4. typo-tolerant fallback (difflib) for single words
  5. duration extraction ("for 3 days")
"""
import re
from difflib import get_close_matches
from functools import lru_cache

from app.utils.synonyms import SYNONYMS

NEGATIONS = (
    r"no", r"not", r"without", r"never", r"denies", r"denied", r"don t", r"dont", r"doesn t", r"doesnt",
    r"didn t", r"didnt", r"haven t", r"havent", r"hasn t", r"hasnt", r"free of", r"free from",
    r"absence of", r"negative for", r"no sign of", r"no signs of", r"nothing like", r"zero",
)
_NEG_RE = re.compile(r"\b(?:" + "|".join(NEGATIONS) + r")\b")
_CLAUSE_SPLIT = re.compile(r"[.;,!?\n]| but | however | although | though | except | yet ")
_STOP = {"having", "feeling", "since", "really", "about", "there", "which", "would", "could", "start",
         "started", "little", "very", "much", "again", "after", "before", "past", "today", "yesterday",
         "severe", "mild", "slight", "bad", "terrible", "constant", "sometimes", "often", "morning",
         "night", "evening", "recently", "quite", "other", "since", "while", "think", "doctor", "pain"}

_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "couple": 2, "few": 3}
_DUR_RE = re.compile(
    r"\b(?:for|since|over|past|last|from)\s+(?:the\s+)?(?:(?:past|last)\s+)?"
    r"(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|couple of|few)\s*"
    r"(hour|day|week|month|year)s?\b")


def normalize(text: str) -> str:
    """Lowercase, drop apostrophes, keep clause punctuation, collapse whitespace."""
    text = text.lower().replace("’", "'").replace("'", " ")
    text = re.sub(r"[^\w\s.;,!?\n]", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _humanise(canonical: str) -> str:
    s = canonical.replace("_", " ")
    s = re.sub(r"[()]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=8)
def _phrase_table(canonical: tuple) -> list:
    """[(phrase, compiled_regex, [canonical symptoms])] longest phrase first."""
    cset = set(canonical)
    table = {}
    for phrase, cands in SYNONYMS.items():
        valid = [c for c in cands if c in cset]
        if valid:
            table[phrase] = valid
    for c in canonical:                      # exact canonical names ("loss of smell")
        h = _humanise(c)
        table.setdefault(h, [c])
    out = []
    for phrase in sorted(table, key=len, reverse=True):
        rx = re.compile(r"\b" + re.escape(phrase) + r"s?\b")
        out.append((phrase, rx, table[phrase]))
    return out


@lru_cache(maxsize=8)
def _fuzzy_keys(canonical: tuple) -> list:
    keys = [k for k in SYNONYMS if " " not in k and len(k) >= 5]
    keys += [_humanise(c) for c in canonical if " " not in _humanise(c) and len(c) >= 5]
    return sorted(set(keys))


def _is_negated(clause: str, start: int) -> bool:
    """A symptom is negated if a negation cue precedes it in the clause within a short window."""
    before = clause[:start]
    m = None
    for m in _NEG_RE.finditer(before):
        pass
    if not m:
        return False
    between = before[m.end():].split()
    # the cue must be close (<=5 words); contrasts like "no cough but fever" are split into clauses earlier
    return len(between) <= 5


def analyze_text(text: str, canonical_symptoms) -> dict:
    """Full analysis. Returns dict(found, negated, evidence, duration)."""
    result = {"found": [], "negated": [], "evidence": {}, "duration": None}
    if not text or not text.strip():
        return result

    canonical = tuple(canonical_symptoms)
    table = _phrase_table(canonical)
    norm = normalize(text)

    dm = _DUR_RE.search(norm)
    if dm:
        n = dm.group(1)
        n = _NUM.get(n.replace(" of", ""), n)
        unit = dm.group(2)
        result["duration"] = f"{n} {unit}{'s' if str(n) != '1' else ''}"

    found, negated, evidence = set(), set(), {}
    consumed_words = set()

    for clause in _CLAUSE_SPLIT.split(norm):
        clause = clause.strip()
        if not clause:
            continue
        used = []  # spans already claimed by a longer phrase
        for phrase, rx, cands in table:
            for m in rx.finditer(clause):
                if any(m.start() < e and m.end() > s for s, e in used):
                    continue
                used.append((m.start(), m.end()))
                consumed_words.update(re.findall(r"\w+", phrase))
                if _is_negated(clause, m.start()):
                    negated.update(cands)
                else:
                    found.update(cands)
                    for c in cands:
                        evidence.setdefault(c, phrase)

        # typo-tolerant fallback for single words not already explained by a phrase
        keys = _fuzzy_keys(canonical)
        for sm in re.finditer(r"\b[a-z]{5,}\b", clause):
            w = sm.group(0)
            if w in consumed_words or w in _STOP or any(s <= sm.start() < e for s, e in used):
                continue
            hit = get_close_matches(w, keys, n=1, cutoff=0.85 if len(w) <= 6 else 0.8)
            if hit:
                cands = [c for c in SYNONYMS.get(hit[0], []) if c in canonical] or \
                        [c for c in canonical if _humanise(c) == hit[0]]
                if _is_negated(clause, sm.start()):
                    negated.update(cands)
                else:
                    found.update(cands)
                    for c in cands:
                        evidence.setdefault(c, f"{w} (≈{hit[0]})")

    negated -= found
    result.update(found=sorted(found), negated=sorted(negated), evidence=evidence)
    return result


def extract_symptoms(text: str, canonical_symptoms: list) -> list:
    """Backwards-compatible helper: just the list of found symptoms."""
    return analyze_text(text, canonical_symptoms)["found"]
