"""Diversity controls: ensure variety across a batch of generated pages.

All hardcoded pools (colors, margins, block weights, flow templates) live in
defaults.py under "style", "brand_palettes", and "planner". This module reads
from DEFAULTS so the behavior can be overridden via YAML config.
"""

import random
from collections import Counter

from .defaults import DEFAULTS


class PageStyle:
    """All visual parameters for a single page, randomized with constraints.

    Pools (papers, text colors, accents, margins, sizes) and flag probabilities
    all come from DEFAULTS["style"]: override via YAML config.
    """

    def __init__(self, defaults=None, brand_palette=None):
        d = (defaults or DEFAULTS)["style"]
        brand_palettes = (defaults or DEFAULTS)["brand_palettes"]
        brand_prob = (defaults or DEFAULTS)["brand_palette_probability"]

        self.paper_name = random.choice(list(d["papers"].keys()))
        self.paper_color = d["papers"][self.paper_name]

        text_names = list(d["text_color_weights"].keys())
        text_weights = [d["text_color_weights"][n] for n in text_names]
        self.text_name = random.choices(text_names, weights=text_weights, k=1)[0]
        self.text_color = d["text_colors"][self.text_name]

        if brand_palette is None and random.random() < brand_prob:
            brand_palette = random.choice(list(brand_palettes.keys()))

        if brand_palette and brand_palette in brand_palettes:
            self.brand_palette_name = brand_palette
            self.brand_palette = brand_palettes[brand_palette]
            self.accent_name = brand_palette
            self.accent_color = self.brand_palette["accent"]
            self.primary_color = self.brand_palette["primary"]
            self.text_on_primary = self.brand_palette["text_on_primary"]
        else:
            self.brand_palette_name = None
            self.brand_palette = None
            self.accent_name = random.choice(list(d["accents"].keys()))
            self.accent_color = d["accents"][self.accent_name]
            self.primary_color = self.accent_color
            self.text_on_primary = (1.0, 1.0, 1.0)

        weights = d.get("margin_preset_weights", {})
        names = list(d["margin_presets"].keys())
        ws = [weights.get(n, 1) for n in names]
        self.margin_name = random.choices(names, weights=ws, k=1)[0]
        self.margins = d["margin_presets"][self.margin_name]

        size_cat = random.choice(list(d["body_size_ranges"].keys()))
        lo, hi = d["body_size_ranges"][size_cat]
        self.body_size = random.uniform(lo, hi)
        self.heading_size = self.body_size * random.uniform(*d["heading_size_multiplier"])
        self.subheading_size = self.body_size * random.uniform(*d["subheading_size_multiplier"])
        self.tiny_size = max(4, self.body_size * random.uniform(*d["tiny_size_multiplier"]))
        self.line_spacing = random.uniform(*d["line_spacing_range"])

        probs = d["flag_probabilities"]
        self.justify = random.random() < probs["justify"]
        self.has_header = random.random() < probs["has_header"]
        self.has_page_number = random.random() < probs["has_page_number"]
        self.has_page_border = random.random() < probs["has_page_border"]
        self.has_edge_shadow = random.random() < probs["has_edge_shadow"]
        self.has_logo = random.random() < probs["has_logo"]
        self.has_banner = random.random() < probs["has_banner"]

    def signature(self):
        """Return a hashable signature for diversity tracking."""
        return (self.paper_name, self.text_name, self.accent_name, self.margin_name)


class LayoutPlanner:
    """Generates block sequences with diversity constraints.

    Block weights and flow templates come from DEFAULTS["planner"].

    Rules:
    - Heading always first
    - No two identical block types in a row (except prose) in random mode
    - At least N distinct block types per page in random mode
    - Tiny text / footnotes always last (if present)
    """

    def __init__(self, min_blocks=3, max_blocks=7, min_distinct=3, defaults=None):
        self.min_blocks = min_blocks
        self.max_blocks = max_blocks
        self.min_distinct = min_distinct
        d = (defaults or DEFAULTS)["planner"]
        self.block_weights = d["block_weights"]
        self.flow_templates = d["flow_templates"]
        self.template_probability = d["template_probability"]
        self.tiny_text_probability = d["tiny_text_probability"]

    def plan(self):
        """Generate a valid block sequence using document flow templates."""
        if random.random() < self.template_probability:
            return self._plan_from_template()
        return self._plan_random()

    def _plan_from_template(self):
        """Pick a template and adapt it to block count constraints."""
        weights = [w for w, _ in self.flow_templates]
        templates = [t for _, t in self.flow_templates]
        template = random.choices(templates, weights=weights, k=1)[0]

        sequence = list(template)
        if len(sequence) > self.max_blocks:
            sequence = sequence[: self.max_blocks]
        while len(sequence) < self.min_blocks:
            sequence.append("prose")

        sequence = ["heading"] + sequence

        if random.random() < self.tiny_text_probability:
            sequence.append("tiny_text")

        return sequence

    def _plan_random(self):
        """Random planning with diversity constraints."""
        n = random.randint(self.min_blocks, self.max_blocks)
        blocks = list(self.block_weights.keys())
        weights = [self.block_weights[b] for b in blocks]

        sequence = []
        used_types = set()
        last_type = None

        for _ in range(n):
            adj_weights = []
            for b, w in zip(blocks, weights):
                if b == last_type and b != "prose":
                    adj_weights.append(0)
                else:
                    adj_weights.append(w)

            remaining_slots = n - len(sequence)
            needed_distinct = self.min_distinct - len(used_types)
            if needed_distinct > 0 and remaining_slots <= needed_distinct + 1:
                for i, b in enumerate(blocks):
                    if b not in used_types:
                        adj_weights[i] *= 3

            total = sum(adj_weights)
            if total == 0:
                break

            probs = [w / total for w in adj_weights]
            chosen = random.choices(blocks, weights=probs, k=1)[0]
            sequence.append(chosen)
            used_types.add(chosen)
            last_type = chosen

        sequence = ["heading"] + sequence

        if "tiny_text" in sequence:
            sequence.remove("tiny_text")
        if random.random() < self.tiny_text_probability:
            sequence.append("tiny_text")

        return sequence


class BatchDiversityTracker:
    """Tracks what's been generated across a batch to ensure variety."""

    def __init__(self, defaults=None):
        self.style_counts = Counter()
        self.block_type_counts = Counter()
        self.layout_hashes = set()
        self.genre_counts = Counter()
        self.total_pages = 0
        d = (defaults or DEFAULTS)["style"]
        self._papers = list(d["papers"].keys())
        self._accents = list(d["accents"].keys())

    def record_page(self, style, block_sequence, genre=None):
        self.total_pages += 1
        self.style_counts[style.signature()] += 1
        for b in block_sequence:
            self.block_type_counts[b] += 1
        self.layout_hashes.add(tuple(block_sequence))
        if genre:
            self.genre_counts[genre] += 1

    def pick_genre(self, genre_pool):
        """Pick an English genre biased toward the least-used one so far.

        With a 7-corpus pool and a 1M batch, uniform sampling will already
        spread evenly; this helps early batches reach coverage faster and
        smooths stochastic undersampling.
        """
        if not genre_pool:
            return None
        counts = [(self.genre_counts[g], g) for g in genre_pool]
        counts.sort()
        min_count = counts[0][0]
        tied = [g for c, g in counts if c == min_count]
        return random.choice(tied)

    def suggest_style_overrides(self):
        """Suggest underrepresented style choices to increase diversity."""
        overrides = {}
        if self.total_pages < 2:
            return overrides

        paper_counts = Counter()
        for sig, count in self.style_counts.items():
            paper_counts[sig[0]] += count

        unused_papers = [p for p in self._papers if p not in paper_counts]
        if unused_papers:
            overrides["preferred_paper"] = random.choice(unused_papers)

        accent_counts = Counter()
        for sig, count in self.style_counts.items():
            accent_counts[sig[2]] += count

        unused_accents = [a for a in self._accents if a not in accent_counts]
        if unused_accents:
            overrides["preferred_accent"] = random.choice(unused_accents)

        return overrides

    def report(self):
        """Return a diversity summary."""
        return {
            "total_pages": self.total_pages,
            "unique_layouts": len(self.layout_hashes),
            "style_distribution": {str(k): v for k, v in self.style_counts.items()},
            "block_type_counts": dict(self.block_type_counts),
            "genre_distribution": dict(self.genre_counts),
        }
