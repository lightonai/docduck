"""docduck: synthetic document page generator.

Pin the PyGObject API versions of Pango/PangoCairo at package import so every
subsequent `from gi.repository import Pango, PangoCairo` (in blocks/, chrome/,
layout.py, etc.) is silent. Without this pin, PyGI emits a warning each time a
submodule imports them.
"""

import gi as _gi

_gi.require_version("Pango", "1.0")
_gi.require_version("PangoCairo", "1.0")

del _gi
