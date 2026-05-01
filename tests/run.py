#!/usr/bin/env python3
"""Run djot test cases across multiple implementations and vote on results.

Usage: tests/run.py <scenario>

A scenario is a (cases_file, extractor) pair registered in SCENARIOS.
Each non-blank, non-`##` line in the cases file is a single djot input.
Each implementation is invoked with the line on stdin; the extractor
pulls a comparison key from the HTML output. Results are tabulated and
the most common key wins the vote.
"""
from __future__ import annotations

import collections
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path(os.environ["HOME"])


@dataclass
class Impl:
    name: str
    candidates: list[list[str]]   # each candidate is argv; first that resolves wins

    def resolve(self) -> list[str] | None:
        for argv in self.candidates:
            p = Path(argv[0])
            if p.exists():
                return argv
        return None

    def available(self) -> bool:
        return self.resolve() is not None

    def run(self, src: str) -> str:
        argv = self.resolve()
        if argv is None:
            return "<MISSING>"
        try:
            r = subprocess.run(
                argv, input=src, capture_output=True,
                text=True, timeout=15,
            )
            return r.stdout if r.returncode == 0 else f"<ERR:{r.returncode}>{r.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "<TIMEOUT>"


def _npm_djot_paths() -> list[list[str]]:
    """Find @djot/djot in nvm/global node_modules."""
    paths = []
    nvm = HOME / ".nvm/versions/node"
    if nvm.exists():
        for v in nvm.iterdir():
            paths.append([str(v / "bin/djot")])
    paths.append(["/tmp/djot-js/node_modules/.bin/djot"])
    paths.append(["/usr/local/bin/djot-js"])
    return paths


IMPLS = [
    Impl("Rust",       [[str(HOME / ".cargo/bin/jotdown")]]),
    Impl("JavaScript", _npm_djot_paths()),
    Impl("Go",         [[str(HOME / "go/bin/godjot")]]),
    Impl("Lua",        [[str(HOME / ".luarocks/bin/djot")],
                        ["/usr/local/bin/djot"]]),
    Impl("PHP",        [[str(HOME / ".local/djot-php/djot-php")],
                        ["/tmp/djot-php/djot-php"]]),
    Impl("Haskell",    [[str(HOME / ".cabal/bin/djoths")]]),
]


# --- Extractors ----------------------------------------------------------

def extract_section_id(html: str) -> str:
    """Pull the id attribute off the first <section> or <h1>..<h6>."""
    if html.startswith("<ERR") or html in ("<TIMEOUT>", "<MISSING>"):
        return html
    m = re.search(r'<(?:section|h[1-6])\b[^>]*\bid="([^"]*)"', html)
    return m.group(1) if m else "<NO-ID>"


# --- Scenarios -----------------------------------------------------------

SCENARIOS = {
    "ids": {
        "cases": "tests/cases/ids.txt",
        "extract": extract_section_id,
        "title": "Heading ID building",
    },
}


def load_cases(path: Path) -> list[str]:
    out = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("##"):
            continue
        out.append(line)
    return out


def vote(results: dict[str, str]) -> tuple[str, int]:
    """Most common (non-error) value wins. Returns (winner, count)."""
    counts = collections.Counter(
        v for v in results.values()
        if not v.startswith("<")
    )
    if not counts:
        return ("<no consensus>", 0)
    winner, n = counts.most_common(1)[0]
    return (winner, n)


def main() -> int:
    scenario = sys.argv[1] if len(sys.argv) > 1 else "ids"
    cfg = SCENARIOS[scenario]
    cases = load_cases(ROOT / cfg["cases"])
    extract = cfg["extract"]

    impls = [i for i in IMPLS if i.available()]
    missing = [i.name for i in IMPLS if not i.available()]
    if missing:
        print(f"# missing: {', '.join(missing)}")
    print(f"# scenario: {cfg['title']} — {len(cases)} cases × {len(impls)} impls\n")

    # Run all cases × impls.
    grid: list[tuple[str, dict[str, str], str, int]] = []
    for src in cases:
        per_impl = {i.name: extract(i.run(src + "\n")) for i in impls}
        winner, n = vote(per_impl)
        grid.append((src, per_impl, winner, n))

    # Tabulate. Each impl column is sized to its widest value.
    col_w = {
        i.name: max(len(i.name), max(len(r[i.name]) for _, r, *_ in grid))
        for i in impls
    }
    src_w = max(len("input"), max(len(s) for s, *_ in grid))
    parts = [f"{'input':<{src_w}}"]
    parts += [f"{i.name:<{col_w[i.name]}}" for i in impls]
    parts += ["agree", "consensus"]
    header = "  ".join(parts)
    print(header)
    print("-" * len(header))
    for src, results, winner, n in grid:
        row = [f"{src:<{src_w}}"]
        for i in impls:
            v = results[i.name]
            mark = " " if v == winner else "*"
            row.append(f"{mark}{v:<{col_w[i.name]-1}}")
        row.append(f"{n}/{len(impls)}")
        row.append(winner)
        print("  ".join(row))

    # Per-impl divergence summary.
    print("\n# per-impl divergences from consensus:")
    name_w = max(len(i.name) for i in impls)
    for i in impls:
        diffs = sum(1 for _, r, w, _ in grid if r[i.name] != w)
        print(f"  {i.name:<{name_w}} {diffs}/{len(grid)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
