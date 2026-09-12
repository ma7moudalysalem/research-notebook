---
layout: default
title: A research notebook, in the open
description: >-
  Paper summaries written in my own words by Mahmoud Ali Salem, while reading
  toward a Master's thesis in AI.
---

# A research notebook, in the open

I am **Mahmoud Ali Salem**, a health-tech engineer reading toward a Master's
thesis in AI. This is where the reading is kept: one page per paper I have read
properly, written from the paper rather than from anyone's summary of it, and
published as I go rather than when it is finished.

Every word on these pages is mine. No abstract is reproduced, no passage is
quoted at length, no figure is lifted, and no publisher's PDF sits in the
repository behind this site. That is not a promise in prose. A checker in the
repository enforces it on every change, and a pull request that breaks it does
not merge. The trade is that these pages can never show you the authors' own
words, so each one links to the paper and asks you to go and read it.

## The summaries

{% include summary-index.html %}

## How a summary gets written

A paper becomes a page here only after I have read it end to end. The writing
happens in a private workspace first and crosses into the public repository
through a promotion step, which refuses anything that should not travel.

Each summary follows the same sections in the same order, because a fixed shape
is what makes two papers comparable: what the paper claims, how it does it, what
it was measured on, what the numbers were, and then the four sections I care
about most. Those are the limitations, the threats to validity, what it would
take to reproduce the work, and the questions I am left with. The last of them
is where a summary earns its place. Anyone can restate a method; saying which
claim you do not yet believe, and why, is the part that takes the reading.

The shape costs something. A short paper gets more headings than it needs, and a
paper that does not fit the mould has to be bent a little to fit it. I take that
over a set of pages that each argue their own case in their own order, because a
notebook is meant to be read across, not one page at a time.

The rules, the two gates a summary passes before it appears, and the things this
repository deliberately does not contain are written up in the repository
itself: [how this repository works][docs-00] and [what is not here][docs-02].
Those two point at the copies in the repository rather than at a page on this
site. GitHub renders them there today, and the alternative would be a link that
quietly hands the reader raw markdown.

[docs-00]: https://github.com/ma7moudalysalem/research-notebook/blob/main/docs/00-how-this-repo-works.md
[docs-02]: https://github.com/ma7moudalysalem/research-notebook/blob/main/docs/02-what-is-not-here.md
