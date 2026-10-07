"""Mode-name → transform-function dispatcher.

`transform(text, mode)` is the single entry point used by the text
generator and the eval/realpage harness. Falls through to a length-
preserving pseudo / gibberish word replacement when `mode` is one of
those two: implemented here because it needs the per-word punctuation
splitter and capitalization-restoration logic.
"""

from __future__ import annotations

from .brands import (
    brand_swap_text,
    citation_format_text,
    lookalike_drugs_text,
    mixed_case_brand_text,
)
from .case import (
    all_caps_mid_sentence_text,
    all_caps_text,
    mixed_case_text,
    punct_storm_text,
    repeat_chars_text,
)
from .glyph import (
    confusables_text,
    digit_heavy_text,
    homoglyph_text,
    leetspeak_text,
)
from .markup import (
    bullet_markers_text,
    code_block_text,
    highlighted_text,
    italic_emphasis_text,
    strikethrough_emphasis_text,
    strikethrough_text,
    whitespace_tabs_text,
    wide_kerning_text,
)
from .multilingual import (
    code_switching_text,
    emails_text,
    long_urls_text,
    stutter_text,
)
from .numbers import (
    date_formats_text,
    leading_zeros_text,
    locale_numbers_text,
    postal_codes_text,
    precision_numbers_text,
    rare_currency_text,
    roman_numerals_text,
    structured_ids_text,
)
from .phrases import (
    critical_not_paragraph,
    factual_swap_paragraph,
    famous_swap_paragraph,
    homophone_trap_paragraph,
    typo_explained_paragraph,
)
from .pseudo import _gibberish_word, _pseudo_word_of_length
from .scramble import scramble_text
from .typos import (
    bold_typos_text,
    diverse_typos_text,
    hyphenation_breaks_text,
)
from .unicode_chars import (
    bidi_text_mode,
    footnote_markers_text,
    foreign_names_text,
    greek_variables_text,
    mixed_script_word_text,
    mojibake_text,
    scientific_symbols_text,
)


def transform(text: str, mode: str) -> str:
    """Apply an adversarial transform to existing Markov text.

    Preserves word count so prose/titles/list-items produce same-shape output.
    Sentence terminators are sprinkled back in for pseudo/gibberish so long
    paragraphs still look paragraph-shaped.
    """
    if mode in (None, "natural") or not text:
        return text
    if mode == "scrambled":
        return scramble_text(text)
    if mode == "confusables":
        return confusables_text(text)
    if mode == "confusables_heavy":
        # 25% swap rate: same lookup table as confusables, ~3x denser.
        # Targets pixel-vs-prior resolution on every other character.
        return confusables_text(text, swap_probability=0.25)
    if mode == "digit_heavy":
        return digit_heavy_text(text)
    if mode == "digit_extreme":
        # 65% leet-swap rate: at this density most vowels + common consonants
        # become digits. Pages are still readable to humans (the spatial
        # gestalt survives) but an LM-leaning OCR has nothing English-looking
        # to anchor to, so it must commit to the pixel reads.
        return digit_heavy_text(text, swap_probability=0.65)
    if mode == "famous_swap":
        n_sent = max(1, text.count(".") + text.count("!") + text.count("?"))
        return famous_swap_paragraph(n_sentences=n_sent)
    if mode == "homophone_trap":
        n_sent = max(1, text.count(".") + text.count("!") + text.count("?"))
        return homophone_trap_paragraph(n_sentences=n_sent)
    if mode == "strikethrough":
        return strikethrough_text(text)

    # Pixel-faithfulness modes (programmatic transforms on Markov text).
    if mode == "all_caps":
        return all_caps_text(text)
    if mode == "mixed_case":
        return mixed_case_text(text)
    if mode == "repeat_chars":
        return repeat_chars_text(text)
    if mode == "punct_storm":
        return punct_storm_text(text)
    if mode == "leading_zeros":
        return leading_zeros_text(text)
    if mode == "diverse_typos":
        return diverse_typos_text(text)
    if mode == "precision_numbers":
        return precision_numbers_text(text)
    if mode == "foreign_names":
        return foreign_names_text(text)
    if mode == "scientific_symbols":
        return scientific_symbols_text(text)
    if mode == "critical_not":
        n_sent = max(1, text.count(".") + text.count("!") + text.count("?"))
        return critical_not_paragraph(n_sentences=n_sent)
    if mode == "factual_swap":
        n_sent = max(1, text.count(".") + text.count("!") + text.count("?"))
        return factual_swap_paragraph(n_sentences=n_sent)
    if mode == "bold_typos":
        return bold_typos_text(text)
    if mode == "typo_explained":
        n_sent = max(1, text.count(".") + text.count("!") + text.count("?"))
        return typo_explained_paragraph(n_sentences=n_sent)
    if mode == "brand_swap":
        return brand_swap_text(text)
    if mode == "homoglyph":
        return homoglyph_text(text)
    if mode == "stutter":
        return stutter_text(text)
    if mode == "mojibake":
        return mojibake_text(text)
    if mode == "leetspeak":
        return leetspeak_text(text)
    if mode == "roman_numerals":
        return roman_numerals_text(text)
    if mode == "wide_kerning":
        return wide_kerning_text(text)
    if mode == "footnote_markers":
        return footnote_markers_text(text)
    if mode == "code_switching":
        return code_switching_text(text)
    if mode == "mixed_case_brand":
        return mixed_case_brand_text(text)
    if mode == "locale_numbers":
        return locale_numbers_text(text)
    if mode == "structured_ids":
        return structured_ids_text(text)
    if mode == "date_formats":
        return date_formats_text(text)
    if mode == "lookalike_drugs":
        return lookalike_drugs_text(text)
    if mode == "citation_format":
        return citation_format_text(text)
    if mode == "hyphenation_breaks":
        return hyphenation_breaks_text(text)
    if mode == "bullet_markers":
        return bullet_markers_text(text)
    if mode == "italic_emphasis":
        return italic_emphasis_text(text)
    if mode == "greek_variables":
        return greek_variables_text(text)
    if mode == "bidi_text":
        return bidi_text_mode(text)
    if mode == "mixed_script_word":
        return mixed_script_word_text(text)
    if mode == "rare_currency":
        return rare_currency_text(text)
    if mode == "highlighted_text":
        return highlighted_text(text)
    if mode == "long_urls":
        return long_urls_text(text)
    if mode == "emails":
        return emails_text(text)
    if mode == "strikethrough_emphasis":
        return strikethrough_emphasis_text(text)
    if mode == "whitespace_tabs":
        return whitespace_tabs_text(text)
    if mode == "all_caps_mid_sentence":
        return all_caps_mid_sentence_text(text)
    if mode == "code_block":
        return code_block_text(text)
    if mode == "postal_codes":
        return postal_codes_text(text)

    # pseudo + gibberish: replace each word, preserving word count AND each
    # word's character length (so page content length doesn't drift relative
    # to natural mode: otherwise length becomes a confounder in OCR scoring).
    orig_words = text.split()
    if not orig_words:
        return text

    # Strip surrounding punctuation to measure letter length; re-attach after.
    def _split_punct(w: str) -> tuple[str, str, str]:
        lead = ""
        trail = ""
        i = 0
        while i < len(w) and not w[i].isalnum():
            lead += w[i]
            i += 1
        j = len(w)
        while j > i and not w[j - 1].isalnum():
            trail = w[j - 1] + trail
            j -= 1
        return lead, w[i:j], trail

    def _make(length: int) -> str:
        return _pseudo_word_of_length(length) if mode == "pseudo" else _gibberish_word(length)

    new_words = []
    for w in orig_words:
        lead, core, trail = _split_punct(w)
        if not core:  # pure punctuation (e.g., "—")
            new_words.append(w)
            continue
        replacement = _make(len(core))
        if core[0].isupper():
            replacement = replacement.capitalize()
        new_words.append(lead + replacement + trail)

    # Ensure the first visible word is capitalized
    for i, w in enumerate(new_words):
        if any(c.isalpha() for c in w):
            new_words[i] = w[0].upper() + w[1:] if w[0].islower() else w
            break
    return " ".join(new_words)
