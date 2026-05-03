# Cross-implementation tests

Generic harness that runs single-line djot inputs through every installed
implementation, extracts a comparison key from each HTML output, and
"votes" on the consensus result.

## Layout

- `run.py` — the harness. `python3 tests/run.py <scenario>`
- `cases/<name>.txt` — one test scenario per file.
- `results/<name>.txt` — last persisted run, committed for diff visibility.

## Case file formats

**`lines`** (one input per line):

    ## comment
    # heading one
    # heading two

**`blocks`** (multi-line cases, separated by `=== name ===`):

    ## comment
    === case-name ===
    multi-line
    djot input

    === another case ===
    > more djot

In both formats, lines starting with `##` are comments.

## Adding a scenario

Drop a cases file under `cases/`, then register it in `SCENARIOS` in
`run.py` with `format` (`lines` or `blocks`), `display` (`table` or
`detail`), and an `extract` function that pulls the comparison key
out of the HTML output. Each scenario shares the same `IMPLS` list.

## Implementations

`run.py` looks for the binaries that `sh/install-djots.sh` installs:
`~/.cargo/bin/jotdown`, `~/.cabal/bin/djoths`, `~/.luarocks/bin/djot`,
`~/go/bin/godjot`, `~/.local/djot-php/djot-php`, plus any `djot` under
`~/.nvm/versions/node/*/bin/`. Missing implementations are reported and
skipped.
