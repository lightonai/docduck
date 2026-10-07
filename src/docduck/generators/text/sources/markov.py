"""Markov-corpus text source. The default implementation."""

from ._base import TextSource, register_text_source


@register_text_source("markov")
class MarkovSource(TextSource):
    """Default source: per-language Markov models built by `docduck-corpora`,
    with a hand-written template fallback when no model is loaded for the
    requested language."""

    def sentence(self, lang: str | None) -> str:
        from .. import sentences as _s

        s = _s._markov_sentence(lang)
        return s if s else _s._template_sentence()

    def short(self, lang: str | None, max_words: int = 12) -> str | None:
        from ..models import _SCRIPT_RETRY_TRIES, LANG_SCRIPTS, _accept_sample, _pick_model
        from ..sentences import _normalize_spacing

        _, model = _pick_model(lang)
        if model is None:
            return None
        s = None
        for _ in range(_SCRIPT_RETRY_TRIES if LANG_SCRIPTS.get(lang or "") else 1):
            s = model.make_short_sentence(max_chars=80, tries=50)
            if _accept_sample(s, lang):
                s = _normalize_spacing(s)
                break
        if s is None:
            return None
        words = s.split()
        return " ".join(words[:max_words]) if len(words) > max_words else s
