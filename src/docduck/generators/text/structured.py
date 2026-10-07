"""Structured-content generators.

Anything that is not a free-form paragraph but is still produced by the
text generator: list items, definition lists, blockquotes, footnotes,
tabular data, and source-code snippets in eight languages.
"""

import random

from ... import config
from .modes import _apply_mode
from .sentences import _NOUNS, _make_sentence, _markov_short

# ---------------------------------------------------------------------------
# Lists, blockquotes, footnotes, definitions
# ---------------------------------------------------------------------------


def gen_list_items(n=None, lang: str = None) -> list[str]:
    """Generate list items (plain text sentences)."""
    if n is None:
        n = random.randint(3, 8)
    return [_apply_mode(_make_sentence(lang)) for _ in range(n)]


def gen_blockquote(lang: str = None) -> str:
    """Generate a blockquote (1-3 sentences)."""
    n = random.randint(1, 3)
    text = " ".join(_make_sentence(lang) for _ in range(n))
    return _apply_mode(text)


def gen_definition_items(n=None, lang: str = None) -> list[tuple[str, str]]:
    """Generate definition list items as (term, definition) pairs."""
    if n is None:
        n = random.randint(3, 6)
    items = []
    for _ in range(n):
        term = _markov_short(lang)
        if not term:
            term = random.choice(_NOUNS).capitalize()
        else:
            term = term.rstrip(".").rstrip(",")
            if len(term) > 30:
                term = term[:27].rsplit(" ", 1)[0]
        defn = " ".join(_make_sentence(lang) for _ in range(random.randint(1, 2)))
        items.append((_apply_mode(term), _apply_mode(defn)))
    return items


def gen_footnotes(n=None, lang: str = None) -> str:
    """Generate footnotes."""
    if n is None:
        n = random.randint(1, 4)
    notes = []
    for i in range(1, n + 1):
        notes.append(f"{i}. {_apply_mode(_make_sentence(lang))}")
    return "\n".join(notes)


# ---------------------------------------------------------------------------
# Table data
# ---------------------------------------------------------------------------


def gen_table_data(headers=None, n_rows=None):
    """Generate random table data."""
    if headers is None:
        headers = random.choice(config.TABLE_HEADERS_POOL)
    if n_rows is None:
        n_rows = random.randint(4, 10)

    rows = []
    for _ in range(n_rows):
        row = []
        for h in headers:
            h_lower = h.lower()
            if any(k in h_lower for k in ["year"]):
                row.append(str(random.randint(1990, 2025)))
            elif any(k in h_lower for k in ["population", "area"]):
                row.append(f"{random.randint(100, 99999):,}")
            elif any(k in h_lower for k in ["%", "score", "accuracy", "efficacy"]):
                row.append(f"{random.uniform(0.1, 99.9):.1f}")
            elif any(k in h_lower for k in ["p-value"]):
                row.append(f"{random.uniform(0.001, 0.1):.3f}")
            elif any(k in h_lower for k in ["$", "gdp"]):
                row.append(f"{random.uniform(10, 9999):.1f}")
            elif any(k in h_lower for k in ["no", "number"]):
                row.append(str(random.randint(1, 118)))
            elif any(
                k in h_lower
                for k in [
                    "weight",
                    "dose",
                    "temp",
                    "wind",
                    "humidity",
                    "latency",
                    "wavelength",
                    "frequency",
                    "energy",
                    "error",
                    "value",
                ]
            ):
                row.append(f"{random.uniform(0.1, 999.9):.2f}")
            elif any(k in h_lower for k in ["symbol"]):
                row.append(
                    random.choice(
                        ["H", "He", "Li", "C", "N", "O", "Fe", "Ag", "Au", "U", "Na", "K", "Ca"]
                    )
                )
            elif any(k in h_lower for k in ["color"]):
                row.append(
                    random.choice(
                        ["Red", "Blue", "Green", "Violet", "Yellow", "Orange", "Infrared"]
                    )
                )
            elif any(k in h_lower for k in ["model", "drug", "parameter"]):
                row.append(random.choice(_NOUNS).capitalize())
            elif any(k in h_lower for k in ["city", "country"]):
                row.append(
                    random.choice(
                        [
                            "London",
                            "Paris",
                            "Tokyo",
                            "Berlin",
                            "Sydney",
                            "Mumbai",
                            "Cairo",
                            "Toronto",
                            "Seoul",
                            "Lima",
                        ]
                    )
                )
            elif any(k in h_lower for k in ["element"]):
                row.append(
                    random.choice(
                        [
                            "Hydrogen",
                            "Helium",
                            "Carbon",
                            "Nitrogen",
                            "Oxygen",
                            "Iron",
                            "Silver",
                            "Gold",
                            "Uranium",
                            "Sodium",
                        ]
                    )
                )
            else:
                row.append(f"{random.uniform(1, 100):.2f}")
        rows.append(row)
    return headers, rows


# ---------------------------------------------------------------------------
# Code snippets: Python is weighted highest, then SQL, then the rest.
# ---------------------------------------------------------------------------


def gen_code_snippet():
    """Generate a random code-like snippet. Returns (language, code)."""
    gen = random.choice(
        [
            _gen_python_snippet,
            _gen_python_snippet,  # weighted higher: most common in docs
            _gen_sql_snippet,
            _gen_rust_snippet,
            _gen_javascript_snippet,
            _gen_c_snippet,
            _gen_go_snippet,
            _gen_bash_snippet,
        ]
    )
    return gen()


def _rand_var():
    return random.choice(
        ["x", "y", "z", "data", "result", "val", "tmp", "arr", "buf", "n", "idx", "count", "total"]
    )


def _rand_func():
    return random.choice(
        [
            "compute",
            "process",
            "transform",
            "analyze",
            "validate",
            "parse",
            "encode",
            "decode",
            "train",
            "predict",
            "evaluate",
            "optimize",
            "fetch",
            "update",
            "filter",
            "aggregate",
        ]
    )


def _rand_type():
    return random.choice(["int", "float", "str", "bool", "list", "dict"])


def _gen_python_snippet():
    style = random.choice(["function", "class", "loop", "comprehension", "decorator"])
    if style == "function":
        name = _rand_func()
        args = ", ".join(
            random.sample(
                [
                    "data",
                    "config",
                    "threshold=0.5",
                    "verbose=False",
                    "n_iter=100",
                    "batch_size=32",
                    "lr=0.001",
                ],
                random.randint(1, 3),
            )
        )
        body_lines = []
        if random.random() < 0.4:
            body_lines.append('    """Process input data and return results."""')
        body_lines.append("    result = []")
        body_lines.append("    for i in range(len(data)):")
        op = random.choice(
            [
                "data[i] * 2",
                "data[i] ** 2",
                "data[i] + offset",
                "max(data[i], threshold)",
                "data[i] / total",
            ]
        )
        body_lines.append(f"        result.append({op})")
        if random.random() < 0.5:
            body_lines.append("    return np.array(result)")
        else:
            body_lines.append("    return result")
        return ("python", f"def {name}({args}):\n" + "\n".join(body_lines))
    elif style == "class":
        name = random.choice(["Model", "Dataset", "Config", "Pipeline", "Tokenizer", "Encoder"])
        attrs = random.sample(
            [
                "hidden_size",
                "num_layers",
                "dropout",
                "vocab_size",
                "learning_rate",
                "batch_size",
                "max_length",
            ],
            random.randint(2, 4),
        )
        init_args = ", ".join(attrs)
        init_body = "\n".join(f"        self.{a} = {a}" for a in attrs)
        method = random.choice(["forward", "fit", "predict", "encode", "__call__"])
        return (
            "python",
            f"class {name}:\n    def __init__(self, {init_args}):\n{init_body}\n\n"
            f"    def {method}(self, x):\n        return self.layer(x)",
        )
    elif style == "loop":
        var = _rand_var()
        n = random.choice(["n", "len(data)", "num_epochs", "100"])
        lines = [f"for i in range({n}):"]
        lines.append(
            f"    {var} = {random.choice(['alpha', 'beta', '0.9'])} * {var} + {random.choice(['(1 - alpha)', 'delta', '0.1'])} * data[i]"
        )
        lines.append(f"    if {var} > threshold:")
        lines.append(f"        results.append({var})")
        if random.random() < 0.4:
            lines.append("        count += 1")
        return ("python", "\n".join(lines))
    elif style == "comprehension":
        return (
            "python",
            random.choice(
                [
                    'filtered = [x for x in data if x > threshold]\nscaled = [x / max(filtered) for x in filtered]\nprint(f"Kept {len(filtered)}/{len(data)} samples")',
                    "pairs = {k: v for k, v in zip(keys, values) if v is not None}\nresult = sorted(pairs.items(), key=lambda x: x[1], reverse=True)",
                    "matrix = [[row[j] for j in selected_cols] for row in data]\nassert len(matrix) == len(data)",
                ]
            ),
        )
    else:  # decorator
        return (
            "python",
            random.choice(
                [
                    "@torch.no_grad()\ndef evaluate(model, dataloader):\n    model.eval()\n    total_loss = 0.0\n    for batch in dataloader:\n        output = model(batch)\n        total_loss += output.loss.item()\n    return total_loss / len(dataloader)",
                    "import functools\n\ndef retry(max_attempts=3):\n    def decorator(func):\n        @functools.wraps(func)\n        def wrapper(*args, **kwargs):\n            for attempt in range(max_attempts):\n                try:\n                    return func(*args, **kwargs)\n                except Exception as e:\n                    if attempt == max_attempts - 1:\n                        raise\n        return wrapper\n    return decorator",
                ]
            ),
        )


def _gen_sql_snippet():
    tables = random.sample(
        ["users", "orders", "products", "experiments", "results", "metrics", "logs", "events"], 2
    )
    cols = random.sample(
        ["name", "id", "created_at", "score", "status", "total", "count", "accuracy", "category"],
        random.randint(2, 4),
    )
    agg = random.choice(["COUNT(*)", "AVG(score)", "SUM(total)", "MAX(accuracy)"])
    condition = random.choice(
        ["score > 0.95", "status = 'active'", "created_at > '2024-01-01'", "category IS NOT NULL"]
    )
    lines = [f"SELECT {', '.join(cols)}, {agg} AS agg_val"]
    lines.append(f"FROM {tables[0]} t")
    if random.random() < 0.6:
        lines.append(f"JOIN {tables[1]} r ON t.id = r.{tables[0][:-1]}_id")
    lines.append(f"WHERE {condition}")
    if random.random() < 0.5:
        lines.append(f"GROUP BY {cols[0]}")
    lines.append("ORDER BY agg_val DESC")
    if random.random() < 0.4:
        lines.append(f"LIMIT {random.choice([10, 20, 50, 100])};")
    else:
        lines[-1] += ";"
    return ("sql", "\n".join(lines))


def _gen_rust_snippet():
    return (
        "rust",
        random.choice(
            [
                "fn compute(data: &[f64]) -> f64 {\n    let sum: f64 = data.iter().sum();\n    let mean = sum / data.len() as f64;\n    let var = data.iter()\n        .map(|x| (x - mean).powi(2))\n        .sum::<f64>() / data.len() as f64;\n    var.sqrt()\n}",
                "fn parse_config(path: &str) -> Result<Config, Error> {\n    let content = fs::read_to_string(path)?;\n    let config: Config = serde_json::from_str(&content)?;\n    Ok(config)\n}",
                "impl Iterator for Fibonacci {\n    type Item = u64;\n\n    fn next(&mut self) -> Option<Self::Item> {\n        let result = self.a;\n        let new_b = self.a + self.b;\n        self.a = self.b;\n        self.b = new_b;\n        Some(result)\n    }\n}",
            ]
        ),
    )


def _gen_javascript_snippet():
    return (
        "javascript",
        random.choice(
            [
                "async function fetchData(url, options = {}) {\n  const response = await fetch(url, options);\n  if (!response.ok) {\n    throw new Error(`HTTP ${response.status}`);\n  }\n  return response.json();\n}",
                "const pipeline = data\n  .filter(item => item.score > threshold)\n  .map(item => ({\n    ...item,\n    normalized: item.score / maxScore,\n  }))\n  .sort((a, b) => b.normalized - a.normalized);",
                "class EventEmitter {\n  constructor() {\n    this.listeners = new Map();\n  }\n\n  on(event, callback) {\n    if (!this.listeners.has(event)) {\n      this.listeners.set(event, []);\n    }\n    this.listeners.get(event).push(callback);\n  }\n}",
            ]
        ),
    )


def _gen_c_snippet():
    return (
        "c",
        random.choice(
            [
                "void quicksort(int *arr, int lo, int hi) {\n    if (lo >= hi) return;\n    int pivot = arr[hi];\n    int i = lo - 1;\n    for (int j = lo; j < hi; j++) {\n        if (arr[j] <= pivot)\n            swap(&arr[++i], &arr[j]);\n    }\n    swap(&arr[i + 1], &arr[hi]);\n    quicksort(arr, lo, i);\n    quicksort(arr, i + 2, hi);\n}",
                "typedef struct {\n    float *data;\n    int rows;\n    int cols;\n} Matrix;\n\nMatrix *matrix_alloc(int rows, int cols) {\n    Matrix *m = malloc(sizeof(Matrix));\n    m->data = calloc(rows * cols, sizeof(float));\n    m->rows = rows;\n    m->cols = cols;\n    return m;\n}",
            ]
        ),
    )


def _gen_go_snippet():
    return (
        "go",
        random.choice(
            [
                "func worker(id int, jobs <-chan int, results chan<- int) {\n    for j := range jobs {\n        result := process(j)\n        results <- result\n    }\n}",
                'type Config struct {\n    Host     string `json:"host"`\n    Port     int    `json:"port"`\n    Workers  int    `json:"workers"`\n    Timeout  time.Duration\n}\n\nfunc LoadConfig(path string) (*Config, error) {\n    data, err := os.ReadFile(path)\n    if err != nil {\n        return nil, err\n    }\n    var cfg Config\n    return &cfg, json.Unmarshal(data, &cfg)\n}',
            ]
        ),
    )


def _gen_bash_snippet():
    return (
        "bash",
        random.choice(
            [
                '#!/bin/bash\nset -euo pipefail\n\nfor file in data/*.csv; do\n    echo "Processing $file"\n    python3 transform.py --input "$file" \\\n        --output "output/$(basename "$file" .csv).parquet"\ndone\necho "Done: $(ls output/ | wc -l) files processed"',
                '#!/bin/bash\nDATA_DIR="${1:-.}"\nTHRESHOLD=${2:-0.95}\n\nfind "$DATA_DIR" -name "*.log" -mtime -7 | while read -r log; do\n    errors=$(grep -c "ERROR" "$log" || true)\n    if [ "$errors" -gt 0 ]; then\n        echo "$log: $errors errors"\n    fi\ndone',
            ]
        ),
    )
