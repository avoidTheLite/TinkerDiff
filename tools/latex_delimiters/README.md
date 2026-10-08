# LaTeX delimiter converter

Converts Markdown math from `\( … \)` / `\[ … \]` to `$ … $` / `$$ … $$` (the syntax GitHub renders) and verifies that nothing else changed.

```
python3 tools/latex_delimiters/convert_latex_delimiters.py PATH...             # dry run
python3 tools/latex_delimiters/convert_latex_delimiters.py --write PATH...     # convert in place
python3 tools/latex_delimiters/convert_latex_delimiters.py --check PATH...     # exit 1 if legacy delimiters remain
python3 tools/latex_delimiters/convert_latex_delimiters.py --html qa.html PATH...   # side-by-side MathJax page
python3 -m unittest discover -s tools/latex_delimiters                         # run the tests
```

## What it does and does not touch

- Converts only prose. Fenced code blocks, inline code spans, escaped dollars (`\$`), and the LaTeX line break `\\[2pt]` are left alone.
- Trims padding in inline math (`\( x \)` becomes `$x$`) because GitHub does not render padded inline math.
- Refuses to write a file that contains an unescaped `$` in prose, since it would be misread as math afterwards.

## Verification

After converting, each file is checked for: the same number, order, and kind (inline or display) of equations; identical equation text; identical surrounding prose; identical code; and no legacy delimiters left. A file that fails is not written.

It also warns about constructs GitHub's renderer mishandles, such as a `|` inside math in a table row.

## Visual check

`--html` writes a page that renders every equation twice, original delimiters on the left and converted on the right. Both columns should look identical. The page loads MathJax from a CDN, so it needs network access when opened. Generate it before running `--write`, because it compares the files' current legacy text with the conversion.
