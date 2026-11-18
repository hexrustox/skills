"""Render the static HTML report for a description optimization loop."""

import html
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_STYLE = """
  :root {
    --bg: #f6f5f0;
    --surface: #ffffff;
    --border: #dedbd1;
    --text: #1b1a17;
    --muted: #6f6b60;
    --accent: #b4492d;
    --good: #4b6b2f;
    --good-bg: #edf3e6;
    --bad: #a12f2f;
    --bad-bg: #f9e9e7;
    --mono: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 1.5rem; background: var(--bg); color: var(--text); font-family: var(--sans); }
  h1 { margin: 0 0 0.25rem; font-size: 1.35rem; }
  .subtitle { color: var(--muted); margin-bottom: 1rem; }
  .summary, .explainer { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.9rem 1rem; margin-bottom: 1rem; }
  .summary p { margin: 0.3rem 0; }
  .summary strong { display: inline-block; min-width: 7rem; }
  .best { color: var(--good); font-weight: 650; }
  .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }
  table { border-collapse: collapse; width: 100%; font-size: 0.8rem; }
  th, td { border-bottom: 1px solid var(--border); padding: 0.45rem 0.55rem; text-align: left; vertical-align: top; }
  th { background: #1b1a17; color: #f6f5f0; font-weight: 600; white-space: nowrap; }
  th.test-col { background: #35556f; }
  th.positive { border-bottom: 3px solid var(--good); }
  th.negative { border-bottom: 3px solid var(--bad); }
  td.description { font-family: var(--mono); font-size: 0.72rem; min-width: 18rem; max-width: 32rem; white-space: pre-wrap; }
  td.result { text-align: center; white-space: nowrap; }
  td.test-result { background: #f0f5f8; }
  .pass { color: var(--good); font-weight: 650; }
  .fail { color: var(--bad); font-weight: 650; }
  .rate { display: block; color: var(--muted); font-size: 0.65rem; font-weight: 400; }
  .score { display: inline-block; border-radius: 4px; padding: 0.1rem 0.35rem; font-weight: 650; }
  .score-good { background: var(--good-bg); color: var(--good); }
  .score-bad { background: var(--bad-bg); color: var(--bad); }
  tr.best-row td { background: #f3f7ee; }
  .legend { display: flex; gap: 1rem; flex-wrap: wrap; margin: 0.75rem 0; color: var(--muted); font-size: 0.78rem; }
  .swatch { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 2px; vertical-align: -0.1rem; }
  .swatch-train { background: #1b1a17; }
  .swatch-test { background: #35556f; }
  .swatch-good { border-bottom: 3px solid var(--good); background: #fff; }
  .swatch-bad { border-bottom: 3px solid var(--bad); background: #fff; }
  footer { margin-top: 1rem; color: var(--muted); font-size: 0.75rem; }
"""


def generate_report(
    data: Mapping[str, Any],
    *,
    auto_refresh: bool = False,
    skill_name: str = "",
) -> str:
    """Render a standalone description optimization report.

    ``auto_refresh`` adds a meta refresh tag for the live page written while
    the loop is running. The final report omits it.
    """
    history = _history(data)
    train_queries = _queries(history, "train_results")
    test_queries = _queries(history, "test_results")
    best_iteration = data.get("best_iteration")
    name = skill_name or _text(data.get("skill_name")) or "skill"
    refresh = '  <meta http-equiv="refresh" content="5">\n' if auto_refresh else ""
    basis = "test" if test_queries else "train"

    parts = [
        "<!DOCTYPE html>\n",
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n',
        refresh,
        f"  <title>{html.escape(name)} description optimization</title>\n",
        f"  <style>{_STYLE}</style>\n",
        "</head>\n<body>\n",
        f"  <h1>{html.escape(name)} description optimization</h1>\n",
        (
            '  <div class="subtitle">Each row is a description attempt. '
            "Train queries drive the improvement prompt; test queries are held out and "
            "choose the best description. The page is generated from saved results.</div>\n"
        ),
        '  <div class="explainer">',
        (
            "The optimizer sees only train failures and prior train results. "
            "Test results are evaluated for scoring and never included in the improvement prompt."
        ),
        "</div>\n",
    ]

    parts.extend(_summary(data, basis))
    parts.append(
        '  <div class="legend">'
        '<span><span class="swatch swatch-train"></span> Train query</span>'
        '<span><span class="swatch swatch-test"></span> Test query</span>'
        '<span><span class="swatch swatch-good"></span> Should trigger</span>'
        '<span><span class="swatch swatch-bad"></span> Should not trigger</span>'
        "</div>\n"
    )

    parts.append('  <div class="table-wrap">\n<table>\n<thead>\n<tr>\n')
    parts.append("  <th>Iter</th>\n  <th>Train</th>\n  <th>Test</th>\n")
    parts.append('  <th class="description">Description</th>\n')
    for query in train_queries:
        css = "positive" if query["should_trigger"] else "negative"
        parts.append(f'  <th class="{css}">{html.escape(query["query"])}</th>\n')
    for query in test_queries:
        css = "positive" if query["should_trigger"] else "negative"
        parts.append(
            f'  <th class="test-col {css}">{html.escape(query["query"])}</th>\n'
        )
    parts.append("</tr>\n</thead>\n<tbody>\n")

    for entry in history:
        iteration = entry.get("iteration")
        row_class = ' class="best-row"' if iteration == best_iteration else ""
        train_passed = _int(entry.get("train_passed"))
        train_total = _int(entry.get("train_total"))
        test_passed = _int(entry.get("test_passed"))
        test_total = _int(entry.get("test_total"))
        parts.append(f"<tr{row_class}>\n")
        parts.append(f"  <td>{html.escape(str(iteration))}</td>\n")
        parts.append(
            f'  <td><span class="score {_score_class(train_passed, train_total)}">'
            f"{train_passed}/{train_total}</span></td>\n"
        )
        parts.append(
            f'  <td><span class="score {_score_class(test_passed, test_total)}">'
            f"{test_passed}/{test_total}</span></td>\n"
        )
        parts.append(
            f'  <td class="description">{html.escape(_text(entry.get("description")))}</td>\n'
        )
        train_results = _result_map(entry.get("train_results"))
        for query in train_queries:
            parts.append(_result_cell(train_results.get(query["query"]), "result"))
        test_results = _result_map(entry.get("test_results"))
        for query in test_queries:
            parts.append(
                _result_cell(test_results.get(query["query"]), "result test-result")
            )
        parts.append("</tr>\n")

    parts.append("</tbody>\n</table>\n</div>\n")
    parts.append(
        "  <footer>Generated by <code>scripts.description_loop</code>. "
        "No server and no network are required.</footer>\n"
    )
    parts.append("</body>\n</html>\n")
    return "".join(parts)


def write_report(
    path: Path,
    data: Mapping[str, Any],
    *,
    auto_refresh: bool = False,
    skill_name: str = "",
) -> Path:
    """Write the report to ``path`` and return it."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        generate_report(data, auto_refresh=auto_refresh, skill_name=skill_name),
        encoding="utf-8",
    )
    return destination


def _summary(data: Mapping[str, Any], basis: str) -> list[str]:
    best_score = _text(data.get("best_score")) or "n/a"
    rows = [
        ("Original", _text(data.get("original_description"))),
        ("Best", _text(data.get("best_description"))),
        ("Last attempt", _text(data.get("final_description"))),
        ("Best score", f"{best_score} ({basis})"),
        ("Best iteration", str(data.get("best_iteration", "n/a"))),
        ("Iterations", str(data.get("iterations_run", 0))),
        (
            "Split",
            f"train {data.get('train_size', '?')} / test {data.get('test_size', '?')}",
        ),
        ("Model", _text(data.get("model")) or "n/a"),
    ]
    parts = ['  <div class="summary">\n']
    for label, value in rows:
        css = ' class="best"' if label == "Best" else ""
        parts.append(
            f"    <p{css}><strong>{label}:</strong> {html.escape(value)}</p>\n"
        )
    exit_reason = _text(data.get("exit_reason"))
    if exit_reason:
        parts.append(f"    <p><strong>Exit:</strong> {html.escape(exit_reason)}</p>\n")
    parts.append("  </div>\n")
    return parts


def _history(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("history")
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def _queries(history: Sequence[Mapping[str, Any]], field: str) -> list[dict[str, Any]]:
    for entry in history:
        results = entry.get(field)
        if isinstance(results, list):
            queries: list[dict[str, Any]] = []
            for result in results:
                if not isinstance(result, dict):
                    continue
                query = result.get("query")
                if isinstance(query, str):
                    queries.append(
                        {
                            "query": query,
                            "should_trigger": bool(result.get("should_trigger")),
                        }
                    )
            return queries
    return []


def _result_map(raw: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, list):
        return {}
    return {
        result["query"]: result
        for result in raw
        if isinstance(result, dict) and isinstance(result.get("query"), str)
    }


def _result_cell(result: dict[str, Any] | None, css_class: str) -> str:
    if result is None:
        return f'  <td class="{css_class}">n/a</td>\n'
    passed = result.get("pass") is True
    label = "PASS" if passed else "FAIL"
    css = "pass" if passed else "fail"
    rates = f"{result.get('triggers', 0)}/{result.get('runs', 0)}"
    return (
        f'  <td class="{css_class}"><span class="{css}">{label}</span>'
        f'<span class="rate">{rates}</span></td>\n'
    )


def _score_class(passed: int, total: int) -> str:
    if total > 0 and passed / total >= 0.8:
        return "score-good"
    if total > 0 and passed / total >= 0.5:
        return "score"
    return "score-bad"


def _int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""
