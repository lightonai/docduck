"""Proper-noun probes: brand names, drug names, and academic citations.

These modes drop curated tokens into prose where the OCR's prior on the
canonical spelling is especially strong. A pixel-faithful OCR transcribes
the exact glyphs; a prior-biased OCR snaps to the famous spelling.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Misspelled famous tech / corporate brands. Each pair is (misspell,
# canonical). Models have very strong priors on these specific token
# sequences: they're high-frequency proper nouns trained on heavily.
# Strong autocorrect signal expected.
# ---------------------------------------------------------------------------

_BRAND_SWAPS = [
    ("Macrosoft", "Microsoft"),
    ("Goggle", "Google"),
    ("Iphone", "iPhone"),
    ("Macbock", "MacBook"),
    ("Linsk", "LinkedIn"),
    ("Amzaon", "Amazon"),
    ("Facbook", "Facebook"),
    ("Instagam", "Instagram"),
    ("Twiter", "Twitter"),
    ("Yutoube", "YouTube"),
    ("Wikipidia", "Wikipedia"),
    ("Nteflix", "Netflix"),
    ("Tesla", "Tesla"),  # control: spelled correctly
    ("Spofify", "Spotify"),
    ("Dropbx", "Dropbox"),
    ("Wallmart", "Walmart"),
    ("Starbcks", "Starbucks"),
    ("McDonaldz", "McDonald's"),
    ("Verison", "Verizon"),
    ("Coca-Coal", "Coca-Cola"),
    ("Adidas", "Adidas"),  # control
    ("Nikee", "Nike"),
    ("Adobee", "Adobe"),
    ("Photshop", "Photoshop"),
    ("Excell", "Excel"),
    ("Powerpiont", "PowerPoint"),
    ("Ubuntoo", "Ubuntu"),
    ("Reditt", "Reddit"),
    ("Pinterst", "Pinterest"),
    ("Cocacola", "Coca-Cola"),
]


def brand_swap_text(text: str, word_prob: float = 0.10) -> str:
    """Replace some Markov words with misspelled famous brand names.

    Each chosen position gets a misspelled brand from the curated list.
    A pixel-faithful OCR transcribes the misspell; a prior-biased OCR
    "corrects" to the canonical brand name.
    """
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            ms = rng.choice(_BRAND_SWAPS)[0]
            out.append(ms)
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Mixed-case brand names: preserve stylised camel/Pascal case of real
# brands. Tests whether OCR snaps to title-case ("YouTube" → "Youtube",
# "iPhone" → "Iphone", "GitHub" → "Github") or preserves the canonical
# spelling.
# ---------------------------------------------------------------------------

_MIXED_CASE_BRANDS: list[str] = [
    "iPhone",
    "iPad",
    "iPod",
    "iMac",
    "MacBook",
    "AirPods",
    "eBay",
    "PayPal",
    "YouTube",
    "GitHub",
    "GitLab",
    "FedEx",
    "JavaScript",
    "TypeScript",
    "WordPress",
    "PostgreSQL",
    "MySQL",
    "DeepMind",
    "OpenAI",
    "DeepL",
    "WhatsApp",
    "PowerPoint",
    "OneDrive",
    "OneNote",
    "QuickTime",
    "PlayStation",
    "GoPro",
    "InDesign",
    "MailChimp",
    "DoorDash",
    "GrubHub",
    "BlackBerry",
    "GoDaddy",
    "OnlyFans",
    "SoundCloud",
    "BitTorrent",
    "CrowdStrike",
    "ChatGPT",
    "AlphaGo",
    "StackOverflow",
    "ProtonMail",
]


def mixed_case_brand_text(text: str, word_prob: float = 0.10) -> str:
    """Replace some words with stylised-case brand names."""
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            out.append(rng.choice(_MIXED_CASE_BRANDS))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Look-alike drug names: pairs of real medications that are 1-2 chars
# apart. Tests OCR's tendency to "fix" to the more common name. The
# downstream cost is *fatal* in pharmacy/medical OCR pipelines.
# ---------------------------------------------------------------------------

_LOOKALIKE_DRUGS = [
    # Each entry is a single name to insert; scorer checks no name from the
    # confusable set was substituted.
    "Celexa",
    "Celebrex",
    "Cerebyx",
    "Hydroxyzine",
    "Hydralazine",
    "Lamictal",
    "Lamisil",
    "Reminyl",
    "Amaryl",
    "Zantac",
    "Zyrtec",
    "Xanax",
    "Adderall",
    "Inderal",
    "Klonopin",
    "Clonidine",
    "Vicoprofen",
    "Vicodin",
    "Glipizide",
    "Glyburide",
    "Nicardipine",
    "Nifedipine",
    "Trazodone",
    "Tramadol",
    "Avastin",
    "Astelin",
    "Fluoxetine",
    "Duloxetine",
    "Paroxetine",
    "Toprol",
    "Topamax",
    "Risperdal",
    "Reglan",
    "Plavix",
    "Paxil",
    "Methocarbamol",
    "Methadone",
    "Methotrexate",
    "Quetiapine",
    "Quinapril",
    "Atenolol",
    "Albuterol",
    "Heparin",
    "Hespan",
]


def lookalike_drugs_text(text: str, word_prob: float = 0.06) -> str:
    """Inject a look-alike drug name into prose."""
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 5 and rng.random() < word_prob:
            out.append(rng.choice(_LOOKALIKE_DRUGS))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Citation format: academic citation styles: `[Smith et al., 2020]`,
# `(Smith, 2020)`, `Smith (2020)`, `Smith2020`. Tests whether OCR preserves
# the specific punctuation / spacing / bracket choice. Real downstream cost
# for bibliographic-extraction pipelines.
# ---------------------------------------------------------------------------

_AUTHORS = [
    "Smith",
    "Johnson",
    "Lee",
    "Brown",
    "Wang",
    "García",
    "Müller",
    "Park",
    "Kowalski",
    "Rossi",
    "Nakamura",
    "Patel",
    "Cohen",
    "Andersson",
    "Tanaka",
]


def citation_format_text(text: str, word_prob: float = 0.08) -> str:
    """Inject diverse citation-format tokens into prose."""
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            author = rng.choice(_AUTHORS)
            year = rng.randint(1995, 2024)
            style = rng.choice(
                [
                    "apa_paren",
                    "apa_inline",
                    "etal_bracket",
                    "etal_paren",
                    "nature",
                    "vancouver",
                ]
            )
            if style == "apa_paren":
                cite = f"({author}, {year})"
            elif style == "apa_inline":
                cite = f"{author} ({year})"
            elif style == "etal_bracket":
                cite = f"[{author} et al., {year}]"
            elif style == "etal_paren":
                cite = f"({author} et al. {year})"
            elif style == "nature":
                cite = f"{author}{year % 100:02d}"
            elif style == "vancouver":
                cite = f"[{rng.randint(1, 99)}]"
            else:
                cite = w
            out.append(cite)
        else:
            out.append(w)
    return " ".join(out)
