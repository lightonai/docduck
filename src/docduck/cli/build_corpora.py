#!/usr/bin/env python3
"""Build serialized Markov chain models from text you supply.

docduck ships one public-domain model, ``en_literature``, and falls back to a
small template grammar when no model exists for a language. Build extra models
from text you have the right to use: a local file, a directory of text files,
or a Hugging Face dataset. Models are written to the package corpora directory
(``src/docduck/corpora``) unless ``--out`` points elsewhere, so the text
generator picks them up on the next run.

Usage:
    docduck-corpora --name en_legal --lang en --input ./corpus/legal/
    docduck-corpora --name fr --lang fr --input french.txt
    docduck-corpora --name fr --lang fr \\
        --hf-dataset my-org/my-corpus:train:text
    docduck-corpora --list
"""

import argparse
import os
import re

import markovify

# Models load from ``src/docduck/corpora``; write there by default so
# `docduck-corpora` and the text generator agree on one directory.
CORPORA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "corpora",
)
STATE_SIZE = 2

# Min/max sentence length (chars) to keep when harvesting text.
MIN_SENTENCE_LEN = 20
MAX_SENTENCE_LEN = 300

# For non-Latin-script languages, the minimum fraction of letters in a
# candidate sentence that must belong to the target script. Below this a
# sentence is treated as foreign-language pollution (for example pure-English
# bibliographic entries in a Chinese text) and dropped. 0.5 keeps sentences
# that are mostly target-script with some mixed-in Latin (technical terms,
# loanwords, names).
SCRIPT_THRESHOLD = 0.5

# Unicode ranges per script. Union of BMP ranges that cover everyday text in
# the target writing system; CJK pairs include common punctuation-adjacent
# regions so sentence ratios are computed on the expected letter set.
_SCRIPT_RANGES = {
    "arabic": [
        (0x0600, 0x06FF),  # Arabic
        (0x0750, 0x077F),  # Arabic Supplement
        (0x08A0, 0x08FF),  # Arabic Extended-A
        (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    ],
    "han": [
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs
        (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    ],
    # Japanese: Han + Hiragana + Katakana. Native Japanese is typically a
    # mix of all three; threshold applies to the union.
    "han_kana": [
        (0x4E00, 0x9FFF),
        (0x3400, 0x4DBF),
        (0x3040, 0x309F),  # Hiragana
        (0x30A0, 0x30FF),  # Katakana
    ],
    # Korean: Hangul syllables + Jamo, occasional Hanja.
    "hangul": [
        (0xAC00, 0xD7AF),  # Hangul Syllables
        (0x1100, 0x11FF),  # Hangul Jamo
        (0x3130, 0x318F),  # Hangul Compatibility Jamo
        (0x4E00, 0x9FFF),  # Hanja
    ],
    "devanagari": [(0x0900, 0x097F)],
    "thai": [(0x0E00, 0x0E7F)],
    "cyrillic": [
        (0x0400, 0x04FF),  # Cyrillic
        (0x0500, 0x052F),  # Cyrillic Supplement
    ],
    "hebrew": [
        (0x0590, 0x05FF),  # Hebrew
        (0xFB1D, 0xFB4F),  # Hebrew Presentation Forms
    ],
}

# Lang code to script family. Latin-script langs (fr/de/es/...) are omitted
# since cross-contamination there is within-script drift, not a different
# writing system: not worth filtering out.
LANG_SCRIPTS = {
    "ar": "arabic",
    "zh": "han",
    "ja": "han_kana",
    "ko": "hangul",
    "hi": "devanagari",
    "th": "thai",
    "ru": "cyrillic",
    "uk": "cyrillic",
    "he": "hebrew",
}

TEXT_SUFFIXES = (".txt", ".md", ".text")


def _in_script(ch: str, script: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _SCRIPT_RANGES[script])


def script_ratio(text: str, script: str) -> float:
    """Fraction of alphabetic chars in `text` that belong to `script`.

    Whitespace, punctuation, digits are ignored: only letters count toward
    both numerator and denominator. Returns 0.0 on empty or punctuation-only
    input. Exposed for tests and for runtime filtering in `text_gen`.
    """
    if not text:
        return 0.0
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    in_script = sum(1 for c in letters if _in_script(c, script))
    return in_script / len(letters)


def clean_text(text: str, lang: str | None = None) -> list[str]:
    """Split raw text into length-bounded sentences.

    For non-Latin-script languages, also drops sentences whose primary script
    falls below SCRIPT_THRESHOLD, which rejects foreign-language pollution
    that would otherwise leak into the Markov chain.
    """
    text = re.sub(r"==+.*?==+", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\s+", " ", text)

    # Split on sentence-ending punctuation (works for most scripts).
    # For CJK, also split on 。！？
    sentences = re.split(r"(?<=[.!?。！？])\s+", text)

    target_script = LANG_SCRIPTS.get(lang) if lang else None
    cleaned = []
    for s in sentences:
        s = s.strip()
        if not (MIN_SENTENCE_LEN <= len(s) <= MAX_SENTENCE_LEN):
            continue
        if target_script and script_ratio(s, target_script) < SCRIPT_THRESHOLD:
            continue
        cleaned.append(s)
    return cleaned


def _iter_text_files(path: str):
    """Yield text file paths from a file or a directory tree."""
    if os.path.isfile(path):
        yield path
        return
    for root, _dirs, files in os.walk(path):
        for name in sorted(files):
            if name.lower().endswith(TEXT_SUFFIXES):
                yield os.path.join(root, name)


def sentences_from_path(path: str, lang: str | None = None) -> list[str]:
    """Read one file or a directory of text files into cleaned sentences."""
    sentences: list[str] = []
    seen: set[str] = set()
    for fp in _iter_text_files(path):
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for s in clean_text(f.read(), lang=lang):
                if s not in seen:
                    seen.add(s)
                    sentences.append(s)
    return sentences


def sentences_from_hf(spec: str, lang: str | None = None) -> list[str]:
    """Harvest sentences from a Hugging Face dataset spec.

    Spec format matches ``docduck --hf-dataset``:
    ``dataset_id[:config[:split[:column]]]``.
    """
    from ..generators.text.sources.hf import HFSource

    sentences = HFSource.from_spec(spec)._sentences
    target_script = LANG_SCRIPTS.get(lang) if lang else None
    if not target_script:
        return sentences
    return [s for s in sentences if script_ratio(s, target_script) >= SCRIPT_THRESHOLD]


# ---------------------------------------------------------------------------
# Model building
# ---------------------------------------------------------------------------


def build_model(sentences: list[str]) -> markovify.NewlineText:
    """Build a Markov model from a list of sentence strings."""
    return markovify.NewlineText("\n".join(sentences), state_size=STATE_SIZE)


def save_model(model: markovify.NewlineText, name: str, out_dir: str = CORPORA_DIR) -> float:
    """Serialize a model to JSON and return the size in KB."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.json")
    with open(path, "w") as f:
        f.write(model.to_json())
    return os.path.getsize(path) / 1024


def available_models(out_dir: str = CORPORA_DIR) -> list[str]:
    """Names of models already present in `out_dir`."""
    if not os.path.isdir(out_dir):
        return []
    return sorted(f.removesuffix(".json") for f in os.listdir(out_dir) if f.endswith(".json"))


def build_corpus(
    name: str,
    path: str | None = None,
    hf_dataset: str | None = None,
    lang: str | None = None,
    out_dir: str = CORPORA_DIR,
    min_sentences: int = 50,
) -> bool:
    """Build one model named `name` from a local path or HF dataset spec."""
    if bool(path) == bool(hf_dataset):
        raise ValueError("provide exactly one of path or hf_dataset")

    if path:
        sentences = sentences_from_path(path, lang=lang)
    else:
        sentences = sentences_from_hf(hf_dataset, lang=lang)

    if len(sentences) < min_sentences:
        print(f"  {name}: SKIP (only {len(sentences)} sentences, need {min_sentences})")
        return False

    size = save_model(build_model(sentences), name, out_dir=out_dir)
    print(f"  {name}: {len(sentences)} sentences, {size:.0f} KB")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docduck-corpora",
        description=("Build Markov text models for docduck from text you supply."),
    )
    parser.add_argument("--name", help="Model name to write (e.g. en_legal, fr).")
    parser.add_argument(
        "--input",
        help="A text file or a directory of .txt/.md files to build from.",
    )
    parser.add_argument(
        "--hf-dataset",
        metavar="SPEC",
        help="Hugging Face dataset to build from, "
        "'dataset_id[:config[:split[:column]]]'. Needs the [hf] extra.",
    )
    parser.add_argument(
        "--lang",
        help="ISO 639-1 code for the model. Enables the script filter for "
        "non-Latin scripts (see LANG_SCRIPTS).",
    )
    parser.add_argument(
        "--out",
        default=CORPORA_DIR,
        help=f"Output directory for the model JSON (default: {CORPORA_DIR}).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the models available in --out and exit.",
    )
    args = parser.parse_args(argv)

    if args.list:
        models = available_models(args.out)
        print("\n".join(models) if models else "(no models)")
        return 0

    if not args.name or (not args.input and not args.hf_dataset):
        parser.print_help()
        return 1

    print(f"Building {args.name} -> {args.out}")
    ok = build_corpus(
        args.name,
        path=args.input,
        hf_dataset=args.hf_dataset,
        lang=args.lang,
        out_dir=args.out,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
