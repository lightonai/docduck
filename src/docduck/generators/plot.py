"""Generate matplotlib plots as Cairo surfaces for image placeholders."""

import io
import random

import cairo
import numpy as np

from ..defaults import DEFAULTS as D

_WARMED_UP = False


def _warmup():
    """Render a throwaway plot so matplotlib's font cache / renderer state
    is initialized before the first real call. Without this, the very first
    ``gen_plot_surface`` call in a process produces different pixels than
    subsequent calls with the same seed: breaking batch reproducibility.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(1, 1), dpi=50)
    ax.plot([0, 1], [0, 1])
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=50)
    plt.close(fig)


def gen_plot_surface(width, height, seed=None):
    """Generate a random matplotlib plot and return it as a Cairo ImageSurface.

    Returns (surface, plot_type) where plot_type is a string like "scatter".
    """
    global _WARMED_UP
    if not _WARMED_UP:
        _warmup()
        _WARMED_UP = True

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # All randomness must come from `seed` so two calls with the same seed
    # produce byte-identical output regardless of the caller's global state.
    if seed is not None:
        rng = np.random.default_rng(seed)
        local_random = random.Random(seed)
    else:
        rng = np.random.default_rng()
        local_random = random.Random()

    dpi = D["plot"]["dpi"]
    fig_w = width / dpi
    fig_h = height / dpi

    plot_type = local_random.choice(
        [
            "scatter",
            "line",
            "bar",
            "histogram",
            "box",
            "pie",
        ]
    )

    # Randomize style: scoped via style.context so this call doesn't mutate
    # matplotlib's global rcParams, which would desync subsequent batches.
    style = local_random.choice(["default", "ggplot", "seaborn-v0_8-whitegrid", "bmh"])
    try:
        style_ctx = plt.style.context(style)
    except Exception:
        style_ctx = plt.rc_context()

    with style_ctx:
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
        # Transparent figure background: docduck paints the page's paper
        # color underneath, and a hard white matplotlib rectangle looked out
        # of place on tinted / aged papers. The axes patch keeps whatever the
        # style dictates (e.g. ggplot's light-grey plot area) so styled charts
        # still look like charts, not just scattered glyphs.
        fig.patch.set_alpha(0.0)

        if plot_type == "scatter":
            n = rng.integers(20, 80)
            x = rng.normal(0, 1, n)
            y = x * rng.uniform(0.3, 2.0) + rng.normal(0, 0.5, n)
            colors = rng.uniform(0.2, 0.8, (n, 3))
            sizes = rng.uniform(10, 80, n)
            ax.scatter(x, y, c=colors, s=sizes, alpha=0.7, edgecolors="gray", linewidths=0.5)
            _random_labels(ax, rng, "scatter")

        elif plot_type == "line":
            n_lines = rng.integers(1, 5)
            x = np.linspace(0, rng.uniform(5, 20), rng.integers(20, 60))
            for _ in range(n_lines):
                noise = rng.normal(0, 0.3, len(x))
                y = np.cumsum(rng.normal(0, 1, len(x))) + noise
                ax.plot(x, y, alpha=0.8, linewidth=rng.uniform(0.8, 2.0))
            _random_labels(ax, rng, "line")

        elif plot_type == "bar":
            n = rng.integers(4, 10)
            labels = [f"{'ABCDEFGHIJ'[i]}" for i in range(n)]
            values = rng.uniform(1, 100, n)
            colors = [plt.cm.tab10(i / n) for i in range(n)]
            ax.bar(labels, values, color=colors, alpha=0.8, edgecolor="gray", linewidth=0.5)
            _random_labels(ax, rng, "bar")

        elif plot_type == "histogram":
            n = rng.integers(100, 500)
            dist = local_random.choice(["normal", "uniform", "bimodal"])
            if dist == "normal":
                data = rng.normal(rng.uniform(-2, 2), rng.uniform(0.5, 2.0), n)
            elif dist == "uniform":
                data = rng.uniform(-3, 3, n)
            else:
                data = np.concatenate(
                    [
                        rng.normal(-1.5, 0.6, n // 2),
                        rng.normal(1.5, 0.6, n - n // 2),
                    ]
                )
            ax.hist(data, bins=rng.integers(10, 30), alpha=0.7, edgecolor="gray", linewidth=0.5)
            _random_labels(ax, rng, "histogram")

        elif plot_type == "box":
            n_groups = rng.integers(3, 7)
            data = [
                rng.normal(rng.uniform(-2, 2), rng.uniform(0.5, 2), rng.integers(20, 60))
                for _ in range(n_groups)
            ]
            ax.boxplot(
                data, patch_artist=True, boxprops=dict(alpha=0.7), medianprops=dict(color="black")
            )
            ax.set_xticklabels([f"G{i + 1}" for i in range(n_groups)])
            _random_labels(ax, rng, "box")

        elif plot_type == "pie":
            n = rng.integers(3, 7)
            values = rng.uniform(1, 10, n)
            labels = [f"{'ABCDEFG'[i]}" for i in range(n)]
            ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=rng.integers(0, 360))

        fig.tight_layout(pad=0.5)

        # Render to PNG bytes, then load as Cairo surface. ``transparent=True``
        # preserves the figure's alpha channel (we set it to 0 above) so Cairo
        # composites the plot onto docduck's paper color cleanly.
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=dpi,
            bbox_inches="tight",
            transparent=True,
            edgecolor="none",
        )
        plt.close(fig)
        buf.seek(0)
        surface = cairo.ImageSurface.create_from_png(buf)
        return surface, plot_type


_AXIS_LABELS = {
    "scatter": (
        ["x", "Time (s)", "Distance (m)", "Feature 1", "Concentration"],
        ["y", "Response", "Velocity (m/s)", "Feature 2", "Absorbance"],
    ),
    "line": (
        ["Time", "Epoch", "Iteration", "x", "Step"],
        ["Value", "Loss", "Accuracy", "Temperature (K)", "Signal"],
    ),
    "bar": (
        ["Category", "Group", "Model", "Method", "Region"],
        ["Count", "Score", "Value", "Frequency", "Percentage"],
    ),
    "histogram": (["Value", "Score", "Measurement", "x"], ["Frequency", "Count", "Density"]),
    "box": (
        ["Group", "Condition", "Treatment", "Dataset"],
        ["Value", "Score", "Measurement", "Response"],
    ),
}


def _random_labels(ax, rng, plot_type):
    """Add random axis labels and optional title."""
    if plot_type in _AXIS_LABELS:
        xlabels, ylabels = _AXIS_LABELS[plot_type]
        if rng.random() > 0.3:
            ax.set_xlabel(rng.choice(xlabels), fontsize=8)
        if rng.random() > 0.3:
            ax.set_ylabel(rng.choice(ylabels), fontsize=8)
    if rng.random() > 0.6:
        ax.set_title("")  # most real figures have captions, not titles
