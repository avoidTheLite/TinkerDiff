import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import convert_latex_delimiters as cld

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
REPO = HERE.parent.parent


def run_cli(args):
    """Run the CLI quietly and return its exit code."""
    with contextlib.redirect_stdout(io.StringIO()):
        return cld.main(args)


class ConvertTests(unittest.TestCase):
    def test_inline_and_block_from_documentation_example(self):
        raw = (
            "Recall (e.g., \\(x_{1}\\) = Memory Saturation) is governed by:\n"
            "\\[\\frac{\\partial P}{\\partial t}=-A\\frac{\\partial P}{\\partial x}-R\\cdot P\\]\n"
        )
        out = cld.convert_latex_delimiters(raw)
        self.assertIn("$x_{1}$", out)
        self.assertIn("$$\\frac{\\partial P}{\\partial t}=-A\\frac{\\partial P}{\\partial x}-R\\cdot P$$", out)
        self.assertNotIn("\\(", out)
        self.assertNotIn("\\[", out)
        self.assertTrue(cld.verify_conversion(raw, out))

    def test_multiline_block(self):
        raw = "\\[\na = b\n\\]\n"
        self.assertEqual(cld.convert_latex_delimiters(raw), "$$\na = b\n$$\n")

    def test_inline_padding_is_trimmed(self):
        self.assertEqual(cld.convert_latex_delimiters("\\( e = R f \\)"), "$e = R f$")

    def test_latex_line_break_inside_block_is_preserved(self):
        raw = "\\[\na = 1 \\\\[2pt]\nb = 2\n\\]"
        out = cld.convert_latex_delimiters(raw)
        self.assertEqual(out, "$$\na = 1 \\\\[2pt]\nb = 2\n$$")
        self.assertTrue(cld.verify_conversion(raw, out))

    def test_code_is_untouched(self):
        raw = "Use `\\( x \\)` here.\n```\n\\[ y \\]\n```\n"
        self.assertEqual(cld.convert_latex_delimiters(raw), raw)

    def test_escaped_dollar_is_not_math(self):
        raw = "Cost \\$10 and \\(x\\) and \\$20."
        out = cld.convert_latex_delimiters(raw)
        self.assertEqual(out, "Cost \\$10 and $x$ and \\$20.")
        self.assertTrue(cld.verify_conversion(raw, out))

    def test_idempotent(self):
        raw = "A \\(x\\) and\n\\[y\\]\n"
        once = cld.convert_latex_delimiters(raw)
        self.assertEqual(cld.convert_latex_delimiters(once), once)


class GoldenFileTests(unittest.TestCase):
    """A known Markdown file with a hand-written expected result."""

    def test_sample_matches_expected(self):
        original = (FIXTURES / "sample.md").read_text()
        expected = (FIXTURES / "sample.expected.md").read_text()
        converted = cld.convert_latex_delimiters(original)
        self.assertEqual(converted, expected)
        self.assertEqual(cld.verification_problems(original, converted), [])

    def test_sample_math_inventory(self):
        spans = cld.extract_math((FIXTURES / "sample.md").read_text(), "legacy")
        kinds = [k for k, _ in spans]
        self.assertEqual(kinds.count("block"), 3)
        self.assertEqual(kinds.count("inline"), 3)

    def test_cli_write_then_check(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "sample.md"
            f.write_text((FIXTURES / "sample.md").read_text())
            self.assertEqual(run_cli(["--check", str(f)]), 1)   # legacy delimiters present
            self.assertEqual(run_cli(["--write", str(f)]), 0)
            self.assertEqual(f.read_text(), (FIXTURES / "sample.expected.md").read_text())
            self.assertEqual(run_cli(["--check", str(f)]), 0)   # nothing left to convert


class VerifierTests(unittest.TestCase):
    ORIGINAL = "Inline \\(a+b\\) and\n\\[c=d\\]\n"

    def test_accepts_faithful_conversion(self):
        self.assertTrue(cld.verify_conversion(self.ORIGINAL, "Inline $a+b$ and\n$$c=d$$\n"))

    def test_rejects_changed_math(self):
        self.assertFalse(cld.verify_conversion(self.ORIGINAL, "Inline $a-b$ and\n$$c=d$$\n"))

    def test_rejects_dropped_equation(self):
        self.assertFalse(cld.verify_conversion(self.ORIGINAL, "Inline $a+b$ and\n"))

    def test_rejects_swapped_kind(self):
        self.assertFalse(cld.verify_conversion(self.ORIGINAL, "Inline $$a+b$$ and\n$c=d$\n"))

    def test_rejects_changed_prose(self):
        self.assertFalse(cld.verify_conversion(self.ORIGINAL, "Inlines $a+b$ and\n$$c=d$$\n"))

    def test_rejects_leftover_legacy_delimiters(self):
        self.assertFalse(cld.verify_conversion(self.ORIGINAL, "Inline $a+b$ and\n\\[c=d\\]\n"))


class SafetyTests(unittest.TestCase):
    def test_unescaped_dollar_in_prose_blocks_conversion(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.md"
            f.write_text("It costs $10 and \\(x\\).\n")
            self.assertEqual(run_cli(["--write", str(f)]), 1)
            self.assertIn("\\(x\\)", f.read_text())  # untouched

    def test_pipe_in_table_math_warns(self):
        warnings = cld.lint_github_math("| a |\n| $|x|$ |\n")
        self.assertTrue(any("splits the cell" in w for w in warnings))

    def test_html_page_lists_every_equation(self):
        original = (FIXTURES / "sample.md").read_text()
        page = cld.build_qa_page([("sample.md", original, cld.convert_latex_delimiters(original), [])])
        self.assertEqual(page.count('<div class="comparison-grid">'), 6)
        self.assertIn("cdn.jsdelivr.net/npm/mathjax", page)


class RepoDocsTests(unittest.TestCase):
    """The real documentation converts faithfully (checked on a copy, not in place)."""

    def test_repo_docs_convert_and_verify(self):
        files = sorted((REPO / "engineering-components").rglob("*.md")) + [REPO / "README.md"]
        for path in files:
            original = path.read_text()
            if not cld.extract_math(original, "legacy") and "$" in original.replace("\\$", ""):
                continue  # already converted
            if cld.find_ambiguous_dollars(original):
                self.fail(f"{path}: unescaped $ in prose")
            converted = cld.convert_latex_delimiters(original)
            self.assertEqual(cld.verification_problems(original, converted), [], str(path))


if __name__ == "__main__":
    unittest.main()
