#!/usr/bin/env python3
"""The public copyright guard - layer three of three.

Three layers, because each of the first two can be stepped over and the trade
is worth it: an extra place to keep in step, in exchange for a rule that holds
whichever route a file took into the repository.

Layer one is `.gitignore`, which anyone can edit. Layer two is
`.githooks/pre-commit`, which runs this file with `--staged` and which
`--no-verify` skips and GitHub's web editor never sees. This is the layer that
runs however the commit was made: `.github/workflows/copyright.yml` calls it
with `--all` on every pull request and every push to main.

It is a deliberately INDEPENDENT implementation of the refusals in the private
toolbox's `promote.py`, not a copy of them. The private tool guards the
promotion path; this guards the repository, including every file that arrived
by some other route - a drag-and-drop in the web editor, a stray `git add`, a
rename. A stale mirror of the thing that catches your worst mistake is a real
risk, so the pairing logic, the YAML reader and the markdown scanning here are
written from the rules in COPYRIGHT.md rather than from the private source.

What this checks and what it does not
--------------------------------------

A stranger cannot reach main: the ruleset requires a pull request and the
owner merges it. The prose rules therefore face ONE realistic adversary: the
owner at 23:40, pasting an abstract, renaming a PDF, copying a blockquote.
Accidents do not use homoglyphs, CJK brackets, `<foreignObject>`, or the PDF
header at byte 1025. So:

* Byte-level and structural checks stay AIRTIGHT. A PDF is a PDF whatever it
  is called; an archive is an archive, whichever of the three ZIP signatures
  it opens with; a bitmap under a `.txt` name is a bitmap (a PNG or a JPEG
  fails UTF-8 decoding and is refused as unreadable, which is the same
  refusal by another name, and a GIF or a BMP - which are ASCII-and-NUL and
  do decode - is sniffed under full format validation and refused for want of
  provenance). A tracked symlink is refused outright and never followed.
* Prose rules are a TRIPWIRE for accidents. They are tuned for ZERO false
  positives on legitimate scholarly prose FIRST - a reading list of thirty
  quoted titles, a 12" display, the '90s, a bibliography of `Zhang's` and
  `the authors'` - because a checker that fires on a bibliography gets
  disabled, and then it catches nothing. A bypass that requires deliberate
  obfuscation is documented, not chased.
* The guard's own source is judged by the byte rules like every other
  non-prose file, with no path exempted. So neither this file nor its tests
  may carry the PDF header - the four characters `%PDF` followed by a hyphen
  - anywhere in their first 2 KB: the sniff would refuse the guard itself,
  and the pre-commit hook would refuse the commit that ships it. The words
  are reworded instead ("the PDF header"), fixture bytes are built by
  concatenation, and a test holds that line.

Known limits, each one a limit and not a fix for the same reason - the one
adversary is an accident, and none of these happens by accident:

* **cross-family quote pairs** (open `«`, close `”`), **CJK corner brackets**
  (`「」`), **U+201F** and the **fullwidth marks** are not quotation marks to
  the pairing rule; nobody pastes a blockquote with a Japanese bracket by
  mistake.
* **a quotation opened in one paragraph and closed in the next** never pairs,
  because pairing resets at every blank line to keep two scare-quoted terms in
  neighbouring bullets from becoming one quotation; an accidental paste keeps
  its marks in one paragraph.
* **nested same-family quotes closing early** (a `"` inside a `"` quotation
  ends it) under-count, never over-count.
* **homoglyph or comment-split headings** (`## Abstrаct` with a Cyrillic а,
  `## Abs<!-- -->tract`) escape the abstract rule; an accident spells the word.
* **chunking a passage across many H2 sections** below both the per-section
  and the per-file ceiling reproduces it in pieces; a deliberate edit, not a
  paste.
* **the PDF header beyond 2 KB of junk**, **EPS**, and **ISOBMFF/AVIF/HEIC/
  JXL/JP2 bytes under a non-image name** are not sniffed; a renamed PDF keeps
  its header at the top, and this repository has no reason to hold those
  formats under any name.
* **TIFF and WebP bytes under a PROSE name** are not sniffed. Prose is
  sniffed only under full format validation (PNG's whole signature, JPEG's
  SOI plus an APPn or DQT marker, a GIF signature plus a plausible logical
  screen descriptor, BMP's self-describing size field), and neither TIFF nor
  WebP has a header that can be validated without guessing. Under a
  non-prose name both are caught by the loose sniff as before, and a real
  file of either kind carries compressed pixel data that does not survive the
  UTF-8 decode every prose file gets.
* **`<foreignObject><img>` inside an SVG** and **an empty editable source
  satisfying provenance** are not caught; the provenance rule verifies that
  the owner made a declaration, not that the declaration is true.
* **a file added under `tools/` that is neither this checker nor its tests**
  (say a second script) is not a guard path, so editing it alongside content
  is not a self-edit finding; harmless, because CI runs main's copy of this
  file against the pull request's tree, and a script that is not the guard
  does not judge anything.
* **a raw `> ` line inside an `.html` file** is a blockquote to the scanner
  although GitHub shows `.html` as source, where it is a literal character;
  a harmless over-match, accepted rather than special-cased.
* **`>>` with no space between the markers** is not a blockquote marker,
  although CommonMark nests one; `>>>` is a doctest prompt in a `.txt` file,
  and a pasted quotation uses `> `.
* **a bare two-digit year followed by more words** (`the class of '80 and`)
  opens a candidate single quotation, which is dropped unless a closing mark
  follows in the same paragraph; `'80s`, `'80.` and `'80,` are decades and
  open nothing.
* **an abstract lead-in whose second paragraph begins with a short
  capitalised line** (`We show three things`, wrapped) is cut there, because
  such a line is what a section title looks like; an under-count.

Design rules, in the order they matter:

* **Fail closed.** A file that cannot be read, decoded or parsed is a finding,
  never a skip. The audit that prompted this rewrite found four holes, and
  every one of them was a check that silently did nothing on unexpected input.
* **Nothing outside the repository is read.** `--all` reads bytes from the
  working tree, so a tracked symlink would let a pull request point the guard
  at a file that is not in the checkout and have it read, judge and quote
  that file in a public CI log. A tracked symlink is therefore a finding of
  its own (`symlink_present`) and its target is never opened. The mode comes
  from git, not from the filesystem, so a Windows checkout - where the link
  is stored as an ordinary file - is judged the same as a POSIX one.
* **The name is not the file.** Extensions are matched case-insensitively
  (`paper.PDF` walked past the old check) and the PDF, archive and image rules
  also read magic bytes, because a publisher PDF committed as `docs/img/scan`
  has no extension at all and a PNG called `notes.dat` is still a PNG. Byte
  sniffing runs on every file that is not prose; a prose file is decoded as
  UTF-8 instead, and neither image bytes nor a real PDF's compressed streams
  survive that. (A hand-typed, pure-ASCII PDF under a `.txt` name would; no
  accident produces one, and a page may name the PDF header in its first
  line.)
* **The rendered page is the thing judged.** GitHub decodes HTML entities,
  renders `<blockquote>`, `<pre>` and `<h2>` as their markdown equivalents,
  shows a ```` ```text ```` fence and an indented code block verbatim, and
  drops `<!-- comments -->` on the floor. The scanner normalises all of those
  before it counts a single word, so what the reader sees is what the rule
  measures - and what the reader does not see is not a finding.
* **No whitelist of directories.** Every `.md`, `.markdown`, `.txt`, `.rst`,
  `.html` and `.htm` file, wherever it sits and in any letter case, is prose.
  The previous version scanned six named directories, and a seventh one was
  all it took to walk past it. Markdown gets the full rendering treatment;
  HTML gets the HTML normalisation; `.txt` and `.rst` are scanned as they are,
  because GitHub shows them as they are.
* **Standard library only.** The public repository has no requirements file
  and must not acquire one for its guard. The `.source.yml` files are flat
  `key: value` documents and are read by a hand-rolled reader below.
* **Nothing private is imported or read.** Constants that originate in private
  config are declared below with a comment naming their source, so drift shows
  up in a diff instead of silently.
* **The judge is not editable by the judged, and not deletable either.** The
  workflow runs main's copy of this file against the pull request's tree;
  that is the real defence. The self-edit rules here are belt and braces on
  top of it, never the only thing standing - and because main's copy is what
  runs, they can also refuse a tree that has dropped the checker, its tests
  or the pre-commit hook (REQUIRED_GUARD_PATHS). Changing the guard is
  allowed; removing it is not.
* **The history says one person wrote it, or it does not merge.**
  `commit_attribution` reads every commit on a pull request and refuses a
  `Co-authored-by:` trailer, a "generated with/by" line, a `[bot]` marker,
  and any author or committer who is not the owner. The claim survives the
  merge - a squash keeps the trailers - so it is refused before it lands.
  `.githooks/commit-msg` refuses the same message locally; a hook does not
  run in GitHub's web editor, which is why the rule is in both places.

Usage:
    python tools/check_copyright.py [--all | --staged | PATH...]

    --all      every tracked file, read from the working tree (CI; the default)
    --staged   files in the git index, read FROM THE INDEX (the pre-commit hook)
    PATH...    specific files or directories, read from the working tree. A
               path that resolves to the repository root - `.`, or the root's
               own absolute path - means the whole tracked tree, as --all does.

Exit 1 on any finding. Findings are printed as GitHub annotations when
GITHUB_ACTIONS is set and as plain `path:line: [check] message` lines otherwise.
"""

from __future__ import annotations

import argparse
import bisect
import html
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Constants mirrored from private configuration. Each one names the private
# file it copies, so a change on either side is visible in a diff. Nothing
# below is READ from the private repository; that would be a dependency, and a
# dependency on a private tree is a guard that stops running the day the tree
# is not there.
# ---------------------------------------------------------------------------

# The operational quotation ceiling, matched to the one the private tool
# refuses on so a summary cannot pass there and fail here. It is a self-imposed
# number, not a legal threshold - fair dealing has no word count. It exists so
# that the rule is checkable at all.
MAX_QUOTE_WORDS = 40

# Three times the single-quotation ceiling, per H2 section. Eight 38-word
# blockquotes reproduce a 300-word passage as surely as one 300-word blockquote
# does; the per-quotation rule cannot see that, this one can.
MAX_QUOTE_AGGREGATE_WORDS = 3 * MAX_QUOTE_WORDS

# And a ceiling for the whole file, on top of the per-section one: three
# sections each just under 120 quoted words are still 350 quoted words.
MAX_QUOTE_FILE_WORDS = 300

# A quoted span of this many words or fewer is a title or a term - "Attention
# Is All You Need", the "cold start" problem - not a quotation, and does not
# count toward either aggregate. A thirty-title reading list must pass.
MIN_AGGREGATE_SPAN_WORDS = 8

# An inline code span longer than this renders as a grey run of prose, which
# is a reproduction; it is counted as a quotation rather than blanked as code.
MAX_CODE_SPAN_WORDS = MAX_QUOTE_WORDS

# The three origins a figure may declare. Deliberately the same three the
# private tool refuses on, restated here as data rather than imported: this
# checker has no access to that repository, and a guard that depends on a file
# it cannot read is a guard that silently stops checking.
IMAGE_ORIGIN_ALLOWED = ("original", "redrawn", "cc-licensed")

# Also matched against the private tool's ceiling, and restated for the same
# reason as above.
RAW_ABSTRACT_WORDS = 60

# Deliberately far tighter than the private repository's file ceiling, which
# has to survive a library of paper PDFs in plain git. Nothing that belongs
# here is big, so a large file is a mistake worth stopping on.
SIZE_CEILING_BYTES = 5 * 1024 * 1024

# How much of a quotation a finding may echo back. The report goes into a CI
# log that is itself public; reproducing the quotation there would be absurd.
REPORTED_SPAN_WORDS = 12

# Where prose lives: every file with one of these extensions, in every
# directory, the root included, in any letter case. There is deliberately no
# directory list here. The previous version had one (summaries/, docs/,
# reading-lists/, curricula/, tutorials/, datasets/) and a 300-word blockquote
# in README.md or notes/a.md was outside it. A whitelist of directories is a
# thing a new directory escapes. The three families are scanned differently:
# markdown is rendered (fences, indented blocks, HTML, entities), HTML gets the
# HTML normalisation, and plain text is judged exactly as it is.
MARKDOWN_EXT = (".md", ".markdown")
HTML_EXT = (".html", ".htm")
PLAIN_EXT = (".txt", ".rst")
PROSE_EXT = MARKDOWN_EXT + HTML_EXT + PLAIN_EXT

# The one directory-scoped prose rule. Matched as a case-insensitive prefix so
# `Summaries/` is not a different place. It applies to markdown summaries; the
# attribution heading is a markdown heading.
SUMMARIES_DIR = "summaries/"

FIGURE_DIR = "assets/figures/"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".svg",
             ".bmp", ".avif", ".heic", ".heif", ".jfif", ".ico", ".apng", ".psd", ".tga")
RASTER_EXT = tuple(e for e in IMAGE_EXT if e != ".svg")
EDITABLE_EXT = (".svg", ".drawio", ".excalidraw", ".mmd", ".py")
SOURCE_SUFFIXES = (".source.yml", ".source.yaml")

# Magic bytes. Each file's first HEAD_BYTES are read once and every byte rule
# looks at that same buffer. A PDF reader accepts `%PDF-` anywhere in the first
# 1024 bytes and this checker looks twice as far - an exact-prefix test was
# walked past by a PDF with a byte of junk in front of it. Beyond 2 KB of junk
# is a documented limit: no accident puts it there.
HEAD_BYTES = 2048
PDF_MAGIC = b"%PDF-"

ARCHIVE_EXT = (".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar", ".jar", ".war")
# (magic, offset, name). `ustar` sits at byte 257 of a POSIX tar header.
# A ZIP announces itself with one of three signatures at byte 0, not one: a
# local file header (`PK\x03\x04`) in the ordinary case, the end-of-central-
# directory record (`PK\x05\x06`) when the archive is empty, and the spanning
# marker (`PK\x07\x08`) when it is split. All three are archives and all three
# are refused. They are tested at offset 0 ONLY, so a page that says "PK is
# the Pakistani country code" in its first line, or carries those bytes
# somewhere in the middle, is not an archive.
ARCHIVE_MAGIC = (
    (b"PK\x03\x04", 0, "zip"),
    (b"PK\x05\x06", 0, "empty zip"),
    (b"PK\x07\x08", 0, "split zip"),
    (b"\x1f\x8b", 0, "gzip"),
    (b"7z\xbc\xaf\x27\x1c", 0, "7z"),
    (b"Rar!", 0, "rar"),
    (b"ustar", 257, "tar"),
)

# (prefix, name). WebP is `RIFF....WEBP` and BMP is `BM` plus a header whose
# size field must agree with the file; both are tested separately, because
# "BM25 is a ranking function" is the first line of a perfectly good note.
RASTER_MAGIC = (
    (b"\x89PNG", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"GIF8", "GIF"),
    (b"II*\x00", "TIFF"),
    (b"MM\x00*", "TIFF"),
)

# The self-edit rules. `.github/` is the whole directory, not just workflows/:
# CODEOWNERS, the labels file and the issue templates are part of the judge
# too, and so is anything else that lands there later - the prefix is matched,
# not a list of names, so a new file under .github/ is covered on the day it
# arrives rather than on the day someone remembers to add it here. The guard
# is this file, its tests and the hooks.
GITHUB_DIR = ".github/"
GUARD_FILES = ("tools/check_copyright.py", "tools/tests/test_check_copyright.py")
GUARD_DIRS = (".githooks/",)
# Content is anything outside all three of these.
NON_CONTENT_DIRS = (".github/", "tools/", ".githooks/")
# The paths a tree under review must CONTAIN. `is_guard` above decides whether
# a changed path belongs to the guard; this decides whether the guard is still
# there at all. A pull request that deletes the checker, its tests or the hook
# changes only guard paths, so the "guard and content do not travel together"
# rule passes it, and after the merge the repository has no guard. Absence is
# therefore a finding of its own. `.githooks/` is a directory to `is_guard`,
# but the hook that runs the checker is a named file here: an empty
# `.githooks/` is not a hook.
REQUIRED_GUARD_PATHS = GUARD_FILES + (".githooks/pre-commit",)

# The one person this repository's history is allowed to name. Written out
# here rather than read from `git config`: a wrong local config is exactly
# where a wrong name in the log comes from, so asking git would be asking the
# thing under test. The trade is that a change of address is a code change.
OWNER_NAME = "Mahmoud Salem"
OWNER_EMAIL = "ma7moudalysalem@gmail.com"
# GitHub rewrites the address to `<id>+<login>@users.noreply.github.com` when
# the owner keeps the real one private. Same person, different spelling, and
# refusing it would refuse commits made in the web editor.
OWNER_NOREPLY = re.compile(r"\A[0-9]+\+ma7moudalysalem@users\.noreply\.github\.com\Z",
                           re.IGNORECASE)
# (pattern, what to call it). Matched against the whole commit message.
# `[bot]` is matched anywhere, not just in an author line, because it is the
# marker GitHub puts in an app's name and it reads the same wherever it lands.
ATTRIBUTION_MARKERS = (
    (re.compile(r"^[ \t]*co-authored-by[ \t]*:", re.IGNORECASE | re.MULTILINE),
     "a Co-authored-by: trailer"),
    (re.compile(r"generated\s+(?:with|by)", re.IGNORECASE), "a \"generated with/by\" line"),
    (re.compile(r"\[bot\]", re.IGNORECASE), "a [bot] marker"),
)
# One record per commit, NUL-terminated so a message containing blank lines,
# a NUL-free binary-looking blob or anything else still splits cleanly. The
# first five lines are fixed fields; everything after them is the message.
COMMIT_LOG_FORMAT = "%H%n%an%n%ae%n%cn%n%ce%n%B%x00"
# Said once, quoted by every finding this rule raises.
ATTRIBUTION_REASON = (
    "This repository's history is meant to read as one person's work: a trailer, a "
    "generated-with line or a bot author in the log is a claim about authorship that "
    "the repository does not want to make, and it outlives the pull request because a "
    "squash keeps it. Rewrite the commit before merging (`git commit --amend`, or "
    "`git rebase -i` for an older one). `.githooks/commit-msg` refuses the same message "
    "locally; this is the half that runs however the commit was made."
)

# A fence whose info string names one of these languages is code and is
# blanked. A fence with ANY other info string - empty, `text`, `abstract`, a
# typo - renders verbatim, as text, and is therefore a place a quotation can
# be pasted and shown to every reader while a scanner that blanks all fences
# never sees it. Those are scanned as prose. The list is closed on purpose: an
# unknown language is prose until it is added here.
KNOWN_LANGUAGES = frozenset({
    "python", "py", "js", "ts", "javascript", "typescript", "bash", "sh", "shell",
    "zsh", "powershell", "ps1", "json", "yaml", "yml", "toml", "ini", "xml", "sql",
    "r", "c", "cpp", "c++", "java", "go", "rust", "rs", "kotlin", "swift", "scala",
    "ruby", "rb", "php", "perl", "lua", "matlab", "julia", "jl", "haskell", "hs",
    "ocaml", "diff", "patch", "dockerfile", "makefile", "latex", "tex", "bibtex",
    "bib", "css", "scss", "html", "mermaid",
})

# The heading every summary ends with, compared case-insensitively against the
# RENDERED headings of the file: one that only exists inside an HTML comment
# or a code fence does not render and does not count.
ATTRIBUTION_TITLE = "source and attribution"

# Characters that render as nothing. They are stripped, not treated as
# separators: text glued together by zero-width joiners is unreadable, so a
# zero-width character in the middle of a word is a typo and not a bypass.
_INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")

# A long inline code span is kept in the scan rather than blanked, wrapped in
# a private pair of marks (the interlinear annotation anchors, which no prose
# contains) so the pairing rule counts it as a quotation of its own family.
CODE_SPAN_OPEN = "\ufff9"
CODE_SPAN_CLOSE = "\ufffb"

# Quotation marks, by family. Within a family an opener is closed by the next
# closer; straight marks have no direction and alternate. The families are
# kept apart so that « never closes a “ and a stray ’ never closes a ".
_OPENERS = {"“": "double", "„": "double", "‘": "single", "«": "guillemet", "‹": "sguillemet",
            CODE_SPAN_OPEN: "code"}
_CLOSERS = {"”": "double", "’": "single", "»": "guillemet", "›": "sguillemet",
            CODE_SPAN_CLOSE: "code"}
_STRAIGHT = {'"': "double", "'": "single"}
QUOTE_MARKS = "".join(_OPENERS) + "".join(_CLOSERS) + "".join(_STRAIGHT)

# The single marks - straight ' and curly ‘ ’ - are the ambiguous ones: the
# same character is an apostrophe in `don't`, `Zhang's`, `the authors'`, `'em`
# and `'90s`, and Word, Notion and Apple Notes emit the closing ’ for every
# one of those at a word start. All three obey one set of word-boundary rules
# (`_single_opens`, `_single_closes`), and these are its tables.
SINGLE_MARKS = "'‘’"
# A word that a mark at word start elides the front of: 'em, 'til, rock 'n'
# roll, 'tis. The whole word after the mark decides, in any letter case.
ELISIONS = frozenset({"em", "til", "till", "tis", "twas", "bout", "cause", "cos", "cuz",
                      "n", "nuff", "round", "neath"})
_WORD_AFTER = re.compile(r"[^\W\d_]+")
# A decade: two digits followed by an `s` ('90s), or by nothing but
# punctuation or the end of the block ('80. and '80,). `'40 percent` is a
# quotation that begins with a number, and opens.
_DECADE_AFTER = re.compile(r"\d\d(?:s\b|(?![\w\s]))")
# What may precede an opening single mark besides whitespace or the start of
# the block. After a letter, a digit, a full stop or a comma (`et al.'s`) the
# mark is an apostrophe.
_SINGLE_OPEN_AFTER = "([{"


# ---------------------------------------------------------------------------
# findings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    check: str
    path: str
    message: str
    line: Optional[int] = None

    def plain(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: [{self.check}] {self.message}"

    def annotation(self) -> str:
        """A GitHub Actions workflow command. Properties and message are escaped
        per the documented rules; an unescaped comma in a path would otherwise
        end the property list early and mis-attribute the finding."""
        def prop(s: str) -> str:
            return (s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                     .replace(":", "%3A").replace(",", "%2C"))

        def data(s: str) -> str:
            return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

        props = f"file={prop(self.path)}"
        if self.line:
            props += f",line={self.line}"
        props += f",title={prop('copyright: ' + self.check)}"
        return f"::error {props}::{data(self.message)}"


# ---------------------------------------------------------------------------
# the repository, read-only
# ---------------------------------------------------------------------------

class RepoError(RuntimeError):
    """The repository itself cannot be examined. Always fatal, always exit 1."""


class Repo:
    """Tracked files and their bytes, from the working tree or from the index.

    `--staged` reads from the INDEX, not the working tree. At pre-commit time
    the two usually agree, but a partially staged file commits what is in the
    index, and the index is therefore the thing to check. Sibling lookups
    (`x.png` -> `x.source.yml`) use the whole index as well, so a declaration
    committed last week satisfies an image staged today.
    """

    def __init__(self, root: Path, from_index: bool) -> None:
        self.root = root
        self.from_index = from_index
        self._blobs: Optional[dict[str, str]] = None   # path -> blob sha (index only)
        self._modes: Optional[dict[str, str]] = None   # path -> index mode, e.g. "120000"

    # -- git ---------------------------------------------------------------

    def git(self, *args: str, check: bool = True) -> bytes:
        try:
            proc = subprocess.run(["git", "-C", str(self.root), *args],
                                  capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            raise RepoError(f"git {' '.join(args)} could not run: {exc}") from exc
        if check and proc.returncode != 0:
            err = proc.stderr.decode("utf-8", "replace").strip()
            raise RepoError(f"git {' '.join(args)} failed ({proc.returncode}): {err}")
        return proc.stdout

    @staticmethod
    def _split_nul(out: bytes) -> list[str]:
        # NUL-delimited, never newline-delimited: a filename may contain a
        # space, a newline, or anything else, and `-z` is the only listing
        # that survives all of them.
        return [p.decode("utf-8", "replace") for p in out.split(b"\0") if p]

    def tracked(self) -> list[str]:
        """Every path in the index (== every tracked file), repo-relative, posix."""
        return self._split_nul(self.git("ls-files", "-z"))

    def staged(self) -> tuple[list[str], list[str]]:
        """(added/modified/renamed paths, deleted paths) in the index vs HEAD.

        A repository with no commit yet has no HEAD to diff against; the empty
        tree is the base in that case, so the first commit is checked too.
        """
        head = self.git("rev-parse", "--verify", "--quiet", "HEAD", check=False).strip()
        base = head.decode() if head else self.git("hash-object", "-t", "tree", "/dev/null",
                                                     check=False).decode().strip()
        if not base:
            # `/dev/null` is not a thing on every platform; the empty tree's
            # id is a constant of git's object model.
            base = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        changed = self._split_nul(self.git("diff", "--cached", "--name-only", "-z",
                                           "--diff-filter=ACMR", base))
        deleted = self._split_nul(self.git("diff", "--cached", "--name-only", "-z",
                                           "--diff-filter=D", base))
        return changed, deleted

    def _read_index(self) -> None:
        blobs: dict[str, str] = {}
        modes: dict[str, str] = {}
        for entry in self.git("ls-files", "-s", "-z").split(b"\0"):
            if not entry:
                continue
            meta, _tab, path = entry.partition(b"\t")
            parts = meta.split()
            if len(parts) >= 2:
                rel = path.decode("utf-8", "replace")
                modes[rel] = parts[0].decode()
                blobs[rel] = parts[1].decode()
        self._blobs, self._modes = blobs, modes

    def _index_blobs(self) -> dict[str, str]:
        if self._blobs is None:
            self._read_index()
        return self._blobs or {}

    def symlinks(self) -> set[str]:
        """Every tracked path git records with mode 120000, i.e. every symlink.

        Read from the INDEX, never from the filesystem. A Windows checkout
        without the privilege to create links stores a symlink as an ordinary
        small file whose content is the target path, so `Path.is_symlink()`
        answers "no" there and the guard would pass exactly the tree the rule
        exists to refuse. Git's mode is the same on every platform.
        """
        if self._modes is None:
            self._read_index()
        return {rel for rel, mode in (self._modes or {}).items() if mode == "120000"}

    # -- bytes ---------------------------------------------------------------

    def read_bytes(self, rel: str) -> bytes:
        """Raw bytes. Raises OSError or RepoError; callers turn that into a finding."""
        if self.from_index:
            sha = self._index_blobs().get(rel)
            if sha is None:
                raise RepoError(f"{rel} is not in the index")
            return self.git("cat-file", "blob", sha)
        return (self.root / rel).read_bytes()

    def size(self, rel: str) -> int:
        if self.from_index:
            sha = self._index_blobs().get(rel)
            if sha is None:
                raise RepoError(f"{rel} is not in the index")
            return int(self.git("cat-file", "-s", sha).decode().strip())
        return (self.root / rel).stat().st_size

    def head_bytes(self, rel: str, n: int) -> bytes:
        if self.from_index:
            return self.read_bytes(rel)[:n]
        with open(self.root / rel, "rb") as fh:
            return fh.read(n)


@dataclass
class Context:
    """Everything a check needs, gathered once."""

    repo: Repo
    targets: list[str]              # the files being judged
    universe: set[str]              # every tracked path, for sibling lookups
    deleted: set[str] = field(default_factory=set)   # staged deletions
    symlinks: set[str] = field(default_factory=set)  # tracked paths with mode 120000
    findings: list[Finding] = field(default_factory=list)
    _texts: dict[str, Optional[str]] = field(default_factory=dict)
    _scans: dict[str, str] = field(default_factory=dict)
    _heads: dict[str, Optional[bytes]] = field(default_factory=dict)
    _unreadable: set[str] = field(default_factory=set)
    # (changed paths, error) against the pull request's base branch; None until asked.
    _base_diff: Optional[tuple[Optional[set[str]], Optional[str]]] = None
    # (base commit, error) for the pull request's base ref; None until asked.
    _base_rev: Optional[tuple[Optional[str], Optional[str]]] = None

    def add(self, check: str, path: str, message: str, line: Optional[int] = None) -> None:
        self.findings.append(Finding(check, path, message, line))

    def unreadable(self, rel: str, why: str) -> None:
        """One finding per unreadable file, however many checks trip over it."""
        if rel not in self._unreadable:
            self._unreadable.add(rel)
            self.add("unreadable_file", rel,
                     f"cannot be read, so nothing about it can be verified: {why}. "
                     "The guard fails closed; fix or remove the file.")

    def head(self, rel: str) -> Optional[bytes]:
        """The first HEAD_BYTES of a file, read once, or None (already reported).

        A tracked symlink is never opened: `symlink_present` has already
        reported it, and following it would read - and quote, in a public CI
        log - a file that is not in the repository at all.
        """
        if rel in self.symlinks:
            return None
        if rel in self._heads:
            return self._heads[rel]
        try:
            head = self.repo.head_bytes(rel, HEAD_BYTES)
        except (OSError, RepoError) as exc:
            self.unreadable(rel, str(exc))
            head = None
        self._heads[rel] = head
        return head

    def text(self, rel: str) -> Optional[str]:
        """UTF-8 text with line endings normalised, or None (already reported).

        A tracked symlink is never opened; see `head`.
        """
        if rel in self.symlinks:
            return None
        if rel in self._texts:
            return self._texts[rel]
        try:
            raw = self.repo.read_bytes(rel)
        except (OSError, RepoError) as exc:
            self.unreadable(rel, str(exc))
            self._texts[rel] = None
            return None
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            self.unreadable(rel, f"not valid UTF-8 (byte {exc.start})")
            self._texts[rel] = None
            return None
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Zero-width and joiner characters render as nothing and are dropped,
        # not turned into separators: `w1<ZWSP>w2` is one unreadable word.
        text = _INVISIBLE.sub("", text)
        self._texts[rel] = text
        return text

    def scan(self, rel: str) -> Optional[str]:
        """The prose view of a prose file (see `prose_scan`), computed once."""
        text = self.text(rel)
        if text is None:
            return None
        if rel not in self._scans:
            self._scans[rel] = prose_scan(text, prose_kind(rel))
        return self._scans[rel]


# ---------------------------------------------------------------------------
# helpers: paths
# ---------------------------------------------------------------------------

def has_ext(rel: str, exts: tuple[str, ...]) -> bool:
    return rel.lower().endswith(tuple(e.lower() for e in exts))


def is_prose(rel: str) -> bool:
    """Every markdown, HTML and plain-text file is prose, in any directory
    including the root, in any letter case."""
    return has_ext(rel, PROSE_EXT)


def prose_kind(rel: str) -> str:
    """"markdown", "html" or "plain": which rendering a prose file gets."""
    if has_ext(rel, MARKDOWN_EXT):
        return "markdown"
    if has_ext(rel, HTML_EXT):
        return "html"
    return "plain"


def is_summary(rel: str) -> bool:
    return rel.lower().startswith(SUMMARIES_DIR) and has_ext(rel, MARKDOWN_EXT)


def is_source_decl(rel: str) -> bool:
    return rel.endswith(SOURCE_SUFFIXES)


def is_guard(rel: str) -> bool:
    low = rel.lower()
    return low in GUARD_FILES or low.startswith(GUARD_DIRS)


def is_content(rel: str) -> bool:
    return not rel.lower().startswith(NON_CONTENT_DIRS)


def stem_of(rel: str) -> str:
    """`assets/figures/unet.png` -> `assets/figures/unet`. Only the last extension
    is removed, so `fig.v2.png` pairs with `fig.v2.source.yml`."""
    head, _sep, base = rel.rpartition("/")
    if "." in base and not base.startswith("."):
        base = base[:base.rfind(".")]
    return f"{head}/{base}" if head else base


def find_decl(stem: str, universe: set[str]) -> Optional[str]:
    return next((stem + suffix for suffix in SOURCE_SUFFIXES if stem + suffix in universe), None)


# ---------------------------------------------------------------------------
# helpers: bytes
# ---------------------------------------------------------------------------

def archive_kind(head: bytes) -> Optional[str]:
    for magic, offset, name in ARCHIVE_MAGIC:
        if head[offset:offset + len(magic)] == magic:
            return name
    return None


def raster_kind(head: bytes, size: Optional[int] = None) -> Optional[str]:
    """The raster format the first bytes announce, or None.

    A BMP is `BM` followed by a header whose four-byte little-endian size
    field at offset 2 states the file's own size and whose reserved bytes at
    6-9 are zero; `BM` alone is the start of "BM25 is a ranking function",
    which is the first line of a perfectly good note. The size is required
    for that test, so a caller that cannot supply it never sees a BMP."""
    for magic, name in RASTER_MAGIC:
        if head.startswith(magic):
            return name
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "WebP"
    if bmp_header(head, size):
        return "BMP"
    return None


def bmp_header(head: bytes, size: Optional[int]) -> bool:
    """`BM`, a four-byte little-endian size field at offset 2 that states the
    file's own size, and four zero reserved bytes. Without the size there is
    no claim: `BM` alone begins "BM25 is a ranking function"."""
    return (head[:2] == b"BM" and len(head) >= 10 and size is not None
            and int.from_bytes(head[2:6], "little") == size and head[6:10] == b"\x00" * 4)


# A GIF's logical screen descriptor follows the six-byte signature: width and
# height as two-byte little-endian integers, a packed field, a background
# colour index, and a pixel aspect ratio. Encoders write 0 for the aspect
# ratio and neither dimension of a real image is zero, which is what separates
# a GIF from a sentence: "GIF89a is the second version of the format" has `e`
# where the aspect ratio belongs.
_GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def strict_raster_kind(head: bytes, size: Optional[int] = None) -> Optional[str]:
    """The raster format the first bytes announce under FULL validation, or None.

    `raster_kind` above is the fail-closed sniff for files that are not prose:
    a prefix is enough there, because a `.dat` file has no business starting
    with `GIF8` whatever follows. This one is for PROSE, where the first line
    is a sentence a person wrote, and a prefix test would refuse a note about
    image formats. Every format is therefore validated as far as its header
    goes: the whole eight-byte PNG signature, a JPEG start-of-image followed
    by an APPn or a quantisation-table marker, a GIF signature followed by a
    plausible logical screen descriptor, and the BMP size field the loose
    sniff already required. TIFF and WebP are deliberately absent: neither has
    a header this rule could validate without guessing, and a documented limit
    beats a checker that fires on a bibliography.
    """
    if head.startswith(PNG_SIGNATURE):
        return "PNG"
    if (len(head) >= 4 and head[:2] == b"\xff\xd8" and head[2] == 0xff
            and (0xe0 <= head[3] <= 0xef or head[3] == 0xdb)):
        return "JPEG"
    if (head[:6] in _GIF_SIGNATURES and len(head) >= 13
            and int.from_bytes(head[6:8], "little")
            and int.from_bytes(head[8:10], "little")
            and head[12] == 0):
        return "GIF"
    if bmp_header(head, size):
        return "BMP"
    return None


# ---------------------------------------------------------------------------
# helpers: markdown
# ---------------------------------------------------------------------------

_FENCE_OPEN = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
_BLOCK_START = re.compile(
    r"^[ \t]{0,3}(?:"
    r"#{1,6}(?:[ \t]|$)"           # ATX heading
    r"|>(?!>)"                     # blockquote marker (`>>>` is a doctest prompt)
    r"|[-*+][ \t]"                 # bullet
    r"|\d{1,9}[.)][ \t]"           # ordered item
    r")")
_SINGLE_LINE_BLOCK = re.compile(
    r"^[ \t]{0,3}(?:#{1,6}(?:[ \t]|$)|([-*_])(?:[ \t]*\1){2,}[ \t]*$)")
_ATX_HEADING = re.compile(r"^[ \t]{0,3}(#{1,6})[ \t]+(.*)$")
_ATX_CLOSING = re.compile(r"[ \t]+#+[ \t]*$")
_SETEXT_UNDERLINE = re.compile(r"^[ \t]{0,3}(=+|-+)[ \t]*$")
# A blockquote marker, optionally inside a list item: `- > quoted` and
# `1. > quoted` render as a blockquote inside a bullet, and the whole bullet is
# the quotation. Up to eight leading spaces are allowed, because a blockquote
# under a nested list item sits at four or six; deeper than that, after a
# blank line, is an indented code block, which `blank_code` marks as a
# blockquote anyway. The marker is a `>` NOT followed by another `>`: `>>>`
# is the doctest prompt of a transcript pasted into a `.txt` file, and
# `> > nested`, with the space, is still two markers.
_BLOCKQUOTE_MARKER = re.compile(r"^[ \t]{0,8}(?:(?:[-*+]|\d{1,9}[.)])[ \t]+)?>(?!>)[ \t]?")
# A list item: indent, marker, and the spaces after it (one to four count as
# the marker's width; more, or none, and the content starts one past it).
_LIST_ITEM = re.compile(r"^([ \t]*)([-*+]|\d{1,9}[.)])([ \t]*)")

# The attribute list of a tag: quoted values may contain `<` and `>` (an
# `alt="a > b"` is legal HTML), so a tag runs to the first `>` outside quotes.
_ATTRS = r"""(?:"[^"]*"|'[^']*'|[^<>"'])*"""

# HTML that GitHub renders as structure. Tags may span lines; the first pass
# below folds each one onto its opening line without changing the line count.
# `<pre>` is a blockquote to this scanner: its content renders verbatim.
_HTML_STRUCT_TAG = re.compile(r"<(/?)(blockquote|pre|h[1-6]|q)\b" + _ATTRS + ">", re.I)
_HTML_H_PAIR = re.compile(r"(<h([1-6])\b" + _ATTRS + r">)(.*?)(</h\2[ \t]*>)", re.I | re.S)
_HTML_BQ = re.compile(r"<(/?)(?:blockquote|pre)\b" + _ATTRS + ">", re.I)
_HTML_H_OPEN = re.compile(r"<h([1-6])\b" + _ATTRS + ">", re.I)
_HTML_H_ANY = re.compile(r"</?h[1-6]\b" + _ATTRS + ">", re.I)
_HTML_Q = re.compile(r"</?q\b" + _ATTRS + ">", re.I)
# Elements GitHub's sanitiser drops with their content: nothing inside renders.
_HTML_HIDDEN = re.compile(r"<(script|style)\b" + _ATTRS + r">.*?</\1[ \t]*>", re.I | re.S)
# Tags that end a run of text: `w1<br>w2` and `<p>w1</p><p>w2</p>` are two
# words to the reader and must be two words to the counter.
_HTML_BLOCK_TAG = re.compile(
    r"</?(?:br|p|div|li|ul|ol|dl|dt|dd|tr|td|th|table|thead|tbody|tfoot|caption|hr"
    r"|section|article|header|footer|nav|aside|figure|figcaption|main|details|summary"
    r"|address|center|form|fieldset|legend)\b" + _ATTRS + ">", re.I)
# A comment does not render. One that is never closed is left alone: CommonMark
# would swallow the rest of the document, and this guard fails closed.
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
# Any other tag, attributes and all. Once the structural tags above have been
# turned into markdown, what remains (`<img alt="...">`, `<a title="...">`,
# `<span>`) renders as nothing a reader can quote: an attribute value is not
# on the page.
_HTML_ANY_TAG = re.compile(r"</?[A-Za-z][\w:.\-]*" + _ATTRS + ">")
# The title of an inline markdown link or image, `[x](url "title")`: a
# tooltip, not text.
_MD_LINK_TITLE = re.compile(
    r"""(\]\([ \t]*(?:<[^<>\n]*>|[^\s()<>]+)[ \t]+)("[^"\n]*"|'[^'\n]*'|\([^()\n]*\))([ \t]*\))""")
# LaTeX's ``quotation'': a double backtick opened, two straight singles
# closed, in one paragraph. Exactly two of each - three backticks are a fence.
_LATEX_QUOTE = re.compile(r"(?<!`)``(?!`)((?:[^\n]|\n(?![ \t]*\n))*?)(?<!')''(?!')")


def count_words(text: str) -> int:
    """A word is a whitespace-delimited token containing a letter or a digit.
    Punctuation standing alone (an em dash, an ellipsis) is not a word. A
    no-break space is whitespace: `w1&nbsp;w2` renders as two words and is two."""
    return sum(1 for tok in text.replace("\u00a0", " ").split() if any(ch.isalnum() for ch in tok))


def excerpt(text: str, limit: int = REPORTED_SPAN_WORDS) -> str:
    toks = text.replace("\u00a0", " ").split()
    shown = " ".join(toks[:limit])
    return shown + (" ..." if len(toks) > limit else "")


def _indent(line: str) -> int:
    """Leading whitespace width, a tab being the next multiple of four."""
    n = 0
    for ch in line:
        if ch == " ":
            n += 1
        elif ch == "\t":
            n += 4 - n % 4
        else:
            break
    return n


def _verbatim(line: str) -> str:
    """A line of a verbatim block, marked as blockquote text. A backtick in it
    cannot open an inline span and a `<` cannot open a tag or a comment: the
    reader sees both as the characters they are."""
    return "> " + line.replace("`", " ").replace("<", " ")


def blank_code(text: str) -> str:
    """Replace code with spaces and mark verbatim blocks as blockquotes.

    The line count is always preserved, so a line number in the result is the
    same line in the original; the length of every line is preserved too,
    except inside a verbatim block (below), so offsets survive as well.

    Three things render as code and are blanked: a fence whose info string
    names a language in KNOWN_LANGUAGES, and an inline code span of up to
    MAX_CODE_SPAN_WORDS words. Three things render VERBATIM - the reader sees
    every word, so they are reproductions, not code - and are marked as a
    blockquote instead, with backticks and `<` inside them neutralised: a
    fence with any other info string (empty, `text`, a typo), an indented
    code block (four spaces or a tab after a blank line, and not the
    continuation of a list item, which needs four more), and an inline code
    span longer than MAX_CODE_SPAN_WORDS, which is kept in place between a
    private pair of quotation marks so the pairing rule counts it.

    A fence that is never closed is NOT treated as code: CommonMark would run
    it to end-of-file, but that would let one stray backtick line hide every
    quotation below it, and this guard fails closed.
    """
    lines = text.split("\n")
    out = list(lines)
    fence: Optional[tuple[str, int, int, bool]] = None    # (char, length, opened-at, verbatim)
    indented: Optional[int] = None      # the indent an open indented block needs
    prev_blank = True                   # the document start behaves like a blank line
    lists: list[int] = []               # content indents of the open list items
    for i, line in enumerate(lines):
        if fence is not None:
            stripped = line.strip()
            if (stripped and stripped[0] == fence[0] and len(stripped) >= fence[1]
                    and stripped == fence[0] * len(stripped)
                    and len(line) - len(line.lstrip(" ")) <= 3):
                out[i] = " " * len(line)
                fence = None
                prev_blank = True
            elif fence[3]:
                out[i] = _verbatim(line)
            else:
                out[i] = " " * len(line)
            continue

        blank = not line.strip()
        indent = _indent(line)
        was_blank, prev_blank = prev_blank, blank
        if indented is not None:
            if blank:
                # A blank line stays inside the block only if more indented
                # text follows; otherwise the block ended at the last text.
                nxt = next((k for k in range(i + 1, len(lines)) if lines[k].strip()), None)
                if nxt is not None and _indent(lines[nxt]) >= indented:
                    out[i] = "> "
                    continue
                indented = None
            elif indent >= indented:
                out[i] = _verbatim(line)
                continue
            else:
                indented = None
        threshold = (lists[-1] if lists else 0) + 4
        if not blank and was_blank and indent >= threshold:
            indented = threshold
            out[i] = _verbatim(line)
            continue
        m = _FENCE_OPEN.match(line)
        if m:
            info = line[m.end():].strip()
            lang = info.split()[0].lower() if info else ""
            fence = (m.group(1)[0], len(m.group(1)), i, lang not in KNOWN_LANGUAGES)
            out[i] = " " * len(line)
            continue
        if not blank:
            while lists and indent < lists[-1]:
                lists.pop()
            lm = _LIST_ITEM.match(line)
            if lm and (lm.group(3) or lm.end() == len(line)):
                after = len(lm.group(3))
                lists.append(indent + len(lm.group(2)) + (after if 0 < after <= 4 else 1))
    if fence is not None:
        for i in range(fence[2], len(lines)):
            out[i] = lines[i]
    # LaTeX's ``quotation'' is paired here, after the fences (a verbatim
    # fence has already lost its backticks) and BEFORE the inline pass, which
    # would otherwise take the double backtick for a code span.
    scan = latex_quotes("\n".join(out))

    # Inline code: a run of N backticks closes at the next run of exactly N,
    # and never across a blank line (a blank line ends the paragraph, so the
    # opener was literal).
    runs = [(m.start(), m.end()) for m in re.finditer(r"`+", scan)]
    buf = list(scan)
    i = 0
    while i < len(runs):
        start, end = runs[i]
        n = end - start
        closer = None
        for j in range(i + 1, len(runs)):
            if re.search(r"\n[ \t]*\n", scan[end:runs[j][0]]):
                break
            if runs[j][1] - runs[j][0] == n:
                closer = j
                break
        if closer is None:
            i += 1
            continue
        cstart, cend = runs[closer]
        if count_words(scan[end:cstart]) > MAX_CODE_SPAN_WORDS:
            # A reproduction in monospace. Keep the words, mark the span, and
            # neutralise anything inside that could pair or open a tag.
            for k in range(start, cend):
                if buf[k] in QUOTE_MARKS or buf[k] in "`<":
                    buf[k] = " "
            buf[start] = CODE_SPAN_OPEN
            buf[cstart] = CODE_SPAN_CLOSE
        else:
            for k in range(start, cend):
                if buf[k] != "\n":
                    buf[k] = " "
        i = closer + 1
    return "".join(buf)


def latex_quotes(scan: str) -> str:
    """LaTeX's ``quotation'' rewritten with the curly marks a reader of the
    rendered page sees, so the pairing rule counts it as a quotation of the
    double family. Both marks must sit in one paragraph. Every line keeps
    its length: each two-character mark becomes a curly mark and a space.
    Exactly two backticks and exactly two straight singles: a fence line has
    three or more, an ordinary `code` span has one, and neither is touched."""
    if "``" not in scan or "''" not in scan:
        return scan
    return _LATEX_QUOTE.sub(lambda m: "“ " + m.group(1) + "” ", scan)


def strip_tags(scan: str) -> str:
    """Every HTML tag still standing, attributes and all, replaced by spaces,
    and the title of an inline markdown link or image (`[x](url "title")`)
    likewise. Neither renders as text: an `<img alt="...">` shows a picture
    and a link title is a tooltip, so a quotation mark inside them is not a
    quotation mark on the page. Newlines inside a tag are kept, so line
    numbers and offsets survive. Runs AFTER `normalise_html` has turned the
    structural tags into markdown, so a `<blockquote>` still counts, and
    BEFORE entities are decoded, so `&lt;img&gt;` stays the literal text it
    renders as."""
    if "<" in scan:
        scan = _HTML_ANY_TAG.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), scan)
    if "](" in scan:
        scan = _MD_LINK_TITLE.sub(lambda m: m.group(1) + " " * len(m.group(2)) + m.group(3), scan)
    return scan


def strip_html_comments(scan: str) -> str:
    """`<!-- ... -->` replaced by spaces, newlines kept. A comment does not
    render, so a blockquote, a heading or a quotation inside one is not on the
    page and is not a finding. An unterminated comment is left as it is."""
    if "<!--" not in scan:
        return scan
    return _HTML_COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), scan)


def _fold_tag(m: re.Match) -> str:
    """A tag that spans lines, folded onto one line; the newlines follow it so
    the line count of the document does not change."""
    s = m.group(0)
    return s.replace("\n", " ") + "\n" * s.count("\n")


def normalise_html(scan: str) -> str:
    """Rewrite the HTML that GitHub renders as structure into the markdown the
    rest of the scanner already understands, line count preserved:

    * `<blockquote>...</blockquote>` and `<pre>...</pre>` become lines prefixed
      with `> `, so the blockquote rule sees them;
    * `<h1>..</h1>` to `<h6>..</h6>` become ATX headings, so an `<h2>Abstract</h2>`
      is an abstract heading;
    * `<q>` becomes a straight quotation mark, because that is what it renders as;
    * `<script>` and `<style>` vanish with their content, as the sanitiser
      makes them;
    * `<br>`, `<p>`, `</p>` and every other block-level tag become whitespace,
      so `w1<br>w2` is two words to the counter as it is to the reader.

    Everything else is kept as it is. This runs on the raw text, BEFORE entity
    decoding: `&lt;blockquote&gt;` renders as literal text, not as a tag.
    """
    if "<" not in scan:
        return scan
    scan = _HTML_HIDDEN.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), scan)
    scan = _HTML_STRUCT_TAG.sub(_fold_tag, scan)
    scan = _HTML_H_PAIR.sub(
        lambda m: m.group(1) + " ".join(m.group(3).split()) + m.group(4) + "\n" * m.group(0).count("\n"),
        scan)

    out: list[str] = []
    depth = 0
    for line in scan.split("\n"):
        at_start = depth
        opened = False

        def bq(m: re.Match) -> str:
            nonlocal depth, opened
            if m.group(1):
                depth = max(depth - 1, 0)
            else:
                depth += 1
                opened = True
            return " "

        if "<" in line:
            line = _HTML_BQ.sub(bq, line)
            hm = _HTML_H_OPEN.search(line)
            if hm:
                line = "#" * int(hm.group(1)) + " " + " ".join(_HTML_H_ANY.sub(" ", line).split())
            line = _HTML_Q.sub('"', line)
            line = _HTML_BLOCK_TAG.sub(lambda m: " " * len(m.group(0)), line)
        if at_start > 0 or opened:
            line = "> " + line
        out.append(line)
    return "\n".join(out)


def _unmark(line: str) -> str:
    """A `>` that only became a blockquote marker by entity decoding is the
    literal character the reader sees, not structure; blank it."""
    while True:
        m = _BLOCKQUOTE_MARKER.match(line)
        if not m:
            return line
        pos = line.index(">", 0, m.end())
        line = line[:pos] + " " + line[pos + 1:]


def decode_entities(scan: str) -> str:
    """HTML entities to characters, line by line so the line count survives
    (`&#10;` decodes to a newline and is folded to a space). `&quot;` is a
    quotation mark to the reader and to this scanner; `&nbsp;` is a space.
    `&gt;` at the start of a line is a literal `>` on the page, not a
    blockquote marker, so a marker that exists only after decoding is
    blanked; one that was already there is kept."""
    if "&" not in scan and "\u00a0" not in scan:
        return scan
    out: list[str] = []
    for line in scan.split("\n"):
        if "&" in line:
            decoded = html.unescape(line).replace("\r", " ").replace("\n", " ")
            if not _BLOCKQUOTE_MARKER.match(line):
                decoded = _unmark(decoded)
            line = decoded
        out.append(line.replace("\u00a0", " "))
    return "\n".join(out)


def prose_scan(text: str, kind: str = "markdown") -> str:
    """The rendered-prose view of a prose file.

    Markdown: code blanked and verbatim blocks marked (LaTeX ``quotes''
    paired on the way), comments stripped, HTML structure normalised, the
    remaining tags and link titles blanked, entities decoded. In that order -
    fences are decided on the literal text as CommonMark decides them, a
    comment hides whatever tag it contains, tags are recognised only when
    literal, and only then do entities become characters. HTML: the same
    without the markdown pass. Plain text (`.txt`, `.rst`): the text itself,
    because GitHub shows it as it is - a `<!--` or a `&quot;` in a .txt file
    is four characters - with only the LaTeX pair rewritten, because a reader
    of ``this'' reads a quotation in any file.
    """
    if kind == "plain":
        return latex_quotes(text)
    text = blank_code(text) if kind == "markdown" else latex_quotes(text)
    return decode_entities(strip_tags(normalise_html(strip_html_comments(text))))


def body_only(scan: str, body_start: int) -> str:
    """The scan with its frontmatter lines blanked, line count kept. A quoted
    `description:` scalar or a `title:` in single quotes is YAML, not a
    quotation, and pairs with nothing; only `raw_abstract_present` reads the
    frontmatter, for its `abstract` key."""
    if not body_start:
        return scan
    lines = scan.split("\n")
    return "\n".join([""] * body_start + lines[body_start:])


def frontmatter_end(text: str) -> int:
    """Index of the first body line, or 0 when there is no frontmatter block."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return i + 1
    return 0


# An `abstract` key at any indentation, bare or quoted, optionally as a list
# item (`- abstract: ...`): `paper:\n  abstract: ...` renders in the
# frontmatter table just as a top-level key does.
_FM_ABSTRACT = re.compile(
    r"""^([ \t]*)(?:-[ \t]+)?(?:"abstract"|'abstract'|abstract)[ \t]*:(?:[ \t]+(.*))?$""", re.I)
_BLOCK_SCALAR = re.compile(r"^[>|][-+0-9]*[ \t]*(?:#.*)?$")


def frontmatter_abstract(text: str) -> Optional[tuple[int, str]]:
    """(line, value) of an `abstract` key in the YAML frontmatter - at any
    indentation, in any letter case, bare or quoted - or None. Minimal on
    purpose: the value is the rest of the key's line plus every following
    line that is blank or indented deeper than the key, which covers plain
    scalars, quoted scalars, and folded (`>`) and literal (`|`) blocks. GitHub
    renders frontmatter as a table, so an abstract there is displayed."""
    end = frontmatter_end(text)
    if not end:
        return None
    lines = text.split("\n")
    for i in range(1, end - 1):
        m = _FM_ABSTRACT.match(lines[i])
        if not m:
            continue
        key_indent = _indent(m.group(1))
        value = (m.group(2) or "").strip()
        parts = [] if not value or _BLOCK_SCALAR.match(value) else [value]
        j = i + 1
        while j < end - 1 and (not lines[j].strip() or _indent(lines[j]) > key_indent):
            parts.append(lines[j].strip())
            j += 1
        return (i + 1, " ".join(p for p in parts if p))
    return None


# An abstract LEAD-IN: a line that is the word "Abstract" and nothing else,
# apart from bold or italic markers and an optional `.` or `:` - and, only
# after that `.` or `:`, the first line of the abstract itself. `Abstract`,
# `**Abstract.** We present...`, `Abstract: We present...`. A sentence that
# happens to begin with the word (`Abstract reasoning is hard.`) is not one.
_ABSTRACT_LEAD_IN = re.compile(
    r"^[ \t]{0,3}[*_]*abstract[*_]*(?:([.:])[*_]*(?:[ \t]+(.*?))?)?[ \t]*$", re.I)
# What a section title looks like in a paper pasted as plain lines: at most
# eight words, optionally numbered (`1`, `1.1`, `2.`, `I.`, `A.`), starting
# with a capital, no sentence-ending punctuation. `1 Introduction`, `2.
# Related Work`, `Methods`.
_SECTION_TITLE = re.compile(
    r"^[ \t]{0,3}(?:(\d+(?:\.\d+)*\.?|[IVXLCDM]+\.|[A-Z]\.)[ \t]+)?[A-Z]")
_SECTION_TITLE_WORDS = 8


def section_title(line: str) -> tuple[bool, bool]:
    """(numbered, looks like a section title) for one line."""
    m = _SECTION_TITLE.match(line)
    stripped = line.strip()
    if not m or not stripped or stripped[-1] in ".!?,;:":
        return False, False
    return m.group(1) is not None, count_words(stripped) <= _SECTION_TITLE_WORDS


def abstract_lead_in(lines: list[str], ln: int, heading_lines: set[int]
                     ) -> Optional[tuple[int, int, str]]:
    """If 1-based line `ln` is an abstract lead-in, (first text line, last
    line, text) of the abstract that follows it, else None.

    The abstract runs from the remainder of the lead-in line to the next
    heading of any kind, or to the next paragraph whose first line looks
    like a section title (`1 Introduction`) - a numbered title ends it
    wherever it sits, because a paste from a PDF often has no blank line
    before one; an unnumbered title (`Methods`) only at a paragraph start,
    because a short wrapped line inside the abstract looks the same."""
    m = _ABSTRACT_LEAD_IN.match(lines[ln - 1])
    if not m:
        return None
    remainder = (m.group(2) or "").strip()
    body = [remainder] if remainder else []
    first = ln if remainder else None
    prev_blank = False
    k = ln + 1
    while k <= len(lines) and k not in heading_lines:
        cur = lines[k - 1]
        blank = not cur.strip()
        if not blank:
            numbered, title = section_title(cur)
            if title and (numbered or prev_blank):
                break
            if first is None:
                first = k
            body.append(cur)
        prev_blank = blank
        k += 1
    return (first or ln, k - 1, "\n".join(body))


def blocks(scan: str) -> list[list[tuple[int, str]]]:
    """Markdown blocks as lists of (1-based line number, line).

    A block ends at a blank line, and a heading, list item or blockquote marker
    starts a new one. Headings and thematic breaks are one line long. This is
    the unit inside which quotation marks are paired: no real quotation spans
    a blank line or a bullet, so pairing is reset at each.
    """
    out: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for no, line in enumerate(scan.split("\n"), start=1):
        if not line.strip():
            if current:
                out.append(current)
                current = []
            continue
        if _SINGLE_LINE_BLOCK.match(line):
            if current:
                out.append(current)
            out.append([(no, line)])
            current = []
            continue
        if _BLOCK_START.match(line) and current:
            out.append(current)
            current = []
        current.append((no, line))
    if current:
        out.append(current)
    return out


def _single_opens(joined: str, i: int) -> bool:
    """A single mark - straight ' or curly ‘ ’ - opens a quotation only at a
    word START: preceded by the start of the block, whitespace or an opening
    bracket, and followed by a letter or a digit. After a letter, a digit, a
    full stop or a comma (`Zhang's`, `et al.'s`, `5'`) it is an apostrophe or
    a foot mark. At a word start it is still an apostrophe when the word is
    an elision (`'em`, `'til`, rock `'n'` roll) or a decade (`'90s`); `'40
    percent` opens, because a quotation may begin with a number."""
    if i > 0 and not (joined[i - 1].isspace() or joined[i - 1] in _SINGLE_OPEN_AFTER):
        return False
    if i + 1 >= len(joined) or not joined[i + 1].isalnum():
        return False
    if joined[i + 1].isdigit():
        return _DECADE_AFTER.match(joined, i + 1) is None
    word = _WORD_AFTER.match(joined, i + 1)
    return word is None or word.group(0).lower() not in ELISIONS


def _single_closes(joined: str, i: int) -> bool:
    """...and closes one only at a word END: preceded by a letter, a digit or
    a closing punctuation mark, never by whitespace, and followed by the end
    of the block, whitespace or punctuation - never between two letters
    (`don't`, `it’s`). This is only consulted while a single quotation is
    pending, so `the authors'` and `goin'` with nothing open are apostrophes
    and `5'` is a foot mark; with `'they write ... results'` or `'see Table
    2'` open, the mark after the `s` or the digit closes it, because the
    opener is the stronger evidence - the same call the double-quote rule
    makes for `"a 12" display"`."""
    if i == 0 or joined[i - 1].isspace():
        return False
    return i + 1 >= len(joined) or not joined[i + 1].isalnum()


def _straight_double_role(joined: str, i: int, pending: dict) -> Optional[str]:
    """A straight " has no direction and alternates. Immediately after a digit
    it is an inch or second mark (`a 12" display`) and opens nothing; with a
    double quotation already open it still closes it, because `"see Table 2"`
    is a quotation and the opener is the stronger evidence."""
    if "double" in pending:
        return "close"
    if i > 0 and joined[i - 1].isdigit():
        return None
    return "open"


def quoted_spans_detail(scan: str) -> list[tuple[int, str, str]]:
    """(line, text, opening mark) for every quotation, pairing marks inside
    each block.

    Marks are paired by family - curly double, curly single, guillemets, single
    guillemets, and the private pair that marks a long inline code span - and
    sequentially within a family: an opening “ is closed by the next ”, « by
    », „ by “ or ”. A straight " has no direction and alternates; it also
    closes a pending curly opener, because the writer's intent is a quotation
    either way; after a digit it is an inch mark unless a quotation is open.
    The single marks - straight ' and curly ‘ ’ alike, because a word
    processor emits ’ for every apostrophe - are marks only at a word start
    (to open) or a word end (to close) under `_single_opens` and
    `_single_closes`, so `don't`, `Zhang's`, `et al.'s`, `the authors'`,
    `'em`, `'90s` and `goin'` open and close nothing. A second opener while
    one is pending is ignored: the span runs from the first, so a stray mark
    dropped into the middle of a quotation cannot split it. An odd trailing
    mark is a typo, not a quotation that runs to the end of the block, and
    is dropped; a pair never crosses a block boundary.
    """
    spans: list[tuple[int, str, str]] = []
    for block in blocks(scan):
        starts: list[int] = []
        numbers: list[int] = []
        offset = 0
        for no, line in block:
            starts.append(offset)
            numbers.append(no)
            offset += len(line) + 1
        joined = "\n".join(line for _no, line in block)
        pending: dict[str, tuple[int, str]] = {}      # family -> (index, opening char)
        for i, ch in enumerate(joined):
            if ch in SINGLE_MARKS:
                fam = "single"
                if fam in pending and ch != "‘" and _single_closes(joined, i):
                    role = "close"
                elif fam not in pending and _single_opens(joined, i):
                    role = "open"
                else:
                    continue
            elif ch in _OPENERS:
                fam = _OPENERS[ch]
                if ch == "“" and fam in pending and pending[fam][1] == "„":
                    role = "close"                       # „German style“
                else:
                    role = "open"
            elif ch in _CLOSERS:
                fam, role = _CLOSERS[ch], "close"
            elif ch in _STRAIGHT:
                fam = _STRAIGHT[ch]
                maybe = _straight_double_role(joined, i, pending)
                if maybe is None:
                    continue
                role = maybe
            else:
                continue
            if role == "open":
                if fam not in pending:
                    pending[fam] = (i, ch)
            elif fam in pending:
                start, opener = pending.pop(fam)
                line_no = numbers[bisect.bisect_right(starts, start) - 1]
                spans.append((line_no, joined[start + 1:i], opener))
    return spans


def quoted_spans(scan: str) -> list[tuple[int, str]]:
    """(line, text) for every quotation; see `quoted_spans_detail`."""
    return [(line, text) for line, text, _opener in quoted_spans_detail(scan)]


def blockquotes(scan: str) -> list[tuple[int, str]]:
    """(first line, text) for every blockquote, markers stripped.

    Consecutive `>` lines are one quote, and so is a plain line that follows a
    `>` line without a blank line between: CommonMark calls that lazy
    continuation and renders it inside the quote, so it is quoted text. A
    marker inside a list item (`- > text`) is a blockquote too.
    """
    out: list[tuple[int, str]] = []
    start: Optional[int] = None
    buf: list[str] = []
    for no, line in enumerate(scan.split("\n"), start=1):
        if _BLOCKQUOTE_MARKER.match(line):
            if start is None:
                start = no
            inner = line
            while _BLOCKQUOTE_MARKER.match(inner):
                inner = _BLOCKQUOTE_MARKER.sub("", inner, count=1)
            buf.append(inner)
        elif start is not None and line.strip() and not _BLOCK_START.match(line):
            buf.append(line)
        else:
            if start is not None:
                out.append((start, "\n".join(buf)))
            start, buf = None, []
    if start is not None:
        out.append((start, "\n".join(buf)))
    return out


def headings(scan: str, body_start: int) -> list[tuple[int, int, str]]:
    """(line, level, title) for ATX and setext headings after the frontmatter."""
    lines = scan.split("\n")
    out: list[tuple[int, int, str]] = []
    for i in range(body_start, len(lines)):
        m = _ATX_HEADING.match(lines[i])
        if m:
            title = _ATX_CLOSING.sub("", m.group(2)).strip()
            out.append((i + 1, len(m.group(1)), title))
            continue
        if (i + 1 < len(lines) and lines[i].strip() and not _BLOCK_START.match(lines[i])
                and _SETEXT_UNDERLINE.match(lines[i + 1])
                and (i == 0 or not lines[i - 1].strip())):
            level = 1 if lines[i + 1].strip().startswith("=") else 2
            out.append((i + 1, level, lines[i].strip()))
    return out


# ---------------------------------------------------------------------------
# helpers: the flat .source.yml reader
# ---------------------------------------------------------------------------

_KV = re.compile(r"^([A-Za-z0-9_.\-]+)[ \t]*:(?:[ \t]+(.*))?$")


def parse_flat_yaml(text: str) -> dict[str, str]:
    """`key: value` lines into a dict. Raises ValueError on anything else.

    This is deliberately not YAML. A `.source.yml` is five flat keys, and a
    reader that accepts only that shape refuses every clever thing a real
    parser would silently accept - anchors, multi-documents, nested maps that
    put `origin` somewhere the rule does not look. Indented lines continue the
    previous value, so a folded scalar under `origin:` produces a value that is
    not in the allowed set rather than an accidental pass.
    """
    out: dict[str, str] = {}
    last: Optional[str] = None
    for no, raw in enumerate(text.split("\n"), start=1):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped in ("---", "..."):
            continue
        if line[0] in " \t":
            if last is None:
                raise ValueError(f"line {no}: indented text before any key")
            out[last] = (out[last] + " " + stripped).strip()
            continue
        m = _KV.match(line)
        if not m:
            raise ValueError(f"line {no}: not a `key: value` line")
        key, value = m.group(1), (m.group(2) or "").strip()
        if key in out:
            raise ValueError(f"line {no}: duplicate key {key!r}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = re.sub(r"[ \t]+#.*$", "", value).strip()
        out[key] = value
        last = key
    return out


def read_decl(ctx: Context, decl: str) -> tuple[Optional[dict[str, str]], Optional[str]]:
    """(parsed declaration, None) or (None, why it declares nothing)."""
    if decl in ctx.symlinks:
        return None, (f"{decl} is a symlink, which the guard never follows; a declaration "
                      "that lives outside the repository declares nothing")
    try:
        raw = ctx.repo.read_bytes(decl)
        data = parse_flat_yaml(raw.decode("utf-8-sig"))
    except (OSError, RepoError, UnicodeDecodeError, ValueError) as exc:
        return None, f"{decl} could not be parsed ({exc}); an unreadable declaration declares nothing"
    if not data:
        return None, f"{decl} is empty"
    return data, None


# ---------------------------------------------------------------------------
# the checks - one function each, every one with its own tests
# ---------------------------------------------------------------------------

def check_no_third_party_pdf(ctx: Context) -> None:
    """No file named *.pdf, in any letter case, anywhere (COPYRIGHT.md, "What is
    not mine": the publisher's PDF is never in this repository, in any form).

    There is no assets/figures/ exemption. The audit renamed a publisher PDF
    into that directory beside an empty .source.yml and every layer passed it.
    Figures here are .svg or .png; a PDF figure is not a thing this repository
    has, so the exemption bought nothing and cost the boundary.
    """
    for rel in ctx.targets:
        if has_ext(rel, (".pdf",)):
            ctx.add("no_third_party_pdf", rel,
                    "a PDF may not be committed anywhere in this repository, whatever the "
                    "directory and whatever the letter case of the extension. "
                    "See COPYRIGHT.md, \"Why a summary of someone else's paper is lawful\". "
                    "Link to the publisher's page instead.")


def check_pdf_magic_bytes(ctx: Context) -> None:
    """The name is not the file: anything with `%PDF-` in its first HEAD_BYTES
    is a PDF, because that is where a PDF reader looks for it.

    The audit committed a publisher PDF as `docs/img/scanned-figure`, with no
    extension, and every layer passed it; the second audit put a newline in
    front of the header and walked past an exact-prefix test. Every tracked
    file that is not prose is read here, regardless of name. A prose file is
    a page, and a page may say `%PDF-` in its opening paragraph, so prose is
    not sniffed at all: a real PDF renamed `paper.txt` carries compressed
    binary streams, fails UTF-8 decoding, and is refused as unreadable by
    every prose rule instead. Beyond HEAD_BYTES of leading junk is a
    documented limit: no accident puts the header there.
    """
    for rel in ctx.targets:
        if is_prose(rel):
            continue
        head = ctx.head(rel)
        if head is None or PDF_MAGIC not in head:
            continue
        ctx.add("pdf_magic_bytes", rel,
                f"the file carries %PDF- in its first {HEAD_BYTES} bytes, which is where a "
                "PDF reader looks for it, so it is a PDF whatever its name. No PDF reaches "
                "this repository (COPYRIGHT.md, \"What is not mine\").")


def check_archive_present(ctx: Context) -> None:
    """No archive, by name or by bytes. This repository holds prose and small
    code; an archive is a container for the things it refuses - a PDF, a
    figure, a dataset sample - and a container the checker cannot see into is
    a container it refuses. No archive is opened: nothing is extracted,
    listed or decompressed, and the finding is the same whatever is inside.
    """
    for rel in ctx.targets:
        by_name = has_ext(rel, ARCHIVE_EXT)
        head = ctx.head(rel)
        if head is None:
            continue
        by_bytes = archive_kind(head)
        if not by_name and by_bytes is None:
            continue
        how = []
        if by_name:
            how.append("its extension says archive")
        if by_bytes:
            how.append(f"its first bytes are those of a {by_bytes} archive")
        ctx.add("archive_present", rel,
                f"{' and '.join(how)}. This repository holds prose and small code; an archive "
                "is a container for the things it refuses, and no archive is opened to find "
                "out which. Commit the files themselves, where each one can be judged.")


def check_symlink_present(ctx: Context) -> None:
    """No tracked symlink, anywhere. The link itself is the finding and its
    target is never read.

    `--all` reads bytes from the working tree, so a pull request that adds
    `docs/x.md -> ../../somewhere/else` would have the guard open, judge and
    QUOTE - into a public CI log - a file that is not in the repository. It
    would also let a link into the checkout's own `.git/` pass as prose. This
    repository has no reason to hold a symlink, so failing closed beats
    deciding which targets are safe to follow, and refusing is cheaper than
    resolving a path safely on three operating systems.

    The mode comes from git (`ls-files -s`, mode 120000), not from the
    filesystem: a Windows checkout without the privilege to create links
    stores the link as an ordinary file whose content is the target path, and
    a filesystem test would answer "no" on exactly the tree under review.
    """
    for rel in ctx.targets:
        if rel not in ctx.symlinks:
            continue
        ctx.add("symlink_present", rel,
                "git records this path as a symlink (mode 120000). A symlink is not a file "
                "this repository can judge: its target may sit outside the checkout entirely, "
                "and the guard does not follow it - nothing at the other end is read. Commit "
                "the file itself, or remove the link.")


def check_size_ceiling(ctx: Context) -> None:
    """No tracked file over SIZE_CEILING_BYTES. Nothing that belongs here is big;
    something that big is a scan, a dataset sample, or a checkpoint."""
    for rel in ctx.targets:
        if rel in ctx.symlinks:
            continue          # never stat through a link; see check_symlink_present
        try:
            size = ctx.repo.size(rel)
        except (OSError, RepoError) as exc:
            ctx.unreadable(rel, str(exc))
            continue
        if size > SIZE_CEILING_BYTES:
            ctx.add("size_ceiling", rel,
                    f"{size} bytes ({size / 1048576:.1f} MB); the ceiling is "
                    f"{SIZE_CEILING_BYTES} bytes (5 MB). Nothing that belongs in this "
                    "repository is that large.")


def check_image_provenance(ctx: Context) -> None:
    """Every image, anywhere, and every file under assets/figures/, needs a
    sibling `<stem>.source.yml` with `origin: original | redrawn | cc-licensed`
    (COPYRIGHT.md, "Figures").

    An image is selected three ways, in one rule: by extension repo-wide, by
    directory, and by BYTES - every tracked file that is not prose is sniffed
    for raster magic, because a PNG called `notes.dat` is a PNG, and the audit
    showed a paper screenshot at summaries/x/fig1.png was enumerated by no
    layer when the old rule looked only inside assets/figures/. A prose file
    is decoded as UTF-8 instead, which no raster survives: a PNG called
    `notes.txt` is refused as unreadable. A README beside the figures is a
    page, not a figure, and is exempt from the directory rule.

    `original` and `redrawn` also require a committed editable source beside
    the image - .svg, .drawio, .excalidraw, .mmd or the .py that plots it. You
    cannot claim you drew something without the thing you drew it with.
    `fair-use-quote` is not an accepted value.

    Known gap, deliberately left: a `cc-licensed` declaration is not required
    here to carry the source URL and the licence name. Whether it must is a
    COPYRIGHT.md policy decision, not a checker decision.
    """
    # Under --staged, an image whose declaration was just staged (or staged
    # for deletion) is re-judged even if the image itself was not touched.
    targets = set(ctx.targets)
    touched_decls = [p for p in list(ctx.targets) + sorted(ctx.deleted) if is_source_decl(p)]
    for decl in touched_decls:
        stem = decl[:-len(".source.yml")] if decl.endswith(".source.yml") else decl[:-len(".source.yaml")]
        for other in ctx.universe:
            if stem_of(other) == stem and not is_source_decl(other):
                targets.add(other)

    for rel in sorted(targets):
        if is_source_decl(rel):
            continue
        if rel not in ctx.universe:
            continue          # a stray path argument; nothing tracked to judge
        if rel in ctx.symlinks:
            continue          # `symlink_present` has it; nothing at the far end is read
        in_figures = rel.lower().startswith(FIGURE_DIR) and not is_prose(rel)
        sniffed: Optional[str] = None
        if not (has_ext(rel, IMAGE_EXT) or in_figures):
            head = ctx.head(rel)
            if head is None:
                continue
            try:
                size: Optional[int] = ctx.repo.size(rel)
            except (OSError, RepoError):
                size = None
            if is_prose(rel):
                # A prose file that does not decode is already refused as
                # unreadable, and that refusal covers every raster whose
                # bytes are not valid UTF-8 - a PNG or a JPEG under a .txt
                # name never reaches this line. What DOES reach it is the
                # UTF-8-clean case: a GIF or a BMP is ASCII-and-NUL from its
                # first byte, decodes cleanly, and renamed `notes.txt` walked
                # past this rule entirely. It is sniffed here under FULL
                # format validation, because the first line of a prose file
                # is a sentence somebody wrote: "GIF89a is the second version
                # of the format" and "BM25 is a ranking function" are notes,
                # not images, and must stay clean.
                if ctx.text(rel) is None:
                    continue
                sniffed = strict_raster_kind(head, size)
            else:
                sniffed = raster_kind(head, size)
            if sniffed is None:
                continue

        stem = stem_of(rel)
        decl = find_decl(stem, ctx.universe)
        if decl is None:
            if sniffed:
                where = (f" The name says nothing about an image, but the first bytes are those "
                         f"of a {sniffed} file, and a file with image bytes needs provenance "
                         "whatever it is called.")
            elif in_figures:
                where = ""
            else:
                where = (" Images normally live under assets/figures/, but provenance is "
                         "required wherever one sits.")
            ctx.add("image_provenance", rel,
                    f"no sibling {stem.rpartition('/')[2]}.source.yml declares where this "
                    "image came from. Every figure needs `origin: original | redrawn | "
                    "cc-licensed` (COPYRIGHT.md, \"Figures\")." + where)
            continue

        data, why = read_decl(ctx, decl)
        if data is None:
            ctx.add("image_provenance", rel,
                    f"{why}. Declare `origin:` (original | redrawn | cc-licensed), "
                    "the source URL and the licence (COPYRIGHT.md, \"Figures\").")
            continue

        origin = data.get("origin")
        if origin is None:
            ctx.add("image_provenance", rel,
                    f"{decl} has no `origin:` key; the allowed values are "
                    f"{', '.join(IMAGE_ORIGIN_ALLOWED)} (COPYRIGHT.md, \"Figures\").")
            continue
        if origin not in IMAGE_ORIGIN_ALLOWED:
            hint = (" `fair-use-quote` is explicitly not accepted here: a figure taken "
                    "from a paper is a separate copyrighted work, and citing it is not "
                    "a licence." if origin == "fair-use-quote" else "")
            ctx.add("image_provenance", rel,
                    f"{decl} declares origin {origin!r}; the allowed values are "
                    f"{', '.join(IMAGE_ORIGIN_ALLOWED)} (COPYRIGHT.md, \"Figures\")." + hint)
            continue
        if origin in ("original", "redrawn"):
            editable = [stem + ext for ext in EDITABLE_EXT if stem + ext in ctx.universe]
            if not editable:
                ctx.add("image_provenance", rel,
                        f"{decl} says origin: {origin}, which requires a committed editable "
                        f"source beside the image ({', '.join(EDITABLE_EXT)} with the same "
                        "stem), and none is tracked. You cannot claim you drew something "
                        "without the thing you drew it with (COPYRIGHT.md, \"Figures\").")


# The same quoted-attribute-tolerant tag parsing the HTML scanner uses
# (`_ATTRS`), for the same reason: a quoted attribute value may contain `>`,
# so a tag runs to the first `>` OUTSIDE quotes. Stopping at the first `>` of
# any kind made `<image aria-label="a > b" href="data:image/png;base64,...">`
# invisible, and an `origin: original` SVG then certified its own bitmap.
_SVG_IMAGE_TAG = re.compile(
    r"<(?:[A-Za-z_][\w.\-]*:)?(?:image|feImage)\b(" + _ATTRS + r")>", re.I | re.S)
_SVG_HREF = re.compile(r"\bhref\s*=\s*(?:([\"'])(.*?)\1|([^\s\"'>]+))", re.I | re.S)


def svg_embedded_rasters(text: str) -> list[str]:
    """The href of every `<image>` (or `<feImage>`) element that embeds a raster:
    a `data:` URI, or a path ending in a raster extension. Attribute values are
    entity-decoded and whitespace-stripped first, so `data&#58;` and a base64
    body folded over several lines are seen for what they are."""
    hits: list[str] = []
    for tag in _SVG_IMAGE_TAG.finditer(text):
        for m in _SVG_HREF.finditer(tag.group(1)):
            raw = m.group(2) if m.group(2) is not None else m.group(3).rstrip("/")
            value = "".join(html.unescape(raw).split())
            low = value.lower()
            path = low.split("?", 1)[0].split("#", 1)[0]
            if low.startswith("data:") or path.endswith(RASTER_EXT):
                hits.append(value[:40] + ("..." if len(value) > 40 else ""))
    return hits


def check_svg_embeds_raster(ctx: Context) -> None:
    """An SVG that wraps a bitmap is a bitmap. An `<image>` element whose href is
    a `data:` URI or a raster file makes the SVG a container for a raster, and
    a container cannot certify itself: `origin: original` with the SVG as its
    own editable source would let any screenshot in by base64-encoding it into
    an `<image>` tag. Such an SVG needs `origin: cc-licensed` in its own
    .source.yml, or a sibling non-SVG editable source that the drawing was
    actually made from.
    """
    for rel in ctx.targets:
        if not has_ext(rel, (".svg",)) or rel not in ctx.universe:
            continue
        text = ctx.text(rel)
        if text is None:
            continue
        embedded = svg_embedded_rasters(text)
        if not embedded:
            continue
        stem = stem_of(rel)
        decl = find_decl(stem, ctx.universe)
        certified = False
        if decl is not None:
            data, _why = read_decl(ctx, decl)
            origin = (data or {}).get("origin")
            if origin == "cc-licensed":
                certified = True
            elif origin in ("original", "redrawn"):
                certified = any(stem + ext in ctx.universe for ext in EDITABLE_EXT if ext != ".svg")
        if certified:
            continue
        ctx.add("svg_embeds_raster", rel,
                f"this SVG embeds a raster image ({', '.join(embedded[:3])}), so it is a "
                "wrapper around a bitmap rather than a drawing, and it cannot certify its own "
                "provenance: an SVG is only its own editable source when it is made of shapes. "
                f"Declare `origin: cc-licensed` in {stem.rpartition('/')[2]}.source.yml with "
                "the source and licence, or commit the non-SVG editable source "
                f"({', '.join(e for e in EDITABLE_EXT if e != '.svg')}) the drawing was made "
                "from (COPYRIGHT.md, \"Figures\").")


def check_attribution_present(ctx: Context) -> None:
    """Every summaries/**/*.md (and *.markdown, any letter case in the directory
    name) carries a rendered H2 heading `Source and attribution` (COPYRIGHT.md,
    "The rules I actually follow", rule 4).

    The heading is looked for on the RENDERED page - code blanked, comments
    stripped, `<h2>` recognised - because a heading that exists only inside a
    comment or a fence is not on the page. Letter case and trailing
    whitespace are ignored; the finding says what was found instead.
    """
    for rel in ctx.targets:
        if not is_summary(rel):
            continue
        text = ctx.text(rel)
        scan = ctx.scan(rel)
        if text is None or scan is None:
            continue
        found = headings(scan, frontmatter_end(text))
        if any(level == 2 and title.strip().lower() == ATTRIBUTION_TITLE
               for _ln, level, title in found):
            continue
        near = [(ln, level, title) for ln, level, title in found
                if re.search(r"source|attribution", title, re.I)]
        raw_has_it = re.search(r"^[ \t]{0,3}#{1,6}[ \t]+source and attribution[ \t#]*$",
                               text, re.I | re.M)
        if near:
            ln, level, title = near[0]
            instead = (f"the nearest heading is {'#' * level + ' ' + title!r} on line {ln}, "
                       f"which is {'not level 2' if level != 2 else 'not that wording'}")
        elif raw_has_it:
            instead = ("the file contains the line, but only inside an HTML comment or a "
                       "code fence, where it does not render")
        else:
            h2s = [title for _ln, level, title in found if level == 2]
            instead = (f"the H2 headings present are {', '.join(repr(t) for t in h2s[:6])}"
                       if h2s else "the file has no H2 heading at all")
        ctx.add("attribution_present", rel,
                f"no rendered H2 heading reads `Source and attribution` ({instead}). Every "
                "summary names the paper, authors, venue, year and a DOI or arXiv link under "
                "that heading (COPYRIGHT.md, \"The rules I actually follow\", rule 4).")


def check_quote_over_limit(ctx: Context) -> None:
    """No blockquote and no quoted span over MAX_QUOTE_WORDS words, in any
    markdown file (COPYRIGHT.md, "The rules I actually follow", rule 2).

    The file is scanned as the reader sees it: code blanked, verbatim fences
    and HTML blockquotes counted as blockquotes, entities decoded. Quotation
    marks are paired by family inside each markdown block; see `quoted_spans`
    for why a regex cannot do this.

    Not scanned: `data:` URIs inside markdown. GitHub does not render them, so
    nothing is displayed to a reader; a bitmap hidden there is invisible. Nor
    the YAML frontmatter: a quoted `description:` is a scalar, not a
    quotation, and only the abstract rule reads that block.
    """
    for rel in ctx.targets:
        if not is_prose(rel):
            continue
        text = ctx.text(rel)
        scan = ctx.scan(rel)
        if text is None or scan is None:
            continue
        scan = body_only(scan, frontmatter_end(text))

        for line, body in blockquotes(scan):
            n = count_words(body)
            if n > MAX_QUOTE_WORDS:
                ctx.add("quote_over_limit", rel,
                        f"a blockquote (or a verbatim fence, which renders as one) runs to "
                        f"{n} words; the ceiling on any single quotation is {MAX_QUOTE_WORDS} "
                        f"(COPYRIGHT.md, \"The rules I actually follow\", rule 2). "
                        f"Begins: {excerpt(body)!r}. Paraphrase it, or quote only the phrase "
                        "whose wording you discuss.",
                        line)

        for line, span, opener in quoted_spans_detail(scan):
            n = count_words(span)
            if n > MAX_QUOTE_WORDS:
                what = ("an inline code span, which renders as a run of verbatim text,"
                        if opener == CODE_SPAN_OPEN else "a quoted span")
                ctx.add("quote_over_limit", rel,
                        f"{what} runs to {n} words; the ceiling on any single "
                        f"quotation is {MAX_QUOTE_WORDS} (COPYRIGHT.md, \"The rules I "
                        f"actually follow\", rule 2). Begins: {excerpt(span)!r}.",
                        line)


def check_quote_aggregate_over_limit(ctx: Context) -> None:
    """Per H2 section - and per file for the text before the first H2 - the
    words inside all blockquotes and quoted spans together may not exceed
    MAX_QUOTE_AGGREGATE_WORDS, and across the whole file they may not exceed
    MAX_QUOTE_FILE_WORDS. Chunking a 300-word passage into eight 38-word
    blockquotes satisfies the single-quotation rule and reproduces the passage
    all the same; this rule is the one that notices. A quoted span that sits
    inside a blockquote is counted once, as part of the blockquote. A quoted
    span of MIN_AGGREGATE_SPAN_WORDS words or fewer is a title or a term and
    counts toward nothing: a reading list of thirty quoted titles is a
    reading list. The frontmatter is not scanned, as in the single rule.
    """
    for rel in ctx.targets:
        if not is_prose(rel):
            continue
        text = ctx.text(rel)
        scan = ctx.scan(rel)
        if text is None or scan is None:
            continue
        body_start = frontmatter_end(text)
        scan = body_only(scan, body_start)
        h2 = [(ln, title) for ln, level, title in headings(scan, body_start) if level == 2]
        h2_lines = [ln for ln, _t in h2]
        totals: dict[int, int] = {}
        first_line: dict[int, int] = {}
        ranges: list[tuple[int, int]] = []

        def tally(line: int, n: int) -> None:
            sec = bisect.bisect_right(h2_lines, line)
            totals[sec] = totals.get(sec, 0) + n
            first_line.setdefault(sec, line)

        for start, body in blockquotes(scan):
            ranges.append((start, start + body.count("\n")))
            tally(start, count_words(body))
        for line, span in quoted_spans(scan):
            if any(a <= line <= b for a, b in ranges):
                continue
            n = count_words(span)
            if n > MIN_AGGREGATE_SPAN_WORDS:
                tally(line, n)

        for sec in sorted(totals):
            n = totals[sec]
            if n <= MAX_QUOTE_AGGREGATE_WORDS:
                continue
            if sec == 0:
                where, line = "before the first H2 heading", first_line[sec]
            else:
                where, line = f"under the heading {h2[sec - 1][1]!r}", h2_lines[sec - 1]
            ctx.add("quote_aggregate_over_limit", rel,
                    f"the blockquotes and quoted spans {where} total {n} words; the ceiling "
                    f"for one section is {MAX_QUOTE_AGGREGATE_WORDS}, three times the "
                    f"single-quotation limit of {MAX_QUOTE_WORDS}, because a passage cut into "
                    "short pieces is still the passage (COPYRIGHT.md, \"The rules I actually "
                    "follow\", rules 2 and 3). Keep the one quotation whose wording you "
                    "discuss and paraphrase the rest.",
                    line)

        whole = sum(totals.values())
        if whole > MAX_QUOTE_FILE_WORDS:
            ctx.add("quote_aggregate_over_limit", rel,
                    f"the blockquotes and quoted spans across the whole file total {whole} "
                    f"words; the ceiling for one file is {MAX_QUOTE_FILE_WORDS}, whatever the "
                    "sections, because a passage spread over several headings is still the "
                    "passage (COPYRIGHT.md, \"The rules I actually follow\", rules 2 and 3). "
                    "Keep the quotations whose wording you discuss and paraphrase the rest.",
                    min(first_line.values()))


def check_raw_abstract_present(ctx: Context) -> None:
    """No more than RAW_ABSTRACT_WORDS words, in total, under a heading that
    mentions "abstract", after a bare `Abstract` lead-in line, or in an
    `abstract` key in the frontmatter (COPYRIGHT.md, "What is not mine": the
    abstract, verbatim).

    Every abstract-named section of the file is counted as a whole, up to the
    next heading of equal or higher level, and all of them are summed with
    the frontmatter key: a 220-word abstract pasted as four 55-word
    paragraphs is a 220-word abstract, and so is one pasted as `## Abstract`
    and `## Abstract (continued)`. A whole paper pasted as plain lines has no
    heading at all - `Abstract` on a line of its own, `**Abstract.**` or
    `Abstract:` followed by the text - and that lead-in is recognised too,
    the abstract running to the next heading or the next line that looks
    like a section title (`1 Introduction`); see `abstract_lead_in`. The
    private guard has a second half that shingle-matches the body against
    the paper's real abstract; that text never reaches this repository, so
    the paste is the route checked here.
    """
    for rel in ctx.targets:
        if not is_prose(rel):
            continue
        text = ctx.text(rel)
        scan = ctx.scan(rel)
        if text is None or scan is None:
            continue

        pieces: list[tuple[int, int, str, str]] = []     # (line, words, where, text)
        fm = frontmatter_abstract(text)
        if fm is not None:
            fm_line, value = fm
            pieces.append((fm_line, count_words(value), "the frontmatter `abstract` key", value))

        lines = scan.split("\n")
        body_start = frontmatter_end(text)
        found = headings(scan, body_start)
        heading_lines = {ln for ln, _lv, _t in found}
        counted: list[tuple[int, int]] = []              # line ranges already counted
        for idx, (line, level, title) in enumerate(found):
            if not re.search(r"abstract", title, re.I):
                continue
            end = len(lines)
            for later_line, later_level, _t in found[idx + 1:]:
                if later_level <= level:
                    end = later_line - 1
                    break
            body = [lines[ln - 1] for ln in range(line + 1, end + 1) if ln not in heading_lines]
            first = next((ln for ln in range(line + 1, end + 1)
                          if ln not in heading_lines and lines[ln - 1].strip()), line)
            pieces.append((first, count_words("\n".join(body)), f"the heading {title!r}",
                           " ".join(body)))
            counted.append((line, end))

        ln = body_start + 1
        while ln <= len(lines):
            if ln in heading_lines or any(a <= ln <= b for a, b in counted):
                ln += 1
                continue
            lead = abstract_lead_in(lines, ln, heading_lines)
            if lead is None:
                ln += 1
                continue
            first, end, body_text = lead
            # The lead-in line may carry the abstract's first line after its
            # colon; the finding names the line, it does not echo it.
            pieces.append((first, count_words(body_text),
                           f"the lead-in line {excerpt(lines[ln - 1].strip())!r} (line {ln})",
                           " ".join(body_text.split("\n"))))
            ln = end + 1

        total = sum(n for _ln, n, _w, _t in pieces)
        if total <= RAW_ABSTRACT_WORDS:
            continue
        pieces.sort()
        if len(pieces) == 1 and fm is not None:
            ctx.add("raw_abstract_present", rel,
                    f"the frontmatter carries an `abstract` key of {total} words, and GitHub "
                    f"renders frontmatter; anything over {RAW_ABSTRACT_WORDS} words there "
                    "reads as the publisher's abstract, which is the authors' expression "
                    "(COPYRIGHT.md, \"What is not mine\"). Remove the key. Begins: "
                    f"{excerpt(pieces[0][3])!r}.",
                    pieces[0][0])
            continue
        where = " and ".join(w for _ln, _n, w, _t in pieces)
        together = ("every paragraph of the section counted together" if len(pieces) == 1
                    else "every abstract-named section of the file counted together")
        ctx.add("raw_abstract_present", rel,
                f"a {total}-word passage sits under {where}, {together}; anything over "
                f"{RAW_ABSTRACT_WORDS} words there reads as the publisher's abstract, which "
                "is the authors' expression (COPYRIGHT.md, \"What is not mine\"). Replace it "
                f"with your own one-sentence framing. Begins: {excerpt(pieces[0][3])!r}.",
                pieces[0][0])


def _notebook_markers(node: object, where: str, hits: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "output_type":
                hits.append(f"{where}: output_type={value!r}")
            elif key == "execution_count" and value is not None:
                hits.append(f"{where}: execution_count={value!r}")
            elif isinstance(key, str) and (key.startswith("image/")
                                           or key in ("text/html", "application/pdf")):
                hits.append(f"{where}: {key} data")
            _notebook_markers(value, where, hits)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            label = f"cell {i}" if where == "cells" else where
            _notebook_markers(item, label, hits)


def check_notebook_outputs(ctx: Context) -> None:
    """A notebook is committed with its outputs stripped. Any output_type, any
    non-null execution_count, any image/*, text/html or application/pdf MIME
    key is a finding: rendered outputs are where a paper's figure ends up
    embedded as base64 without anyone deciding to commit a figure.

    The JSON is parsed and walked rather than grepped, so an output that
    carries only a MIME bundle and no `output_type` key is still found. A
    notebook that is not valid JSON is a finding, not a skip.
    """
    for rel in ctx.targets:
        if not has_ext(rel, (".ipynb",)):
            continue
        text = ctx.text(rel)
        if text is None:
            continue
        try:
            doc = json.loads(text)
        except ValueError as exc:
            ctx.add("notebook_outputs", rel,
                    f"not valid JSON ({exc}), so its outputs cannot be inspected; the guard "
                    "fails closed. Re-save it from Jupyter with outputs cleared.")
            continue
        hits: list[str] = []
        if isinstance(doc, dict):
            for key, value in doc.items():
                _notebook_markers(value, "cells" if key == "cells" else key, hits)
        else:
            _notebook_markers(doc, "document", hits)
        if hits:
            shown = "; ".join(hits[:5]) + (f"; and {len(hits) - 5} more" if len(hits) > 5 else "")
            ctx.add("notebook_outputs", rel,
                    f"contains rendered output ({shown}). Clear all outputs before "
                    "committing: `jupyter nbconvert --clear-output --inplace`. An embedded "
                    "image is a figure with no provenance (COPYRIGHT.md, \"Figures\").")


def base_candidates(base: str) -> tuple[str, ...]:
    """The local names a pull request's base ref can already be sitting under,
    in the order they are tried. `.github/workflows/copyright.yml` checks the
    tree out with `fetch-depth: 0`, so on Actions the base commit is in the
    clone before this file runs and `origin/<ref>` resolves at once."""
    return (base, f"origin/{base}", f"refs/remotes/origin/{base}")


def resolve_base(ctx: Context, base: str) -> Optional[str]:
    """The commit the base ref names, resolved LOCALLY, or None.

    No network. `rev-parse --verify --quiet <ref>^{commit}` answers from the
    objects already in the clone and says nothing on failure.
    """
    for ref in base_candidates(base):
        out = ctx.repo.git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}",
                           check=False).decode("utf-8", "replace").strip()
        if out:
            return out
    return None


def base_commit(ctx: Context) -> tuple[Optional[str], Optional[str]]:
    """(the commit the pull request's base ref names, None), or (None, why it
    could not be determined). Resolved once; every rule that needs the base
    reads the same answer, so the three of them cost git one resolution.

    The base ref is resolved LOCALLY first - the ref itself, then
    `origin/<ref>`, then `refs/remotes/origin/<ref>` - and the network is
    touched only when none of the three resolve. The workflow checks the tree
    out with `fetch-depth: 0`, so in CI the base commit is already present and
    no fetch happens at all; fetching unconditionally turned a restricted
    runner or one dropped packet into a blocking finding on a valid pull
    request. When nothing resolves and the fetch fails too, the caller gets
    the reason and blocks on it: failing open is the hole these rules exist
    to close.
    """
    if ctx._base_rev is not None:
        return ctx._base_rev
    base = os.environ.get("GITHUB_BASE_REF", "").strip()
    rev = resolve_base(ctx, base)
    if rev is None:
        try:
            ctx.repo.git("fetch", "--depth=1", "origin", base)
        except RepoError as exc:
            ctx._base_rev = (None, _unresolved_base_message(base, exc))
            return ctx._base_rev
        rev = "FETCH_HEAD"
    ctx._base_rev = (rev, None)
    return ctx._base_rev


def changed_against_base(ctx: Context) -> tuple[Optional[set[str]], Optional[str]]:
    """(paths that differ from the pull request's base branch, None), or
    (None, why that could not be determined). Diffed once; both self-edit
    rules read the same answer. Renames are listed as a deletion and an
    addition, so a guard file moved aside still counts as changed.

    The base commit comes from `base_commit` above, which is where the
    resolution order and the fail-closed behaviour are explained.
    """
    if ctx._base_diff is not None:
        return ctx._base_diff
    base = os.environ.get("GITHUB_BASE_REF", "").strip()
    rev, why = base_commit(ctx)
    if rev is None:
        ctx._base_diff = (None, why)
        return ctx._base_diff
    try:
        out = ctx.repo.git("diff", "--name-only", "-z", "--no-renames", rev)
    except RepoError as exc:
        ctx._base_diff = (None, f"git diff against {base} failed ({exc})")
        return ctx._base_diff
    ctx._base_diff = (set(ctx.repo._split_nul(out)), None)
    return ctx._base_diff


def _unresolved_base_message(base: str, exc: Exception) -> str:
    return (f"the base branch {base!r} could not be resolved locally (tried "
            f"{', '.join(base_candidates(base))}) and fetching it failed ({exc}). This "
            "finding blocks the pull request on purpose: failing open here is the hole "
            "this rule exists to close, because a guard that cannot see the base branch "
            "cannot tell a guard change from a content change and would wave both through. "
            f"Run `git fetch origin {base}` on the runner, or check the tree out with "
            "`fetch-depth: 0` (as .github/workflows/copyright.yml does) so the base commit "
            "is present before the guard runs")


def check_workflow_self_edit(ctx: Context) -> None:
    """On a pull request, .github/ (the whole directory: workflows, CODEOWNERS,
    the labels file, issue templates) may not change in the same pull request
    as anything outside it.

    Both halves matter. A PR that can edit its own guard AND ship content in
    the same breath can neuter the guard for exactly that content, and a
    skipped required job reads as satisfied. A PR that touches ONLY .github/
    is a workflow change, reviewed as such, and must be able to merge - without
    that, no workflow fix can ever land, including the one that ships this
    checker. GITHUB_BASE_REF is set only on pull-request events, so a local
    run and a push to main skip this silently.
    """
    if not os.environ.get("GITHUB_BASE_REF", "").strip():
        return
    changed, why = changed_against_base(ctx)
    if changed is None:
        ctx.add("workflow_self_edit", GITHUB_DIR, f"{why}; the guard fails closed.")
        return
    github = {p for p in changed if p.lower().startswith(GITHUB_DIR)}
    outside = changed - github
    if github and outside:
        ctx.add("workflow_self_edit", GITHUB_DIR,
                f"{len(github)} file(s) under .github/ and {len(outside)} file(s) outside it "
                f"differ from {os.environ['GITHUB_BASE_REF'].strip()}. Workflow files may not "
                "change in the same pull request as content: a PR that can edit its own guard "
                "can neuter it for what it ships. Land the workflow change in its own PR, "
                "reviewed as such.")


def check_guard_self_edit(ctx: Context) -> None:
    """On a pull request, this checker, its tests and .githooks/ may not change
    in the same pull request as content - anything outside .github/, tools/
    and .githooks/. The guard and the content it judges do not travel in one
    pull request. And whatever else the pull request does, the tree under
    review must still CONTAIN every path in REQUIRED_GUARD_PATHS.

    The second half closes a hole in the first. The pairing rule fires only
    when a guard path changes AND content changes, so a pull request that
    merely DELETES this file - or its tests, or the pre-commit hook - touches
    guard paths alone, passes, and leaves a repository whose documents all
    say it is guarded and whose guard is not there. Deletion fails closed
    here. Guard-only MODIFICATIONS stay permitted: without them no fix to the
    guard could ever land, including the one that ships this rule.

    Belt and braces. The real defence is in the workflow, which runs main's
    copy of this file against the pull request's tree, so a PR that rewrites
    this rule is judged by the version that does not contain the rewrite - and
    a PR that deletes this file is judged by main's copy, which is why the
    absence check can see the deletion at all. This rule must never be the
    only thing standing.
    """
    if not os.environ.get("GITHUB_BASE_REF", "").strip():
        return
    missing = [p for p in REQUIRED_GUARD_PATHS if p not in ctx.universe]
    if missing:
        ctx.add("guard_self_edit", missing[0],
                f"the tree under review does not contain {', '.join(missing)}. A pull "
                "request may change the guard, but it may not remove it: after this merged, "
                "the repository would carry documents that say it is guarded and no guard to "
                f"do it. The required paths are {', '.join(REQUIRED_GUARD_PATHS)}. Restore "
                "the missing one(s) from main.")
    changed, why = changed_against_base(ctx)
    if changed is None:
        ctx.add("guard_self_edit", GUARD_FILES[0], f"{why}; the guard fails closed.")
        return
    guard = sorted(p for p in changed if is_guard(p))
    content = sorted(p for p in changed if is_content(p))
    if guard and content:
        ctx.add("guard_self_edit", guard[0],
                f"the guard ({', '.join(guard[:3])}) and content it judges "
                f"({', '.join(content[:3])}{', ...' if len(content) > 3 else ''}) differ from "
                f"{os.environ['GITHUB_BASE_REF'].strip()} in the same pull request. The guard "
                "and the content it judges do not travel in one pull request: land the guard "
                "change first, on its own, and the content after it has been judged by the "
                "guard that is on main.")


def parse_commit_log(out: str) -> list[dict]:
    """The records produced by COMMIT_LOG_FORMAT, in log order.

    Raises ValueError on a record that does not have its five fixed fields.
    A malformed record is not skipped: it would be a commit the rule below
    never looked at, which is the same silence the first audit found four of.
    """
    records: list[dict] = []
    for chunk in out.split("\0"):
        if not chunk.strip():
            continue
        lines = chunk.lstrip("\n").split("\n")
        if len(lines) < 6:
            raise ValueError(f"a commit record has {len(lines)} line(s), not the expected six "
                             "or more (sha, author name, author email, committer name, "
                             "committer email, message)")
        records.append({
            "sha": lines[0],
            "author_name": lines[1],
            "author_email": lines[2],
            "committer_name": lines[3],
            "committer_email": lines[4],
            "message": "\n".join(lines[5:]),
        })
    return records


def is_owner_email(email: str) -> bool:
    """True for the owner's address in either spelling it can appear in."""
    email = email.strip()
    return email.lower() == OWNER_EMAIL or bool(OWNER_NOREPLY.match(email))


def attribution_faults(record: dict) -> list[str]:
    """Every reason one commit fails the attribution rule, in message order."""
    faults = [f"its message carries {label}"
              for pattern, label in ATTRIBUTION_MARKERS if pattern.search(record["message"])]
    for role in ("author", "committer"):
        name, email = record[f"{role}_name"].strip(), record[f"{role}_email"]
        if name != OWNER_NAME or not is_owner_email(email):
            faults.append(f"its {role} is {name} <{email.strip()}>, not "
                          f"{OWNER_NAME} <{OWNER_EMAIL}>")
    return faults


def check_commit_attribution(ctx: Context) -> None:
    """On a pull request, every commit in base..HEAD must read as the owner's
    own work: no `Co-authored-by:` trailer, no "generated with/by" line, no
    `[bot]` marker, and an author and a committer who are the owner.

    Why the repository holds this line: its history is meant to read as one
    person's work, and a trailer or a bot author in the log is a claim about
    authorship that the repository does not want to make. The trade is that a
    genuine collaborator cannot be credited in a trailer; this notebook has
    one author, and if that changes the rule changes with it.

    `.githooks/commit-msg` refuses the same message locally, but a hook does
    not run in GitHub's web editor and `--no-verify` skips it, so this half
    runs however the commit was made. GITHUB_BASE_REF is set only on
    pull-request events, so a local run and a push to main skip this silently.
    """
    if not os.environ.get("GITHUB_BASE_REF", "").strip():
        return
    rev, why = base_commit(ctx)
    if rev is None:
        ctx.add("commit_attribution", ".githooks/commit-msg", f"{why}; the guard fails closed.")
        return
    try:
        out = ctx.repo.git("log", f"--format={COMMIT_LOG_FORMAT}", f"{rev}..HEAD")
    except RepoError as exc:
        ctx.add("commit_attribution", ".githooks/commit-msg",
                f"the commits on this pull request could not be listed ({exc}), so their "
                "authorship cannot be checked; the guard fails closed.")
        return
    try:
        records = parse_commit_log(out.decode("utf-8", "replace"))
    except ValueError as exc:
        ctx.add("commit_attribution", ".githooks/commit-msg",
                f"the commit log could not be parsed ({exc}), so authorship cannot be "
                "checked; the guard fails closed.")
        return
    for record in records:
        faults = attribution_faults(record)
        if faults:
            ctx.add("commit_attribution", ".githooks/commit-msg",
                    f"commit {record['sha'][:12]} is refused because "
                    f"{'; and '.join(faults)}. {ATTRIBUTION_REASON}")


CHECKS: tuple[Callable[[Context], None], ...] = (
    check_no_third_party_pdf,
    check_pdf_magic_bytes,
    check_archive_present,
    check_symlink_present,
    check_size_ceiling,
    check_image_provenance,
    check_svg_embeds_raster,
    check_attribution_present,
    check_quote_over_limit,
    check_quote_aggregate_over_limit,
    check_raw_abstract_present,
    check_notebook_outputs,
    check_workflow_self_edit,
    check_guard_self_edit,
    check_commit_attribution,
)


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def repo_root(start: Path) -> Path:
    try:
        proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                              capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RepoError(f"git is not available: {exc}") from exc
    if proc.returncode != 0:
        raise RepoError(f"{start} is not inside a git repository")
    return Path(proc.stdout.decode("utf-8", "replace").strip())


def relative_posix(root: Path, given: str) -> str:
    p = Path(given)
    p = p if p.is_absolute() else (Path.cwd() / p)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise RepoError(f"{given} is not inside the repository {root}") from exc


def gather(root: Path, mode: str, paths: Optional[list[str]] = None) -> list[Finding]:
    """Run every check. `mode` is "all", "staged" or "paths"."""
    repo = Repo(root, from_index=(mode == "staged"))
    universe = set(repo.tracked())
    deleted: set[str] = set()

    if mode == "all":
        targets = sorted(universe)
    elif mode == "staged":
        changed, gone = repo.staged()
        targets = sorted(p for p in changed if p in universe)
        deleted = set(gone)
    else:
        targets_set: set[str] = set()
        for given in paths or []:
            rel = relative_posix(root, given)
            if rel in (".", ""):
                # The repository root itself. `Path.relative_to` renders it as
                # ".", which as a directory prefix is "./" - a string no git
                # path ever starts with, so `check_copyright.py .` selected
                # nothing and exited 0 while looking like a full run. The root
                # means the whole tracked tree, exactly like --all.
                targets_set.update(universe)
                continue
            if (root / rel).is_dir():
                targets_set.update(p for p in universe if p.startswith(rel.rstrip("/") + "/"))
            else:
                targets_set.add(rel)
        targets = sorted(targets_set)

    ctx = Context(repo=repo, targets=targets, universe=universe, deleted=deleted,
                  symlinks=repo.symlinks())
    for check in CHECKS:
        check(ctx)
    ctx.findings.sort(key=lambda f: (f.path, f.line or 0, f.check, f.message))
    return ctx.findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_copyright.py",
        description="The copyright guard for the public research notebook. Exit 1 on any finding.")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--all", action="store_true",
                       help="every tracked file, from the working tree (CI; the default)")
    scope.add_argument("--staged", action="store_true",
                       help="files staged in the git index, read from the index (pre-commit)")
    parser.add_argument("paths", nargs="*", metavar="PATH",
                        help="specific files or directories to check instead")
    parser.add_argument("--root", metavar="DIR", default=None,
                        help="repository root (default: the git toplevel of the cwd)")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if args.paths and (args.all or args.staged):
        print("error: PATH arguments cannot be combined with --all or --staged", file=sys.stderr)
        return 2
    mode = "staged" if args.staged else ("paths" if args.paths else "all")
    on_actions = bool(os.environ.get("GITHUB_ACTIONS"))

    try:
        root = Path(args.root).resolve() if args.root else repo_root(Path.cwd())
        findings = gather(root, mode, args.paths)
    except RepoError as exc:
        # The repository could not be examined at all. That is a failure, not
        # a pass with a warning: a guard that cannot look has not looked.
        if on_actions:
            print(Finding("repository", ".", str(exc)).annotation())
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1

    for f in findings:
        print(f.annotation() if on_actions else f.plain())

    if findings:
        print(f"\ncopyright guard: {len(findings)} finding(s). See COPYRIGHT.md for the rules; "
              "nothing here is worth an argument with an author.")
        return 1
    print(f"copyright guard: no findings ({mode}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
