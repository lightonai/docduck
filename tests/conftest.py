"""Test suite configuration.

Forces 72 DPI rendering (1:1 pixels) during tests; at the default 200 DPI
every rendered page is 2500x3333, which is 7.7x more pixels and dominates
test runtime. Tests that specifically verify DPI scaling pass output_dpi
explicitly.

Also resets the module-global text-generation state (content_mode and the
active TextSource) between tests so the suite is order-independent.
"""

import os

# Must be set BEFORE `docduck.composer` is imported so DEFAULT_OUTPUT_DPI picks it up.
os.environ.setdefault("DOCDUCK_OUTPUT_DPI", "72")

import pytest  # noqa: E402  (after the DPI env var is set)


@pytest.fixture(autouse=True)
def _reset_text_generator_state():
    """Reset content_mode and the active TextSource around every test so a
    test that flips them (for example by composing a page with a specific
    content_mode) cannot poison the next test."""
    from docduck.generators import text as text_gen

    text_gen.set_content_mode("natural")
    text_gen.reset_text_source()
    yield
    text_gen.set_content_mode("natural")
    text_gen.reset_text_source()
