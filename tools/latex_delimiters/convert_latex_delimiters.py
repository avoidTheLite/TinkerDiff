#!/usr/bin/env python3
"""Convert LaTeX math delimiters in Markdown from \\( \\) / \\[ \\] to $ / $$.

    \\( x \\)   ->  $x$        (inline)
    \\[ x \\]   ->  $$x$$      (display)

Only prose is converted. Fenced code blocks, inline code spans, escaped
dollar signs (\\$), and the LaTeX line break \\\\[ are left alone. After
converting, the result is verified: the same math in the same order and kind,
identical surrounding text, identical code, and no legacy delimiters left.

Usage:
    convert_latex_delimiters.py PATH...              dry run: report per file
    convert_latex_delimiters.py --write PATH...      convert in place (only files that verify)
    convert_latex_delimiters.py --check PATH...      exit 1 if any legacy delimiter or problem remains
    convert_latex_delimiters.py --html OUT PATH...   write a side-by-side MathJax QA page (no file changes)

PATH may be a Markdown file or a directory (searched recursively for *.md).
"""
import argparse
import html
import re
import sys
from pathlib import Path

# Fenced code blocks (``` or ~~~) and single-backtick inline code.
_CODE_RE = re.compile(
    r"(?ms)^[ \t]*(?P<fence>```|~~~).*?^[ \t]*(?P=fence)[^\n]*$|`[^`\n]*`"
)

# Legacy delimiters. The lookbehind skips a LaTeX line break such as \\[2pt].
_BLOCK_LEGACY = r"(?<!\\)\\\[(.*?)(?<!\\)\\\]"
_INLINE_LEGACY = r"(?<!\\)\\\((.*?)(?<!\\)\\\)"
LEGACY_RE = re.compile(f"{_BLOCK_LEGACY}|{_INLINE_LEGACY}", re.DOTALL)
_BLOCK_LEGACY_RE = re.compile(_BLOCK_LEGACY, re.DOTALL)
_INLINE_LEGACY_RE = re.compile(_INLINE_LEGACY)  # inline math must stay on one line

# New delimiters. A backslash before $ escapes it.
NEW_RE = re.compile(
    r"(?<!\\)\$\$(?P<block>.*?)(?<!\\)\$\$|(?<!\\)\$(?P<inline>[^\n$]+?)(?<!\\)\$",
    re.DOTALL,
)
_BARE_DOLLAR_RE = re.compile(r"(?<!\\)\$")


def split_code(text):
    """Split text into [(is_code, segment), ...] preserving order and content."""
    parts, pos = [], 0
    for m in _CODE_RE.finditer(text):
        if m.start() > pos:
            parts.append((False, text[pos:m.start()]))
        parts.append((True, m.group(0)))
        pos = m.end()
    if pos < len(text):
        parts.append((False, text[pos:]))
    return parts


def _convert_prose(segment):
    # Display first, so its content is never mistaken for inline math.
    segment = _BLOCK_LEGACY_RE.sub(lambda m: "$$" + m.group(1) + "$$", segment)
    # GitHub does not render $ x $ with padding, so inline content is trimmed.
    segment = _INLINE_LEGACY_RE.sub(lambda m: "$" + m.group(1).strip() + "$", segment)
    return segment


def convert_latex_delimiters(text):
    """Return text with legacy math delimiters replaced; code is untouched."""
    return "".join(
        seg if is_code else _convert_prose(seg) for is_code, seg in split_code(text)
    )


def _extract(text, style):
    """Return (spans, skeleton, code_segments) for the given delimiter style.

    spans: [(kind, content)] in document order, kind in {"block", "inline"}.
    skeleton: prose with each math span replaced by a placeholder.
    """
    spans, skeleton, code = [], [], []
    for is_code, seg in split_code(text):
        if is_code:
            code.append(seg)
            skeleton.append("\x00CODE\x00")
            continue
        last = 0
        regex = LEGACY_RE if style == "legacy" else NEW_RE
        for m in regex.finditer(seg):
            skeleton.append(seg[last:m.start()])
            if style == "legacy":
                kind = "block" if m.group(1) is not None else "inline"
                content = m.group(1) if kind == "block" else m.group(2)
            else:
                kind = "block" if m.group("block") is not None else "inline"
                content = m.group(kind)
            spans.append((kind, content))
            skeleton.append("\x00MATH\x00")
            last = m.end()
        skeleton.append(seg[last:])
    return spans, "".join(skeleton), code


def extract_math(text, style="legacy"):
    """Public helper: [(kind, stripped content)] for 'legacy' or 'new' delimiters."""
    return [(k, c.strip()) for k, c in _extract(text, style)[0]]


def find_ambiguous_dollars(text):
    """Line numbers of unescaped $ in prose outside code and outside math.

    Such a dollar sign would pair with another one and be read as math once the
    document uses $ delimiters, so it must be escaped (\\$) before converting.
    """
    lines = []
    offset = 0
    for is_code, seg in split_code(text):
        if not is_code:
            prose = LEGACY_RE.sub(lambda m: "\x00" * len(m.group(0)), seg)
            prose = NEW_RE.sub(lambda m: "\x00" * len(m.group(0)), prose)
            for m in _BARE_DOLLAR_RE.finditer(prose):
                lines.append(text.count("\n", 0, offset + m.start()) + 1)
        offset += len(seg)
    return lines


def verification_problems(original, converted):
    """Return a list of human-readable problems; empty means the conversion is faithful."""
    problems = []
    o_spans, o_skel, o_code = _extract(original, "legacy")
    c_spans, c_skel, c_code = _extract(converted, "new")

    if len(o_spans) != len(c_spans):
        problems.append(f"math span count differs: {len(o_spans)} original vs {len(c_spans)} converted")
    for i, (o, c) in enumerate(zip(o_spans, c_spans), 1):
        if o[0] != c[0]:
            problems.append(f"span {i}: kind changed {o[0]} -> {c[0]}")
        elif o[1].strip() != c[1].strip():
            problems.append(f"span {i}: content changed: {o[1].strip()!r} -> {c[1].strip()!r}")
    if o_skel != c_skel:
        problems.append("text outside math changed")
    if o_code != c_code:
        problems.append("code blocks/spans changed")
    leftover = _extract(converted, "legacy")[0]
    if leftover:
        problems.append(f"{len(leftover)} legacy delimiter pair(s) remain")
    return problems


def verify_conversion(original_text, converted_text):
    """True when the conversion is faithful (see verification_problems)."""
    return not verification_problems(original_text, converted_text)


def lint_github_math(text):
    """Warnings for constructs GitHub's math renderer commonly mishandles."""
    warnings = []
    # Blank out code (keeping line structure) so documented examples are not linted.
    text = "".join(re.sub(r"[^\n]", " ", seg) if is_code else seg for is_code, seg in split_code(text))
    for n, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("|"):
            for m in NEW_RE.finditer(line):
                body = m.group("block") if m.group("block") is not None else m.group("inline")
                if "|" in body:
                    warnings.append(f"line {n}: '|' inside math in a table row splits the cell")
        for m in NEW_RE.finditer(line):
            if m.group("inline") is not None and m.group("inline") != m.group("inline").strip():
                warnings.append(f"line {n}: inline math has leading/trailing space")
    return warnings


# ---------------------------------------------------------------- visual QA page

_PAGE_HEAD = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>LaTeX Conversion Visual QA</title>
    <!-- Configure MathJax to recognize both delimiter styles -->
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            }
        };
    </script>
    <script async src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js"></script>
    <style>
        body { font-family: sans-serif; margin: 40px; }
        .comparison-grid { display: flex; gap: 40px; }
        .column { flex: 1; padding: 20px; border: 1px solid #ccc; border-radius: 6px; overflow-x: auto; }
        h2 { border-bottom: 2px solid #eee; padding-bottom: 5px; }
        .file { margin-top: 48px; }
        .row { margin: 16px 0; }
        .ok { color: #1a7f37; font-weight: bold; }
        .bad { color: #cf222e; font-weight: bold; }
        code { background: #f6f8fa; padding: 1px 4px; }
    </style>
</head>
<body>
    <h1>Math Rendering Verification</h1>
    <p>For every equation, both columns should render visually identical output.</p>
"""


def _qa_row(kind, content, idx):
    content = content.strip()
    esc = html.escape(content)
    if kind == "block":
        left, right = f"\\[{esc}\\]", f"$${esc}$$"
        label = "Block"
    else:
        left, right = f"\\({esc}\\)", f"${esc}$"
        label = "Inline"
    return (
        f'<div class="row"><b>#{idx} {label}</b>\n'
        f'<div class="comparison-grid">\n'
        f'<div class="column"><h2>1. Original (&#92;( and &#92;[)</h2><div>{left}</div></div>\n'
        f'<div class="column"><h2>2. Converted (&#36; and &#36;&#36;)</h2><div>{right}</div></div>\n'
        f"</div></div>\n"
    )


def build_qa_page(results):
    """results: [(path, original_text, converted_text, problems)] -> HTML string."""
    total = sum(len(_extract(o, "legacy")[0]) for _, o, _, _ in results)
    bad = sum(1 for *_, p in results if p)
    out = [_PAGE_HEAD]
    status = '<span class="ok">all files verified</span>' if not bad else f'<span class="bad">{bad} file(s) failed</span>'
    out.append(f"<p>{total} equation(s) in {len(results)} file(s): {status}.</p>\n")
    for path, original, converted, problems in results:
        spans = _extract(original, "legacy")[0]
        verdict = '<span class="ok">verified</span>' if not problems else '<span class="bad">FAILED</span>'
        out.append(f'<div class="file"><h2><code>{html.escape(str(path))}</code>: {len(spans)} equation(s), {verdict}</h2>\n')
        for p in problems:
            out.append(f'<p class="bad">{html.escape(p)}</p>\n')
        for i, (kind, content) in enumerate(spans, 1):
            out.append(_qa_row(kind, content, i))
        out.append("</div>\n")
    out.append("</body>\n</html>\n")
    return "".join(out)


# ---------------------------------------------------------------- CLI

def _collect(paths):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.is_file():
            files.append(p)
        else:
            raise SystemExit(f"not found: {p}")
    return files


def process_file(path):
    """Return (original, converted, problems, warnings)."""
    original = Path(path).read_text(encoding="utf-8")
    problems = []
    for ln in find_ambiguous_dollars(original):
        problems.append(f"line {ln}: unescaped '$' in prose; escape it as \\$ before converting")
    converted = convert_latex_delimiters(original)
    if converted != original:  # nothing to verify when the file is already converted
        problems += verification_problems(original, converted)
    return original, converted, problems, lint_github_math(converted)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="convert files in place (only files that verify)")
    mode.add_argument("--check", action="store_true", help="fail if legacy delimiters or problems remain")
    ap.add_argument("--html", metavar="OUT", help="write a side-by-side visual QA page and make no changes")
    args = ap.parse_args(argv)

    failed = False
    results = []
    for path in _collect(args.paths):
        original, converted, problems, warnings = process_file(path)
        n_blocks = sum(1 for k, _ in _extract(original, "legacy")[0] if k == "block")
        n_inline = sum(1 for k, _ in _extract(original, "legacy")[0] if k == "inline")
        results.append((path, original, converted, problems))
        changed = converted != original
        tag = "CONVERT" if changed else "ok     "
        print(f"{tag} {path}: {n_blocks} block, {n_inline} inline")
        for p in problems:
            print(f"   PROBLEM: {p}")
        for w in warnings:
            print(f"   warning: {w}")
        if problems or (args.check and changed):
            failed = True
        if args.write and changed and not problems and not args.html:
            Path(path).write_text(converted, encoding="utf-8")
            print(f"   written")

    if args.html:
        Path(args.html).write_text(build_qa_page(results), encoding="utf-8")
        print(f"wrote {args.html}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
