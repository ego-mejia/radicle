"""The usage guide Radi answers from: markdown sections searched with BM25, no LLM needed."""

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path

GUIDE_DIR = Path(__file__).parent / "guide"
LANGUAGES = ("en", "es")
STOPWORDS = frozenset(
    """a an and are as at be by can do does for from how i in is it me my of on or the to
    what when where which who why with you your el la los las un una unos unas y o de del
    al en es son como que para por con se mi mis me lo le les su sus hay hacer puedo""".split()
)


@dataclass(frozen=True)
class Section:
    title: str
    body: str
    key: str | None  # from `## Title {#key}`, the same in every language
    terms: Counter[str]
    title_terms: frozenset[str]


def _fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in plain if not unicodedata.combining(c))


SUFFIXES = (
    "amos", "emos", "imos", "ando", "iendo", "ado", "ido", "ing", "ed",
    "ar", "er", "ir", "es", "as", "os", "s", "e", "o", "a",
)  # fmt: skip


def stem(word: str) -> str:
    """Crude bilingual stem: crear, creo, creó, create and created all give 'cre'/'creat'."""
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def terms(text: str) -> list[str]:
    """Lowercase stems without accents or stopwords, so English and Spanish both match."""
    return [
        stem(word)
        for word in re.findall(r"[a-z0-9]+", _fold(text))
        if len(word) >= 2 and word not in STOPWORDS
    ]


@cache
def sections(lang: str) -> tuple[Section, ...]:
    text = (GUIDE_DIR / f"{lang if lang in LANGUAGES else 'en'}.md").read_text(encoding="utf-8")
    out = []
    for chunk in re.split(r"^## ", text, flags=re.M):
        if not chunk.strip():
            continue
        heading, _, body = chunk.partition("\n")
        match = re.match(r"(.*?)\s*\{#([a-z-]+)\}\s*$", heading)
        title, key = (match[1], match[2]) if match else (heading, None)
        out.append(
            Section(
                title.strip(),
                body.strip(),
                key,
                Counter(terms(f"{title} {body}")),
                frozenset(terms(title)),
            )
        )
    return tuple(out)


def search(query: str, lang: str = "en", limit: int = 3) -> list[Section]:
    """The sections that best answer `query`, best first; none when nothing matches.
    Weak matches (under 40% of the best score) are left out."""
    docs = sections(lang)
    wanted = set(terms(query))
    if not wanted:
        return []
    n = len(docs)
    avg = sum(sum(d.terms.values()) for d in docs) / n
    scored = []
    for doc in docs:
        length = sum(doc.terms.values())
        score = 0.0
        for term in wanted:
            tf = doc.terms.get(term, 0)
            if not tf:
                continue
            df = sum(1 for d in docs if term in d.terms)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / avg))
            if term in doc.title_terms:  # the title says what the section is about
                score += idf * 3
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    best = scored[0][0] if scored else 0
    return [doc for score, doc in scored[:limit] if score >= 0.4 * best]


def contents(lang: str = "en") -> list[str]:
    return [s.title for s in sections(lang)]
