# Copyright, licensing and attribution

**This is the authoritative map.** Where `LICENSE`, `LICENSES/CC-BY-4.0.txt`
and this file appear to disagree, this file is what I intend, and the
disagreement is a bug worth reporting.

It is informed practice, not legal advice. If you need certainty about reuse,
particularly of figures, ask a lawyer or the publisher.

*(This used to be a blockquote. The copyright checker cannot tell an author's
own callout from a 48-word quotation, and it should not be taught to. Plain
paragraphs say the same thing.)*

## The map

| Path | Licence | Why |
|---|---|---|
| `tools/**` | MIT | It is software. |
| `reproductions/*/code/**` | MIT, unless a `NOTICE` in that directory says otherwise | A reproduction derived from copyleft upstream carries the upstream terms. The `NOTICE` file is authoritative for that directory. |
| `tutorials/*/code/**` | MIT | Software. |
| `summaries/**` | **CC BY 4.0** | Prose. A software licence says nothing sensible about a paper summary. |
| `reading-lists/**`, `curricula/**`, `docs/**` | **CC BY 4.0** | Prose. |
| `tutorials/*/*.md` | **CC BY 4.0** | Prose. |
| `datasets/*.md` | **CC BY 4.0** | These are my descriptions. They do **not** license the datasets themselves — each card states the dataset's own terms. |
| `assets/figures/**` | See the `.source.yml` beside each file | Provenance is declared per figure, and a figure with no `.source.yml` does not get committed. |
| `references/public.bib` | CC0-equivalent | Bibliographic facts are not copyrightable. |

`summaries/LICENSE` repeats the CC BY marker at directory level, because
GitHub's licence detector only reads the root `LICENSE` and would otherwise
label the prose MIT — and a scraper reads the directory.

---

## Why a summary of someone else's paper is lawful

Because it is **my writing about their work**, not their work.

Copyright protects a particular expression, not the ideas, facts, methods or
results inside it. A summary written in my own words, describing what a paper
did and what I concluded from it, is my own copyrightable expression. That is
the same basis on which every literature review, every textbook and every
journal club has always operated.

What is *not* mine, and never appears here:

- **The publisher's PDF.** Never in this repository, in any form. It lives only
  in a private repository that is single-user by design and never made public.
- **The abstract, verbatim.** It is the authors' expression, it is short enough
  that copying it is copying a whole work, and it is one click away anyway.
- **Figures, tables and screenshots taken from a paper.** See below.
- **Long quotations.** See the ceiling below.

## The rules I actually follow

1. **Write from the note, not from the paper.** Read it, close it, write. If a
   sentence would collapse on being paraphrased, it is a quotation and needs
   marking as one.
2. **A 40-word ceiling on any single quotation**, in quotation marks, with the
   source named. This is an operational limit I chose, not a legal threshold —
   fair dealing and fair use have no word count. It exists so the rule is
   *checkable*, and `tools/promote.py` refuses above it.
3. **Quote only to discuss the wording itself.** If the quote could be replaced
   by a paraphrase without loss, paraphrase it.
4. **Every summary ends with `## Source and attribution`** naming title,
   authors, venue, year and a DOI or arXiv link, and stating that the summary
   is my own words. This is not decoration: it is the thing that makes the
   summary usable by someone else.
5. **Never imply endorsement.** A summary is my reading. Where I disagree with
   a paper I say so as my own view, and where I am unsure I say that too.

## Figures

The strictest rule here, because it is the one people get wrong.

**A figure from a paper is a separate copyrighted work.** Reproducing it needs
permission, or a specific exception, and "I cited it" is not a licence. Redrawing
it while preserving its layout still produces a derivative work.

Three lawful options, in the order I prefer them:

1. **Generate it from my own reproduction run.** Best by a distance: the figure
   is mine, and it is also *evidence*, because it shows the result I actually
   obtained rather than the one that was published.
2. **Redraw from the text.** Read the description, close the paper, draw the
   concept from understanding. The test is whether it looks like the original —
   if it does, it is a derivative, whatever route it took.
3. **Link to the publisher's page.** Costs a click and is always safe.

Enforced mechanically: every file in `assets/figures/` requires a sibling
`<name>.source.yml` declaring `origin: original | redrawn | cc-licensed`, and
`original` or `redrawn` requires a committed editable source — an `.svg`,
`.drawio`, `.excalidraw`, `.mmd` or the `.py` that plots it. You cannot claim
you drew something without the thing you drew it with. `fair-use-quote` is not
an accepted value in this repository.

CC-licensed figures are allowed with correct attribution, and the
`.source.yml` records the licence and the source URL.

## Datasets

A dataset card here describes a dataset. It does not license one.

No dataset content is redistributed from this repository — no images, no
samples, no derived CSVs. Where a dataset's terms restrict what may be
published from work using it, the card says so, and `promote.py` refuses to
publish anything referencing a dataset whose `redistribution` is `forbidden` or
`unverified`.

## Reproductions

Reproducing published work means running someone else's code, and academic
repositories very often have **no licence file at all**. Code with no licence
is not public domain: all rights are reserved by default, and publishing a
derivative of it under this repository's MIT would be straightforward
infringement.

So: upstream code is pinned by URL and commit SHA, cloned outside the
repository, and never vendored here. Each reproduction carries a
`LICENSE-CHECK.md` recording the upstream licence and the verdict — publishable,
metrics-and-figures only, or private-only. Permissive upstream may be derived
from; copyleft must carry its own terms; unlicensed or non-commercial requires a
clean-room reimplementation or stays private.

## Contributions

By opening a pull request you certify the
[Developer Certificate of Origin](https://developercertificate.org/) — sign off
with `git commit -s`.

DCO rather than a CLA, deliberately. The prose here is CC BY, which makes the
provenance of contributed text something I inherit; the DCO is the lightest
mechanism that addresses it. A CLA bot would deter a two-line typo fix and
signal a corporate posture that does not fit a student's notebook.

---

## Reporting a copyright concern

If something here reproduces your work beyond what you consider acceptable —
whether or not you believe it is unlawful — email
[ma7moudalysalem@gmail.com](mailto:ma7moudalysalem@gmail.com) with the file path and what you would like
changed.

I will acknowledge within **7 days** and, where the concern is about a figure,
a quotation or a licence claim, I will **remove or replace the material first
and discuss afterwards**. Nothing in this repository is worth an argument with
an author, and no summary here depends on the specific passage.

Please do not open a public issue for this; email is faster and does not put
your complaint in a search index.
