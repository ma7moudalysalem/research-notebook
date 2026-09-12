# research-notebook

Paper summaries and reading notes in machine learning, written by **Mahmoud Ali
Salem** while reading toward a Master's thesis in AI, and kept in the open. Six
papers are summarised so far, one in each of six tracks, because the thesis
topic is not settled yet and holding the tracks at equal depth is how that
stays honest rather than tidy.

**Readable version:
[ma7moudalysalem.github.io/research-notebook](https://ma7moudalysalem.github.io/research-notebook/).**
The site is a rendering of this repository and nothing else. The files here are
the source; everything the site shows is in this tree as plain text, and if the
two ever disagree, the repository is right.

Everything here is my own writing. No paper PDFs, no figures lifted from
publications, no abstracts - and a checker CI requires on every pull request
rather than a promise that they are absent. Summaries reach this repository
only by promotion from a private workspace, never by hand.
[COPYRIGHT.md](COPYRIGHT.md) is the detail.

---

## Start here

If you read one thing, read the **[CLIP
summary](summaries/04-multimodal/radford2021clip.md)**. It sets the paper's five
claims against what the experiments actually demonstrate, and says which one
cannot be separated from the private 400-million-pair corpus at all. That
separation is what every summary here is for; the rest is a matter of which
paper interests you.

Two more, if there is time:

- **[Attention Is All You
  Need](summaries/03-foundation-models/vaswani2017attention.md)** - the
  architecture everything since is a variation on, read for the design
  decisions rather than the diagram.
- **[Vision Transformer](summaries/02-computer-vision/dosovitskiy2021vit.md)** -
  why inductive bias is a data-efficiency prior you can outgrow, and why the
  central claim rests on a corpus nobody outside the authors can check.

The six tracks, each with its one summary, so the equal-depth claim above takes
one click to check:
[medical imaging](summaries/01-medical-imaging/ronneberger2015unet.md) ·
[computer vision](summaries/02-computer-vision/dosovitskiy2021vit.md) ·
[foundation models](summaries/03-foundation-models/vaswani2017attention.md) ·
[multimodal](summaries/04-multimodal/radford2021clip.md) ·
[AI systems](summaries/05-ai-systems/dao2022flashattention.md) ·
[ML theory](summaries/06-ml-theory/zhang2017rethinking.md).

---

## What is in here

| | | |
|---|---|---|
| [`summaries/`](summaries/) | One file per paper read properly. My own words, with a source-and-attribution block. | live |
| [`docs/`](docs/) | How this repository works, and what is deliberately not in it. | live |
| [`tools/`](tools/) | The copyright checker CI requires on every pull request, and its tests. Standard library only, so anyone can read exactly what is enforced. | live |
| `reproductions/` | Papers run rather than read, with a scorecard: the paper's number, mine, the gap, and what the method section left out. | not yet |
| `reading-lists/` | Staged paths through a topic, with a reason per entry and what was left out. | not yet |
| `curricula/` | Learning tracks, including what was actually done rather than only what was planned. | not yet |
| `datasets/` | Dataset cards: licence, access tier, and what may lawfully be published from work using them. | not yet |

The rows marked *not yet* have no directory behind them. That is the rule
rather than an omission: **a directory is created when it holds its first real
file**, so nothing here is an empty folder standing in for work. Unlinked means
it does not exist; when it exists, it will be a link. The trade is that this
page cannot show you a plan, only what has been done.

---

## How a summary gets written

Three passes, after Keshav's *How to Read a Paper* (ACM SIGCOMM CCR 37(3),
2007). Pass one is five minutes and decides whether to continue; pass two is an
hour with the figures; pass three is re-implementing the argument in your head.

What is mine rather than Keshav's is the machinery around it. A note template
whose required sections scale with how far the reading actually went, so a note
cannot claim `read` until its TL;DR, Method, Results, Limitations and Questions
are all genuinely written. A promotion tool that refuses on rules this
repository cannot check for itself - a paper not finished reading, a link into
drafts, a dataset whose terms forbid publishing work done on it - and writes
nothing anywhere when one of them fires. And a fixed shape every summary here
holds to - TL;DR, Contributions, Method, Datasets, Results, Limitations,
Threats to validity, Reproducibility, Questions, Source and attribution - so
two summaries can be compared rather than only read.

The section that does the work is Contributions, which splits what the authors
claim from what their experiments demonstrate. That split is a judgement, and
it is the part of these notes most likely to be wrong, which is why the
Questions section stays in even when it is unflattering.

---

## The copyright guard

[`tools/check_copyright.py`](tools/check_copyright.py) is a single
standard-library script - no dependencies, no network - that runs **fifteen
checks** over the whole tree and has **350 tests** beside it in
[`tools/tests/`](tools/tests/). It is a required status check: a pull request
that fails it does not merge.

It refuses a PDF by name and by its first bytes, an archive, a symlink, any
file over 5 MB, an image without a sibling file declaring where it came from, a
summary missing its attribution block, a quotation over 40 words or 120 quoted
words in one section, a pasted abstract, a notebook with rendered output, and a
commit whose authorship is not the owner's.

Two things about it are worth a supervisor's minute. The workflow runs `main`'s
copy of the checker against the pull request's tree, so a pull request cannot
weaken the guard that is judging it. And the guard is honest about its own
reach: the byte-level checks are meant to be airtight, because a PDF is a PDF
whatever it is called, while the prose checks are a tripwire tuned first for
zero false positives on ordinary scholarly writing. The trade is deliberate - a
checker that fires on a bibliography gets switched off, and a switched-off
checker catches nothing - and it means a determined author could still get past
the prose rules. The known limits are named in the checker's own docstring
rather than left to be discovered.

[`docs/00-how-this-repo-works.md`](docs/00-how-this-repo-works.md) lists every
check and the audits that broke earlier versions of it.

---

## What is not here

Stated plainly, because absence reads as an oversight otherwise:

- **No publisher PDFs**, in any form, in any commit.
- **No figures or tables** copied from papers. An image may only appear with a
  `.source.yml` declaring it original, redrawn or CC-licensed, and for the
  first two the editable source is committed alongside it.
- **No abstracts**, verbatim or lightly reworded.
- **No unpublished results, drafts, or thesis material.** Those live in a
  private workspace and cross into this one only through a reviewed,
  one-directional promotion.
- **No dataset content**, not even a sample.

[`docs/02-what-is-not-here.md`](docs/02-what-is-not-here.md) gives the reasoning
for each.

---

## Licence

Dual, because this repository holds two different kinds of thing: **code** in
`tools/` is MIT, and **prose** in `summaries/` and `docs/` is CC BY 4.0.
[COPYRIGHT.md](COPYRIGHT.md) is the authoritative path-to-licence map, and it
also sets out why a summary of someone else's paper is my own work and where
that line sits.

## Corrections welcome

If a summary here is wrong,
[tell me](https://github.com/ma7moudalysalem/research-notebook/issues/new?template=correction.yml).
That is the most useful issue this repository can receive, and it is genuinely
wanted: these are one person's readings, written to be revised. If you are an
author of a paper summarised here, doubly so.
