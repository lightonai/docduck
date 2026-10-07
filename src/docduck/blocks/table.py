"""Table block: adaptive column widths, multiple visual styles."""

import random

from gi.repository import Pango, PangoCairo

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..table import gen as table_gen
from ._helpers import layout_height, maybe_highlight, pango_layout, pango_to_markdown
from ._registry import register_block


@register_block("table", weight=12)
def draw_table(
    ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, max_height=None, **kw
):
    d = D["table"]
    lang = kw.get("lang")
    spec = table_gen.gen_table(lang=lang)

    n_cols = spec.n_cols
    compact = getattr(spec, "compact_rows", False)
    row_h = random.randint(18, 22) if compact else random.randint(*d["row_height"])
    n_header_rows = len(spec.header_rows)
    header_row_h = row_h + d["header_height_pad"]
    total_header_h = header_row_h * n_header_rows
    # Dense tables use smaller font + tighter padding so 10-14 narrow
    # columns of compact numeric content fit without ellipsizing.
    font_size = 7 if compact else min(style.body_size if style else 9, d["font_size_cap"])

    data_rows = spec.data_rows
    # Randomly highlight a handful of non-label data cells (marker-pen look).
    # First-column row labels are excluded since real highlights usually mark
    # numeric values, not group names. Probability is low enough to stay a
    # noticeable-but-sparse signal in training data.
    highlight_prob = d.get("highlight_prob", 0.0)
    if highlight_prob > 0:
        data_rows = [
            [
                maybe_highlight(cell, highlight_prob)
                if (ci > 0 or not spec.has_row_headers)
                else cell
                for ci, cell in enumerate(row)
            ]
            for row in data_rows
        ]
    truncated_row_spans = dict(spec.row_spans)
    if max_height:
        available = max_height - d["caption_overhead"] - total_header_h - d["bottom_margin"]
        max_rows = max(1, int(available / row_h))
        if max_rows < len(data_rows):
            data_rows = data_rows[:max_rows]
            # Shrink any rowspan that would extend past the truncation; drop
            # rowspans whose anchor row was itself truncated away.
            fixed: dict = {}
            for (r0, c0), rs in truncated_row_spans.items():
                if r0 >= max_rows:
                    continue
                new_rs = min(rs, max_rows - r0)
                if new_rs > 1:
                    fixed[(r0, c0)] = new_rs
            truncated_row_spans = fixed

    header_font = (
        fonts.get("sans", font_size, bold=True) if fonts else f"DejaVu Sans Bold {font_size}"
    )
    body_font = fonts.get("serif", font_size) if fonts else f"DejaVu Serif {font_size}"
    row_header_font = header_font

    cell_pad = 6 if compact else d["cell_h_pad"]
    col_max_w = [0] * n_cols
    for hrow in spec.header_rows:
        ci = 0
        for hcell in hrow:
            layout = pango_layout(ctx, hcell.text, header_font, 9999)
            _, ext = layout.get_pixel_extents()
            need = ext.width + cell_pad * 2
            if hcell.colspan == 1:
                col_max_w[ci] = max(col_max_w[ci], need)
            else:
                # Spread a wide group-header's natural width across the columns
                # it spans (equally): otherwise wide labels like "Conversion
                # Regular" over 2 narrow cols get silently ellipsized.
                share = need // hcell.colspan
                for j in range(hcell.colspan):
                    if ci + j < n_cols:
                        col_max_w[ci + j] = max(col_max_w[ci + j], share)
            ci += hcell.colspan
    for row in data_rows[:8]:
        for ci, cell_text in enumerate(row):
            if ci < n_cols and cell_text:
                layout = pango_layout(ctx, cell_text, body_font, 9999)
                _, ext = layout.get_pixel_extents()
                col_max_w[ci] = max(col_max_w[ci], ext.width + cell_pad * 2)

    min_col_w = max(40, width // (n_cols * 3))
    col_max_w = [max(w, min_col_w) for w in col_max_w]
    total_natural = sum(col_max_w)
    if total_natural > 0:
        col_widths = [int(w / total_natural * width) for w in col_max_w]
        col_widths[-1] = width - sum(col_widths[:-1])
    else:
        col_widths = [width // n_cols] * n_cols

    table_style = spec.style or random.choice(d["styles"])
    has_stripes = random.random() < d["stripe_probability"]
    has_header_bg = random.random() < d["header_bg_probability"]
    # Borderless tables define columns purely by text alignment: no rules,
    # no tint, no stripes. The OCR model must infer structure from whitespace.
    if table_style == "borderless":
        has_stripes = False
        has_header_bg = False

    caption = spec.caption
    cap_font = (
        fonts.get("serif", font_size, bold=True) if fonts else f"DejaVu Serif Bold {font_size}"
    )
    ctx.move_to(x, y)
    cap_layout = pango_layout(ctx, caption, cap_font, width, alignment=Pango.Alignment.CENTER)
    ctx.set_source_rgb(*text_color)
    PangoCairo.show_layout(ctx, cap_layout)
    caption_h = layout_height(cap_layout) + d["caption_bottom_pad"]
    table_y = y + caption_h
    table_w = sum(col_widths)

    col_x_offsets = [0] * n_cols
    for ci in range(1, n_cols):
        col_x_offsets[ci] = col_x_offsets[ci - 1] + col_widths[ci - 1]

    def draw_cell(cx, cy, cw, ch, text, fstr, align=Pango.Alignment.LEFT, valign="center"):
        """Draw a cell and return the text actually rendered (truncated if needed).

        `valign`: "center" (default, vertically centers text in the cell box)
        or "top" (anchors text to the first row of a multi-row span). Top
        alignment is required for borderless rowspan labels: otherwise a
        6-row group label floats in mid-air with no rule to anchor it.
        """
        if not text:
            return ""
        ctx.save()
        inner_w = cw - cell_pad
        # Cells with <span bgcolor="…"> markup (highlighted values) need
        # markup mode so Pango paints the background. Ellipsize then can't
        # truncate cleanly through tags, so disable it: highlighted cells
        # are always short numbers, no risk of overflow in practice.
        is_markup = "<span" in text
        layout = pango_layout(ctx, text, fstr, inner_w, alignment=align, markup=is_markup)
        if not is_markup:
            layout.set_ellipsize(Pango.EllipsizeMode.END)
        _, ext = layout.get_pixel_extents()
        if valign == "top":
            # Align to the single-row zone at the top, matching non-spanned rows.
            ty = cy + (row_h - ext.height) / 2
        else:
            ty = cy + (ch - ext.height) / 2
        ctx.move_to(cx + cell_pad // 2, ty)
        ctx.set_source_rgb(*text_color)
        PangoCairo.show_layout(ctx, layout)
        ctx.restore()

        # Fidelity: if Pango ellipsized, figure out what was actually shown.
        if not layout.is_ellipsized():
            return text
        # Binary-search the longest prefix whose un-ellipsized layout fits
        # in inner_w. That prefix + "…" is what the viewer sees.
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            probe = pango_layout(ctx, text[:mid] + "…", fstr, 9999, alignment=align)
            _, probe_ext = probe.get_pixel_extents()
            if probe_ext.width <= inner_w:
                lo = mid
            else:
                hi = mid - 1
        return (text[:lo].rstrip() + "…") if lo > 0 else "…"

    def hline(ly, thick=False):
        ctx.set_source_rgb(*text_color)
        ctx.set_line_width(d["thick_line_width"] if thick else d["normal_line_width"])
        ctx.move_to(x, ly)
        ctx.line_to(x + table_w, ly)
        ctx.stroke()

    def vline(lx, y1, y2):
        ctx.set_source_rgba(*text_color, d["vline_opacity"])
        ctx.set_line_width(d["vline_width"])
        ctx.move_to(lx, y1)
        ctx.line_to(lx, y2)
        ctx.stroke()

    if table_style in ("booktabs", "bordered"):
        hline(table_y, thick=True)
    elif table_style == "grid":
        hline(table_y)

    # Draw header rows (capture rendered text for ground-truth fidelity)
    rendered_header_rows: list[list[tuple[str, int]]] = []  # [(text, colspan), ...]
    cur_y = table_y
    for hri, header_row in enumerate(spec.header_rows):
        if has_header_bg:
            ctx.set_source_rgba(*accent_color, d["header_bg_opacity"])
            ctx.rectangle(x, cur_y, table_w, header_row_h)
            ctx.fill()

        rendered_row: list[tuple[str, int]] = []
        col_offset = 0
        for hcell in header_row:
            cell_x = col_x_offsets[col_offset] if col_offset < n_cols else 0
            cell_w = sum(col_widths[col_offset : col_offset + hcell.colspan])
            shown = draw_cell(
                x + cell_x,
                cur_y,
                cell_w,
                header_row_h,
                hcell.text,
                header_font,
                align=Pango.Alignment.CENTER if hcell.colspan > 1 else Pango.Alignment.LEFT,
            )
            rendered_row.append((shown, hcell.colspan))
            col_offset += hcell.colspan
        rendered_header_rows.append(rendered_row)

        cur_y += header_row_h

        # Non-leaf header rows get `cmidrule`-style short horizontal rules
        # under each colspan'd cell, indicating exactly which columns the
        # group covers. This matches the LaTeX booktabs convention: much
        # clearer than the old partial-vertical-separator hack which only
        # drew inconsistent stubs on the first row.
        if hri < n_header_rows - 1 and table_style != "borderless":
            ctx.set_source_rgb(*text_color)
            ctx.set_line_width(d["normal_line_width"])
            col_offset_cm = 0
            for hcell in header_row:
                if hcell.colspan > 1:
                    right = col_offset_cm + hcell.colspan - 1
                    x1 = x + col_x_offsets[col_offset_cm] + cell_pad // 2
                    x2 = x + col_x_offsets[right] + col_widths[right] - cell_pad // 2
                    ctx.move_to(x1, cur_y)
                    ctx.line_to(x2, cur_y)
                    ctx.stroke()
                col_offset_cm += hcell.colspan
        elif hri == n_header_rows - 1:
            if table_style in ("booktabs", "bordered", "grid"):
                hline(cur_y, thick=(table_style == "booktabs"))
            elif table_style == "minimal":
                hline(cur_y)

    # Data rows (capture rendered cell text per cell for ground-truth fidelity)
    rendered_data_rows: list[list[str]] = []
    # Track rowspans and colspans per cell position. Cells covered by
    # either a rowspan from above or a colspan from the left are skipped
    # when drawing and when emitting <td>.
    row_spans = truncated_row_spans
    col_spans: dict = dict(spec.col_spans)
    covered: set[tuple[int, int]] = set()
    for (r0, c0), rs in row_spans.items():
        for offset in range(1, rs):
            covered.add((r0 + offset, c0))
    for (r0, c0), cs in col_spans.items():
        for offset in range(1, cs):
            covered.add((r0, c0 + offset))

    data_start_y = cur_y
    for ri, row in enumerate(data_rows):
        ry = data_start_y + ri * row_h
        is_empty_row = all(c == "" for c in row) and not any(
            (ri, c) in covered for c in range(n_cols)
        )

        if has_stripes and ri % 2 == 1 and not is_empty_row:
            ctx.set_source_rgba(*text_color, d["stripe_opacity"])
            ctx.rectangle(x, ry, table_w, row_h)
            ctx.fill()

        # Pad rows shorter than n_cols so rendered_row stays rectangular;
        # truncate overflow so HTML emission doesn't produce misaligned rows.
        row = list(row) + [""] * max(0, n_cols - len(row))
        row = row[:n_cols]

        rendered_row: list[str] = []
        for ci, cell in enumerate(row):
            if ci >= n_cols:
                rendered_row.append(cell)
                continue
            if (ri, ci) in covered:
                rendered_row.append("")  # placeholder: no <td> emitted
                continue
            is_row_header = spec.has_row_headers and ci == 0
            font = row_header_font if is_row_header else body_font
            rs = row_spans.get((ri, ci), 1)
            cs = col_spans.get((ri, ci), 1)
            cell_h = row_h * rs
            cell_w = sum(col_widths[ci : ci + cs])
            align = Pango.Alignment.CENTER if cs > 1 and ci > 0 else Pango.Alignment.LEFT
            # Borderless tables can't disambiguate a centered rowspan label
            # from surrounding blanks: anchor it to the top of the span,
            # matching how real financial reports render row groups.
            valign = "top" if table_style == "borderless" and rs > 1 else "center"
            shown = draw_cell(
                x + col_x_offsets[ci],
                ry,
                cell_w,
                cell_h,
                cell,
                font,
                align=align,
                valign=valign,
            )
            rendered_row.append(shown)
        rendered_data_rows.append(rendered_row)

        if table_style in ("grid", "bordered") and not is_empty_row:
            # Skip hline segments that would cut through a live rowspan.
            # A cell at (ri+1, ci) is covered iff the boundary falls inside its span.
            below_covered = {ci for ci in range(n_cols) if (ri + 1, ci) in covered}
            if not below_covered:
                hline(ry + row_h)
            else:
                seg_start = x
                ctx.set_source_rgb(*text_color)
                ctx.set_line_width(d["normal_line_width"])
                for ci in range(n_cols):
                    col_left = x + col_x_offsets[ci]
                    col_right = col_left + col_widths[ci]
                    if ci in below_covered:
                        if seg_start < col_left:
                            ctx.move_to(seg_start, ry + row_h)
                            ctx.line_to(col_left, ry + row_h)
                            ctx.stroke()
                        seg_start = col_right
                if seg_start < x + table_w:
                    ctx.move_to(seg_start, ry + row_h)
                    ctx.line_to(x + table_w, ry + row_h)
                    ctx.stroke()

    bottom = data_start_y + len(data_rows) * row_h

    if table_style in ("booktabs", "bordered"):
        hline(bottom, thick=True)
    elif table_style == "minimal":
        hline(bottom)

    # Vertical lines: skip the portions that cross through a colspan-covered
    # header cell, otherwise the vline cuts through the group label text.
    if table_style in ("grid", "bordered"):
        header_covered: list[set[int]] = []
        for header_row in spec.header_rows:
            # NOTE: this variable shadowed the outer `covered: set[tuple]`
            # before: which silently broke GT emission below. Keep it
            # distinctly named.
            hdr_cover: set[int] = set()
            col_off = 0
            for hcell in header_row:
                for b in range(col_off + 1, col_off + hcell.colspan):
                    hdr_cover.add(b)
                col_off += hcell.colspan
            header_covered.append(hdr_cover)

        # Per-data-row: which internal column boundaries are covered by a
        # data-cell colspan (so v-lines don't cut through spanning cells).
        data_col_covered: list[set[int]] = [set() for _ in data_rows]
        for (r0, c0), cs in col_spans.items():
            if r0 < len(data_col_covered):
                for b in range(c0 + 1, c0 + cs):
                    data_col_covered[r0].add(b)

        for ci in range(1, n_cols):
            y_cursor = table_y
            for hri in range(n_header_rows):
                if ci not in header_covered[hri]:
                    vline(x + col_x_offsets[ci], y_cursor, y_cursor + header_row_h)
                y_cursor += header_row_h
            # Data rows: draw per-row so we can skip rows where ci is colspan-covered.
            for ri in range(len(data_rows)):
                if ci not in data_col_covered[ri]:
                    vline(
                        x + col_x_offsets[ci],
                        y_cursor + ri * row_h,
                        y_cursor + (ri + 1) * row_h,
                    )

    # Ground truth HTML: use the *rendered* text (post-truncation) so the
    # transcription matches what's actually visible on the page.
    gt_lines = [f"## {caption}", "", "<table>", "  <thead>"]
    for rendered_row in rendered_header_rows:
        gt_lines.append("    <tr>")
        for text_shown, colspan in rendered_row:
            cs = f' colspan="{colspan}"' if colspan > 1 else ""
            gt_lines.append(f"      <th{cs}>{text_shown}</th>")
        gt_lines.append("    </tr>")
    gt_lines.append("  </thead>")
    gt_lines.append("  <tbody>")
    for ri, row in enumerate(rendered_data_rows):
        gt_lines.append("    <tr>")
        for ci, cell in enumerate(row):
            if (ri, ci) in covered:
                continue  # covered by a row/col span
            tag = "th" if spec.has_row_headers and ci == 0 else "td"
            rs = row_spans.get((ri, ci), 1)
            cs_val = col_spans.get((ri, ci), 1)
            rs_attr = f' rowspan="{rs}"' if rs > 1 else ""
            cs_attr = f' colspan="{cs_val}"' if cs_val > 1 else ""
            # Convert any highlight span inside the cell to ==value== so the
            # ground truth marks highlighted data without leaking raw Pango.
            cell_md = pango_to_markdown(cell) if "<span" in cell else cell
            gt_lines.append(f"      <{tag}{rs_attr}{cs_attr}>{cell_md}</{tag}>")
        gt_lines.append("    </tr>")
    gt_lines.append("  </tbody>")
    gt_lines.append("</table>")
    ground_truth = "\n".join(gt_lines)

    return BlockResult(
        height=bottom - y + d["bottom_margin"],
        text=ground_truth,
        data={
            "caption": spec.caption,
            "header_rows": [[t for t, _ in row] for row in rendered_header_rows],
            "data_rows": rendered_data_rows,
            "n_cols": n_cols,
        },
    )
