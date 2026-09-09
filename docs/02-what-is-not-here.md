# 02 — What is not here

> An absence that is not explained reads as an oversight. This page turns "did
> he forget?" into "he thought about this", which for the things below is the
> difference that matters.

## No publisher PDFs

Not in any directory, not in any commit, not in history. `.gitignore` refuses
`*.pdf` outside `assets/figures/`, a pre-commit hook refuses it again, and a
required CI check refuses it a third time. Three cheap independent layers,
because this is the one mistake here with legal consequences and no clean undo:
a history rewrite on a public repository does not remove forks, mirrors or
caches.

Papers I have read exist as **notes about them**, which is my writing, not
theirs.

## No figures or tables from papers

A figure is a separate copyrighted work, and "I cited it" is not a licence.
Redrawing one while preserving its layout still produces a derivative.

Where a figure does appear here it carries a `.source.yml` declaring
`origin: original | redrawn | cc-licensed`, and `original` or `redrawn` also
requires the editable source committed beside it — the `.svg`, the `.drawio`,
or the `.py` that plots it. You cannot claim you drew something without the
thing you drew it with.

The best case, and the one I reach for first, is a figure generated from my own
reproduction run. That one is not merely lawful; it is evidence.

## No abstracts

The abstract is the authors' expression, it is short enough that copying it
copies a whole work, and it is one click away. Every summary here opens with a
TL;DR written from the note rather than from the paper.

## No unpublished research

No drafts, no proposal, no thesis chapters, no experiment results that have not
been through a deliberate decision to publish. Those live in a private
workspace, and the only path from there to here is a promotion tool that
refuses ten conditions and then hands a human a rendered diff to read.

The direction is one-way by construction, not by discipline: the two clones do
not share a git remote, and the toolbox hard-fails if either ever names the
other.

## No dataset content

Not one byte, not even a sample. In the medical-imaging case a "sample image"
is patient data under a data use agreement, and a dataset card is not a
licence — each one records the dataset's own terms and what may lawfully be
published from work using it.

## No "papers read" counter

It would be the most tempting badge on the list. It is not here because the
number exists only in the private workspace, so publishing it would be either a
claim nobody can check or a private aggregate smuggled past the promotion gate.
Every number on this repository is derivable from files you can see.

## No AI-generated summaries

The notes here are mine, written from reading the papers. Where I am unsure of
something I say so in the note rather than smoothing it over, which is also the
most reliable way to tell.
