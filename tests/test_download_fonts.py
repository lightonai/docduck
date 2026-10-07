"""Tests for the Google Fonts downloader + fontconfig bridge."""

import os
from unittest import mock

from docduck.cli.download_fonts import CURATED, write_fontconfig


def test_curated_uses_iso15924_script_codes():
    """All keys must be 4-letter ISO-15924 script codes (first char uppercase)."""
    for script in CURATED:
        assert len(script) == 4, script
        assert script[0].isupper(), script
        assert script[1:].islower(), script


def test_curated_entries_are_license_family_pairs():
    """Each entry is (family_slug, license_dir) with a known license."""
    for script, families in CURATED.items():
        for fam, lic in families:
            assert isinstance(fam, str) and fam.islower() and fam, (script, fam)
            assert lic in {"ofl", "ufl", "apache"}, (script, fam, lic)


def test_write_fontconfig_produces_valid_xml(tmp_path, monkeypatch):
    """The fontconfig override must include system defaults + the font dir."""
    # Redirect the cache location via $HOME so the test doesn't touch real state.
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    # Force Path.home() to follow $HOME on systems that cache it otherwise.
    with mock.patch("docduck.cli.download_fonts.Path.home", return_value=fake_home):
        font_dir = tmp_path / "fonts"
        font_dir.mkdir()
        cfg = write_fontconfig(font_dir)

    assert cfg.exists()
    xml = cfg.read_text()
    # Must inherit system defaults so downloaded fonts add to, not replace.
    assert "<include" in xml and "fonts.conf" in xml
    # Must include our font directory by absolute path.
    assert f"<dir>{font_dir.resolve()}</dir>" in xml
    # And be well-formed XML.
    assert xml.startswith("<?xml")
    assert "</fontconfig>" in xml


def test_auto_register_respects_existing_fontconfig_file(monkeypatch):
    """If FONTCONFIG_FILE is already set, the auto-register is a no-op."""
    from docduck.fonts import _auto_register_docduck_fonts

    monkeypatch.setenv("FONTCONFIG_FILE", "/caller/path/fonts.conf")
    _auto_register_docduck_fonts()
    assert os.environ["FONTCONFIG_FILE"] == "/caller/path/fonts.conf"


def test_auto_register_noop_when_no_fonts_dir(tmp_path, monkeypatch):
    """With no ./fonts/ and no cached config present, FONTCONFIG_FILE stays unset."""
    from docduck.fonts import _auto_register_docduck_fonts

    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    monkeypatch.delenv("DOCDUCK_FONTS_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    with mock.patch("docduck.fonts.Path.home", return_value=tmp_path):
        _auto_register_docduck_fonts()
    assert "FONTCONFIG_FILE" not in os.environ


def test_auto_register_sets_fontconfig_when_dir_and_cfg_present(tmp_path, monkeypatch):
    """If both ./fonts/ and the cached config exist, FONTCONFIG_FILE gets set."""
    from docduck.fonts import _auto_register_docduck_fonts

    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    monkeypatch.delenv("DOCDUCK_FONTS_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "fonts").mkdir()
    cfg_dir = tmp_path / ".cache" / "docduck"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "fontconfig.conf"
    cfg_path.write_text("<fontconfig/>")
    try:
        with mock.patch("docduck.fonts.Path.home", return_value=tmp_path):
            _auto_register_docduck_fonts()
        assert os.environ.get("FONTCONFIG_FILE") == str(cfg_path)
    finally:
        os.environ.pop("FONTCONFIG_FILE", None)
