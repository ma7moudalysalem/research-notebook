---
citekey: zhang2017rethinking
title: Understanding deep learning requires rethinking generalization
authors:
  - Chiyuan Zhang
  - Samy Bengio
  - Moritz Hardt
  - Benjamin Recht
  - Oriol Vinyals
year: 2017
venue: ICLR
venue_type: conference
arxiv: '1611.03530'
url: https://arxiv.org/abs/1611.03530
tracks:
  - ML Theory & Methodology
tags:
  - domain/ml-theory
  - task/classification
  - method/regularisation
  - arch/cnn
  - data/noisy-labels
  - meta/seminal
  - meta/critique
---

# Understanding deep learning requires rethinking generalization

## TL;DR

Take a standard image classifier, replace every label with a random one, change
nothing else, and it still drives training error to zero. It therefore has the
capacity to memorise the entire dataset, which means no complexity measure
defined over the hypothesis class alone can explain why the same network
generalises when the labels are real. The paper offers no replacement theory. It
demolishes the existing account and hands the field a question, and that is
precisely why it still matters nine years later.

## Contributions

They **claim**:

1. Deep networks easily fit random labels, so their effective capacity is
   sufficient to memorise the training set outright.
2. The same holds when the *inputs* are destroyed rather than the labels:
   shuffled pixels, random pixels, Gaussian noise.
3. Explicit regularisation (weight decay, dropout, data augmentation) is neither
   necessary nor sufficient for controlling generalisation error.
4. A construction: a two-layer ReLU network with 2n + d parameters can express
   any labelling of n points in d dimensions. Finite-sample expressivity, not
   asymptotic universal approximation.
5. Implicit regularisation by SGD is real but is not a complete explanation
   either.

What they **demonstrate** is 1, 2 and 4 beyond argument. Claim 3 is demonstrated
for the regularisers with knobs on them, which is not quite the same as the
sentence they wrote. Claim 5 is demonstrated as a negative: they show the
minimum-norm story is incomplete, not what the right story is.

The gap worth watching is between "these bounds are vacuous" and "these tools
cannot explain generalisation". The experiments establish the first. The title
asserts the second, and a decade of follow-up work has been arguing about the
step between them.

## Method

There is no architecture here. The method is an experimental design, and its
whole force comes from one property: **nothing changes except the data**. Same
network, same optimiser, same hyperparameters, same number of epochs. If the
outcome changes, the data caused it, and no capacity or tuning confound can be
offered as an alternative explanation. It is the cleanest experimental design I
have read in a machine-learning paper, and it is almost embarrassingly simple.

**The randomisation ladder.** Train small Inception, AlexNet and MLPs on
CIFAR-10, and Inception V3 on ImageNet, on a sequence of progressively destroyed
datasets:

- true labels, the control;
- partially corrupted labels, a fraction p of labels reassigned uniformly at
  random, sweeping p from 0 to 1 so the two regimes are connected rather than
  contrasted;
- fully random labels;
- shuffled pixels, one fixed random permutation applied to every image, which
  destroys spatial structure but preserves the pixel statistics;
- random pixels, a fresh permutation per image;
- Gaussian noise, each image replaced by a sample from a Gaussian matched to the
  dataset's mean and covariance, so there is no image left at all.

The prediction from classical learning theory is that a hypothesis class capable
of fitting the noise cases has a Rademacher complexity near 1 and therefore a
vacuous bound. The prediction from practice was that the networks would fail to
fit. The networks fit.

**The regularisation arm.** Turn data augmentation, weight decay and dropout off
in every combination and retrain on true labels. Also examine the pieces that
are not usually called regularisers: early stopping and batch normalisation.

**The theory arm.** Theorem 1: a two-layer ReLU network with 2n + d parameters
and width n realises any function on a sample of size n in d dimensions. So the
capacity to memorise is not exotic, not a property of depth, and not something a
parameter count rules out for any realistic dataset size.

**The implicit-regularisation arm.** For linear models, SGD from zero converges
to the minimum ℓ2-norm solution in the span of the data, which is a genuine
implicit bias. They run minimum-norm kernel regression on MNIST and CIFAR-10 and
it does respectably with no explicit regularisation at all. Then they break their
own story: a wavelet preprocessing step lowers test error while *increasing* the
norm of the solution, so norm alone is not the quantity that tracks
generalisation.

## Datasets

- **CIFAR-10**, 50,000 training images across 10 classes, which is where almost
  all the randomisation experiments live.
- **ImageNet (ILSVRC 2012)**, used to show the effect is not an artefact of a
  small dataset.

No cards exist for either of these yet, so nothing is wikilinked here and I have
not written a `datasets:` frontmatter key that would dangle. Both are
open-access, so the cards would be quick to write. Worth doing when the first
experiment needs one.

## Results

The result is categorical rather than numerical, which is unusual and is part of
why it landed so hard.

- **Zero training error on CIFAR-10 with completely random labels**, for
  Inception and for plain MLPs. Test error sits at chance, which for ten
  balanced classes is 90% error. The baseline comparison is the same network on
  true labels: identical setup, and now it also generalises. The delta between
  those two runs is entirely in the data.
- **Fitting random labels takes only a small constant factor longer** than
  fitting true labels. It is not a pathological run that barely converges after a
  hundred times the budget. It is the same training curve, slightly delayed.
- **The input-corruption ladder is monotone and complete.** Shuffled pixels,
  random pixels and pure Gaussian noise are all fitted to zero training error.
  There is no version of "the data still had exploitable structure" left
  standing.
- **The partial-corruption sweep** shows generalisation error degrading smoothly
  as the corruption fraction rises, with training error staying at zero
  throughout. The network is doing both things at once: learning the signal that
  remains and memorising the rest.
- **Explicit regularisation costs a few points and is not the mechanism.**
  Switching off augmentation, weight decay and dropout reduces CIFAR-10 test
  accuracy by a modest margin, single-digit percentage points as I read the
  table, while training accuracy stays at 100%. I am recording that
  qualitatively on purpose: the exact figures are in the paper's table and I am
  not confident enough of the decimals to write them here, and the argument does
  not need them. A tuning knob worth a few points is not the difference between
  memorisation and generalisation.
- **The Rademacher consequence.** A class that fits random labels perfectly has
  empirical Rademacher complexity of essentially 1, so every uniform-convergence
  bound built on it returns something like "test error ≤ 1". True and useless.

**The comparison they did not run.** They never compute a *norm-based or
margin-based* complexity measure on the random-label networks to check whether
such a measure separates the two regimes. That is the obvious next experiment,
it was cheap even in 2016, and the field ran it immediately afterwards
(spectrally-normalised margin bounds and the path-norm line of work). Running it
themselves would have turned "no complexity measure explains this" into a
falsifiable claim about a specific family of measures, and it would have blunted
the objection that the paper attacks only the weakest available theory. They
also do not measure *which* examples get memorised under partial corruption, a
per-example question that had to wait for later work on memorisation and
influence.

## Limitations

**Admitted.** The results do not preclude the existence of a suitable complexity
measure, and they say so. The theory is about expressivity, not about what SGD
actually finds, and they say that too. The implicit-regularisation story is
explicitly left incomplete.

**Not admitted, and more interesting.**

- A vacuous bound is uninformative, not wrong. "Uniform convergence cannot
  explain this" is a much stronger sentence than "the bounds I evaluated are
  loose", and the paper's rhetoric slides between them. Data-dependent and
  algorithm-dependent bounds are not tested.
- The evidence base is convolutional networks on two vision classification
  datasets with cross-entropy and SGD. It was read, including by me before this
  read, as a statement about deep learning as such.
- "Explicit regularisation is not necessary" leans hard on architectural choices
  that are themselves enormous priors. Convolution, weight sharing, pooling and
  batch normalisation encode a great deal about images. The honest version of
  claim 3 is that *the regularisers with hyperparameters attached* are not the
  mechanism, which is a narrower and still interesting claim.
- Chance-level test accuracy on random labels is trivially expected and the
  paper occasionally presents it as though it were part of the surprise. The
  surprise is entirely in the fit, not in the failure to generalise.
- I did not see variance across seeds reported for the headline curves. For a
  result this categorical it does not change the conclusion, but the habit of
  reporting single runs was being normalised in exactly this era.

## Threats to validity

Almost none of the usual ones bite, which is the mark of a good experimental
design. The test set does not matter: the conclusion is about *training* error.
Seeds do not matter: fitting random labels to zero error is not a marginal
outcome that a lucky initialisation produced. Hyperparameter fairness does not
matter, because the whole point is that the hyperparameters were held fixed
across conditions. CIFAR-10's decade of community reuse as a de facto validation
set inflates the true-label numbers somewhat, and is irrelevant to the
randomisation result.

What does threaten the *interpretation* is scope. Everything was done on vision
classification with 2016-era convnets. That the conclusion has survived
transformers, self-supervised pretraining and scale is a fact established by
later work, not by this paper, and I should not cite this paper for it.

## Reproducibility

- **Code available:** I found no official repository from the authors. Faithful
  third-party reimplementations are plentiful, and the core experiment is a
  label-tensor shuffle, which is roughly one line.
- **Weights available:** none, and they would be meaningless here. The artefact
  is the experimental design.
- **Compute reported:** not in any detail. The CIFAR-10 experiments are
  single-GPU and cheap by any standard; the ImageNet Inception runs are the
  expensive part and are the part I would skip.
- **Would I be able to reproduce this?** Yes, completely, on one consumer GPU
  overnight, and I should. Take a small ResNet on CIFAR-10, permute the label
  tensor, train to zero training error, plot both curves. This is the strongest
  candidate for my first experiment in ML theory: it costs almost
  nothing, it produces a figure I will reuse in a proposal, and it converts a
  fact I have read into a fact I have watched happen. The hypothesis to
  pre-register before the first run writes itself.

## Questions

- Medical labels are not corrupted uniformly at random. Inter-rater disagreement
  is *structured* noise, concentrated on genuinely ambiguous cases. Does the
  memorisation picture look the same when the noise is systematic and correlated
  with input difficulty, or does structured noise get absorbed into the learned
  function in a way uniform noise cannot?
- Is there any published complexity measure that separates the true-label from
  the random-label regime **and** remains informative in the n ≈ 10³ regime that
  medical imaging actually occupies? Most of the follow-up work is validated at
  CIFAR scale and above, and small-n is where I need it.
- Can the randomisation test be repurposed from demonstration to routine
  diagnostic? Shuffle the masks and retrain a segmentation model: if it still
  reaches a suspiciously good Dice, something is leaking through the pipeline.
  What is the sensitivity and specificity of that test as a leakage detector, and
  what does it cost to run on every experiment?
- What is the analogue of the randomisation test for self-supervised
  pretraining, where there are no labels to shuffle? Corrupting the augmentation
  policy is not obviously the same object, and if there is no analogue then a
  whole class of models has no cheap memorisation check.
- If a network can fit any labelling, what exactly does a validation curve on a
  200-patient held-out split license me to claim? This is a methodology question
  rather than a theory question, and I think the answer determines the shape of
  every results chapter I will write.

## Source and attribution

- **Paper:** Understanding deep learning requires rethinking generalization
- **Authors:** Chiyuan Zhang, Samy Bengio, Moritz Hardt, Benjamin Recht, Oriol Vinyals
- **Published in:** International Conference on Learning Representations (ICLR), 2017
- **arXiv:** [arXiv:1611.03530](https://arxiv.org/abs/1611.03530)

The summary above is my own words, written from reading the paper. It is not the authors' abstract, it is not a translation of one, and no figure, table or passage of the original is reproduced here. Credit for the work belongs to the authors listed above; go and read them.

Citekey `zhang2017rethinking`. Prose here is CC BY 4.0 — see [`summaries/LICENSE`](../LICENSE), and [`COPYRIGHT.md`](../../COPYRIGHT.md) for the authoritative path-to-licence map.
