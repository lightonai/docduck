"""Centralized defaults for all rendering parameters.

Every magic number from the pipeline lives here. Values are organized by
block type / subsystem. Override any value by passing a custom defaults dict
to PageConfig or directly to block renderers.

Usage:
    from docduck.defaults import DEFAULTS

    # Read a value
    dpi = DEFAULTS["math"]["dpi_choices"]

    # Override for a run
    my_defaults = DEFAULTS.copy()
    my_defaults["math"]["dpi_choices"] = [300]
"""

import copy


def _defaults():
    """Return a fresh defaults dict. Call copy.deepcopy() if mutating."""
    return {
        # ---------------------------------------------------------------
        # Page-level
        # ---------------------------------------------------------------
        "page": {
            "width": 900,
            "height": 1200,
            "block_spacing": (3, 8),  # uniform range
            "min_remaining": 30,  # px before stopping layout
        },
        # ---------------------------------------------------------------
        # Heading block
        # ---------------------------------------------------------------
        "heading": {
            "fallback_sizes": [14, 16, 18, 20],
            "styles": ["plain", "underline", "accent_bg", "centered", "small_caps"],
            "underline_widths": [0.8, 1.0, 1.5, 2.0],
            "underline_extent": (0.3, 1.0),  # fraction of page width
            "underline_padding": 8,
            "accent_bg_height_pad": 10,
            "accent_bg_x_pad": 8,
            "accent_bg_y_pad": 3,
            "bottom_margin": 10,
        },
        # ---------------------------------------------------------------
        # Prose block
        # ---------------------------------------------------------------
        "prose": {
            "n_paragraphs": (1, 4),
            "fallback_sizes": [9, 10, 11],
            "fallback_line_spacing": 2.5,
            "bottom_margin": 12,
            # Per-sentence probability that inline text is wrapped in a
            # marker-pen highlight (GT emits ==phrase==). Off by default; opt
            # in with e.g. `DEFAULTS["prose"]["highlight_prob"] = 0.08`.
            "highlight_prob": 0.0,
            # When truncating visible markup-stripped text back into a
            # markdown prefix, search for this many trailing chars to find
            # the word boundary in the markdown output.
            "tail_search_chars": 30,
        },
        # ---------------------------------------------------------------
        # Tiny text (footnotes)
        # ---------------------------------------------------------------
        "tiny_text": {
            "footnote_count": (2, 5),
            "fallback_sizes": [5, 6, 7],
            "rule_probability": 0.6,
            "rule_opacity": 0.4,
            "rule_width": 0.5,
            "rule_extent": 0.3,  # fraction of page width
            "rule_spacing": 6,
            "line_spacing": 1.5,
            "bottom_margin": 16,
        },
        # ---------------------------------------------------------------
        # Multi-column block
        # ---------------------------------------------------------------
        "multicolumn": {
            "column_counts": [2, 2, 3],  # weighted: 2 cols twice as likely
            "gutter_width": (18, 35),
            "n_paragraphs": (3, 6),
            "fallback_sizes": [9, 10, 11],
            "fallback_line_spacing": 2.0,
            "max_column_height": 400,
            "separator_opacity": 0.3,
            "separator_width": 0.5,
            "bottom_margin": 15,
        },
        # ---------------------------------------------------------------
        # Table block
        # ---------------------------------------------------------------
        "table": {
            "row_height": (28, 36),
            "header_height_pad": 6,
            "font_size_cap": 11,
            "caption_overhead": 30,
            "caption_bottom_pad": 8,
            "styles": ["booktabs", "grid", "minimal", "bordered", "borderless"],
            "stripe_probability": 0.5,
            "header_bg_probability": 0.8,
            "cell_h_pad": 14,
            "thick_line_width": 1.8,
            "normal_line_width": 0.5,
            "vline_opacity": 0.3,
            "vline_width": 0.5,
            "header_bg_opacity": 0.18,
            "stripe_opacity": 0.05,
            "bottom_margin": 15,
            # Per-cell probability of a marker-pen highlight (GT emits ==value==).
            # Off by default; opt in with `DEFAULTS["table"]["highlight_prob"] = 0.04`.
            "highlight_prob": 0.0,
            # Headers sampled via Markov short phrases in the target language.
            # A few tokens stay literal because they're language-agnostic.
            "header_literal_tokens": {
                "pvalue": ["p", "p-value"],
                "percent_suffix": " (%)",
            },
            # Max length (chars) for a sampled header
            "header_max_chars": 20,
            # Number of words to request from the Markov model per header
            "header_max_words": 3,
            # Probability of each advanced feature
            "summary_row_probability": 0.20,
            "index_column_probability": 0.15,
            "hierarchical_probability": 0.18,
            # Weights for each structural table generator
            "generator_weights": {
                "simple": 0.07,
                "standard": 0.08,
                "wide": 0.09,
                "tall": 0.09,
                "grouped_header": 0.12,
                "sparse": 0.07,
                "single_column": 0.04,
                "key_value": 0.07,
                "hierarchical": 0.09,
                "indexed": 0.04,
                "deep_header": 0.05,
                "nested_rowspan": 0.05,
                "matrix": 0.03,
                "pivot": 0.04,
                "irregular": 0.04,
                "dense": 0.03,
            },
        },
        # ---------------------------------------------------------------
        # Math block
        # ---------------------------------------------------------------
        "math": {
            "multiline_probability": 0.3,
            "label_range": (1, 50),
            "fontsize_range": (10, 14),
            "dpi_choices": [150, 170, 200],
            "multiline_spacing": (2, 5),
            "min_label_size": 7,
            "bottom_margin": 8,
            # Procedural equation generator (generators/math.py)
            "coeff_int_range": (2, 15),
            "coeff_float_range": (0.1, 9.9),
            "polynomial_degree_range": (3, 6),
        },
        # ---------------------------------------------------------------
        # Plot generator
        # ---------------------------------------------------------------
        "plot": {
            "dpi": 100,
        },
        # ---------------------------------------------------------------
        # Code block
        # ---------------------------------------------------------------
        "code": {
            "font_size_cap": 10,
            "h_pad": 12,
            "v_pad": 10,
            "layout_width_pad": 24,  # total left+right padding for text
            "bg_styles": [
                # (bg_color, is_dark)
                ((0.93, 0.93, 0.93), False),
                ((0.15, 0.15, 0.18), True),
                ((0.95, 0.94, 0.90), False),
                ((0.12, 0.12, 0.15), True),
                ((0.96, 0.96, 0.98), False),
                ((0.22, 0.24, 0.28), True),
            ],
            "dark_text_color": (0.85, 0.85, 0.85),
            "border_radii": [0, 4, 6, 8],
            "border_probability": 0.6,
            "border_opacity": 0.15,
            "border_width": 0.8,
            "accent_bar_probability": 0.3,
            "accent_bar_width": 3,
            "bottom_margin": 12,
        },
        # ---------------------------------------------------------------
        # Image placeholder block
        # ---------------------------------------------------------------
        "image": {
            "height_range": (80, 180),
            "width_fraction": (0.4, 1.0),
            "pattern_types": [
                "gradient",
                "noise",
                "circles",
                "grid",
                "bars",
                "radial",
                "checker",
            ],
            "border_probability": 0.7,
            "border_opacity": 0.2,
            "border_width": 0.8,
            "caption_size_offset": 1,  # added to style.tiny_size
            "bottom_margin": 20,
            # Pattern fallback parameters
            "gradient_color_range": (0.3, 0.8),  # uniform per RGB channel
            "noise_brightness_range": (80, 220),  # uint8 grayscale floor/ceil
            "circles_count_range": (5, 20),
            "circles_radius_range": (8, 60),
            "grid_step_range": (12, 30),
            "grid_dot_count_range": (10, 50),
        },
        # ---------------------------------------------------------------
        # Rule (horizontal divider) block
        # ---------------------------------------------------------------
        "rule": {
            "styles": ["thin", "thick", "double", "dashed", "ornament", "dots"],
            "width_fraction": (0.4, 1.0),
            "opacity": 0.3,
            "thin_width": 0.5,
            "thick_width": 2.0,
            "double_width": 0.5,
            "double_gap": 4,  # pixels between the two lines
            "dashed_width": 0.8,
            "dashed_pattern": [6, 4],
            "dots_width": 1.0,
            "dots_pattern": [1, 4],
            "ornament_gap": 15,
            "ornament_size": 6,
            "height": 18,
        },
        # ---------------------------------------------------------------
        # List block
        # ---------------------------------------------------------------
        "list": {
            "item_count": (3, 8),
            "fallback_sizes": [9, 10, 11],
            "list_types": ["bullet", "numbered", "letter"],
            "indent": 24,
            "bullet_indent": 18,
            "nested_probability": 0.25,
            "item_spacing": 4,
            "bottom_margin": 12,
        },
        # ---------------------------------------------------------------
        # Blockquote
        # ---------------------------------------------------------------
        "blockquote": {
            "fallback_sizes": [9, 10, 11],
            "bar_width": 3,
            "bar_padding": 12,
            "bar_opacity": 0.5,
            "v_padding": 8,
            "bg_probability": 0.4,
            "attribution_probability": 0.3,
            "bottom_margin": 12,
        },
        # ---------------------------------------------------------------
        # Definition list
        # ---------------------------------------------------------------
        "definition_list": {
            "item_count": (3, 6),
            "fallback_sizes": [9, 10, 11],
            "definition_indent": 24,
            "item_spacing": 8,
            "bottom_margin": 12,
        },
        # ---------------------------------------------------------------
        # Subheading (h2/h3)
        # ---------------------------------------------------------------
        "subheading": {
            "levels": [2, 2, 3],  # weighted toward h2
            "fallback_sizes": [12, 13, 14],
            "underline_probability": 0.4,
            "bottom_margin": 6,
        },
        # ---------------------------------------------------------------
        # Composer / page chrome
        # ---------------------------------------------------------------
        "composer": {
            "edge_shadow_width": 12,
            "edge_shadow_color": (0.5, 0.5, 0.5),
            "edge_shadow_opacity": 0.15,
            "border_opacity": 0.15,
            "border_width": 0.8,
            "border_pad": 10,
            "header_y_offset": 30,
            "header_opacity": 0.4,
            "header_rule_opacity": 0.15,
            "header_rule_width": 0.5,
            "header_rule_y_offset": 12,
            "page_number_range": (1, 300),
            "page_number_opacity": 0.4,
        },
        # ---------------------------------------------------------------
        # Layout manager
        # ---------------------------------------------------------------
        "layout": {
            "min_useful_height": 30,
            "scratch_min_height": 400,
        },
        # ---------------------------------------------------------------
        # Text generation
        # ---------------------------------------------------------------
        "text_gen": {
            "markov_tries": 50,
            "markov_max_words": 35,
            "short_max_chars": 80,
            "title_max_len": 60,
            "heading_max_len": 50,
            "table_rows_range": (4, 10),
            "footnote_count": (1, 4),
        },
        # ---------------------------------------------------------------
        # Text quality filters / language handling
        # ---------------------------------------------------------------
        "text": {
            # Minimum fraction of target-script letters required for a sampled
            # Markov sentence to be accepted (non-Latin languages only).
            "script_ratio_threshold": 0.5,
        },
        # ---------------------------------------------------------------
        # Page style pools (colors, margins, sizes)
        # ---------------------------------------------------------------
        "style": {
            "papers": {
                "cream": (0.98, 0.96, 0.91),
                "white": (1.0, 1.0, 1.0),
                "light_gray": (0.95, 0.95, 0.95),
                "aged": (0.96, 0.94, 0.88),
                "blue_white": (0.97, 0.97, 1.0),
                "warm_white": (0.99, 0.98, 0.95),
                "cool_gray": (0.94, 0.95, 0.96),
                "parchment": (0.95, 0.92, 0.85),
            },
            "text_colors": {
                "near_black": (0.10, 0.08, 0.06),
                "black": (0.0, 0.0, 0.0),
                "charcoal": (0.20, 0.20, 0.20),
                "dark_brown": (0.15, 0.12, 0.10),
                "sepia": (0.30, 0.20, 0.10),
                "warm_gray": (0.25, 0.22, 0.20),
                "dark_blue": (0.10, 0.10, 0.20),
                "navy_text": (0.12, 0.15, 0.30),
            },
            "text_color_weights": {
                "black": 30,
                "near_black": 25,
                "charcoal": 15,
                "dark_brown": 8,
                "warm_gray": 7,
                "sepia": 5,
                "dark_blue": 5,
                "navy_text": 5,
            },
            "accents": {
                "red": (0.55, 0.12, 0.10),
                "navy": (0.10, 0.30, 0.55),
                "forest": (0.15, 0.45, 0.25),
                "gold": (0.50, 0.35, 0.10),
                "purple": (0.35, 0.15, 0.50),
                "teal": (0.10, 0.40, 0.45),
                "burgundy": (0.45, 0.08, 0.18),
                "slate": (0.30, 0.35, 0.40),
            },
            "margin_presets": {
                # tight matches production-like scans (receipts, dense forms,
                # ledgers) where margins are ~2-3% of page width.
                "tight": {"top": 25, "bottom": 25, "left": 25, "right": 25},
                "narrow": {"top": 50, "bottom": 50, "left": 50, "right": 50},
                "normal": {"top": 70, "bottom": 70, "left": 70, "right": 70},
                "wide": {"top": 100, "bottom": 100, "left": 100, "right": 100},
                "academic": {"top": 80, "bottom": 80, "left": 90, "right": 70},
                "book": {"top": 90, "bottom": 80, "left": 110, "right": 70},
                "magazine": {"top": 60, "bottom": 60, "left": 55, "right": 55},
            },
            # Sampling weights for margin_presets. Skewed toward tight/narrow
            # to match what OCR pipelines actually see at inference time.
            "margin_preset_weights": {
                "tight": 25,
                "narrow": 25,
                "normal": 15,
                "magazine": 12,
                "academic": 10,
                "book": 8,
                "wide": 5,
            },
            "body_size_ranges": {
                "tiny": (5, 7),
                "small": (8, 9),
                "normal": (10, 11),
                "large": (12, 14),
            },
            "heading_size_multiplier": (1.6, 2.5),
            "subheading_size_multiplier": (1.1, 1.4),
            "tiny_size_multiplier": (0.5, 0.7),
            "line_spacing_range": (1.5, 4.0),
            "flag_probabilities": {
                "justify": 0.7,
                "has_header": 0.5,
                "has_page_number": 0.7,
                "has_page_border": 0.1,
                "has_edge_shadow": 0.25,
                "has_logo": 0.15,
                "has_banner": 0.12,
            },
        },
        # ---------------------------------------------------------------
        # Brand palettes: coordinated color schemes for themed docs
        # ---------------------------------------------------------------
        # Each palette provides: primary, secondary, accent, text_on_primary
        "brand_palettes": {
            "tech_blue": {
                "primary": (0.10, 0.35, 0.75),
                "secondary": (0.90, 0.93, 0.98),
                "accent": (0.95, 0.45, 0.15),
                "text_on_primary": (1.0, 1.0, 1.0),
            },
            "legal_navy": {
                "primary": (0.08, 0.15, 0.32),
                "secondary": (0.93, 0.90, 0.82),
                "accent": (0.60, 0.45, 0.15),
                "text_on_primary": (1.0, 0.98, 0.92),
            },
            "medical_teal": {
                "primary": (0.05, 0.45, 0.50),
                "secondary": (0.92, 0.96, 0.95),
                "accent": (0.85, 0.30, 0.35),
                "text_on_primary": (1.0, 1.0, 1.0),
            },
            "government": {
                "primary": (0.08, 0.20, 0.45),
                "secondary": (0.96, 0.94, 0.88),
                "accent": (0.65, 0.10, 0.15),
                "text_on_primary": (1.0, 1.0, 1.0),
            },
            "academic_crimson": {
                "primary": (0.50, 0.08, 0.15),
                "secondary": (0.94, 0.92, 0.88),
                "accent": (0.15, 0.25, 0.45),
                "text_on_primary": (1.0, 0.98, 0.95),
            },
            "corporate_gray": {
                "primary": (0.22, 0.24, 0.28),
                "secondary": (0.94, 0.94, 0.94),
                "accent": (0.95, 0.55, 0.10),
                "text_on_primary": (1.0, 1.0, 1.0),
            },
            "eco_green": {
                "primary": (0.15, 0.40, 0.22),
                "secondary": (0.94, 0.96, 0.90),
                "accent": (0.75, 0.55, 0.15),
                "text_on_primary": (1.0, 1.0, 1.0),
            },
        },
        # Probability of using a brand palette instead of random accent
        "brand_palette_probability": 0.3,
        # ---------------------------------------------------------------
        # Layout planner (block weights + flow templates)
        # ---------------------------------------------------------------
        "planner": {
            "block_weights": {
                "prose": 25,
                "table": 12,
                "math": 10,
                "code": 10,
                "image": 12,
                "multicolumn": 8,
                "list": 10,
                "blockquote": 5,
                "definition_list": 4,
                "subheading": 6,
                "rule": 4,
                "callout": 6,
                "form": 5,
            },
            "template_probability": 0.7,
            "tiny_text_probability": 0.4,
            "flow_templates": [
                # (weight, sequence_body)
                (20, ["prose", "subheading", "prose", "math", "prose", "table"]),
                (15, ["prose", "subheading", "prose", "table", "prose", "image"]),
                (10, ["prose", "math", "prose", "subheading", "prose", "math"]),
                (15, ["prose", "code", "prose", "subheading", "prose", "code"]),
                (10, ["prose", "code", "prose", "table", "prose"]),
                (10, ["prose", "list", "prose", "code", "prose"]),
                (10, ["prose", "table", "prose", "image", "prose"]),
                (8, ["prose", "image", "prose", "subheading", "prose", "table"]),
                (8, ["prose", "blockquote", "prose", "list"]),
                (8, ["prose", "definition_list", "prose", "table"]),
                (8, ["prose", "math", "prose", "math", "prose", "table", "prose"]),
                (6, ["prose", "multicolumn", "subheading", "prose", "table"]),
                (5, ["multicolumn", "rule", "prose", "image"]),
                (10, ["prose", "list"]),
                (8, ["prose", "table"]),
                (5, ["prose", "blockquote"]),
                (8, ["prose", "callout", "prose", "table"]),
                (6, ["callout", "prose", "list", "prose"]),
                # Form-style layouts
                (10, ["form", "form", "form"]),
                (8, ["prose", "form", "form"]),
                (6, ["form", "form", "prose", "form"]),
                (8, ["subheading", "form", "subheading", "form"]),
                (5, ["prose", "form", "table", "form"]),
            ],
        },
        # ---------------------------------------------------------------
        # Logo block (top-of-page branding)
        # ---------------------------------------------------------------
        "logo": {
            "styles": ["geometric", "monogram", "wordmark"],
            "height": 50,
            "shape_size": 36,
            "padding": 12,
            "text_size": 14,
            "shapes": ["square", "circle", "triangle", "rounded_square", "stacked"],
            "company_words": [
                "Alpha",
                "Beta",
                "Gamma",
                "Delta",
                "Nova",
                "Orion",
                "Apex",
                "Vertex",
                "Nexus",
                "Pinnacle",
                "Summit",
                "Horizon",
                "Quantum",
                "Meridian",
                "Atlas",
                "Forge",
                "Catalyst",
                "Prism",
                "Vector",
                "Element",
                "Matrix",
                "Spectrum",
                "Synergy",
                "Lumen",
                "Axis",
            ],
            "company_suffixes": [
                "Labs",
                "Corp",
                "Systems",
                "Group",
                "Research",
                "Institute",
                "Associates",
                "Partners",
                "Industries",
                "Technologies",
                "Works",
                "",
                "",
                "",  # sometimes no suffix
            ],
            "bottom_margin": 12,
        },
        # ---------------------------------------------------------------
        # Callout / info box block
        # ---------------------------------------------------------------
        "callout": {
            # Color palette only. The callout label is sampled from the
            # active TextSource per render via `_markov_short(lang, max_words)`,
            # so labels track the page language and stay diverse.
            "kinds": {
                "note": {"bg": (0.90, 0.93, 0.98), "border": (0.20, 0.40, 0.70)},
                "warning": {"bg": (0.98, 0.94, 0.80), "border": (0.75, 0.55, 0.10)},
                "danger": {"bg": (0.98, 0.90, 0.90), "border": (0.75, 0.15, 0.15)},
                "tip": {"bg": (0.90, 0.96, 0.90), "border": (0.15, 0.50, 0.25)},
                "info": {"bg": (0.92, 0.93, 0.96), "border": (0.30, 0.35, 0.55)},
            },
            "label_max_words": 2,
            "fallback_sizes": [9, 10, 11],
            "icon_size": 18,
            "bar_width": 4,
            "h_padding": 14,
            "v_padding": 10,
            "border_radius": 4,
            "bottom_margin": 14,
            "n_sentences": (1, 3),
        },
        # ---------------------------------------------------------------
        # Banner chrome (colored strip at top of page)
        # ---------------------------------------------------------------
        "banner": {
            "height_range": (45, 80),
            "title_size_offset": 4,  # added to heading_size
            "title_font_weight": "bold",
            "show_subtitle_probability": 0.4,
            "subtitle_size_offset": 0,  # relative to body_size
        },
        # ---------------------------------------------------------------
        # Form block (fill-in fields, checkboxes, signatures)
        # ---------------------------------------------------------------
        "form": {
            "fallback_sizes": [9, 10, 11],
            # Number of fields per form section
            "n_fields": (3, 8),
            # Weights for each field type
            "field_type_weights": {
                "text": 0.40,  # underlined or boxed text field
                "checkbox": 0.25,  # ☐ Label (or checked ☒)
                "radio": 0.10,  # ○ / ● Label
                "date": 0.10,  # MM / DD / YYYY
                "multiline": 0.08,  # large textarea-style box
                "signature": 0.07,  # signature line
            },
            # Visual style options
            "field_styles": ["underline", "boxed"],
            "field_style_probabilities": {"underline": 0.6, "boxed": 0.4},
            # Probability a text field is pre-filled with sample text
            "fill_probability": 0.85,
            # Probability a checkbox is checked (instead of empty)
            "check_probability": 0.6,
            # Layout
            "label_width_fraction": 0.35,  # fraction of width used for labels
            "field_height": 22,
            "row_spacing": 8,
            "section_title_probability": 0.8,
            "boxed_field_bg": (0.98, 0.98, 0.98),
            "boxed_field_border": (0.35, 0.35, 0.35),
            "boxed_field_border_width": 0.6,
            "underline_width": 0.8,
            "underline_color": (0.2, 0.2, 0.2),
            "checkbox_size": 11,
            "checkbox_border_width": 0.8,
            # Group box around the whole form section
            "section_border_probability": 0.4,
            "section_border_opacity": 0.3,
            "section_header_bg_probability": 0.5,
            "section_header_bg_opacity": 0.12,
            "bottom_margin": 14,
            # Numeric prefix probability (e.g. "1. Name", "2. Date")
            "number_fields_probability": 0.35,
        },
    }


# The global defaults instance. Deep-copy before mutating.
DEFAULTS = _defaults()


def get_defaults():
    """Return a mutable deep copy of the defaults."""
    return copy.deepcopy(DEFAULTS)
