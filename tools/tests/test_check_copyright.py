"""Tests for tools/check_copyright.py - one per check firing, one per check
staying quiet on a clean file, plus every regression case from the two audits
that shaped it: the first (four holes, every one a check that silently did
nothing on unexpected input) and the second (sixty attacks, sixteen through -
scope, quotation glyphs, HTML structure, verbatim fences, aggregates, and
bytes that did not match their names). The third pass (the `Z` cases below)
tuned the prose rules against the threat model in the checker's docstring:
every accident-shaped hole closed with a regression test, and every false
positive on legitimate scholarly prose closed with a NEGATIVE test that must
never fire again. The fourth pass (the `B`, `F` and `H` cases) came from an
independent verifier's harness: the guard flagging its own source, elisions
and word-processor apostrophes, frontmatter and HTML attributes fed to the
quote rules, a doctest prompt read as a blockquote, and a whole paper pasted
with `Abstract` as a bare line. The fifth pass (the `R` cases) came from the
review of pull request #9: the two ZIP signatures that are not the local-file
header, tracked symlinks, UTF-8-clean rasters under prose names, an SVG
`<image>` tag whose href hid behind a quoted `>`, a pull request that DELETES
the guard rather than editing it, `check_copyright.py .` selecting nothing,
a base-ref fetch on every run, and a hook that tested the worktree only.
The sixth pass added `commit_attribution` and the commit-msg hook tests: the
history is meant to read as one person's work, so both halves of that rule -
the hook locally, the checker on the pull request - are held by tests here.

One rule of this file: the PDF header bytes are never written out literally
in its first two kilobytes (`PDF_BYTES` below is built by concatenation),
because the checker sniffs every non-prose file, this one included, and
would refuse the commit that ships it. A test at the end holds that line.

Each test builds a real throwaway git repository under tmp_path, because the
checker enumerates files with `git ls-files -z` and reads `--staged` files from
the index; a fake listing would test a different program. Every negative test
asserts the SPECIFIC check name, never merely a non-zero exit.

Standard library + pytest only, like the checker itself.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import check_copyright as cc  # noqa: E402

SCRIPT = TOOLS / "check_copyright.py"

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64
# Concatenated on purpose: see the module docstring (B1).
PDF_BYTES = b"%PDF" + b"-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"

ATTRIBUTION = (
    "\n## Source and attribution\n\n- **Paper:** A paper\n\n"
    "The summary above is my own words.\n"
)

# A drawing made of shapes: its own editable source.
SVG_SHAPES = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
              '<rect x="1" y="1" width="8" height="8"/><path d="M0 0L10 10"/></svg>\n')


@pytest.fixture(autouse=True)
def _start_as_if_local(monkeypatch):
    """Every test begins outside GitHub Actions.

    The suite also runs ON Actions, as the guard's self-test, where the runner
    exports GITHUB_BASE_REF=main. That switches the self-edit rules on inside
    every temporary fixture repository, which has no such branch to fetch, and
    turned the first pull request after the guard landed red on six unrelated
    tests. The tests that exercise those rules set the variables themselves.
    """
    for name in ("GITHUB_ACTIONS", "GITHUB_BASE_REF", "GITHUB_HEAD_REF"):
        monkeypatch.delenv(name, raising=False)


def svg_with_image(href: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
            f'<image width="10" height="10" {href}/></svg>\n')


def words(n: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def summary(body: str = "Own words about the paper.\n", attribution: bool = True) -> str:
    return "# Title\n\n## TL;DR\n\n" + body + (ATTRIBUTION if attribution else "")


# ---------------------------------------------------------------------------
# a throwaway git repository per test
# ---------------------------------------------------------------------------

def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root),
         "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false",
         "-c", "core.hooksPath=.no-hooks-here", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0, f"git {' '.join(args)} failed: {proc.stderr}"
    return proc.stdout


def write(root: Path, files: dict) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")


BASELINE = {
    "README.md": "# Notebook\n\nA public research notebook.\n",
    "docs/00-intro.md": "# How this works\n\nProse, in my own words.\n",
    "summaries/03-foundation-models/clean.md": summary(),
    "assets/figures/net.png": PNG_BYTES,
    "assets/figures/net.source.yml": "origin: redrawn\nsource: https://example.invalid/paper\nlicense: CC BY 4.0\n",
    "assets/figures/net.svg": "<svg xmlns='http://www.w3.org/2000/svg'/>\n",
}


def make_repo(tmp_path: Path, files: dict | None = None, commit: bool = True) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    write(root, {**BASELINE, **(files or {})})
    git(root, "add", "-A", "--force")
    if commit:
        git(root, "commit", "-q", "--no-verify", "-m", "init")
    return root


def run(root: Path, mode: str = "all", paths: list[str] | None = None) -> list[cc.Finding]:
    return cc.gather(root, mode, paths)


def checks(findings: list[cc.Finding], path: str | None = None) -> set[str]:
    return {f.check for f in findings if path is None or f.path == path}


def only(findings: list[cc.Finding], check: str) -> list[cc.Finding]:
    return [f for f in findings if f.check == check]


# ---------------------------------------------------------------------------
# the baseline is clean
# ---------------------------------------------------------------------------

def test_baseline_repo_is_clean(tmp_path):
    assert run(make_repo(tmp_path)) == []


# ---------------------------------------------------------------------------
# no_third_party_pdf
# ---------------------------------------------------------------------------

def test_pdf_uppercase_extension_is_caught(tmp_path):
    root = make_repo(tmp_path, {"paper.PDF": PDF_BYTES})
    assert "no_third_party_pdf" in checks(run(root), "paper.PDF")


def test_pdf_anywhere_including_assets_figures_is_caught(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.pdf": PDF_BYTES,
                                "assets/figures/x.source.yml": ""})
    found = checks(run(root), "assets/figures/x.pdf")
    # The audit case: caught twice, by the PDF rule AND the provenance rule.
    assert "no_third_party_pdf" in found
    assert "image_provenance" in found


def test_pdf_rule_quiet_on_markdown(tmp_path):
    root = make_repo(tmp_path, {"docs/paper-notes.md": "# Notes\n\nNot a pdf.\n"})
    assert "no_third_party_pdf" not in checks(run(root))


# ---------------------------------------------------------------------------
# pdf_magic_bytes
# ---------------------------------------------------------------------------

def test_pdf_bytes_without_extension_are_caught(tmp_path):
    root = make_repo(tmp_path, {"docs/img/scan": PDF_BYTES})
    found = checks(run(root), "docs/img/scan")
    assert "pdf_magic_bytes" in found
    assert "no_third_party_pdf" not in found          # the name rule alone misses it


def test_pdf_bytes_behind_bak_extension_are_caught(tmp_path):
    root = make_repo(tmp_path, {"assets/paper.pdf.bak": PDF_BYTES})
    assert "pdf_magic_bytes" in checks(run(root), "assets/paper.pdf.bak")


def test_pdf_header_after_leading_junk_is_caught(tmp_path):
    # Y1. A PDF reader accepts the header anywhere in the first 1024 bytes;
    # an exact-prefix test was walked past by three newlines and a comment.
    junk = b"\n\n\n%% a comment line before the header\n" + b"\x00" * 200
    root = make_repo(tmp_path, {"docs/img/scan": junk + PDF_BYTES})
    assert "pdf_magic_bytes" in checks(run(root), "docs/img/scan")


def test_magic_rule_quiet_on_png(tmp_path):
    root = make_repo(tmp_path)
    assert "pdf_magic_bytes" not in checks(run(root))


# ---------------------------------------------------------------------------
# archive_present
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["data/sample.ZIP", "vendor/lib.jar", "dump.tar.gz", "x.tgz",
                                  "x.7z", "x.rar", "x.war", "x.bz2", "x.xz", "docs/x.tar"])
def test_archive_by_extension_is_caught(tmp_path, name):
    # Y2. By name, in any letter case, whatever the bytes say.
    root = make_repo(tmp_path, {name: b"nothing to see here"})
    hits = only(run(root), "archive_present")
    assert [f.path for f in hits] == [name]
    assert "container for the things it refuses" in hits[0].message


@pytest.mark.parametrize("name, head", [
    ("docs/notes.bin", b"PK\x03\x04\x14\x00" + b"\x00" * 40),
    ("docs/blob", b"\x1f\x8b\x08\x00" + b"\x00" * 40),
    ("docs/seven", b"7z\xbc\xaf\x27\x1c\x00\x04" + b"\x00" * 40),
    ("docs/r", b"Rar!\x1a\x07\x01\x00" + b"\x00" * 40),
    ("docs/t", b"\x00" * 257 + b"ustar\x00" + b"\x00" * 250),
])
def test_archive_by_magic_bytes_is_caught(tmp_path, name, head):
    # Y3. By bytes, whatever the name says.
    root = make_repo(tmp_path, {name: head})
    assert "archive_present" in checks(run(root), name)


def test_archive_rule_quiet_on_prose_and_images(tmp_path):
    assert "archive_present" not in checks(run(make_repo(tmp_path)))


# ---------------------------------------------------------------------------
# size_ceiling
# ---------------------------------------------------------------------------

def test_file_over_five_mb_is_caught(tmp_path):
    root = make_repo(tmp_path, {"docs/big.md": b"x" * (cc.SIZE_CEILING_BYTES + 1)})
    assert "size_ceiling" in checks(run(root), "docs/big.md")


def test_file_at_exactly_five_mb_passes(tmp_path):
    root = make_repo(tmp_path, {"docs/edge.md": b"x" * cc.SIZE_CEILING_BYTES})
    assert "size_ceiling" not in checks(run(root))


# ---------------------------------------------------------------------------
# image_provenance
# ---------------------------------------------------------------------------

def test_fair_use_quote_origin_is_rejected(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.png": PNG_BYTES,
                                "assets/figures/x.source.yml": "origin: fair-use-quote\n"})
    hits = only(run(root), "image_provenance")
    assert [f.path for f in hits] == ["assets/figures/x.png"]
    assert "fair-use-quote" in hits[0].message


def test_redrawn_without_editable_source_is_caught(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.png": PNG_BYTES,
                                "assets/figures/x.source.yml": "origin: redrawn\n"})
    hits = only(run(root), "image_provenance")
    assert [f.path for f in hits] == ["assets/figures/x.png"]
    assert "editable source" in hits[0].message


def test_original_with_drawio_source_passes(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.png": PNG_BYTES,
                                "assets/figures/x.source.yml": "origin: original\n",
                                "assets/figures/x.drawio": "<mxfile/>\n"})
    assert "image_provenance" not in checks(run(root))


def test_cc_licensed_needs_no_editable_source(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.jpg": PNG_BYTES,
                                "assets/figures/x.source.yaml":
                                    "origin: cc-licensed  # inline comment\n"
                                    "source: https://example.invalid\nlicense: CC BY 4.0\n"})
    assert "image_provenance" not in checks(run(root))


def test_svg_declared_original_is_its_own_editable_source(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/d.svg": "<svg/>\n",
                                "assets/figures/d.source.yml": "origin: 'original'\n"})
    assert "image_provenance" not in checks(run(root))


def test_missing_source_yml_is_caught(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.png": PNG_BYTES})
    assert "image_provenance" in checks(run(root), "assets/figures/x.png")


def test_source_yml_missing_origin_key_is_caught(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.png": PNG_BYTES,
                                "assets/figures/x.source.yml": "source: https://example.invalid\n"})
    assert "image_provenance" in checks(run(root), "assets/figures/x.png")


def test_unparseable_source_yml_is_caught(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.png": PNG_BYTES,
                                "assets/figures/x.source.yml": "- origin: redrawn\n"})
    hits = only(run(root), "image_provenance")
    assert [f.path for f in hits] == ["assets/figures/x.png"]
    assert "could not be parsed" in hits[0].message


def test_nested_origin_does_not_count(tmp_path):
    # A real YAML parser would find origin two levels down; this rule wants it
    # at the top, and anything else is not a declaration.
    root = make_repo(tmp_path, {"assets/figures/x.png": PNG_BYTES,
                                "assets/figures/x.source.yml":
                                    "x.png:\n  origin: redrawn\n"})
    assert "image_provenance" in checks(run(root), "assets/figures/x.png")


def test_undecodable_source_yml_is_caught(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/x.png": PNG_BYTES,
                                "assets/figures/x.source.yml": b"\xff\xfeorigin: redrawn\n"})
    assert "image_provenance" in checks(run(root), "assets/figures/x.png")


def test_image_outside_assets_figures_is_caught(tmp_path):
    root = make_repo(tmp_path, {"summaries/x/fig1.png": PNG_BYTES})
    hits = only(run(root), "image_provenance")
    assert [f.path for f in hits] == ["summaries/x/fig1.png"]


def test_uppercase_image_extension_is_caught(tmp_path):
    root = make_repo(tmp_path, {"docs/Shot.PNG": PNG_BYTES})
    assert "image_provenance" in checks(run(root), "docs/Shot.PNG")


@pytest.mark.parametrize("ext", [".bmp", ".avif", ".heic", ".heif", ".jfif", ".ico",
                                 ".apng", ".psd", ".tga", ".BMP"])
def test_widened_image_extensions_need_provenance(tmp_path, ext):
    # Y4. A screenshot saved as .bmp was not an "image" to the old extension list.
    root = make_repo(tmp_path, {f"docs/shot{ext}": b"BM" + b"\x00" * 60})
    assert "image_provenance" in checks(run(root), f"docs/shot{ext}")


# A BMP whose header agrees with itself: `BM`, the file size, four zero bytes.
BMP_BYTES = b"BM" + (50).to_bytes(4, "little") + b"\x00" * 4 + b"\x00" * 40
assert len(BMP_BYTES) == 50


@pytest.mark.parametrize("name, head", [
    ("docs/notes.dat", PNG_BYTES),
    ("assets/scan", JPEG_BYTES),
    ("docs/anim.dat", b"GIF89a" + b"\x00" * 40),
    ("docs/photo", b"RIFF\x00\x10\x00\x00WEBPVP8 " + b"\x00" * 40),
    ("docs/t.raw", b"II*\x00\x08\x00\x00\x00" + b"\x00" * 40),
    ("docs/t2.raw", b"MM\x00*\x00\x00\x00\x08" + b"\x00" * 40),
    ("docs/bitmap", BMP_BYTES),
])
def test_raster_bytes_under_any_name_need_provenance(tmp_path, name, head):
    # Y5. A PNG called notes.dat is a PNG; a file with image bytes needs
    # provenance whatever it is called. (Fixture renamed from notes.txt in the
    # third pass: .txt is prose now, and a PNG under a prose name is refused
    # as unreadable instead - see below.)
    root = make_repo(tmp_path, {name: head})
    hits = only(run(root), "image_provenance")
    assert [f.path for f in hits] == [name]
    assert "first bytes" in hits[0].message


def test_raster_bytes_under_a_prose_name_are_refused_as_unreadable(tmp_path):
    # Z13. Prose files are not sniffed - they are decoded as UTF-8, which no
    # raster survives. The refusal is the same refusal by another name.
    root = make_repo(tmp_path, {"docs/notes.txt": PNG_BYTES, "docs/shot.md": JPEG_BYTES})
    found = run(root)
    assert "unreadable_file" in checks(found, "docs/notes.txt")
    assert "unreadable_file" in checks(found, "docs/shot.md")
    assert "image_provenance" not in checks(found)


def test_bm25_note_is_not_a_bitmap(tmp_path):
    # Z12. `BM` alone is the start of a sentence; a BMP header states the
    # file's own size and has four zero reserved bytes.
    root = make_repo(tmp_path, {"docs/ranking.dat": b"BM25 is a ranking function used in retrieval." + b"\x00" * 20})
    assert run(root) == []
    assert cc.raster_kind(b"BM25 is a ranking", 40) is None
    assert cc.raster_kind(BMP_BYTES, 50) == "BMP"
    assert cc.raster_kind(BMP_BYTES, 51) is None          # size field disagrees
    assert cc.raster_kind(BMP_BYTES, None) is None        # size unknown, no claim


def test_sniffed_raster_with_declaration_passes(tmp_path):
    root = make_repo(tmp_path, {"docs/notes.dat": PNG_BYTES,
                                "docs/notes.source.yml": "origin: cc-licensed\n"})
    assert "image_provenance" not in checks(run(root))


def test_any_file_under_assets_figures_needs_provenance(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/notes.dat": "a stray file\n"})
    assert "image_provenance" in checks(run(root), "assets/figures/notes.dat")


def test_readme_under_assets_figures_needs_no_provenance(tmp_path):
    # Z14. A README belongs beside the figures; it is a page, not a figure.
    root = make_repo(tmp_path, {"assets/figures/README.md": "# Figures\n\nHow these were drawn.\n",
                                "assets/figures/notes.txt": "plain notes\n"})
    assert run(root) == []


def test_provenance_rule_quiet_on_declared_figure(tmp_path):
    assert "image_provenance" not in checks(run(make_repo(tmp_path)))


# ---------------------------------------------------------------------------
# svg_embeds_raster
# ---------------------------------------------------------------------------

def test_svg_with_embedded_data_uri_is_not_self_certifying(tmp_path):
    # Y6. A screenshot base64-encoded into an <image> tag, declared original,
    # with the SVG as its own "editable source".
    root = make_repo(tmp_path, {
        "assets/figures/d.svg": svg_with_image('href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="'),
        "assets/figures/d.source.yml": "origin: original\n"})
    found = run(root)
    hits = only(found, "svg_embeds_raster")
    assert [f.path for f in hits] == ["assets/figures/d.svg"]
    assert "cannot certify its own provenance" in hits[0].message
    assert "image_provenance" not in checks(found)      # that rule alone was satisfied


def test_svg_with_xlink_href_to_raster_file_is_caught(tmp_path):
    root = make_repo(tmp_path, {
        "assets/figures/d.svg": svg_with_image('xlink:href="../screens/fig1.PNG"'),
        "assets/figures/d.source.yml": "origin: original\n"})
    assert "svg_embeds_raster" in checks(run(root), "assets/figures/d.svg")


def test_svg_with_entity_encoded_or_folded_data_uri_is_caught(tmp_path):
    root = make_repo(tmp_path, {
        "assets/figures/d.svg": svg_with_image('href="data&#58;image/jpeg;base64,\n  /9j/4AAQ\n  SkZJRg=="'),
        "assets/figures/d.source.yml": "origin: redrawn\n"})
    assert "svg_embeds_raster" in checks(run(root), "assets/figures/d.svg")


def test_svg_with_embedded_raster_and_no_declaration_is_caught_twice(tmp_path):
    root = make_repo(tmp_path, {"docs/d.svg": svg_with_image('href="data:image/png;base64,AAAA"')})
    found = checks(run(root), "docs/d.svg")
    assert "svg_embeds_raster" in found
    assert "image_provenance" in found


def test_svg_embedding_raster_passes_when_cc_licensed(tmp_path):
    root = make_repo(tmp_path, {
        "assets/figures/d.svg": svg_with_image('href="data:image/png;base64,AAAA"'),
        "assets/figures/d.source.yml": "origin: cc-licensed\nsource: https://example.invalid\nlicense: CC BY 4.0\n"})
    assert "svg_embeds_raster" not in checks(run(root))


def test_svg_embedding_raster_passes_with_non_svg_editable_sibling(tmp_path):
    root = make_repo(tmp_path, {
        "assets/figures/d.svg": svg_with_image('href="data:image/png;base64,AAAA"'),
        "assets/figures/d.source.yml": "origin: original\n",
        "assets/figures/d.drawio": "<mxfile/>\n"})
    assert "svg_embeds_raster" not in checks(run(root))


def test_small_legitimate_svg_passes(tmp_path):
    root = make_repo(tmp_path, {"assets/figures/d.svg": SVG_SHAPES,
                                "assets/figures/d.source.yml": "origin: original\n"})
    found = run(root)
    assert "svg_embeds_raster" not in checks(found)
    assert "image_provenance" not in checks(found)
    assert found == []


# ---------------------------------------------------------------------------
# attribution_present
# ---------------------------------------------------------------------------

def test_deeply_nested_summary_without_attribution_is_caught(tmp_path):
    root = make_repo(tmp_path, {"summaries/deep/nested/x.md": summary(attribution=False)})
    assert "attribution_present" in checks(run(root), "summaries/deep/nested/x.md")


def test_attribution_present_passes(tmp_path):
    root = make_repo(tmp_path, {"summaries/deep/nested/x.md": summary()})
    assert "attribution_present" not in checks(run(root))


def test_attribution_heading_is_matched_case_insensitively(tmp_path):
    # Z7. Fixture inverted in the third pass: `## Source and Attribution` and
    # trailing whitespace render as the same heading and pass.
    root = make_repo(tmp_path, {"summaries/a/x.md":
                                "# T\n\n## SOURCE and Attribution   \n\nfine\n"})
    assert "attribution_present" not in checks(run(root))


def test_attribution_heading_wording_and_level_must_match(tmp_path):
    # Z7. ...but the wording and the level must, and the finding says what
    # was found instead.
    bad = make_repo(tmp_path / "wording", {"summaries/a/x.md": "# T\n\n## Sources\n\nx\n"})
    hits = only(run(bad), "attribution_present")
    assert hits and "'## Sources'" in hits[0].message and "not that wording" in hits[0].message
    lvl = make_repo(tmp_path / "level", {"summaries/a/x.md": "# T\n\n### Source and attribution\n\nx\n"})
    hits = only(run(lvl), "attribution_present")
    assert hits and "not level 2" in hits[0].message
    none = make_repo(tmp_path / "none", {"summaries/a/x.md": "# T\n\n## Method\n\nx\n"})
    hits = only(run(none), "attribution_present")
    assert hits and "'Method'" in hits[0].message


def test_attribution_heading_in_a_comment_or_fence_does_not_render(tmp_path):
    # Z7. A heading that only exists inside an HTML comment or a code fence is
    # not on the page and does not count.
    comment = make_repo(tmp_path / "c", {"summaries/a/x.md":
                                         "# T\n\nbody\n\n<!--\n## Source and attribution\n-->\n"})
    hits = only(run(comment), "attribution_present")
    assert hits and "does not render" in hits[0].message
    fence = make_repo(tmp_path / "f", {"summaries/a/x.md":
                                       "# T\n\nbody\n\n```python\n## Source and attribution\n```\n"})
    assert "attribution_present" in checks(run(fence), "summaries/a/x.md")


def test_html_h2_attribution_heading_renders_and_passes(tmp_path):
    root = make_repo(tmp_path, {"summaries/a/x.md":
                                "# T\n\nbody\n\n<h2>Source and attribution</h2>\n\n- **Paper:** A paper\n"})
    assert "attribution_present" not in checks(run(root))


def test_attribution_not_required_outside_summaries(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": "# Doc\n\nno attribution needed\n"})
    assert "attribution_present" not in checks(run(root))


def test_summaries_directory_is_matched_case_insensitively(tmp_path):
    # X13. `Summaries/` is not a different place.
    assert cc.is_summary("Summaries/a.md") and cc.is_summary("SUMMARIES/deep/x.MD")
    root = make_repo(tmp_path, {"Summaries/a.md": summary(attribution=False)})
    # On a case-insensitive filesystem git records this beside the baseline
    # summaries/; the finding must land on it under whichever spelling git kept.
    hits = only(run(root), "attribution_present")
    assert [f.path.lower() for f in hits] == ["summaries/a.md"]


def test_markdown_extension_variant_needs_attribution(tmp_path):
    # 14. `.markdown` renders exactly like `.md`.
    root = make_repo(tmp_path, {"summaries/x.markdown": summary(attribution=False)})
    assert "attribution_present" in checks(run(root), "summaries/x.markdown")


# ---------------------------------------------------------------------------
# quote_over_limit: scope
# ---------------------------------------------------------------------------

def test_300_word_blockquote_in_summary_is_caught(tmp_path):
    root = make_repo(tmp_path, {"summaries/a/x.md": summary("> " + words(300) + "\n")})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == ["summaries/a/x.md"]
    assert "300 words" in hits[0].message
    # The finding must not reproduce the quotation.
    assert "w20 " not in hits[0].message and hits[0].message.count("w") < 40


def test_quote_rule_covers_every_prose_directory(tmp_path):
    files = {f"{d}x.md": f'# D\n\n"{words(50)}"\n'
             for d in ("summaries/a/", "docs/", "reading-lists/", "curricula/",
                       "tutorials/t/", "datasets/")}
    root = make_repo(tmp_path, files)
    hits = {f.path for f in only(run(root), "quote_over_limit")}
    assert hits == set(files)


def test_root_readme_blockquote_is_caught(tmp_path):
    # X11. The previous rule ran over six named directories and README.md was
    # outside all of them. Every markdown file is prose, the root included.
    root = make_repo(tmp_path, {"README.md": "# R\n\n> " + words(300) + "\n"})
    assert "quote_over_limit" in checks(run(root), "README.md")


def test_markdown_in_a_new_directory_is_caught(tmp_path):
    # X12. A directory list is a whitelist that a new directory escapes.
    root = make_repo(tmp_path, {"notes/a.md": "# N\n\n> " + words(300) + "\n"})
    assert "quote_over_limit" in checks(run(root), "notes/a.md")


def test_markdown_extension_variant_is_scanned(tmp_path):
    root = make_repo(tmp_path, {"docs/x.MARKDOWN": f'# D\n\n"{words(50)}"\n'})
    assert "quote_over_limit" in checks(run(root), "docs/x.MARKDOWN")


def test_readme_with_no_quotations_is_clean(tmp_path):
    text = ("# research-notebook\n\nPaper summaries and reading notes, kept in the open. "
            "It doesn't matter which track you start on; Zhang's result and the authors' "
            "claim are both discussed. Nothing here is a quotation.\n\n## Licence\n\n"
            "- **Code** - `tools/` - MIT.\n- **Prose** - summaries, notes - CC BY 4.0.\n")
    root = make_repo(tmp_path, {"README.md": text})
    assert run(root) == []


# ---------------------------------------------------------------------------
# quote_over_limit: blockquotes and straight/curly double marks
# ---------------------------------------------------------------------------

def test_40_word_blockquote_passes_and_41_fails(tmp_path):
    ok = make_repo(tmp_path / "ok", {"summaries/a/x.md": summary("> " + words(40) + "\n")})
    assert "quote_over_limit" not in checks(run(ok))
    bad = make_repo(tmp_path / "bad", {"summaries/a/x.md": summary("> " + words(41) + "\n")})
    assert "quote_over_limit" in checks(run(bad), "summaries/a/x.md")


def test_multiline_blockquote_is_one_quote(tmp_path):
    body = "> " + words(20) + "\n> " + words(21, "v") + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_lazy_continuation_counts_toward_the_blockquote(tmp_path):
    body = "> " + words(30) + "\n" + words(20, "v") + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_41_word_quoted_span_is_caught_and_40_is_not(tmp_path):
    bad = make_repo(tmp_path / "bad", {"docs/x.md": f'# D\n\nThey say "{words(41)}" here.\n'})
    assert "quote_over_limit" in checks(run(bad), "docs/x.md")
    ok = make_repo(tmp_path / "ok", {"docs/x.md": f'# D\n\nThey say "{words(40)}" here.\n'})
    assert "quote_over_limit" not in checks(run(ok))


def test_curly_quotes_are_paired_too(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\nThey say “{words(41)}” here.\n"})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_scare_quotes_across_two_bullets_are_not_one_quote(tmp_path):
    body = ('- The "A" result, followed by ' + words(30) + ' of discussion.\n'
            '- The "B" result, followed by ' + words(30, "v") + ' more.\n')
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" not in checks(run(root))


def test_odd_trailing_mark_across_bullets_is_not_paired(tmp_path):
    # An unbalanced mark in one bullet must not pair with a mark in the next.
    body = ('- He wrote "A and then ' + words(30) + '\n'
            '- and B" closes nothing, ' + words(30, "v") + '\n')
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" not in checks(run(root))


def test_text_between_two_short_quotes_is_not_a_quote(tmp_path):
    body = 'The "first" term and ' + words(60) + ' then the "second" term.\n'
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" not in checks(run(root))


def test_quote_finding_reports_the_line(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\nfine\n\n> " + words(50) + "\n"})
    hits = only(run(root), "quote_over_limit")
    assert hits and hits[0].line == 5


# ---------------------------------------------------------------------------
# quote_over_limit: the other quotation glyphs (X1, X2, X3, X7)
# ---------------------------------------------------------------------------

def test_curly_single_quotes_are_paired(tmp_path):
    # X1. British-style ‘single’ quotation marks were not marks at all.
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\nThey say ‘{words(41)}’ here.\n"})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_39_word_british_quotation_passes(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\nAs they put it, ‘{words(39)}’, and so on.\n"})
    assert "quote_over_limit" not in checks(run(root))


@pytest.mark.parametrize("opener, closer", [("«", "»"), ("‹", "›"), ("„", "“"), ("„", "”")])
def test_guillemets_and_low_nine_quotes_are_paired(tmp_path, opener, closer):
    # X2, X3. «French», ‹nested› and „German“ marks.
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\nThey say {opener}{words(41)}{closer} here.\n"})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


@pytest.mark.parametrize("opener, closer", [("&quot;", "&quot;"), ("&ldquo;", "&rdquo;"),
                                            ("&lsquo;", "&rsquo;"), ("&laquo;", "&raquo;"),
                                            ("&#8220;", "&#8221;")])
def test_html_entity_quotation_marks_are_decoded(tmp_path, opener, closer):
    # X3. GitHub decodes the entity into a quotation mark; so does the scanner.
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\nThey say {opener}{words(41)}{closer} here.\n"})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_nbsp_entities_do_not_glue_words_together(tmp_path):
    # X7. `w0&nbsp;w1&nbsp;...` rendered as 41 words and counted as one.
    glued = "&nbsp;".join(f"w{i}" for i in range(41))
    root = make_repo(tmp_path, {"docs/x.md": f'# D\n\nThey say "{glued}" here.\n'})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_literal_no_break_spaces_do_not_glue_words_together(tmp_path):
    glued = "\u00a0".join(f"w{i}" for i in range(41))
    root = make_repo(tmp_path, {"docs/x.md": f'# D\n\n> {glued}\n'})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_apostrophes_are_not_quotation_marks(tmp_path):
    body = ("It doesn't matter; Zhang's result and the authors' claim, the '90s and rock 'n' roll, "
            + words(60) + " end with a 'quoted' word and the participants' view.\n")
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" not in checks(run(root))


def test_straight_single_quotes_at_word_boundaries_are_marks(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\nThey say '{words(41)}' here.\n"})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


# ---------------------------------------------------------------------------
# quote_over_limit: HTML structure (X4, X5, X8)
# ---------------------------------------------------------------------------

def test_html_blockquote_element_is_a_blockquote(tmp_path):
    # X4. GitHub renders <blockquote> as a blockquote; the scanner saw a tag.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n<blockquote>\n" + words(300) + "\n</blockquote>\n"})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert "300 words" in hits[0].message


def test_html_blockquote_with_paragraphs_on_one_line_is_a_blockquote(tmp_path):
    body = '<blockquote cite="x"><p>' + words(150) + "</p><p>" + words(150, "v") + "</p></blockquote>\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_html_blockquote_with_blank_lines_inside_is_one_blockquote(tmp_path):
    body = "<blockquote>\n" + words(30) + "\n\n" + words(30, "v") + "\n</blockquote>\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_encoded_blockquote_tag_is_literal_text_not_a_tag(tmp_path):
    body = "&lt;blockquote&gt;\n" + words(300) + "\n&lt;/blockquote&gt;\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" not in checks(run(root))


def test_html_q_element_is_a_quotation(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\nThey wrote <q>" + words(41) + "</q> there.\n"})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


@pytest.mark.parametrize("prefix", ["- > ", "* > ", "+ > ", "1. > ", "12) > "])
def test_blockquote_inside_a_list_item_is_a_blockquote(tmp_path, prefix):
    # X8. `- > quoted` renders as a blockquote inside a bullet.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + prefix + words(300) + "\n"})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert "300 words" in hits[0].message


def test_blockquote_inside_a_bullet_continues_on_indented_lines(tmp_path):
    body = "- > " + words(25) + "\n  > " + words(25, "v") + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


# ---------------------------------------------------------------------------
# quote_over_limit: fences (X14)
# ---------------------------------------------------------------------------

def test_quote_inside_code_fence_is_not_a_finding(tmp_path):
    # Fixture changed from ```text to ```python in the second hardening: a
    # ```text fence renders verbatim and is now scanned as prose (see below);
    # a fence in a real language is code and is blanked.
    # Inline fixture shortened from 50 to 30 words in the third pass: a code
    # span over MAX_CODE_SPAN_WORDS renders as a run of verbatim text and is a
    # quotation now (see the verbatim-block tests below).
    body = '```python\n"' + words(80) + '"\n```\n\nAnd inline `"' + words(30, "v") + '"` too.\n'
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" not in checks(run(root))


def test_quote_after_a_code_fence_is_still_scanned(tmp_path):
    body = '```\ncode\n```\n\n"' + words(50) + '"\n'
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_unterminated_fence_does_not_hide_a_quotation(tmp_path):
    body = '```\n\n"' + words(50) + '"\n'
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


@pytest.mark.parametrize("info", ["text", "", "txt", "plain", "md", "markdown", "TEXT"])
def test_verbatim_fence_is_scanned_as_prose(tmp_path, info):
    # X14. A ```text fence renders every word verbatim; blanking it as code
    # made it the perfect hiding place. It is a reproduction, and counts as one.
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\n```{info}\n" + words(300) + "\n```\n"})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert "300 words" in hits[0].message


def test_backticks_inside_a_verbatim_fence_do_not_open_code_spans(tmp_path):
    body = "```text\n`" + words(150) + "`\n`" + words(150, "v") + "`\n```\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


def test_code_fence_in_a_real_language_is_code(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n```python\n" + words(300) + "\n```\n"})
    found = run(root)
    assert "quote_over_limit" not in checks(found)
    assert found == []


def test_short_pseudocode_in_a_text_fence_passes(tmp_path):
    # The block the existing summaries actually carry.
    body = ("Then a standard pre-norm transformer encoder, repeated `L` times:\n\n```text\n"
            "z = z + MHSA(LayerNorm(z))\n"
            "z = z + MLP(LayerNorm(z))         # one GELU hidden layer, width 4D\n```\n")
    root = make_repo(tmp_path, {"summaries/a/x.md": summary(body)})
    assert run(root) == []


# ---------------------------------------------------------------------------
# quote_aggregate_over_limit (X6)
# ---------------------------------------------------------------------------

def test_chunked_blockquotes_trip_the_aggregate(tmp_path):
    # X6. Eight 38-word blockquotes: each under 40, together a 304-word passage.
    body = "## Section\n\n" + "\n\n".join("> " + words(38, f"p{k}x") for k in range(8)) + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    found = run(root)
    hits = only(found, "quote_aggregate_over_limit")
    # 304 words is over the per-section ceiling AND the per-file one (Z4), so
    # both findings land on the file; each names its own ceiling.
    assert {f.path for f in hits} == {"docs/x.md"} and len(hits) == 2
    assert all("304 words" in f.message for f in hits)
    assert any("'Section'" in f.message for f in hits)
    assert any("whole file" in f.message for f in hits)
    assert "quote_over_limit" not in checks(found)      # the single-quote rule cannot see it


def test_eight_distinct_short_quotations_pass_the_aggregate(tmp_path):
    body = "## Section\n\n" + "\n\n".join(
        f'They said "{words(10, f"q{k}x")}" and moved on.' for k in range(8)) + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_aggregate_over_limit" not in checks(run(root))


def test_aggregate_is_per_h2_section(tmp_path):
    # 114 words in each of two sections: fine per section, 228 across the file.
    chunk = "\n\n".join("> " + words(38, f"p{k}x") for k in range(3))
    body = "## One\n\n" + chunk + "\n\n## Two\n\n" + chunk.replace("p", "r") + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_aggregate_over_limit" not in checks(run(root))


def test_aggregate_counts_text_before_the_first_h2(tmp_path):
    body = "\n\n".join(f'A "{words(35, f"q{k}x")}" claim.' for k in range(4)) + "\n\n## Later\n\nfine\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    hits = only(run(root), "quote_aggregate_over_limit")
    assert hits and "before the first H2" in hits[0].message


def test_aggregate_does_not_double_count_quotes_inside_blockquotes(tmp_path):
    # 3 x 38 = 114 words, every blockquote itself full of quotation marks.
    body = "## S\n\n" + "\n\n".join('> "' + words(38, f"p{k}x") + '"' for k in range(3)) + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_aggregate_over_limit" not in checks(run(root))


# ---------------------------------------------------------------------------
# raw_abstract_present
# ---------------------------------------------------------------------------

def test_long_paragraph_under_abstract_heading_is_caught(tmp_path):
    root = make_repo(tmp_path, {"summaries/a/x.md":
                                summary("## Abstract\n\n" + words(220) + "\n\n## Method\n\nshort\n")})
    hits = only(run(root), "raw_abstract_present")
    assert [f.path for f in hits] == ["summaries/a/x.md"]
    assert "220-word" in hits[0].message


def test_same_paragraph_under_method_is_not_caught(tmp_path):
    root = make_repo(tmp_path, {"summaries/a/x.md":
                                summary("## Method\n\n" + words(220) + "\n")})
    assert "raw_abstract_present" not in checks(run(root))


def test_abstract_section_ends_at_next_heading(tmp_path):
    body = "## Abstract\n\nOne line.\n\n## Method\n\n" + words(220) + "\n"
    root = make_repo(tmp_path, {"summaries/a/x.md": summary(body)})
    assert "raw_abstract_present" not in checks(run(root))


def test_short_paragraphs_under_abstract_pass(tmp_path):
    # Fixture changed from 60 + 60 words in the second hardening: the section
    # is now counted as a whole, so two short paragraphs must be short together.
    body = "## Abstract\n\n" + words(30) + "\n\n" + words(30, "v") + "\n"
    root = make_repo(tmp_path, {"summaries/a/x.md": summary(body)})
    assert "raw_abstract_present" not in checks(run(root))


def test_abstract_split_into_short_paragraphs_is_caught(tmp_path):
    # X9. 220 words as four 55-word paragraphs, each under the old per-paragraph limit.
    body = "## Abstract\n\n" + "\n\n".join(words(55, f"p{k}x") for k in range(4)) + "\n\n## Method\n\nshort\n"
    root = make_repo(tmp_path, {"summaries/a/x.md": summary(body)})
    hits = only(run(root), "raw_abstract_present")
    assert [f.path for f in hits] == ["summaries/a/x.md"]
    assert "220-word" in hits[0].message


def test_heading_containing_abstract_anywhere_in_title_counts(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n### Their abstract, verbatim\n\n" + words(61) + "\n"})
    assert "raw_abstract_present" in checks(run(root), "docs/x.md")


def test_setext_abstract_heading_counts(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\nAbstract\n--------\n\n" + words(61) + "\n"})
    assert "raw_abstract_present" in checks(run(root), "docs/x.md")


@pytest.mark.parametrize("tag", ["<h2>Abstract</h2>", '<h2 id="abs">Abstract</h2>', "<H3>Abstract</H3>",
                                 "<h2>\nAbstract\n</h2>"])
def test_html_heading_named_abstract_is_a_heading(tmp_path, tag):
    # X5. GitHub renders <h2>Abstract</h2> as a heading; the scanner saw a tag.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + tag + "\n\n" + words(220) + "\n\n## Method\n\nshort\n"})
    hits = only(run(root), "raw_abstract_present")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert "220-word" in hits[0].message


def test_frontmatter_comment_is_not_a_heading(tmp_path):
    text = "---\ntitle: T\n# abstract: nothing here\n---\n\n" + words(100) + "\n"
    root = make_repo(tmp_path, {"docs/x.md": text})
    assert "raw_abstract_present" not in checks(run(root))


def _frontmatter(key_line: str, n_words: int) -> str:
    folded = "\n".join("  " + words(10, f"l{k}x") for k in range(n_words // 10))
    return f"---\ntitle: T\n{key_line}\n{folded}\ntags: [a]\n---\n\n# T\n\nBody, in my own words.\n"


@pytest.mark.parametrize("key_line", ["abstract: >", "abstract: |", "Abstract: >-", "ABSTRACT: |+", "abstract:"])
def test_frontmatter_abstract_block_scalar_is_caught(tmp_path, key_line):
    # X10. `abstract: >` with the text folded underneath; GitHub renders frontmatter.
    root = make_repo(tmp_path, {"docs/x.md": _frontmatter(key_line, 70)})
    hits = only(run(root), "raw_abstract_present")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert hits[0].line == 3 and "frontmatter" in hits[0].message


def test_frontmatter_abstract_inline_scalar_is_caught(tmp_path):
    text = f'---\nabstract: "{words(70)}"\n---\n\n# T\n\nBody.\n'
    root = make_repo(tmp_path, {"docs/x.md": text})
    assert "raw_abstract_present" in checks(run(root), "docs/x.md")


def test_frontmatter_short_abstract_passes(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": _frontmatter("abstract: >", 20)})
    assert "raw_abstract_present" not in checks(run(root))


# ---------------------------------------------------------------------------
# third pass, accident-shaped holes: Z1 scope, Z2 verbatim blocks, Z3 tag
# boundaries, Z4 the per-file ceiling, Z5 summed abstracts, Z6 the PDF header
# window, Z8 nested list blockquotes, Z9 quoted attribute values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["docs/x.txt", "docs/x.rst", "notes/X.TXT", "docs/x.Rst"])
def test_plain_text_and_rst_files_are_prose_scanned_as_they_are(tmp_path, name):
    # Z1. A .txt or .rst file is a page GitHub shows as it is; a `>` line in
    # it is quoted text, in any directory and any letter case.
    root = make_repo(tmp_path, {name: "Title\n\n> " + words(300) + "\n"})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == [name]
    assert "300 words" in hits[0].message


@pytest.mark.parametrize("name, body", [
    ("docs/x.html", "<h1>T</h1>\n<blockquote>\n" + words(300) + "\n</blockquote>\n"),
    ("docs/x.htm", "<p>intro</p>\n<pre>\n" + words(300) + "\n</pre>\n"),
    ("docs/X.HTML", "<blockquote><p>" + words(150) + "</p><p>" + words(150, "v") + "</p></blockquote>\n"),
])
def test_html_files_get_the_html_normalisation(tmp_path, name, body):
    # Z1. An .html file is prose too, and its <blockquote> and <pre> are
    # blockquotes to the scanner as they are to the reader.
    root = make_repo(tmp_path, {name: body})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == [name]
    assert "300 words" in hits[0].message


def test_html_file_abstract_heading_counts(tmp_path):
    root = make_repo(tmp_path, {"docs/x.html": "<h2>Abstract</h2>\n<p>" + words(220) + "</p>\n<h2>Method</h2>\n"})
    assert "raw_abstract_present" in checks(run(root), "docs/x.html")


def test_plain_text_takes_no_markdown_or_entity_rendering(tmp_path):
    # Z1. In a .txt file `&quot;` is six characters and a fence is three
    # backticks: nothing is decoded, nothing is blanked, and only what a
    # reader of the raw file sees is judged.
    root = make_repo(tmp_path, {"docs/entities.txt": "&quot;" + words(41) + "&quot;\n",
                                "docs/fence.txt": "```python\n> " + words(300) + "\n```\n"})
    found = run(root)
    assert "quote_over_limit" not in checks(found, "docs/entities.txt")
    assert "quote_over_limit" in checks(found, "docs/fence.txt")


def test_indented_code_block_renders_verbatim_and_is_a_blockquote(tmp_path):
    # Z2. Four spaces (or a tab) after a blank line render the text verbatim,
    # every word visible: it is a reproduction, and counts as one.
    spaces = make_repo(tmp_path / "s", {"docs/x.md": "# D\n\nintro\n\n    " + words(300) + "\n"})
    hits = only(run(spaces), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"] and "300 words" in hits[0].message
    tab = make_repo(tmp_path / "t", {"docs/x.md": "# D\n\nintro\n\n\t" + words(300) + "\n"})
    assert "quote_over_limit" in checks(run(tab), "docs/x.md")


def test_list_continuation_paragraph_is_not_an_indented_code_block(tmp_path):
    # Z2, negative. Four spaces under a bullet continue the bullet; it takes
    # four more to be code there.
    body = "- A point.\n\n    " + words(300) + "\n\n- Another.\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert run(root) == []
    deeper = make_repo(tmp_path / "d", {"docs/x.md": "# D\n\n- A point.\n\n        " + words(300) + "\n"})
    assert "quote_over_limit" in checks(run(deeper), "docs/x.md")


def test_indented_text_without_a_blank_line_before_it_is_a_paragraph(tmp_path):
    # Z2, negative. CommonMark needs a blank line before an indented block;
    # without one the indentation is a paragraph continuation and renders as
    # ordinary prose.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\nA sentence that\n    " + words(300) + "\n"})
    assert run(root) == []


@pytest.mark.parametrize("info", ["abstract", "quote", "pseudo", "excerpt", "Text", "verbatim"])
def test_fence_with_an_unknown_info_string_is_prose(tmp_path, info):
    # Z2. Anything not in KNOWN_LANGUAGES renders verbatim and is scanned.
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\n```{info}\n" + words(300) + "\n```\n"})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


@pytest.mark.parametrize("lang", ["js", "yaml", "Python", "c++", "mermaid", "bibtex", "Dockerfile", "sh"])
def test_fence_in_a_known_language_is_code(tmp_path, lang):
    # Z2, negative. The closed list, in any letter case.
    root = make_repo(tmp_path, {"docs/x.md": f"# D\n\n```{lang}\n> " + words(300) + "\n```\n"})
    assert run(root) == []
    assert lang.lower() in cc.KNOWN_LANGUAGES


def test_pre_element_is_a_blockquote(tmp_path):
    # Z2. <pre> renders its content verbatim.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n<pre>\n" + words(300) + "\n</pre>\n"})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"] and "300 words" in hits[0].message


def test_long_inline_code_span_is_a_quotation(tmp_path):
    # Z2. Forty-one words in backticks render as a grey run of prose, every
    # word visible; forty are code and are blanked.
    bad = make_repo(tmp_path / "bad", {"docs/x.md": "# D\n\nAs in `" + words(41) + "` here.\n"})
    hits = only(run(bad), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert "inline code span" in hits[0].message and "41 words" in hits[0].message
    ok = make_repo(tmp_path / "ok", {"docs/x.md": "# D\n\nAs in `" + words(40) + "` here.\n"})
    assert run(ok) == []


def test_long_inline_code_spans_count_toward_the_aggregate(tmp_path):
    body = "## S\n\n" + "\n\n".join("See `" + words(41, f"c{k}x") + "` there." for k in range(4)) + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert "quote_aggregate_over_limit" in checks(run(root), "docs/x.md")


@pytest.mark.parametrize("sep", ["<br>", "<br/>", "<br />", "</p><p>", "<div>", "</li><li>", "<hr>"])
def test_block_level_tag_boundaries_separate_words(tmp_path, sep):
    # Z3. `w1<br>w2` is two words to the reader and must be two to the counter.
    glued = sep.join(f"w{i}" for i in range(41))
    root = make_repo(tmp_path, {"docs/x.md": f'# D\n\nThey say "{glued}" here.\n'})
    assert "quote_over_limit" in checks(run(root), "docs/x.md")


@pytest.mark.parametrize("zw", ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"])
def test_zero_width_characters_are_stripped_not_separators(tmp_path, zw):
    # Z3, negative. Text glued by zero-width characters is one unreadable
    # word; that is a typo, not a bypass, and not a finding.
    glued = zw.join(f"w{i}" for i in range(41))
    root = make_repo(tmp_path, {"docs/x.md": f'# D\n\nThey say "{glued}" here.\n'})
    assert run(root) == []


def test_file_ceiling_catches_a_quotation_spread_over_sections(tmp_path):
    # Z4. 114 quoted words in each of three sections: under the per-section
    # 120 every time, 342 across the file.
    def chunk(p: str) -> str:
        return "\n\n".join("> " + words(38, f"{p}{k}x") for k in range(3))
    body = ("## One\n\n" + chunk("a") + "\n\n## Two\n\n" + chunk("b")
            + "\n\n## Three\n\n" + chunk("c") + "\n")
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    hits = only(run(root), "quote_aggregate_over_limit")
    assert len(hits) == 1 and hits[0].path == "docs/x.md"
    assert "whole file" in hits[0].message and "342 words" in hits[0].message
    assert f"ceiling for one file is {cc.MAX_QUOTE_FILE_WORDS}" in hits[0].message


def test_file_ceiling_is_300_words():
    assert cc.MAX_QUOTE_FILE_WORDS == 300 and cc.MAX_QUOTE_AGGREGATE_WORDS == 120


def test_abstract_split_across_two_abstract_headings_is_summed(tmp_path):
    # Z5. `## Abstract` and `## Abstract (continued)` at 35 words each are a
    # 70-word abstract.
    body = ("## Abstract\n\n" + words(35) + "\n\n## Abstract (continued)\n\n" + words(35, "v")
            + "\n\n## Method\n\nshort\n")
    root = make_repo(tmp_path, {"summaries/a/x.md": summary(body)})
    hits = only(run(root), "raw_abstract_present")
    assert [f.path for f in hits] == ["summaries/a/x.md"]
    assert "70-word" in hits[0].message and "counted together" in hits[0].message
    assert "'Abstract'" in hits[0].message and "'Abstract (continued)'" in hits[0].message


def test_two_short_abstract_sections_pass_together(tmp_path):
    body = "## Abstract\n\n" + words(25) + "\n\n## Abstract (continued)\n\n" + words(25, "v") + "\n"
    root = make_repo(tmp_path, {"summaries/a/x.md": summary(body)})
    assert "raw_abstract_present" not in checks(run(root))


def test_frontmatter_abstract_and_abstract_heading_are_summed(tmp_path):
    text = ("---\nabstract: " + words(35) + "\n---\n\n# T\n\n## Abstract\n\n" + words(35, "v")
            + "\n\n## Method\n\nshort\n")
    root = make_repo(tmp_path, {"docs/x.md": text})
    hits = only(run(root), "raw_abstract_present")
    assert hits and "70-word" in hits[0].message and "frontmatter" in hits[0].message


@pytest.mark.parametrize("key", ["paper:\n  abstract: >", 'paper:\n  "abstract": |',
                                 "paper:\n  'ABSTRACT': >-", "paper:\n\tabstract: |", "meta:\n  - abstract: >"])
def test_frontmatter_abstract_key_at_any_indentation_bare_or_quoted(tmp_path, key):
    # Z5. A nested, quoted or list-item `abstract` key renders in the
    # frontmatter table just as a top-level one does.
    folded = "\n".join("      " + words(10, f"l{k}x") for k in range(7))
    text = f"---\ntitle: T\n{key}\n{folded}\n---\n\n# T\n\nBody, in my own words.\n"
    root = make_repo(tmp_path, {"docs/x.md": text})
    hits = only(run(root), "raw_abstract_present")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert hits[0].line == 4 and "frontmatter" in hits[0].message


def test_pdf_header_deep_in_the_first_two_kilobytes_is_caught(tmp_path):
    # Z6. `%PDF-` anywhere in the first 2048 bytes; 1500 bytes of junk in
    # front of it is still a PDF.
    assert cc.HEAD_BYTES == 2048
    root = make_repo(tmp_path, {"docs/img/scan": b"\x00" * 1500 + PDF_BYTES})
    hits = only(run(root), "pdf_magic_bytes")
    assert [f.path for f in hits] == ["docs/img/scan"] and "2048 bytes" in hits[0].message


@pytest.mark.parametrize("prefix", ["- a\n  - > ", "- a\n  - b\n    > ", "1. a\n   - b\n      > ",
                                    "- a\n\n    > ", "* a\n  * b\n    * c\n      > "])
def test_blockquote_under_a_nested_list_item_is_a_blockquote(tmp_path, prefix):
    # Z8. A `>` under a nested list item sits at four, six or eight spaces
    # and is still a blockquote, not an indented code block.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + prefix + words(300) + "\n"})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert "300 words" in hits[0].message


def test_html_tag_with_angle_brackets_inside_quoted_attributes_is_a_tag(tmp_path):
    # Z9. `alt="a > b"` is legal HTML; the tag runs to the first `>` outside
    # quotes, and GitHub renders it as the element it is.
    body = ("<blockquote title=\"a < b\" data-x='c > d'>\n" + words(300) + "\n</blockquote>\n\n"
            "<h2 title=\"x > y\">Abstract</h2>\n\n" + words(220, "v") + "\n\n## Method\n\nshort\n")
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    found = run(root)
    assert "quote_over_limit" in checks(found, "docs/x.md")
    assert "raw_abstract_present" in checks(found, "docs/x.md")


# ---------------------------------------------------------------------------
# third pass, false positives: every one a NEGATIVE test that must never
# fire again - Z10 short quoted spans, Z11 straight marks beside digits and
# letters, Z13 prose naming the PDF header, Z15 HTML comments, Z16 `&gt;`
# ---------------------------------------------------------------------------

def test_thirty_quoted_titles_in_a_reading_list_pass(tmp_path):
    # Z10. Thirty eight-word titles are 240 quoted words and no quotation.
    body = "## Papers\n\n" + "\n".join(f'- "{words(8, f"t{k}x")}" (2024)' for k in range(30)) + "\n"
    root = make_repo(tmp_path, {"reading-lists/x.md": "# R\n\n" + body})
    assert run(root) == []


def test_nine_word_quoted_spans_count_toward_the_aggregate(tmp_path):
    # ...and a nine-word span is a quotation: fifteen of them are 135 words.
    body = "## S\n\n" + "\n\n".join(f'They wrote "{words(9, f"q{k}x")}" and then more.' for k in range(15)) + "\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    hits = only(run(root), "quote_aggregate_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"] and "135 words" in hits[0].message
    assert cc.MIN_AGGREGATE_SPAN_WORDS == 8


def test_inch_and_foot_marks_after_digits_are_not_quotation_marks(tmp_path):
    # Z11. `12"` and `5'` are measurements; nothing opens at them.
    body = ("A 12\" display and a 5' cable on the \"cold start\" problem, then " + words(60)
            + " with a 27\" monitor, 6' of rope, and a 1.5\" margin.\n")
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert run(root) == []


def test_apostrophes_beside_digits_and_letters_are_not_marks(tmp_path):
    # Z11. `'90s`, `don't`, `Zhang's`, `authors'`, `rock 'n' roll`.
    body = ("Since the '90s, Zhang's group and the authors' collaborators haven't stopped; "
            "it's rock 'n' roll, and " + words(60) + " isn't quoted, nor is the participants' view.\n")
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert run(root) == []


def test_straight_single_mark_does_not_pair_across_paragraphs(tmp_path):
    # Z11. A candidate pair must sit in one paragraph.
    body = "He said 'this is " + words(30) + "\n\n" + words(30, "v") + " and that was it' he said.\n"
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body})
    assert run(root) == []


def test_single_quotation_ending_in_a_digit_still_closes(tmp_path):
    # ...but with a quotation open, the mark after `Table 2` closes it, as the
    # double-quote rule already does for `"see Table 2"`.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\nThey say '" + words(40) + " Table 2' here.\n"})
    hits = only(run(root), "quote_over_limit")
    assert hits and "42 words" in hits[0].message


def test_quoted_spans_straight_marks_beside_digits():
    assert cc.quoted_spans('a 12" display and 5\' of cable\n') == []
    spans = cc.quoted_spans('"see Table 2" and \'Figure 3\' then the \'90s and a 6\' pole\n')
    assert [s for _l, s in spans] == ["see Table 2", "Figure 3"]


def test_prose_naming_the_pdf_header_is_not_a_pdf(tmp_path):
    # Z13. A page may say `%PDF-` in its first line; prose is not sniffed.
    # The same bytes under a non-prose name are a PDF whatever the name.
    root = make_repo(tmp_path, {
        "docs/formats.txt": "%PDF-1.7 is the header every PDF file begins with.\n",
        "docs/formats.md": "%PDF- is the magic; see below.\n\n# Formats\n",
        "docs/formats.html": "<p>%PDF-1.4 marks a PDF.</p>\n",
        "docs/formats": "%PDF-1.7 is the header every PDF file begins with.\n",
    })
    found = run(root)
    for prose in ("docs/formats.txt", "docs/formats.md", "docs/formats.html"):
        assert checks(found, prose) == set()
    assert checks(found, "docs/formats") == {"pdf_magic_bytes"}


def test_commented_out_blockquote_quotation_and_heading_do_not_render(tmp_path):
    # Z15. Nothing inside `<!-- -->` is on the page, so nothing inside it is
    # a finding, for every prose rule at once.
    body = ("<!--\n> " + words(300) + "\n-->\n\n<!-- \"" + words(50, "v") + "\" -->\n\n"
            "<!-- ## Abstract -->\n\n" + words(100, "a") + "\n\n<!-- <blockquote>" + words(60, "b")
            + "</blockquote> -->\n\nfine\n")
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n" + body,
                                "summaries/a/x.md": summary("<!--\n> " + words(300) + "\n-->\n")})
    assert run(root) == []


def test_comments_are_literal_in_plain_text(tmp_path):
    # ...and a .txt file shows them, so the same body is a finding there.
    body = "<!--\n> " + words(300) + "\n-->\n"
    root = make_repo(tmp_path, {"docs/x.txt": body})
    assert "quote_over_limit" in checks(run(root), "docs/x.txt")


def test_encoded_gt_at_line_start_is_literal_text_not_a_marker(tmp_path):
    # Z16. `&gt;` renders as a `>` character, not as a blockquote.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n&gt; " + words(300) + "\n",
                                "docs/y.md": "# D\n\n- &gt; " + words(300) + "\n"})
    assert run(root) == []


def test_real_marker_survives_entity_decoding_on_its_line(tmp_path):
    # ...and the other direction: a real `>` line that also contains entities
    # is still a blockquote after decoding.
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n> &gt; " + words(150) + " &amp; " + words(150, "v") + "\n"})
    hits = only(run(root), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"] and "300 words" in hits[0].message


def test_decode_entities_protects_a_decoded_marker_only():
    assert cc.decode_entities("&gt; x\n> &gt; y\n- &gt; z\n") == "  x\n> > y\n-   z\n"


# ---------------------------------------------------------------------------
# notebook_outputs
# ---------------------------------------------------------------------------

def notebook(cells: list) -> str:
    return json.dumps({"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5})


def code_cell(outputs=None, execution_count=None) -> dict:
    return {"cell_type": "code", "source": ["1 + 1"], "metadata": {},
            "outputs": outputs or [], "execution_count": execution_count}


def test_notebook_with_only_image_output_and_no_output_type_is_caught(tmp_path):
    cell = code_cell(outputs=[{"data": {"image/svg+xml": "<svg/>"}, "metadata": {}}])
    root = make_repo(tmp_path, {"tutorials/t/nb.ipynb": notebook([cell])})
    hits = only(run(root), "notebook_outputs")
    assert [f.path for f in hits] == ["tutorials/t/nb.ipynb"]
    assert "image/svg+xml" in hits[0].message


def test_notebook_with_stream_output_is_caught(tmp_path):
    cell = code_cell(outputs=[{"output_type": "stream", "name": "stdout", "text": ["hi"]}])
    root = make_repo(tmp_path, {"nb.ipynb": notebook([cell])})
    assert "notebook_outputs" in checks(run(root), "nb.ipynb")


def test_notebook_with_execution_count_is_caught(tmp_path):
    root = make_repo(tmp_path, {"nb.ipynb": notebook([code_cell(execution_count=3)])})
    assert "notebook_outputs" in checks(run(root), "nb.ipynb")


def test_notebook_with_html_mime_is_caught(tmp_path):
    cell = code_cell(outputs=[{"data": {"text/html": "<table/>", "text/plain": "x"}}])
    root = make_repo(tmp_path, {"nb.ipynb": notebook([cell])})
    assert "notebook_outputs" in checks(run(root), "nb.ipynb")


def test_notebook_extension_is_case_insensitive(tmp_path):
    root = make_repo(tmp_path, {"Nb.IPYNB": notebook([code_cell(execution_count=1)])})
    assert "notebook_outputs" in checks(run(root), "Nb.IPYNB")


def test_notebook_that_is_not_json_is_caught(tmp_path):
    root = make_repo(tmp_path, {"nb.ipynb": "{not json"})
    assert "notebook_outputs" in checks(run(root), "nb.ipynb")


def test_clean_notebook_passes(tmp_path):
    cells = [code_cell(), {"cell_type": "markdown", "source": ["# hi"], "metadata": {}}]
    root = make_repo(tmp_path, {"nb.ipynb": notebook(cells)})
    assert "notebook_outputs" not in checks(run(root))


# ---------------------------------------------------------------------------
# unreadable files, odd names, case
# ---------------------------------------------------------------------------

def test_undecodable_prose_file_is_a_finding_not_a_skip(tmp_path):
    root = make_repo(tmp_path, {"summaries/a/x.md": b"\xff\xfe\x00bad bytes " + ATTRIBUTION.encode()})
    found = run(root)
    assert "unreadable_file" in checks(found, "summaries/a/x.md")
    assert len(only(found, "unreadable_file")) == 1


def test_filename_with_a_space_is_handled(tmp_path):
    root = make_repo(tmp_path, {
        "summaries/03-foundation-models/my paper.md": summary(),
        "assets/figures/my fig.png": PNG_BYTES,
        "assets/figures/my fig.source.yml": "origin: cc-licensed\n",
        "my paper.PDF": PDF_BYTES,
    })
    found = run(root)
    assert [f.path for f in only(found, "no_third_party_pdf")] == ["my paper.PDF"]
    assert "image_provenance" not in checks(found)
    assert "attribution_present" not in checks(found)


# ---------------------------------------------------------------------------
# --staged reads the index, not the working tree
# ---------------------------------------------------------------------------

def test_staged_mode_checks_only_the_index(tmp_path):
    root = make_repo(tmp_path)
    write(root, {"paper.PDF": PDF_BYTES, "stray.pdf": PDF_BYTES})
    git(root, "add", "--force", "paper.PDF")          # stray.pdf stays untracked
    found = run(root, "staged")
    assert [f.path for f in only(found, "no_third_party_pdf")] == ["paper.PDF"]


def test_staged_mode_reads_staged_content_not_worktree(tmp_path):
    root = make_repo(tmp_path)
    write(root, {"summaries/a/x.md": summary(attribution=False)})
    git(root, "add", "summaries/a/x.md")
    write(root, {"summaries/a/x.md": summary()})       # worktree fixed, index not
    assert "attribution_present" in checks(run(root, "staged"), "summaries/a/x.md")


def test_staged_mode_ignores_unstaged_worktree_edits(tmp_path):
    root = make_repo(tmp_path)
    write(root, {"summaries/03-foundation-models/clean.md": summary(attribution=False)})
    assert run(root, "staged") == []                   # nothing staged, nothing judged


def test_staged_deletion_of_source_yml_rejudges_the_image(tmp_path):
    root = make_repo(tmp_path)
    git(root, "rm", "-q", "--cached", "assets/figures/net.source.yml")
    assert "image_provenance" in checks(run(root, "staged"), "assets/figures/net.png")


def test_staged_mode_works_before_the_first_commit(tmp_path):
    root = make_repo(tmp_path, {"paper.PDF": PDF_BYTES}, commit=False)
    assert "no_third_party_pdf" in checks(run(root, "staged"), "paper.PDF")


def test_staged_mode_sniffs_bytes_from_the_index(tmp_path):
    root = make_repo(tmp_path)
    # Fixture renamed from notes.txt in the third pass: .txt is prose, and
    # prose is decoded rather than sniffed.
    write(root, {"docs/notes.dat": PNG_BYTES, "docs/pack.bin": b"PK\x03\x04" + b"\x00" * 40})
    git(root, "add", "docs/notes.dat", "docs/pack.bin")
    found = run(root, "staged")
    assert "image_provenance" in checks(found, "docs/notes.dat")
    assert "archive_present" in checks(found, "docs/pack.bin")


def test_path_arguments_check_those_files(tmp_path):
    root = make_repo(tmp_path, {"paper.PDF": PDF_BYTES, "docs/x.md": f'# D\n\n"{words(50)}"\n'})
    found = run(root, "paths", [str(root / "docs")])
    assert checks(found) == {"quote_over_limit"}


# ---------------------------------------------------------------------------
# workflow_self_edit and guard_self_edit (16d)
# ---------------------------------------------------------------------------

GUARD_STUBS = {
    "tools/check_copyright.py": "print('a stub standing in for the guard')\n",
    "tools/tests/test_check_copyright.py": "def test_nothing():\n    pass\n",
    ".githooks/pre-commit": "#!/bin/sh\nexit 0\n",
}


def _clone_with_upstream(tmp_path: Path, extra: dict | None = None) -> Path:
    origin = make_repo(tmp_path, {".github/workflows/copyright.yml": "name: copyright\n",
                                  ".github/CODEOWNERS": "* @owner\n",
                                  **GUARD_STUBS, **(extra or {})})
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", origin.as_uri(), str(work))
    return work


def _pr_branch(work: Path) -> None:
    """Move off the base branch, once, before a pull request commits anything.

    A pull request is a branch that has DIVERGED from the base; committing
    onto `main` would leave the clone's own `main` pointing at the pull
    request, which is not what a checkout of a pull request looks like on
    Actions (a detached head, with the base reachable as `origin/main`) and
    is a fixture that says nothing changed now that the checker resolves the
    base ref locally before it reaches for the network.
    """
    if git(work, "rev-parse", "--abbrev-ref", "HEAD").strip() != "pr":
        git(work, "checkout", "-q", "-b", "pr")


def _pr(work: Path, files: dict) -> None:
    """Commit `files` onto the clone as if they were a pull request."""
    _pr_branch(work)
    write(work, files)
    git(work, "add", "-A", "--force")
    git(work, "commit", "-q", "--no-verify", "-m", "pr")


def test_workflow_edit_on_a_pull_request_is_caught(tmp_path, monkeypatch):
    # Fixture extended in the second hardening: the rule is now an AND, so the
    # workflow change ships beside content to be caught.
    work = _clone_with_upstream(tmp_path)
    _pr(work, {".github/workflows/copyright.yml": "name: copyright\njobs: {}\n",
               "docs/new.md": "# New\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "workflow_self_edit")
    assert hits and "same pull request" in hits[0].message


def test_workflow_only_pull_request_passes_workflow_rule(tmp_path, monkeypatch):
    # Without this, no workflow fix could ever merge - including the one that
    # ships this checker. The second path is invented for this fixture and
    # exists nowhere in the repository: the rule matches the .github/ prefix
    # rather than a list of names, so any second file under it will do.
    work = _clone_with_upstream(tmp_path)
    _pr(work, {".github/workflows/copyright.yml": "name: copyright\njobs: {}\n",
               ".github/fixture-only-not-a-real-file.yml": "synthetic: true\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "workflow_self_edit" not in checks(run(work))


def test_content_only_pull_request_passes_workflow_rule(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr(work, {"docs/new.md": "# New\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "workflow_self_edit" not in checks(run(work))


def test_whole_github_directory_is_the_judge(tmp_path, monkeypatch):
    # CODEOWNERS, not workflows/: the rule covers all of .github/.
    work = _clone_with_upstream(tmp_path)
    _pr(work, {".github/CODEOWNERS": "* @someone-else\n", "docs/new.md": "# New\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "workflow_self_edit" in checks(run(work))


def test_workflow_rule_is_silent_without_base_ref(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr(work, {".github/workflows/copyright.yml": "name: changed\n", "docs/new.md": "# N\n"})
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    found = checks(run(work))
    assert "workflow_self_edit" not in found and "guard_self_edit" not in found


def test_unfetchable_base_ref_fails_closed(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    monkeypatch.setenv("GITHUB_BASE_REF", "no-such-branch")
    found = checks(run(work))
    assert "workflow_self_edit" in found
    assert "guard_self_edit" in found


@pytest.mark.parametrize("guard_file", ["tools/check_copyright.py",
                                        "tools/tests/test_check_copyright.py",
                                        ".githooks/pre-commit",
                                        ".githooks/commit-msg"])
def test_guard_edit_with_content_in_one_pull_request_is_caught(tmp_path, monkeypatch, guard_file):
    work = _clone_with_upstream(tmp_path)
    _pr(work, {guard_file: "# changed\n", "docs/new.md": "# New\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "guard_self_edit")
    assert hits and "do not travel in one pull request" in hits[0].message


def test_guard_only_pull_request_passes_guard_rule(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr(work, {"tools/check_copyright.py": "# changed\n",
               "tools/tests/test_check_copyright.py": "# changed\n",
               ".githooks/pre-commit": "# changed\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "guard_self_edit" not in checks(run(work))


def test_guard_with_workflow_but_no_content_passes_guard_rule(tmp_path, monkeypatch):
    # .github/, tools/ and .githooks/ are all "not content" for this rule.
    work = _clone_with_upstream(tmp_path)
    _pr(work, {"tools/check_copyright.py": "# changed\n",
               ".github/workflows/copyright.yml": "name: changed\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "guard_self_edit" not in checks(run(work))


def test_other_tools_with_content_pass_guard_rule(tmp_path, monkeypatch):
    # tools/ in general is not the guard; only the checker, its tests and the hooks are.
    work = _clone_with_upstream(tmp_path)
    _pr(work, {"tools/build_index.py": "print(1)\n", "docs/new.md": "# New\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "guard_self_edit" not in checks(run(work))


def test_content_only_pull_request_passes_guard_rule(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr(work, {"docs/new.md": "# New\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "guard_self_edit" not in checks(run(work))


# ---------------------------------------------------------------------------
# commit_attribution
#
# The history is meant to read as one person's work, so a trailer, a
# generated-with line, a [bot] marker or a stranger in the author or committer
# field is refused on the pull request. The fixture repositories elsewhere in
# this file commit as `t <t@example.invalid>`, which this rule refuses by
# design; every test below therefore sets the identity it means to test.
# ---------------------------------------------------------------------------

OWNER = "Mahmoud Salem"
OWNER_MAIL = "ma7moudalysalem@gmail.com"
OWNER_NOREPLY_MAIL = "1234567+ma7moudalysalem@users.noreply.github.com"


def _pr_as(work: Path, message: str, name: str = OWNER, email: str = OWNER_MAIL,
           committer_name: str | None = None, committer_email: str | None = None,
           files: dict | None = None) -> None:
    """One pull-request commit with a chosen message, author and committer.

    A later `-c` beats an earlier one, so these override the identity the
    `git` helper above sets for every other test; `--author` then moves the
    author away from the committer where a test needs the two to differ.
    """
    _pr_branch(work)
    write(work, files or {"docs/new.md": "# New\n\nProse.\n"})
    git(work, "add", "-A", "--force")
    git(work,
        "-c", f"user.name={committer_name or name}",
        "-c", f"user.email={committer_email or email}",
        "commit", "-q", "--no-verify", "--author", f"{name} <{email}>", "-m", message)


def test_owner_authored_commit_passes_attribution(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: add a note\n\nSigned-off-by: Mahmoud Salem <ma7moudalysalem@gmail.com>\n")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "commit_attribution" not in checks(run(work))


def test_co_authored_by_trailer_is_refused(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: add a note\n\nCo-authored-by: Someone Else <else@example.invalid>\n")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "commit_attribution")
    assert len(hits) == 1
    head = git(work, "rev-parse", "HEAD").strip()
    assert head[:12] in hits[0].message
    assert "Co-authored-by: trailer" in hits[0].message
    assert "one person's work" in hits[0].message


def test_generated_with_line_is_refused(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: add a note\n\nGenerated with a tool that wrote the prose.\n")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "commit_attribution")
    assert hits and 'generated with/by" line' in hits[0].message


def test_bot_author_is_refused(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "chore: bump a thing", name="renovate[bot]",
           email="renovate[bot]@users.noreply.github.com")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "commit_attribution")
    assert hits and "its author is renovate[bot]" in hits[0].message


def test_a_different_human_author_is_refused(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: add a note", name="Someone Else", email="else@example.invalid")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "commit_attribution")
    assert hits and "its author is Someone Else <else@example.invalid>" in hits[0].message


def test_a_different_committer_is_refused_even_when_the_author_is_the_owner(tmp_path, monkeypatch):
    # Both fields are checked: a rebase by someone else rewrites the committer
    # and leaves the author alone.
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: add a note", committer_name="Someone Else",
           committer_email="else@example.invalid")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "commit_attribution")
    assert hits and "its committer is Someone Else" in hits[0].message
    assert "its author is" not in hits[0].message


def test_github_noreply_address_is_the_same_person(tmp_path, monkeypatch):
    # The owner keeping the real address private, or committing in the web
    # editor. Refusing this form would refuse the owner's own commits.
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: add a note", email=OWNER_NOREPLY_MAIL)
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "commit_attribution" not in checks(run(work))
    assert cc.is_owner_email(OWNER_NOREPLY_MAIL)
    assert cc.is_owner_email(OWNER_MAIL.upper())
    assert not cc.is_owner_email("ma7moudalysalem@users.noreply.github.com")
    assert not cc.is_owner_email("evil+ma7moudalysalem@users.noreply.github.com")


def test_attribution_rule_is_silent_without_base_ref(tmp_path, monkeypatch):
    # Same condition as the other self-edit rules: no pull request, no rule.
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: a note\n\nCo-authored-by: Someone <s@example.invalid>\n",
           name="Someone Else", email="else@example.invalid")
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    assert "commit_attribution" not in checks(run(work))


def test_attribution_rule_reads_every_commit_in_the_range(tmp_path, monkeypatch):
    # One clean commit does not cover for a dirty one behind it.
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: first\n\nCo-authored-by: Someone <s@example.invalid>\n",
           files={"docs/one.md": "# One\n\nProse.\n"})
    dirty = git(work, "rev-parse", "HEAD").strip()
    _pr_as(work, "docs: second", files={"docs/two.md": "# Two\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "commit_attribution")
    assert len(hits) == 1 and dirty[:12] in hits[0].message


def test_attribution_findings_name_the_hook_that_holds_the_other_half(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _pr_as(work, "docs: a note", name="Someone Else", email="else@example.invalid")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "commit_attribution")
    assert hits and hits[0].path == ".githooks/commit-msg"


def test_commit_log_parser_fails_closed_on_a_short_record():
    with pytest.raises(ValueError):
        cc.parse_commit_log("sha\nname\nemail\n\0")
    parsed = cc.parse_commit_log("sha\nan\nae\ncn\nce\nsubject\n\nbody\n\0\n")
    assert len(parsed) == 1
    assert parsed[0]["sha"] == "sha" and parsed[0]["committer_email"] == "ce"
    assert parsed[0]["message"] == "subject\n\nbody\n"


# ---------------------------------------------------------------------------
# the CLI: exit codes and output formats
# ---------------------------------------------------------------------------

def cli(root: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_ACTIONS", "GITHUB_BASE_REF")}
    full_env.update(env or {})
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(root),
                          capture_output=True, text=True, encoding="utf-8", env=full_env)


def test_cli_exit_1_and_plain_lines_on_findings(tmp_path):
    root = make_repo(tmp_path, {"paper.PDF": PDF_BYTES})
    proc = cli(root, "--all")
    assert proc.returncode == 1
    assert "paper.PDF: [no_third_party_pdf]" in proc.stdout


def test_cli_exit_0_on_clean_repo_and_default_is_all(tmp_path):
    root = make_repo(tmp_path)
    proc = cli(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "no findings" in proc.stdout


def test_cli_emits_github_annotations_under_actions(tmp_path):
    root = make_repo(tmp_path, {"docs/x.md": "# D\n\n> " + words(50) + "\n"})
    proc = cli(root, "--all", env={"GITHUB_ACTIONS": "true"})
    assert proc.returncode == 1
    line = next(l for l in proc.stdout.splitlines() if l.startswith("::error "))
    assert line.startswith("::error file=docs/x.md,line=3,title=copyright%3A quote_over_limit::")


def test_cli_exit_1_on_every_new_check(tmp_path):
    root = make_repo(tmp_path, {
        "README.md": "# R\n\n> " + words(300) + "\n",
        "docs/pack.zip": b"PK\x03\x04",
        "docs/d.svg": svg_with_image('href="data:image/png;base64,AAAA"'),
        "docs/agg.md": "# D\n\n## S\n\n" + "\n\n".join("> " + words(38, f"p{k}x") for k in range(8)) + "\n",
    })
    proc = cli(root, "--all", env={"GITHUB_ACTIONS": "true"})
    assert proc.returncode == 1
    for check in ("quote_over_limit", "archive_present", "svg_embeds_raster", "quote_aggregate_over_limit"):
        assert f"title=copyright%3A {check}::" in proc.stdout


def test_cli_outside_a_repository_fails_closed(tmp_path):
    bare = tmp_path / "plain"
    bare.mkdir()
    proc = cli(bare, "--all", env={"GIT_CEILING_DIRECTORIES": str(tmp_path)})
    assert proc.returncode == 1


def test_annotation_escapes_properties_and_message():
    f = cc.Finding("c", "a,b:c.md", "50% done\nnext", 7)
    assert f.annotation() == "::error file=a%2Cb%3Ac.md,line=7,title=copyright%3A c::50%25 done%0Anext"


# ---------------------------------------------------------------------------
# fourth pass: B1 the guard judging itself, F1-F6 false positives in ordinary
# prose (every one a NEGATIVE test), H1-H4 accident holes (every one fires)
# ---------------------------------------------------------------------------

def test_guard_files_do_not_carry_the_pdf_header_in_their_first_two_kilobytes():
    # B1. pdf_magic_bytes sniffs every non-prose file for the header anywhere
    # in its first HEAD_BYTES, and the guard's own .py files are non-prose
    # files like any other; no path is exempt. The literal is built here by
    # concatenation for the same reason.
    header = b"%PDF" + b"-"
    for path in (SCRIPT, Path(__file__)):
        head = path.read_bytes()[:cc.HEAD_BYTES]
        assert header not in head, (
            f"{path.name} spells out the PDF header within its first {cc.HEAD_BYTES} bytes. "
            "The byte rule would then refuse the guard's own file, and the pre-commit hook "
            "would refuse the commit that ships it. Reword the docstring (say 'the PDF "
            "header') or build the bytes by concatenation; see the module docstrings.")


def test_guard_judges_its_own_files_clean_when_tracked(tmp_path):
    # B1, self-consistency. The real tools/ copied into a fresh repository
    # with both guard files tracked: --all (CI) and --staged (the hook, with
    # the two files staged) must both find nothing. Any future drift - a
    # literal header, an archive-shaped byte string near the top - shows here.
    root = tmp_path / "self"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    shutil.copytree(TOOLS, root / "tools",
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    git(root, "add", "-f", *cc.GUARD_FILES)
    assert set(cc.Repo(root, False).tracked()) == set(cc.GUARD_FILES)
    assert run(root, "all") == []
    assert run(root, "staged") == []
    proc = cli(root, "--staged")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = cli(root, "--all")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_apostrophe_elisions_do_not_open_quotations(tmp_path):
    # F1. A straight ' at a word start is an apostrophe when the word is an
    # elision: 'em, 'til, 'tis, 'bout, 'cause, rock 'n' roll. A trailing '
    # after a letter (goin', nothin') closes nothing when nothing is open.
    bodies = [
        "Give 'em a break, " + words(45) + " because it is rock 'n' roll, plainly.\n",
        "Wait 'til the end, " + words(45) + " and then we are goin' home.\n",
        "'Cause 'tis 'bout time, " + words(45) + " with nothin' goin' on.\n",
    ]
    root = make_repo(tmp_path, {f"docs/e{k}.md": "# D\n\n" + b for k, b in enumerate(bodies)})
    assert run(root) == []
    assert [s for _l, s in cc.quoted_spans("Give 'em a break and 'quoted' rock 'n' roll\n")] == ["quoted"]
    # ...and a real quotation after an elision still fires.
    bad = make_repo(tmp_path / "bad", {"docs/x.md": "# D\n\nGive 'em a break: '" + words(41) + "' they said.\n"})
    hits = only(run(bad), "quote_over_limit")
    assert hits and "41 words" in hits[0].message


def test_apostrophe_after_a_full_stop_or_a_letter_does_not_open(tmp_path):
    # F2. `et al.'s` sits after a full stop; the mark opens only after the
    # start of the block, whitespace or an opening bracket.
    body = ("Vaswani et al.'s central claim, " + words(45)
            + " is what they call 'self-attention' throughout.\n")
    ok = make_repo(tmp_path / "ok", {"docs/x.md": "# D\n\n" + body})
    assert run(ok) == []
    bad = make_repo(tmp_path / "bad", {"docs/x.md": "# D\n\nVaswani et al.'s claim, that '" + words(41) + "' holds.\n"})
    hits = only(run(bad), "quote_over_limit")
    assert hits and "41 words" in hits[0].message
    assert cc.quoted_spans("x.'no' y,'no' z;'no' w:'no' v'no' 5'no'\n") == []
    assert [s for _l, s in cc.quoted_spans("('yes') ['yes'] {'yes'}\n")] == ["yes"] * 3


def test_curly_single_marks_obey_the_same_word_boundary_rules(tmp_path):
    # F3. Word, Notion and Apple Notes emit ’ for every apostrophe, at word
    # starts too (’90s, ’em): the curly marks obey the straight marks' rules.
    files = {
        "docs/a.md": "# D\n\nIn the ’90s the field moved on, " + words(45) + " and Zhang’s method won.\n",
        "docs/b.md": "# D\n\nThe authors’ claim stands, " + words(45) + " and we don’t dispute it.\n",
        "docs/c.md": "# D\n\nGive ’em a break ’til then, " + words(45) + " and it’s fine.\n",
    }
    assert run(make_repo(tmp_path, files)) == []
    bad = make_repo(tmp_path / "bad", {"docs/x.md": "# D\n\nThey say ‘" + words(41) + "’ here.\n"})
    hits = only(run(bad), "quote_over_limit")
    assert hits and "41 words" in hits[0].message
    # A wrong-direction ’ at a word start still opens a real quotation.
    assert [s for _l, s in cc.quoted_spans("say ’one two’ and it’s fine\n")] == ["one two"]
    assert cc.quoted_spans("don’t and ‘90s and the authors’ view, ’em and ’til\n") == []


def test_frontmatter_is_not_scanned_for_quotations(tmp_path):
    # F4. A quoted `description:` scalar and single-quoted `title:`/`arxiv:`
    # values are YAML, not quotations; the quote rules never read the block.
    files = {
        "docs/a.md": '---\ntitle: T\ndescription: "' + words(45) + '"\n---\n\n# T\n\nBody.\n',
        "docs/b.md": ("---\ntitle: 'Llama 2: Open Foundation and Fine-Tuned Chat Models'\n"
                      "authors: " + words(45) + "\narxiv: '2307.09288'\n---\n\n# T\n\nBody.\n"),
        "docs/c.md": '---\ntitle: "Open\nauthors: ' + words(45) + '\nnote: end"\n---\n\n# T\n\nBody.\n',
        "docs/d.md": "---\ntitle: T\n---\n\n# T\n\n" + "\n\n".join(
            f'A "{words(35, f"q{k}x")}" claim.' for k in range(3)) + "\n",
    }
    found = run(make_repo(tmp_path, files))
    assert "quote_over_limit" not in checks(found)
    assert "quote_aggregate_over_limit" not in checks(found)
    # The same marks in the body pair as before...
    body = make_repo(tmp_path / "body", {"docs/x.md": '# T\n\ndescription: "' + words(45) + '"\n'})
    assert "quote_over_limit" in checks(run(body), "docs/x.md")
    # ...and the abstract key in the frontmatter is still read.
    fm = make_repo(tmp_path / "fm", {"docs/x.md": f'---\nabstract: "{words(70)}"\n---\n\n# T\n\nBody.\n'})
    assert "raw_abstract_present" in checks(run(fm), "docs/x.md")


def test_html_attribute_values_and_link_titles_are_not_quotations(tmp_path):
    # F5. Ten <img alt="..."> under one heading are 160 attribute words and
    # no quotation; a markdown link title is a tooltip.
    imgs = "## Figures\n\n" + "\n\n".join(
        f'<img src="f{k}.png" alt="{words(16, f"a{k}x")}">' for k in range(10)) + "\n"
    links = "## Links\n\n" + "\n".join(
        f'- [x{k}](https://example.invalid/{k} "{words(9, f"t{k}x")}")' for k in range(15)) + "\n"
    one = ('# D\n\n<img alt="' + words(41) + '"> and [y](u \'' + words(41, "v")
           + "') and ![z](i.png (" + words(41, "z") + ")) here.\n")
    root = make_repo(tmp_path, {"docs/i.md": "# D\n\n" + imgs, "docs/l.md": "# D\n\n" + links,
                                "docs/one.md": one, "docs/h.html": '<p>' + imgs + '</p>\n'})
    assert run(root) == []
    # A <blockquote> with attributes still counts: normalisation runs first.
    bq = make_repo(tmp_path / "bq", {"docs/x.md": '# D\n\n<blockquote class="x" cite="y">\n' + words(300) + "\n</blockquote>\n"})
    hits = only(run(bq), "quote_over_limit")
    assert [f.path for f in hits] == ["docs/x.md"] and "300 words" in hits[0].message
    # An encoded tag is literal text and its quotation marks are real ones.
    enc = make_repo(tmp_path / "enc", {"docs/x.md": '# D\n\n&lt;img alt="' + words(41) + '"&gt;\n'})
    assert "quote_over_limit" in checks(run(enc), "docs/x.md")
    assert cc.strip_tags('a <img alt="x\ny"> b\n').count("\n") == 2


def test_doctest_prompt_is_not_a_blockquote_marker(tmp_path):
    # F6. `>>>` is the doctest prompt; the marker is a `>` NOT followed by
    # another `>`. `> > nested`, with the space, is still two markers.
    transcript = ">>> import numpy as np\n>>> " + words(46) + "\n... " + words(10, "v") + "\n"
    ok = make_repo(tmp_path / "ok", {"docs/x.txt": "Notes\n\n" + transcript})
    assert run(ok) == []
    bad = make_repo(tmp_path / "bad", {"docs/x.txt": "Notes\n\n> " + words(46) + "\n",
                                       "docs/n.md": "# D\n\n> > nested " + words(46) + "\n"})
    found = run(bad)
    assert "quote_over_limit" in checks(found, "docs/x.txt")
    assert "quote_over_limit" in checks(found, "docs/n.md")
    assert cc.blockquotes(">>> a\n") == []
    assert cc.blockquotes("> > a\n") == [(1, "a")]


def test_raw_marker_line_in_an_html_file_is_an_accepted_over_match(tmp_path):
    # F7. GitHub shows an .html file as source, where a `> ` line is a
    # literal character; the scanner reads it as a blockquote all the same.
    # A harmless over-match, accepted and named in the checker's known
    # limits rather than special-cased - this test pins both halves.
    root = make_repo(tmp_path, {"docs/x.html": "<p>intro</p>\n> " + words(46) + "\n"})
    assert "quote_over_limit" in checks(run(root), "docs/x.html")
    assert "a raw `> ` line inside an `.html` file" in cc.__doc__


PAPER_PASTE = ("Title\n\nA. Person, B. Person\nUniversity\n\nAbstract\n\n" + words(180)
               + "\n\n1 Introduction\n\n" + words(200, "v") + "\n")


def test_pasted_paper_with_a_bare_abstract_line_is_caught(tmp_path):
    # H1. The most plausible accident: a whole paper pasted, `Abstract` on a
    # line of its own, no markdown heading anywhere. The abstract runs to the
    # next line that looks like a section title.
    root = make_repo(tmp_path, {"docs/paper.txt": PAPER_PASTE, "docs/paper.md": PAPER_PASTE})
    found = run(root)
    for name in ("docs/paper.txt", "docs/paper.md"):
        hits = [f for f in only(found, "raw_abstract_present") if f.path == name]
        assert len(hits) == 1, name
        assert "180-word" in hits[0].message and "lead-in" in hits[0].message
        assert "'Abstract'" in hits[0].message and "line 6" in hits[0].message
        assert hits[0].line == 8


@pytest.mark.parametrize("body", [
    "# T\n\n**Abstract.** " + words(180) + "\n\n## 1 Introduction\n\n" + words(200, "v") + "\n",
    "# T\n\nAbstract: " + words(180) + "\n\n2. Related Work\n\n" + words(200, "v") + "\n",
    "# T\n\n_Abstract_:\n" + words(180) + "\n\nMethods\n\n" + words(200, "v") + "\n",
    "# T\n\nABSTRACT\n\n" + words(180) + "\nI. Introduction\n" + words(200, "v") + "\n",
    "# T\n\n<b>Abstract</b>\n\n" + words(180) + "\n\nA. Setup\n\n" + words(200, "v") + "\n",
])
def test_abstract_lead_in_shapes_are_caught(tmp_path, body):
    # H1. `**Abstract.**`, `Abstract:` and the bare word, ended by a numbered
    # heading, a numbered plain line, or a bare capitalised title.
    root = make_repo(tmp_path, {"docs/x.md": body})
    hits = only(run(root), "raw_abstract_present")
    assert [f.path for f in hits] == ["docs/x.md"]
    assert "180-word" in hits[0].message and "lead-in" in hits[0].message
    # The finding names the lead-in line; it must not echo the abstract that
    # begins on it (`Abstract: <180 words>`) into a public CI log.
    echoed = re.findall(r"\bw\d+\b", hits[0].message)
    assert "w20" not in echoed and len(echoed) <= 2 * cc.REPORTED_SPAN_WORDS


def test_short_abstract_after_a_lead_in_passes(tmp_path):
    # H1, negative. Forty words under the lead-in and two hundred under
    # `1 Introduction`: the section title ends the abstract.
    body = "Abstract\n\n" + words(40) + "\n\n1 Introduction\n\n" + words(200, "v") + "\n"
    root = make_repo(tmp_path, {"docs/x.txt": body, "docs/y.md": "# T\n\n" + body})
    assert run(root) == []


def test_prose_beginning_with_the_word_abstract_is_not_a_lead_in(tmp_path):
    # H1, negative. The lead-in is the WHOLE line apart from `.` or `:`.
    files = {
        "docs/a.md": "# T\n\nThe abstract of the paper says that " + words(100) + "\n",
        "docs/b.md": "# T\n\nAbstract reasoning is hard. " + words(100) + "\n",
        "docs/c.txt": "Abstract reasoning is hard.\n" + words(100) + "\n",
        "docs/d.md": "# T\n\nAbstracts are short. " + words(100) + "\n",
    }
    assert run(make_repo(tmp_path, files)) == []
    assert cc.abstract_lead_in(["Abstract reasoning is hard."], 1, set()) is None
    assert cc.abstract_lead_in(["Abstract."], 1, set()) == (1, 1, "")


def test_abstract_heading_tests_still_hold_beside_the_lead_in(tmp_path):
    # H1. `## Abstract` sections are counted as before and not twice: a
    # lead-in line INSIDE a counted section is part of that section, not a
    # second piece. `Abstract:` is itself a word of the section to the reader
    # and to the counter, so 1 + 34 + 35 words are the 70 reported.
    body = "## Abstract\n\nAbstract: " + words(34) + "\n\n" + words(35, "v") + "\n\n## Method\n\nshort\n"
    root = make_repo(tmp_path, {"summaries/a/x.md": summary(body)})
    hits = only(run(root), "raw_abstract_present")
    assert len(hits) == 1 and "70-word" in hits[0].message and "lead-in" not in hits[0].message
    assert "'Abstract'" in hits[0].message and "every paragraph of the section" in hits[0].message
    # ...and a lead-in OUTSIDE every abstract section is still its own piece,
    # summed with the heading section rather than counted twice or dropped.
    # There the `Abstract:` token IS the lead-in and only the remainder
    # counts: 35 + 35.
    both = ("## Abstract\n\n" + words(35) + "\n\n## Method\n\nshort\n\nAbstract: " + words(35, "v")
            + "\n\n1 Introduction\n\n" + words(50, "x") + "\n")
    root = make_repo(tmp_path / "both", {"docs/x.md": "# T\n\n" + both})
    hits = only(run(root), "raw_abstract_present")
    assert len(hits) == 1 and "70-word" in hits[0].message
    assert "the heading 'Abstract'" in hits[0].message and "lead-in" in hits[0].message


def test_single_quotation_ending_in_s_closes(tmp_path):
    # H2. `'they write ... results'`: with a single quotation open, the mark
    # after the `s` closes it. With nothing open, `the authors'` is an
    # apostrophe, before and after a closed quotation.
    bad = make_repo(tmp_path / "bad", {"docs/x.md": "# D\n\nThey write '" + words(40) + " results' and stop.\n"})
    hits = only(run(bad), "quote_over_limit")
    assert hits and "41 words" in hits[0].message
    ok = make_repo(tmp_path / "ok", {
        "docs/a.md": "# D\n\nThe authors' position is clear, " + words(45) + " and the participants' view too.\n",
        "docs/b.md": "# D\n\nA 'closed quotation' first, " + words(45) + " then the authors' view.\n"})
    assert run(ok) == []
    assert [s for _l, s in cc.quoted_spans("'a closed quotation' then the authors' view\n")] == ["a closed quotation"]


def test_single_quotation_beginning_with_a_digit_opens(tmp_path):
    # H3. `'40 percent ...'` is a quotation that begins with a number; only
    # the decade shape ('90s, '80.) is refused.
    bad = make_repo(tmp_path / "bad", {"docs/x.md": "# D\n\nThey found '40 percent " + words(39) + "' of cases.\n"})
    hits = only(run(bad), "quote_over_limit")
    assert hits and "41 words" in hits[0].message
    ok = make_repo(tmp_path / "ok", {
        "docs/a.md": "# D\n\nIn the '90s, " + words(45) + " it held, as in the '80s and '90s.\n",
        "docs/b.md": "# D\n\nThe class of '80, " + words(45) + " and the '90s.\n"})
    assert run(ok) == []
    assert cc.quoted_spans("the '80s, the '80. and '80\n") == []
    assert [s for _l, s in cc.quoted_spans("'40 percent' and '2020 was'\n")] == ["40 percent", "2020 was"]


def test_latex_double_backtick_quotation_is_paired(tmp_path):
    # H4. ``forty-one words'' pasted from a .tex source is a quotation; the
    # pair is made before the inline-code pass sees the backticks.
    bad = make_repo(tmp_path / "bad", {"docs/x.md": "# D\n\nThey write ``" + words(41) + "'' there.\n",
                                       "docs/x.txt": "Notes\n\nThey write ``" + words(41) + "'' there.\n"})
    found = run(bad)
    for name in ("docs/x.md", "docs/x.txt"):
        hits = [f for f in only(found, "quote_over_limit") if f.path == name]
        assert hits and "41 words" in hits[0].message, name
    ok = make_repo(tmp_path / "ok", {
        "docs/a.md": "# D\n\nThey write ``" + words(40) + "'' there.\n",
        "docs/b.md": "# D\n\nAn inline `code` span and ``a `tick` inside`` stay code, " + words(45) + ".\n",
        "docs/c.md": "# D\n\n```python\nx = ``" + words(41) + "''\n```\n",
        "docs/d.md": "# D\n\n``" + words(30) + "\n\n" + words(30, "v") + "'' across a blank line.\n"})
    assert run(ok) == []
    assert cc.latex_quotes("``a b'' c\n") == "“ a b”  c\n"      # lengths preserved
    assert len(cc.blank_code("say ``x'' and `code`\n")) == len("say ``x'' and `code`\n")
    assert "code" not in cc.blank_code("say ``x'' and `code`\n")


# ---------------------------------------------------------------------------
# fifth pass (the `R` cases), from the review of pull request #9. Eight holes,
# each closed with a POSITIVE test that the hole now fires and a NEGATIVE test
# that the fix did not cost a false positive: R1 the two other ZIP
# signatures, R2 tracked symlinks, R3 UTF-8-clean rasters under prose names,
# R4 the SVG `<image>` tag boundary, R5 a pull request that DELETES the guard,
# R6 `check_copyright.py .`, R7 fetching the base ref on every run, R8 the
# hook's worktree-only test for the checker.
# ---------------------------------------------------------------------------

# R1 --------------------------------------------------------------------------

@pytest.mark.parametrize("name, head, how", [
    ("docs/empty.bin", b"PK\x05\x06" + b"\x00" * 18, "empty zip"),
    ("docs/split.bin", b"PK\x07\x08" + b"\x00" * 40, "split zip"),
])
def test_empty_and_split_zip_signatures_are_archives(tmp_path, name, head, how):
    # R1. Only the local-file header PK\x03\x04 was recognised. An archive
    # with nothing in it opens with the end-of-central-directory record and a
    # split one with the spanning marker; both are archives.
    root = make_repo(tmp_path, {name: head})
    hits = only(run(root), "archive_present")
    assert [f.path for f in hits] == [name]
    assert how in hits[0].message


def test_prose_about_pk_and_late_zip_bytes_are_not_archives(tmp_path):
    # R1, negative. The signatures are tested at offset 0 and nowhere else.
    root = make_repo(tmp_path, {
        "docs/pk.md": "PK is the Pakistani country code, and also how a zip begins.\n",
        "docs/pk.txt": "PK is the Pakistani country code.\n",
        "docs/late.bin": b"not an archive: " + b"PK\x03\x04" + b"PK\x05\x06" + b"PK\x07\x08",
    })
    assert run(root) == []
    assert cc.archive_kind(b"PK is the Pakistani country code") is None
    assert cc.archive_kind(b"xPK\x03\x04") is None
    assert cc.archive_kind(b"PK\x05\x06" + b"\x00" * 18) == "empty zip"
    assert cc.archive_kind(b"PK\x07\x08" + b"\x00" * 18) == "split zip"


# R2 --------------------------------------------------------------------------

def stage_symlink(root: Path, path: str, target: str, worktree: str) -> None:
    """Add `path` to the index as a symlink (mode 120000) pointing at `target`,
    and put `worktree` on disk at that path.

    Forged through the index rather than with `os.symlink`, for the same
    reason the checker reads the mode from git: creating a real link needs a
    privilege Windows does not hand out by default, and on such a checkout the
    link arrives as an ordinary file whose content is the target path. The
    working-tree bytes here are what a guard that FOLLOWED the link would
    read; every test below asserts that nothing read them.
    """
    blob = root / ".symlink-target-blob"
    blob.write_text(target, encoding="utf-8", newline="")
    git(root, "add", "--force", ".symlink-target-blob")
    sha = git(root, "rev-parse", ":.symlink-target-blob").strip()
    git(root, "rm", "-q", "--cached", ".symlink-target-blob")
    blob.unlink()
    write(root, {path: worktree})
    git(root, "update-index", "--add", "--cacheinfo", f"120000,{sha},{path}")


def test_tracked_symlinks_are_findings_and_their_targets_are_never_read(tmp_path):
    # R2. --all reads bytes from the working tree, so a link could have the
    # guard read - and quote, into a public CI log - a file outside the
    # checkout. The link is the finding; nothing at the far end is opened.
    root = make_repo(tmp_path)
    quoted = "# L\n\n> " + words(300) + "\n"
    stage_symlink(root, "docs/inside.md", "../summaries/03-foundation-models/clean.md", quoted)
    stage_symlink(root, "docs/outside.md", "../../../elsewhere/paper.md", quoted)
    found = run(root)
    assert {f.path for f in only(found, "symlink_present")} == {"docs/inside.md",
                                                                "docs/outside.md"}
    assert "mode 120000" in only(found, "symlink_present")[0].message
    # Read, those bytes are a 300-word blockquote. No rule saw one.
    assert "quote_over_limit" not in checks(found)
    assert checks(found, "docs/inside.md") == {"symlink_present"}
    assert checks(found, "docs/outside.md") == {"symlink_present"}
    assert cc.Repo(root, False).symlinks() == {"docs/inside.md", "docs/outside.md"}


def test_a_symlink_named_like_an_image_is_not_read_for_provenance(tmp_path):
    # R2. The byte rules have nothing to sniff and do not try.
    root = make_repo(tmp_path)
    stage_symlink(root, "docs/fig.png", "../../outside/fig.png", "PNG-ish worktree bytes")
    found = run(root)
    assert "symlink_present" in checks(found, "docs/fig.png")
    assert "unreadable_file" not in checks(found)
    assert "pdf_magic_bytes" not in checks(found)


def test_an_ordinary_file_is_not_a_symlink(tmp_path):
    # R2, negative. The same path, the same bytes, an ordinary blob: judged as
    # before, and no symlink finding anywhere.
    root = make_repo(tmp_path, {"docs/inside.md": "# L\n\n> " + words(300) + "\n"})
    found = run(root)
    assert "symlink_present" not in checks(found)
    assert "quote_over_limit" in checks(found, "docs/inside.md")
    assert cc.Repo(root, False).symlinks() == set()


# R3 --------------------------------------------------------------------------

# A minimal GIF whose every byte is ASCII or NUL: signature, a 1x1 logical
# screen descriptor (width, height, packed field, background index, pixel
# aspect ratio), trailer. It decodes as UTF-8, so the "prose is decoded, never
# sniffed" rule used to wave it straight through under a .txt or .md name.
GIF_BYTES = (b"GIF89a" + (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
             + b"\x00\x00\x00" + b";")
assert len(GIF_BYTES) == 14 and GIF_BYTES.decode("utf-8")


@pytest.mark.parametrize("name", ["docs/anim.txt", "docs/anim.md", "notes/A.TXT",
                                  "docs/anim.markdown", "docs/anim.rst"])
def test_utf8_clean_gif_under_a_prose_name_needs_provenance(tmp_path, name):
    # R3. A GIF renamed .txt survives the UTF-8 decode and was never sniffed.
    root = make_repo(tmp_path, {name: GIF_BYTES})
    hits = only(run(root), "image_provenance")
    assert [f.path for f in hits] == [name]
    assert "first bytes" in hits[0].message and "GIF" in hits[0].message


@pytest.mark.parametrize("name", ["docs/shot.txt", "docs/shot.md"])
def test_utf8_clean_bmp_under_a_prose_name_needs_provenance(tmp_path, name):
    root = make_repo(tmp_path, {name: BMP_BYTES})
    hits = only(run(root), "image_provenance")
    assert [f.path for f in hits] == [name]
    assert "BMP" in hits[0].message


def test_sniffed_prose_raster_with_a_declaration_passes(tmp_path):
    root = make_repo(tmp_path, {"docs/anim.txt": GIF_BYTES,
                                "docs/anim.source.yml": "origin: cc-licensed\n"})
    assert "image_provenance" not in checks(run(root))


def test_prose_naming_an_image_format_is_not_an_image(tmp_path):
    # R3, negative. The first line of a prose file is a sentence somebody
    # wrote. Full format validation is what keeps these clean.
    root = make_repo(tmp_path, {
        "docs/gif.md": "GIF89a is the second version of the format.\n\n# Formats\n",
        "docs/gif.txt": "GIF87a is the first version; GIF89a added transparency.\n",
        "docs/bm25.md": "BM25 is a ranking function used in retrieval.\n\n# Ranking\n",
        "docs/bm25.txt": "BM25 is a ranking function used in retrieval.\n",
        "docs/png.rst": "PNG files open with a high byte and the three letters PNG.\n",
    })
    assert run(root) == []


def test_strict_raster_kind_requires_whole_headers():
    # R3. The prose sniff validates; the non-prose sniff still takes a prefix.
    assert cc.strict_raster_kind(PNG_BYTES) == "PNG"
    assert cc.strict_raster_kind(b"\x89PNG" + b"x" * 20) is None
    assert cc.strict_raster_kind(JPEG_BYTES) == "JPEG"
    assert cc.strict_raster_kind(b"\xff\xd8\xff\xdb" + b"\x00" * 20) == "JPEG"
    assert cc.strict_raster_kind(b"\xff\xd8\xff\x01" + b"\x00" * 20) is None
    assert cc.strict_raster_kind(GIF_BYTES) == "GIF"
    assert cc.strict_raster_kind(b"GIF89a" + b"\x00" * 40) is None        # a 0x0 screen
    assert cc.strict_raster_kind(b"GIF89a is the second version") is None
    assert cc.strict_raster_kind(BMP_BYTES, 50) == "BMP"
    assert cc.strict_raster_kind(BMP_BYTES, 51) is None
    assert cc.strict_raster_kind(BMP_BYTES) is None
    assert cc.raster_kind(b"\x89PNG" + b"x" * 20) == "PNG"
    assert cc.raster_kind(b"GIF89a" + b"\x00" * 40) == "GIF"


# R4 --------------------------------------------------------------------------

GT_IN_ATTRIBUTE_SVG = ('<svg xmlns="http://www.w3.org/2000/svg">'
                       '<image aria-label="a > b" '
                       'href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==">'
                       "</svg>\n")


def test_svg_image_tag_with_a_gt_inside_a_quoted_attribute_is_found(tmp_path):
    # R4. The tag pattern stopped at the first `>` of any kind, so the tag was
    # never matched, no raster was seen, and `origin: original` with the SVG
    # as its own editable source certified the bitmap.
    root = make_repo(tmp_path, {"assets/figures/d.svg": GT_IN_ATTRIBUTE_SVG,
                                "assets/figures/d.source.yml": "origin: original\n"})
    hits = only(run(root), "svg_embeds_raster")
    assert [f.path for f in hits] == ["assets/figures/d.svg"]
    assert "cannot certify its own provenance" in hits[0].message
    embedded = cc.svg_embedded_rasters(GT_IN_ATTRIBUTE_SVG)
    assert len(embedded) == 1 and embedded[0].startswith("data:image/png;base64,")


def test_svg_with_no_raster_stays_clean_even_with_a_gt_in_an_attribute(tmp_path):
    # R4, negative. Tolerating quoted `>` must not invent a raster.
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
           "<title>a &gt; b</title>"
           '<rect aria-label="a > b" x="1" y="1" width="8" height="8"/>'
           '<image aria-label="a > b" href="inset.svg"/>'
           '<path d="M0 0L10 10"/></svg>\n')
    root = make_repo(tmp_path, {"assets/figures/d.svg": svg,
                                "assets/figures/d.source.yml": "origin: original\n"})
    assert run(root) == []
    assert cc.svg_embedded_rasters(svg) == []
    assert cc.svg_embedded_rasters(SVG_SHAPES) == []


# R5 --------------------------------------------------------------------------

def _delete_in_pr(work: Path, *paths: str) -> None:
    _pr_branch(work)
    for path in paths:
        git(work, "rm", "-q", path)
    git(work, "commit", "-q", "--no-verify", "-m", "pr")


def test_deleting_the_checker_alone_is_a_finding(tmp_path, monkeypatch):
    # R5. A deletion changes guard paths only, so the "guard and content do
    # not travel together" rule passed it and the merge left no guard.
    work = _clone_with_upstream(tmp_path)
    _delete_in_pr(work, "tools/check_copyright.py")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "guard_self_edit")
    assert len(hits) == 1 and hits[0].path == "tools/check_copyright.py"
    assert "does not contain tools/check_copyright.py" in hits[0].message
    assert "may not remove it" in hits[0].message


def test_deleting_the_hook_alone_is_a_finding(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _delete_in_pr(work, ".githooks/pre-commit")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "guard_self_edit")
    assert len(hits) == 1 and hits[0].path == ".githooks/pre-commit"
    assert "does not contain .githooks/pre-commit" in hits[0].message


def test_deleting_the_tests_alone_is_a_finding(tmp_path, monkeypatch):
    work = _clone_with_upstream(tmp_path)
    _delete_in_pr(work, "tools/tests/test_check_copyright.py")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    hits = only(run(work), "guard_self_edit")
    assert len(hits) == 1 and hits[0].path == "tools/tests/test_check_copyright.py"


def test_modifying_the_checker_alone_still_passes(tmp_path, monkeypatch):
    # R5, negative. Guard-only MODIFICATIONS must keep merging; without them
    # no fix to the guard could ever land, including this one.
    work = _clone_with_upstream(tmp_path)
    _pr(work, {"tools/check_copyright.py": "# changed\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "guard_self_edit" not in checks(run(work))


def test_the_normal_tree_passes_the_guard_presence_rule(tmp_path, monkeypatch):
    # R5, negative. A content-only pull request on a tree that still has its
    # guard is clean, and the required set is exactly these three paths.
    work = _clone_with_upstream(tmp_path)
    _pr(work, {"docs/new.md": "# New\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert "guard_self_edit" not in checks(run(work))
    assert cc.REQUIRED_GUARD_PATHS == ("tools/check_copyright.py",
                                       "tools/tests/test_check_copyright.py",
                                       ".githooks/pre-commit")
    assert all(cc.is_guard(p) for p in cc.REQUIRED_GUARD_PATHS)


# R6 --------------------------------------------------------------------------

def test_repository_root_as_a_path_argument_scans_the_whole_tree(tmp_path, monkeypatch):
    # R6. `.` resolved to the prefix "./", which matches no git path, so the
    # run selected nothing and exited 0 while looking like a full scan.
    root = make_repo(tmp_path, {"paper.PDF": PDF_BYTES,
                                "docs/x.md": f'# D\n\n"{words(50)}"\n'})
    monkeypatch.chdir(root)
    everything = {"no_third_party_pdf", "pdf_magic_bytes", "quote_over_limit"}
    assert checks(run(root, "paths", ["."])) == everything
    assert checks(run(root, "paths", [str(root)])) == everything
    assert run(root, "paths", ["."]) == run(root, "all")
    assert run(root, "paths", [str(root)]) == run(root, "all")


def test_a_subdirectory_path_argument_still_selects_only_its_own(tmp_path, monkeypatch):
    # R6, negative. Widening the root must not widen a subdirectory.
    root = make_repo(tmp_path, {"paper.PDF": PDF_BYTES,
                                "docs/x.md": f'# D\n\n"{words(50)}"\n'})
    monkeypatch.chdir(root)
    found = run(root, "paths", ["docs"])
    assert [f.path for f in found] == ["docs/x.md"]
    assert checks(found) == {"quote_over_limit"}


def test_cli_dot_scans_the_whole_tree(tmp_path):
    root = make_repo(tmp_path, {"paper.PDF": PDF_BYTES})
    proc = cli(root, ".")
    assert proc.returncode == 1
    assert "paper.PDF: [no_third_party_pdf]" in proc.stdout
    clean = make_repo(tmp_path / "clean")
    proc = cli(clean, ".")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "no findings (paths)" in proc.stdout


# R7 --------------------------------------------------------------------------

def test_base_ref_resolved_locally_is_never_fetched(tmp_path, monkeypatch):
    # R7. The workflow checks the tree out with fetch-depth 0, so the base
    # commit is already there and `origin/<ref>` resolves. Fetching anyway
    # turned a restricted runner or one dropped packet into a blocking
    # finding on a valid pull request.
    work = _clone_with_upstream(tmp_path)
    # What such a checkout looks like: origin/release exists, release does not.
    git(work, "update-ref", "refs/remotes/origin/release", "HEAD")
    _pr(work, {"docs/new.md": "# New\n\nProse.\n"})
    monkeypatch.setenv("GITHUB_BASE_REF", "release")

    calls: list[tuple] = []
    real_git = cc.Repo.git

    def spy(self, *args, **kwargs):
        calls.append(args)
        return real_git(self, *args, **kwargs)

    monkeypatch.setattr(cc.Repo, "git", spy)
    found = run(work)
    assert "workflow_self_edit" not in checks(found)
    assert "guard_self_edit" not in checks(found)
    assert not [a for a in calls if a and a[0] == "fetch"]
    assert ("rev-parse", "--verify", "--quiet", "release^{commit}") in calls
    assert ("rev-parse", "--verify", "--quiet", "origin/release^{commit}") in calls
    assert [a for a in calls if a and a[0] == "diff" and "--no-renames" in a]
    assert cc.base_candidates("main") == ("main", "origin/main", "refs/remotes/origin/main")


def test_unresolvable_base_ref_still_blocks_and_says_what_to_run(tmp_path, monkeypatch):
    # R7, the other half. Failing open is the hole the rule exists to close,
    # so when nothing resolves and the fetch fails too, the finding stands.
    work = _clone_with_upstream(tmp_path)
    monkeypatch.setenv("GITHUB_BASE_REF", "no-such-branch")
    found = run(work)
    for check in ("workflow_self_edit", "guard_self_edit", "commit_attribution"):
        hits = only(found, check)
        assert hits, check
        message = hits[0].message
        assert "could not be resolved locally" in message
        assert "origin/no-such-branch, refs/remotes/origin/no-such-branch" in message
        assert "failing open here is the hole this rule exists to close" in message
        assert "git fetch origin no-such-branch" in message
        assert "fetch-depth: 0" in message
        assert message.endswith("; the guard fails closed.")


# R8 --------------------------------------------------------------------------

HOOK = TOOLS.parent / ".githooks" / "pre-commit"
SH = shutil.which("sh")
needs_sh = pytest.mark.skipif(SH is None, reason="no POSIX sh on PATH")


def run_hook(root: Path, path_env: str | None = None) -> subprocess.CompletedProcess:
    """The real hook script, run by sh, in a throwaway repository."""
    env = dict(os.environ)
    if path_env is not None:
        env["PATH"] = path_env
    return subprocess.run([SH, HOOK.as_posix()], cwd=str(root), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env)


@needs_sh
def test_hook_blocks_when_the_checker_is_missing_from_the_worktree(tmp_path):
    # R8, one way round: tracked, but not on disk. The hook cannot run it.
    root = make_repo(tmp_path, {"tools/check_copyright.py": "import sys\nsys.exit(0)\n"})
    (root / "tools" / "check_copyright.py").unlink()
    proc = run_hook(root)
    assert proc.returncode == 1
    assert "COMMIT BLOCKED" in proc.stderr
    assert "WORKING TREE" in proc.stderr
    assert "NOT IN THE INDEX" not in proc.stderr


@needs_sh
def test_hook_blocks_when_the_checker_is_missing_from_the_index(tmp_path):
    # R8, the other way round: on disk, but `git rm --cached` took it out of
    # the index. The old hook found the file, ran it happily, and let through
    # the very commit that removed the guard from the repository.
    root = make_repo(tmp_path, {"tools/check_copyright.py": "import sys\nsys.exit(0)\n"})
    git(root, "rm", "-q", "--cached", "tools/check_copyright.py")
    proc = run_hook(root)
    assert proc.returncode == 1
    assert "COMMIT BLOCKED" in proc.stderr
    assert "NOT IN THE INDEX" in proc.stderr
    assert "WORKING TREE" not in proc.stderr
    assert (root / "tools" / "check_copyright.py").is_file()


@needs_sh
def test_hook_gets_past_both_presence_tests_when_the_checker_is_there(tmp_path):
    # R8, negative. With the file in both places the hook proceeds to the
    # interpreter search - proved here by scrubbing python off PATH and
    # getting that failure rather than either presence failure.
    root = make_repo(tmp_path, {"tools/check_copyright.py": "import sys\nsys.exit(0)\n"})
    # A PATH holding git and nothing else. Pointing at git's own directory is
    # not that: on a Linux runner git lives in /usr/bin beside python3, so the
    # hook found an interpreter, ran the stub checker and exited 0 - this test
    # failed in CI while passing on Windows, where git's directory holds no
    # python.
    only_git = tmp_path / "only-git"
    only_git.mkdir()
    shim = only_git / "git"
    shim.write_text('#!/bin/sh\nexec "%s" "$@"\n' % Path(shutil.which("git")).as_posix(),
                    encoding="utf-8", newline="\n")
    shim.chmod(0o755)
    proc = run_hook(root, path_env=str(only_git))
    assert proc.returncode == 1
    assert "no python interpreter on PATH" in proc.stderr
    assert "WORKING TREE" not in proc.stderr and "NOT IN THE INDEX" not in proc.stderr


# ---------------------------------------------------------------------------
# .githooks/commit-msg - the local half of the attribution rule
# ---------------------------------------------------------------------------

MSG_HOOK = TOOLS.parent / ".githooks" / "commit-msg"
SIGN_OFF = f"Signed-off-by: {OWNER} <{OWNER_MAIL}>\n"


def run_msg_hook(tmp_path: Path, message: str) -> subprocess.CompletedProcess:
    """The real commit-msg hook, run by sh, over a message file."""
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text(message, encoding="utf-8", newline="\n")
    return subprocess.run([SH, MSG_HOOK.as_posix(), str(msg)], cwd=str(tmp_path),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


@needs_sh
def test_msg_hook_accepts_a_conventional_commit_signed_by_the_owner(tmp_path):
    proc = run_msg_hook(tmp_path, "docs: add a note\n\n" + SIGN_OFF)
    assert proc.returncode == 0, proc.stderr


@needs_sh
@pytest.mark.parametrize("line, wanted", [
    ("Co-authored-by: Someone Else <else@example.invalid>", "a Co-authored-by: trailer"),
    ("co-authored-by: someone <s@example.invalid>", "a Co-authored-by: trailer"),
    ("Generated with a tool that wrote it", 'a "generated with/by" line'),
    ("generated   by something", 'a "generated with/by" line'),
    ("Bumped by renovate[bot]", "a [bot] marker"),
])
def test_msg_hook_rejects_an_authorship_claim(tmp_path, line, wanted):
    proc = run_msg_hook(tmp_path, f"docs: add a note\n\n{line}\n\n" + SIGN_OFF)
    assert proc.returncode == 1
    assert wanted in proc.stderr
    assert "one person's work" in proc.stderr


@needs_sh
def test_msg_hook_does_not_fire_on_the_bare_word_bot(tmp_path):
    # Negative: `[bot]` is the marker, not the letters b, o and t. An
    # unescaped bracket expression matched any one of them.
    proc = run_msg_hook(tmp_path, "docs: a note about bots and robots\n\n" + SIGN_OFF)
    assert proc.returncode == 0, proc.stderr


@needs_sh
def test_msg_hook_requires_the_sign_off_to_name_the_owner(tmp_path):
    proc = run_msg_hook(tmp_path,
                        "docs: add a note\n\nSigned-off-by: Someone Else <else@example.invalid>\n")
    assert proc.returncode == 1
    assert "does not name the owner" in proc.stderr
    assert f"Signed-off-by: {OWNER} <{OWNER_MAIL}>" in proc.stderr


@needs_sh
def test_msg_hook_keeps_its_existing_rules(tmp_path):
    # The grammar, the 72-character ceiling, the missing sign-off and the
    # merge exemption all predate the attribution rules and must survive them.
    assert run_msg_hook(tmp_path, "add a note\n\n" + SIGN_OFF).returncode == 1
    assert "want: type(optional-scope): subject" in run_msg_hook(
        tmp_path, "add a note\n\n" + SIGN_OFF).stderr
    long_subject = "docs: " + "x" * 70
    assert "the ceiling is 72" in run_msg_hook(tmp_path, long_subject + "\n\n" + SIGN_OFF).stderr
    assert "Missing DCO sign-off" in run_msg_hook(tmp_path, "docs: add a note\n").stderr
    assert run_msg_hook(tmp_path, "Merge branch 'main'\n").returncode == 0


# ---------------------------------------------------------------------------
# unit tests for the markdown helpers, because the pairing rule is the part
# most likely to be "fixed" into a regex later
# ---------------------------------------------------------------------------

def test_quoted_spans_pair_in_reading_order():
    spans = cc.quoted_spans('say "one two" and "three"\n')
    assert [s for _l, s in spans] == ["one two", "three"]


def test_quoted_spans_reset_at_block_boundaries():
    text = '- "open\n- close"\n\n"para one\n\n# head"\n> "bq\nmore"\n'
    spans = cc.quoted_spans(text)
    assert [s for _l, s in spans] == ["bq\nmore"]


def test_quoted_spans_pair_by_family():
    text = 'say “one two” and «three» and ‘four’ and „fünf“ and ‹six› and "seven"\n'
    assert [s for _l, s in cc.quoted_spans(text)] == ["one two", "three", "four", "fünf", "six", "seven"]


def test_quoted_spans_do_not_cross_families():
    # A » cannot close a “, and a ’ (an apostrophe, here) cannot close a ".
    text = '“open » still open ” closed\n\n"the paper’s claim" done\n'
    assert [s for _l, s in cc.quoted_spans(text)] == ["open » still open ", "the paper’s claim"]


def test_quoted_spans_ignore_a_second_opener_while_one_is_pending():
    # A stray opener dropped into the middle of a quotation does not split it.
    text = "“one two “three four” five\n"
    assert [s for _l, s in cc.quoted_spans(text)] == ["one two “three four"]


def test_quoted_spans_straight_single_only_at_word_boundaries():
    # Expectation changed in the fourth pass (F1): `'n'` is an elision, not
    # a one-letter quotation.
    text = "don't and Zhang's and the authors' 'quoted' rock 'n' roll\n"
    assert [s for _l, s in cc.quoted_spans(text)] == ["quoted"]


def test_blank_code_preserves_length_and_newlines():
    # Fixture changed from a bare ``` fence in the second hardening: an empty
    # info string is a verbatim fence now, and only a real language is code.
    text = "a `code` b\n```python\nfenced\n```\nc\n"
    scan = cc.blank_code(text)
    assert len(scan) == len(text) and scan.count("\n") == text.count("\n")
    assert "code" not in scan and "fenced" not in scan and scan.startswith("a ") and "c\n" in scan


def test_blank_code_marks_a_verbatim_fence_as_a_blockquote():
    text = "a\n```text\nkept `tick`\n\nmore\n```\nb\n"
    lines = cc.blank_code(text).split("\n")
    assert len(lines) == len(text.split("\n"))
    assert lines[2] == "> kept  tick " and lines[3] == "> " and lines[4] == "> more"
    assert lines[1].strip() == "" and lines[5].strip() == "" and lines[6] == "b"


def test_normalise_html_keeps_the_line_count():
    text = "x\n<blockquote\n cite='a'>\nq1\n\nq2\n</blockquote>\n<h2>\nAbstract\n</h2>\ntail <q>w</q>\n"
    scan = cc.normalise_html(text)
    assert scan.count("\n") == text.count("\n")
    lines = scan.split("\n")
    assert lines[3] == "> q1" and lines[4] == "> " and lines[5] == "> q2"
    assert lines[7] == "## Abstract" and lines[10] == 'tail "w"'


def test_decode_entities_keeps_the_line_count():
    text = "a&#10;b\n&quot;c&nbsp;d&quot;\n"
    scan = cc.decode_entities(text)
    assert scan.count("\n") == text.count("\n")
    assert scan == 'a b\n"c d"\n'


def test_frontmatter_abstract_reader():
    assert cc.frontmatter_abstract("---\nAbstract: |\n  a b\n\n  c\nx: 1\n---\nbody\n") == (2, "a b c")
    assert cc.frontmatter_abstract("---\nabstract: plain words here\n---\n") == (2, "plain words here")
    # Inverted in the third pass (Z5): a nested key renders in the frontmatter
    # table just as a top-level one does, so any indentation counts.
    assert cc.frontmatter_abstract("---\nmeta:\n  abstract: nested\n---\n") == (3, "nested")
    assert cc.frontmatter_abstract('---\n"abstract": quoted key\n---\n') == (2, "quoted key")
    assert cc.frontmatter_abstract("# no frontmatter\n\nabstract: x\n") is None


def test_parse_flat_yaml_rejects_duplicates_and_accepts_quotes():
    assert cc.parse_flat_yaml('origin: "redrawn"\nnote: x # c\n') == {"origin": "redrawn", "note": "x"}
    with pytest.raises(ValueError):
        cc.parse_flat_yaml("origin: a\norigin: b\n")
    with pytest.raises(ValueError):
        cc.parse_flat_yaml("just words\n")


def test_count_words_ignores_bare_punctuation():
    assert cc.count_words("one — two ... three-four 5") == 4


def test_count_words_treats_no_break_space_as_whitespace():
    assert cc.count_words("one\u00a0two\u00a0three") == 3


def test_svg_embedded_rasters_helper():
    assert cc.svg_embedded_rasters(SVG_SHAPES) == []
    assert cc.svg_embedded_rasters(svg_with_image('href="shapes.svg"')) == []
    assert cc.svg_embedded_rasters(svg_with_image("href=fig.jpg")) == ["fig.jpg"]
    assert len(cc.svg_embedded_rasters('<svg><feImage xlink:href="data:image/png;base64,AAAA"/></svg>')) == 1


def test_no_3_12_only_syntax_in_checker():
    # CI runs on the ubuntu runner's Python; the guard must import on 3.11.
    for path in (SCRIPT, Path(__file__)):
        src = path.read_text(encoding="utf-8")
        ast.parse(src, filename=str(path), feature_version=(3, 11))
        assert "\ntype " not in src
        assert not any(line.lstrip().startswith(("def ", "class ")) and "[" in line.split("(")[0]
                       for line in src.splitlines())
