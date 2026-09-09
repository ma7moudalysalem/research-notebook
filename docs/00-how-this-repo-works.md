# 00 — How this repository works

This is the public half of a two-repository setup.

| | Repository | Visibility | Role |
|---|---|---|---|
| A | `research-workspace` | private | Where everything originates: papers, notes, ideas, experiments, drafts. |
| B | **this one** | public | Receives content only through a promotion tool. |

The edge is **one-directional and tool-mediated**. Content is never copied
across by hand. The two clones do not share a git remote, and the toolbox
hard-fails if either ever names the other — so the catastrophic mistake, a push
from the private clone landing here, is structurally impossible rather than
merely unlikely.

## What promotion actually does

`rw promote <note>` runs ten refusals before it writes anything:

| Refusal | Catches |
|---|---|
| `publish_not_candidate` | Publishing something you never decided to publish. |
| `status_not_read` | A summary of a paper you have not finished reading. |
| `wikilink_into_never_public` | A link into drafts, ideas, the journal or meeting notes. |
| `quote_over_limit` | A quotation over 40 words. |
| `raw_abstract_present` | The publisher's abstract, pasted while reading and never rewritten. |
| `image_without_source_yml` | A figure with no declared provenance. |
| `image_origin_not_allowed` | A figure whose origin is not original, redrawn or CC-licensed. |
| `dataset_not_redistributable` | Publishing work on a dataset whose terms forbid it. |
| `leak_scan_hit` | Absolute paths, credentials, private addresses. |
| `pdf_in_payload` | A PDF, belt and braces. |

If none of them fires, it transforms: frontmatter is rebuilt from an allowlist
rather than filtered against a denylist, so a field added privately next year is
private by default; wikilinks are flattened, because github.com renders an
unresolved `[[link]]` as literal brackets; and a `## Source and attribution`
section is appended.

Then it stops. **It does not commit, it does not push, and it does not open the
pull request.** It prints the commands and waits.

That is deliberate. No automated check can judge whether a paraphrase sits too
close to its source. The control for that is a person reading the rendered
diff, and a tool that pushed would have removed the moment at which that person
exists.

## Why the summaries are trustworthy about their own limits

Two rules do most of the work.

**A note cannot claim to be read until it is.** `status: read` is rejected
unless TL;DR, Method, Results, Limitations and Questions are all genuinely
non-empty — "TODO" does not count. So a summary here is not a skim written up
confidently.

**Required detail scales with how far you got.** Capturing a paper needs four
fields. That is on purpose: a nine-field form at 23:40 is a paper that never
gets recorded, and lost capture is the failure that kills a system like this.
Rigour arrives with the reading, not at the door.

## Generated, not maintained

Indexes, per-track listings and the bibliography are generated from each note's
frontmatter and live inside marked blocks. They are timestamp-free, so
regenerating an unchanged repository produces an unchanged file and CI can
assert it. Nothing here is a hand-kept list that has quietly gone stale.
