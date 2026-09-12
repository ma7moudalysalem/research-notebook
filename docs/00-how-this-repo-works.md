# 00 — How this repository works

This is the public half of a two-repository setup.

| | Repository | Visibility | Role |
|---|---|---|---|
| A | `research-workspace` | private | Where everything originates: papers, notes, ideas, experiments, drafts. |
| B | **this one** | public | Receives content only through a promotion tool, and refuses it on arrival if it should not be here. |

The edge is **one-directional and tool-mediated**. Content is never copied
across by hand. The two clones do not share a git remote, and the private
toolbox hard-fails if either ever names the other, so the catastrophic mistake
— a push from the private clone landing here — is structurally impossible
rather than merely unlikely.

## Two gates, in two places

A summary passes through two sets of rules before it is public, and they are
enforced by different code in different repositories. That split is the point
of this page, because it is easy to read the wrong thing into it.

### Enforced privately, before anything is written

`rw promote` runs in the private workspace. These refusals see private
information — reading state, the idea backlog, dataset agreements — that this
repository does not have and cannot check. If one of them fires, no file is
written anywhere.

| Refusal | Catches |
|---|---|
| `publish_not_candidate` | Publishing something never marked as a candidate. |
| `status_not_read` | A summary of a paper not finished reading. |
| `wikilink_into_never_public` | A link into drafts, ideas, the journal or meeting notes. |
| `dataset_not_redistributable` | Work on a dataset whose terms forbid publishing it. |
| `leak_scan_hit` | Absolute paths, credentials, private addresses, names on a denylist. |

Two more run as warnings rather than refusals: a link to a note that exists but
is not yet public, and a reference to a private-only path such as a config file
a reader here could never open.

**This repository does not enforce any of those.** It cannot know whether a
paper was read. If you are reading this to decide whether to trust the
summaries, the honest answer is that the reading discipline is a private
commitment, and what you *can* verify from here is the second gate.

### Enforced here, by code you can read

`tools/check_copyright.py` runs on every pull request, from a workflow that
takes its definition from `main` rather than from the pull request. Standard
library only, no network, and its tests are beside it. As of this writing it
checks:

| Check | Refuses |
|---|---|
| `no_third_party_pdf` | Any file named `.pdf`, in any letter case, anywhere. |
| `pdf_magic_bytes` | Any file whose bytes are a PDF, whatever it is called. |
| `archive_present` | Any archive, by name or by bytes. A zip is a container for the things above. |
| `size_ceiling` | Any file over 5 MB. Nothing that belongs here is large. |
| `image_provenance` | Any image, anywhere, without a sibling `.source.yml` declaring `origin: original`, `redrawn` or `cc-licensed` — and for the first two, the editable source it was made from. |
| `svg_embeds_raster` | An SVG wrapping a bitmap, which would otherwise certify itself as original. |
| `attribution_present` | A summary without its `## Source and attribution` section. |
| `quote_over_limit` | A blockquote, a quoted span, an indented or unlabelled code block, or a `<pre>` element over 40 words. All four render as somebody else's words. |
| `quote_aggregate_over_limit` | More than 120 quoted words in one section, or 300 in one file — so a long passage cannot be smuggled in as short pieces. Spans of eight words or fewer are titles and terms, and do not count. |
| `raw_abstract_present` | More than 60 words under any heading called *abstract*, after a bare `Abstract` line — the shape a paste from a PDF produces — or under an `abstract` key in frontmatter. |
| `notebook_outputs` | A notebook with rendered cells, which is the likeliest route for a figure or a data sample. |
| `workflow_self_edit`, `guard_self_edit` | A pull request that changes the guard *and* content in one go. |
| `unreadable_file` | Anything the checker could not open or decode. It fails closed rather than skipping. |

The 40-word ceiling is an operational choice, not a legal threshold; fair
dealing has no word count. It exists so the rule is *checkable*.

The prose rules read `.md`, `.txt`, `.rst` and `.html`. A fence labelled with
a real language is code and is skipped; a fence with no label, or with a label
like `quote`, renders verbatim and is treated as a quotation. HTML comments are
stripped first, because they do not render. Frontmatter is read only for the
`abstract` key: a quoted title is the owner's own text.

## Why a pull request cannot judge itself

The workflow checks out two copies. `main`'s copy of the checker goes in one
directory; the pull request's tree goes in another. The checker from the first
is run *against* the second. Nothing from the pull request is ever executed.

That matters because the obvious way to defeat a guard is to edit it in the
same pull request as the thing it would refuse. Here that edit is inert: the
version of the checker that runs is the one already on `main`, and a change to
it only takes effect after it has itself been merged through the unchanged
guard. The `_self_edit` checks are a second lock on the same door.

## What this guard is for, and what it is not

It helps to say who the guard is guarding against, because it is not who a
reader might assume.

A stranger cannot reach `main`. The ruleset requires a pull request and the
owner merges it. So the prose rules — the quotation ceiling, the abstract
detector — face one realistic adversary: the owner, late at night, pasting an
abstract or copying a blockquote or renaming a PDF. Accidents. Accidents do not
use look-alike Unicode in a heading, or bury a PDF header two kilobytes deep,
or split a quotation across paragraphs so the marks never pair.

Two consequences follow. The byte-level checks are meant to be airtight,
because a PDF is a PDF whatever it is called and there is no accidental way to
disguise one. The prose checks are a **tripwire**, tuned first for zero false
positives on ordinary scholarly writing — a reading list of quoted titles, a
12" display, the '90s — because a checker that fires on a bibliography gets
disabled, and a disabled checker catches nothing. The obfuscations it would
take a determined author to reach are listed by name in the checker's own
docstring as known limits, not silently absent.

And one thing no rule of either kind can judge: whether a paraphrase sits too
close to its source. No word count decides that. The residual control is a
person reading the rendered diff before the pull request is opened, which is
why promotion is a deliberate weekly act and not a background job. If a summary
here is closer to its source than it should be, the guard did not fail; a
reader did, and the
[correction template](../.github/ISSUE_TEMPLATE/correction.yml) is the remedy.

## It has been broken before

Two adversarial audits were run against the shell version of this guard, and
both got through it. A publisher PDF renamed to `.PDF`. A PDF with no
extension at all. A screenshot placed anywhere except the one directory the
old check looked in. A notebook whose filename contained a space, which made
the check fail *open*. A 300-word quotation pasted in the web editor, where no
local hook runs. And a pull request that replaced the checker with three lines
that always passed.

Two more were run against the version you are reading about. They got through
with a 300-word quotation as an indented block, as a fence with no language,
and as a `<pre>` element; with a paper pasted whole, its `Abstract` a bare
line rather than a heading; and, in the other direction, they made the guard
fire on a reading list of quoted titles, on a 12" display, on the '90s, and —
the one that would have blocked the commit shipping it — on the checker's own
source, because its docstring named the PDF header bytes.

Every one of those is now a regression test in `tools/tests/`. A fifth audit
will find more; that directory is where to look for what has already been
tried, and the correction template is where to report what has not.

## Generated, not maintained

Indexes, per-track listings and the bibliography in the private workspace are
generated from each note's frontmatter and live inside marked blocks. They are
timestamp-free, so regenerating an unchanged tree produces an unchanged file
and CI can assert it. The same discipline applies to the one generated file
here: `.cspell/people.txt` is rebuilt from the authors of the public summaries
on every promotion, and from nothing else — copying the private dictionary
would have published a reading list nobody agreed to make public.
