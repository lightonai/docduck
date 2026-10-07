# Third-party notices

docduck is distributed under the Apache License, Version 2.0 (see `LICENSE`).
It builds on open source libraries and ships a text model derived from
public-domain text. This file lists those components, their licenses, and the
obligations that come with them.

## Redistribution summary

The Python source code in this repository is licensed under Apache-2.0. All
runtime dependencies are permissively licensed (Apache-2.0, MIT, BSD, PSF-style,
HPND) except for two GUI bindings, `pycairo` and `PyGObject`, which are licensed
under LGPL-2.1. LGPL-2.1 libraries may be used by an Apache-2.0 project when they
are linked dynamically and remain separately replaceable. docduck imports them
as ordinary installed packages and does not vendor, statically link, or freeze
their source. Do not bundle these libraries into a single binary or into the
docduck wheel; doing so would make the combined work subject to LGPL-2.1.

## Runtime dependencies

| Package | Version | License (SPDX) | Role |
| --- | --- | --- | --- |
| pycairo | 1.27.0 | LGPL-2.1-only OR MPL-1.1 | Cairo bindings for drawing |
| PyGObject | 3.50.0 | LGPL-2.1-or-later | Pango and PangoCairo bindings |
| matplotlib | 3.10.1 | Matplotlib License (PSF-style) | Plots and math rendering fallback |
| numpy | 2.2.4 | BSD-3-Clause | Array math |
| markovify | 0.9.4 | MIT | Markov text models |
| PyYAML | 6.0+ | MIT | Config parsing |
| Pillow | 11.2.1 | MIT-CMU (HPND) | JPEG recompression for scan artifacts |

## Optional dependencies

| Extra | Package | License (SPDX) |
| --- | --- | --- |
| sft | pyarrow | Apache-2.0 |
| hf | datasets | Apache-2.0 |
| dev | pytest | MIT |
| dev | ruff | MIT |

## System libraries

The Cairo, Pango, and gobject-introspection system libraries are licensed under
LGPL-2.1-or-later (Cairo is dual LGPL-2.1 / MPL-1.1). They are linked at runtime
through `pycairo` and `PyGObject` and are not distributed with this repository.

## Bundled data: Markov corpora

`src/docduck/corpora/en_literature.json` is a text model built from Project
Gutenberg texts that are public domain in the United States. It is covered by
the project's Apache-2.0 license.

## Assets

`assets/example.png` and `examples/images/*` were produced by the project and
are covered by the Apache-2.0 license.

`assets/logo.svg` includes the Twemoji mallard duck (U+1F986) from
`jdecked/twemoji`, licensed under CC-BY 4.0
(https://creativecommons.org/licenses/by/4.0/). The duck path is used
unmodified with attribution.

## Full license texts

Full texts are distributed with each package and are available upstream:

- LGPL-2.1: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html
- MPL-1.1: https://www.mozilla.org/en-US/MPL/1.1/
- MIT: https://opensource.org/license/mit
- BSD-3-Clause: https://opensource.org/license/bsd-3-clause
- Apache-2.0: https://www.apache.org/licenses/LICENSE-2.0
- Matplotlib: https://matplotlib.org/stable/project/license.html
- HPND (Pillow): https://github.com/python-pillow/Pillow/blob/main/LICENSE
