"""Tests for the script-coverage filter in build_corpora.

The filter's job is to reject cross-script pollution in multilingual corpora:
most visibly, pure-English bibliographic entries that get spliced into
CJK corpora and leak out of the Markov chain at sample time. These tests
pin the behavior for the exact sentences that triggered the fix.
"""

from docduck.cli.build_corpora import (
    LANG_SCRIPTS,
    SCRIPT_THRESHOLD,
    clean_text,
    script_ratio,
)

# --------------------------------------------------------------------------
# script_ratio: the low-level check
# --------------------------------------------------------------------------


def test_script_ratio_pure_target_script():
    # "Politics current-leadership administrative-division" in zh
    assert script_ratio("政治 现任领导 行政区划", "han") == 1.0


def test_script_ratio_pure_latin_gets_zero():
    # Exactly the kind of entry we saw leaking out of the zh corpus.
    assert script_ratio("Princeton, Princeton University Press, 1988.", "han") == 0.0


def test_script_ratio_mixed_below_threshold():
    # Bibliographic-style mix: mostly English with a Chinese tail.
    ratio = script_ratio("外部連結 What Is AI?—An introduction to elementary logic.", "han")
    assert ratio < SCRIPT_THRESHOLD  # correctly flagged as polluted


def test_script_ratio_mixed_above_threshold():
    # Realistic native zh with a single English loanword: should keep.
    ratio = script_ratio("系统使用现代的Python框架进行数据分析", "han")
    assert ratio >= SCRIPT_THRESHOLD


def test_script_ratio_ignores_whitespace_and_digits():
    # Counts letters only; spaces + digits don't sway the ratio.
    assert script_ratio("政治   1988   现任", "han") == 1.0


def test_script_ratio_returns_zero_on_empty_or_punctuation_only():
    assert script_ratio("", "han") == 0.0
    assert script_ratio("   ,.!?   ", "han") == 0.0


def test_script_ratio_recognises_arabic():
    assert script_ratio("الحمد لله رب العالمين", "arabic") == 1.0
    assert script_ratio("Hello world", "arabic") == 0.0


def test_script_ratio_han_kana_covers_hiragana():
    # Pure hiragana should count as in-script for Japanese.
    assert script_ratio("こんにちは", "han_kana") == 1.0


# --------------------------------------------------------------------------
# clean_text: the end-to-end corpus filter
# --------------------------------------------------------------------------


# Sentences separated by whitespace so the CJK-aware sentence splitter in
# clean_text can tokenize them. Mirrors raw multilingual article spacing.
SAMPLE_ZH_TEXT = (
    "政治现任领导行政区划济南市现辖10个市辖区、2个县。 "
    "Princeton, Princeton University Press, 1988. "
    "Spinoza in the Making is a classic work. "
    "他是第一套支援Power Macintosh的Office套裝軟體，最後一版針對Mac釋出的Office是：Office 4.2.1。"
)


def testclean_text_drops_english_bibs_for_zh():
    """All-English bibliographic sentences must NOT survive the zh filter."""
    kept = clean_text(SAMPLE_ZH_TEXT, lang="zh")
    joined = " ".join(kept)
    assert "Princeton University Press" not in joined
    assert "Spinoza in the Making" not in joined


def testclean_text_keeps_native_zh_sentences():
    kept = clean_text(SAMPLE_ZH_TEXT, lang="zh")
    joined = " ".join(kept)
    assert (
        "濟南市" in joined or "济南市" in joined or "Power Macintosh" in joined
    )  # some zh survives


def testclean_text_no_filter_for_latin_langs():
    """French/German etc. should not have the non-Latin filter applied."""
    english_bib = "Smith J., Harvard University Press, 2019."
    kept = clean_text(english_bib, lang="fr")  # fr isn't in LANG_SCRIPTS
    assert english_bib in " ".join(kept) or any("Harvard" in s for s in kept)


def testclean_text_no_filter_when_lang_omitted():
    """Called with no lang, the function behaves exactly as before the fix."""
    kept = clean_text(SAMPLE_ZH_TEXT)
    # Without a lang, everything meeting length bounds passes through.
    assert any("Princeton" in s for s in kept)


# --------------------------------------------------------------------------
# Lang → script mapping
# --------------------------------------------------------------------------


def test_lang_scripts_cover_non_latin_langs():
    """Every language we ship a non-Latin corpus for should be mapped."""
    expected = {"ar", "zh", "ja", "ko", "hi", "th", "ru", "uk", "he"}
    assert expected.issubset(LANG_SCRIPTS.keys())


def test_latin_langs_not_mapped():
    """Mapping Latin-script langs would mis-fire the filter: keep them out."""
    for code in ("en", "fr", "de", "es", "it", "pt", "nl"):
        assert code not in LANG_SCRIPTS
