"""Tests for the remaining pools in docduck.config."""

from docduck import config


class TestConfigPools:
    def test_math_equations_multiline(self):
        for eq_lines in config.MATH_EQUATIONS_MULTILINE:
            assert isinstance(eq_lines, list)
            assert len(eq_lines) >= 2
            for line in eq_lines:
                assert isinstance(line, str)
                assert len(line) > 0

    def test_table_headers_are_lists(self):
        for headers in config.TABLE_HEADERS_POOL:
            assert isinstance(headers, list)
            assert len(headers) >= 3
            assert all(isinstance(h, str) for h in headers)
