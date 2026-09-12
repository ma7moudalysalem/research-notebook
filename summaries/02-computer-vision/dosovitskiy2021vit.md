---
citekey: dosovitskiy2021vit
title: 'An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale'
authors:
  - Alexey Dosovitskiy
  - Lucas Beyer
  - Alexander Kolesnikov
  - Dirk Weissenborn
  - Xiaohua Zhai
  - Thomas Unterthiner
  - Mostafa Dehghani
  - Matthias Minderer
  - Georg Heigold
  - Sylvain Gelly
  - Jakob Uszkoreit
  - Neil Houlsby
year: 2021
venue: ICLR
venue_type: conference
arxiv: '2010.11929'
url: https://arxiv.org/abs/2010.11929
tracks:
  - Computer Vision
  - Foundation Models
tags:
  - domain/computer-vision
  - domain/foundation-models
  - task/classification
  - task/representation-learning
  - arch/vit
  - arch/transformer
  - modality/image
  - method/supervised
  - method/transfer-learning
  - data/large-scale
  - meta/seminal
---

# An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale

## TL;DR

Cut an image into 16x16 patches, embed each one with a single linear layer, and
run a nearly unmodified NLP transformer encoder over the resulting sequence with
a prepended class token. Trained on ImageNet alone this loses to a comparable
ResNet; pretrained on 300 million images it wins, at roughly a quarter of the
pretraining compute of the strongest CNN. The paper is usually remembered as
"attention works for vision", but its actual argument is about data: the
convolutional inductive bias is a data-efficiency prior that you can buy your
way out of, if you can afford the data.

## Contributions

1. **A nearly unmodified NLP transformer, applied to image patches, matches or
   beats CNNs on image classification.** Demonstrated at large pretraining
   scale. What is demonstrated is narrower than what is remembered: this is
   classification transfer, not vision.
2. **The CNN's inductive biases are not necessary given enough pretraining
   data.** Demonstrated as a correlation across three pretraining corpora —
   ImageNet-1k, ImageNet-21k, JFT-300M — with a visible crossover. Not
   demonstrated as a controlled manipulation: dataset size, semantic diversity,
   label taxonomy and label noise all move together.
3. **A better accuracy-per-pretraining-compute trade-off than the strongest
   CNNs.** Demonstrated with a TPU-core-day accounting that is credible,
   self-reported, and compared against other people's published configurations.
4. **Implicitly, that this scales further.** Stated as a prospect, not shown.
   It turned out to be right, which is a separate fact from it being evidenced
   here.

## Method

Reshape an image `x` of shape `H x W x C` into `N = H*W/P^2` flattened patches
of size `P^2 * C`, with `P` = 16 (also 14 and 32 in the variants). One learned
linear projection maps each patch to `D` dimensions. That projection is the only
vision-specific component in the entire model, and it is exactly equivalent to a
`P x P` convolution with stride `P`.

Prepend a learned `[class]` token. Add learned **1D** position embeddings, not
2D. The paper tries 2D-aware variants and reports no gain, and the learned 1D
embeddings recover a 2D-looking similarity structure anyway.

Then a standard pre-norm transformer encoder, repeated `L` times:

```text
z = z + MHSA(LayerNorm(z))
z = z + MLP(LayerNorm(z))         # one GELU hidden layer, width 4D
```

Classification reads the final `[class]` token through an MLP head with one
hidden layer at pretraining time, and a single linear layer at fine-tuning time.

Sizes, which are worth memorising because the whole literature names models this
way: **Base** `L=12, D=768`, MLP 3072, 12 heads, ~86M parameters; **Large**
`L=24, D=1024`, MLP 4096, 16 heads, ~307M; **Huge** `L=32, D=1280`, MLP 5120,
16 heads, ~632M. "ViT-L/16" is Large with 16x16 patches. Halving the patch side
quadruples the sequence length and therefore the attention cost, so patch size,
not depth, is the real compute dial.

Fine-tuning: discard the pretraining head, attach a zero-initialised `D x K`
linear layer, and fine-tune at a *higher* resolution than pretraining. Higher
resolution at fixed patch size means a longer sequence, so the pretrained
position embeddings are 2D-interpolated onto the new grid. That interpolation is
the one place where 2D image structure is injected by hand, and it is worth
noticing that the "no inductive bias" architecture needs it.

A **hybrid** variant replaces raw-patch projection with feature maps from a
ResNet stage. It is better at small compute budgets and no better at large ones,
which is itself a small piece of evidence for the paper's thesis.

## Datasets

Pretraining: **ImageNet-1k** (about 1.3M images), **ImageNet-21k** (about 14M
images, 21k classes), and **JFT-300M** (about 303M images, 18k classes,
in-house at Google and not publicly available).

Evaluation: ImageNet, ImageNet ReaL, CIFAR-10 and CIFAR-100, Oxford-IIIT Pets,
Oxford Flowers-102, and the 19-task VTAB suite.

No dataset cards exist for any of these yet, so this note carries no `datasets:`
frontmatter key — a reference to a dataset card that has not been written is a
broken claim about provenance. Note also what a card for JFT-300M would have to
say: access effectively private, redistribution not merely unverified but
inapplicable, and no licence excerpt to quote because there is no public
licence. That is not a filing inconvenience, it is the paper's central
scientific problem, and it is written up under Limitations.

## Results

**The headline.** Pretrained on JFT-300M, ViT-H/14 reaches 88.55% ImageNet top-1
against 87.54% for BiT-L (ResNet152x4) pretrained on the same JFT corpus. One
point. The point is not the point. The cost is: roughly 2.5k TPUv3-core-days
for ViT-H/14 against roughly 9.9k for BiT-L and roughly 12.3k for Noisy Student
(EfficientNet-L2), which lands in the same accuracy range. Equal-or-better
accuracy at about a quarter of the pretraining compute is the result that made
people switch.

Also reported for ViT-H/14 on JFT: ImageNet ReaL 90.72%, CIFAR-100 94.55%,
VTAB-19 77.63%. VTAB is the more honest transfer claim of the set; ImageNet
top-1 at that level is close to label-noise saturation, and a one-point margin
there should not be read as a one-point margin in capability.

**The result that actually matters is the crossover.** Pretrained on ImageNet-1k
alone, ViT underperforms comparable ResNets, and the diagnostic detail is that
the *larger* ViTs underperform the smaller ones, which is the signature of
overfitting rather than of insufficient capacity. Pretrained on ImageNet-21k
they are roughly level. Pretrained on JFT-300M, ViT pulls ahead and the ordering
by model size finally matches the ordering by capacity. The crossing point sits
somewhere around one hundred million pretraining images.

**The footnote that became a field.** A small masked-patch-prediction experiment
gets ViT-B/16 to about 79.9% on ImageNet — roughly 2 points over training from
scratch, and roughly 4 points behind supervised pretraining. Presented as a
preliminary exploration in 2021; it is what the next three years of vision
self-supervision were about.

**The comparisons that were not run:**

- **No CNN trained with ViT's own augmentation and regularisation recipe on
  ImageNet-1k.** The paper concludes "transformers need data" from an experiment
  that also varies the training recipe. DeiT showed within a year that a
  substantial part of that gap is recipe rather than architecture, which means
  the framing here was over-attributed at the time it was published.
- **No public-data replication of the crossover.** Every claim above the 14M
  mark rests on JFT-300M, which no one outside Google can obtain. As published,
  the central claim is not falsifiable by an outsider.
- **No dense prediction at all.** No detection, no segmentation, no
  localisation. "Transformers work for vision" is evidenced entirely by
  whole-image classification, and the property that makes segmentation hard,
  spatial precision at object boundaries, is exactly what patchification
  coarsens.
- **No matched-parameter, matched-data, matched-recipe pairing** against a CNN.
  The compute accounting compares against particular published models, not
  against a controlled counterpart.
- **Essentially no robustness or distribution-shift evaluation.** An inductive
  bias learned from data rather than built into the architecture is precisely
  the thing you would expect to degrade off-distribution, and that hypothesis is
  never tested here.

## Limitations

**Admitted.** Not applied to detection or segmentation. Self-supervised
pretraining lags supervised by a clear margin and is barely explored. Further
scaling is untested.

**Not admitted:**

- **JFT-300M is proprietary.** The paper's core scientific claim cannot be
  checked, re-run or refuted by anyone without access to a corpus that is not
  distributed. This is nowhere listed as a limitation and it is the largest one.
  Every citation of "transformers need scale" is a citation of an experiment
  nobody can repeat.
- **"Inductive bias is unnecessary at scale" is an over-claim on this
  evidence.** Patchification with a linear projection *is* an inductive bias,
  and a strong one: locality within a 16x16 window, and a fixed grid. What the
  paper removes is convolutional weight sharing and hierarchical locality across
  scales, not locality itself.
- **Learned 1D position embeddings at a fixed grid** make every resolution
  change an interpolation hack. For any domain with variable input geometry —
  which is most of medical imaging, where field of view and voxel spacing vary
  by scanner and protocol — that is a structural constraint, not a detail.
- **Attention is quadratic in sequence length.** At `P`=16, a 224x224 image is
  196 tokens; a 512x512 slice is over a thousand; a modest 3D volume is
  intractable without changing the model. The paper never confronts this because
  it never leaves moderate-resolution 2D natural images.
- **Every benchmark is a curated natural-image classification set** with large,
  clean, roughly balanced labels. The regime where a foundation model would be
  most valuable — a few hundred labelled examples, severe class imbalance,
  genuine expert disagreement about the label — is not represented anywhere in
  the evaluation.

## Threats to validity

- **Contamination.** A 300M-image web-scale pretraining corpus and downstream
  tests on ImageNet and CIFAR is the classic setup for leakage. The paper does
  run de-duplication against the downstream test sets, which is the right
  instinct and more than many contemporaries did, but near-duplicate image
  matching does not catch semantic leakage — the same object, same photographer,
  different frame.
- **Asymmetric hyperparameter budget.** The ViT recipe was developed by this
  team; the BiT and Noisy Student comparisons are other groups' published
  configurations. That asymmetry always favours the proposing method and is
  never quantified.
- **The compute accounting is self-reported** in TPUv3-core-days, against
  numbers taken from papers that ran on different hardware. Directionally
  credible; not a controlled measurement.
- **Metric saturation.** Above roughly 88% ImageNet top-1, label errors are a
  meaningful share of the residual. Reporting ReaL and VTAB alongside is the
  correct response and it is to the authors' credit, but it also means the
  headline comparison is the least informative number in the table.
- **Would a different seed change it?** Unknown; variance is not reported at the
  Huge scale, and at that cost it plausibly could not have been.

## Reproducibility

- **Code available:** yes. `google-research/vision_transformer`, JAX/Flax, plus
  faithful reimplementations in every framework since. The architecture is short
  enough to write from the paper.
- **Weights available:** partially, and the partition matters. The
  ImageNet-21k-pretrained Base and Large checkpoints were released and are what
  essentially everyone actually uses. The JFT-300M-pretrained models behind the
  headline numbers were not released, and the corpus they were trained on is not
  available either.
- **Compute reported:** yes, and unusually honestly: thousands of
  TPUv3-core-days. That number is the most useful line in the paper, because it
  tells you precisely who is able to run this experiment.
- **Would I be able to reproduce this?** The architecture, trivially.
  Fine-tuning a released ViT-B/16 on a downstream task, comfortably, on one
  consumer GPU. The paper's actual finding — the data-scale crossover — no, and
  neither can any academic lab, because JFT-300M does not exist outside Google.
  The closest honest approximation is to run the crossover over
  ImageNet-1k → ImageNet-21k → a LAION subset and be explicit that the
  composition confound has changed rather than been removed.

## Questions

- The crossover is reported in **images**. Is the causal variable image count,
  label count, semantic diversity, or total gradient steps? Three hundred
  thousand chest radiographs from four scanners are not the same three hundred
  thousand as a web crawl, and knowing which axis drives the crossover decides
  whether large-scale medical pretraining is worth attempting at all.
- Patchification asserts locality inside a 16x16 window and independence across
  window boundaries. For a task whose evidence is a 3mm lesion, what is the
  measurable cost of that boundary, and can it be characterised as a function of
  patch size relative to object size rather than discovered per dataset?
- ViT wins on transfer at scale and loses at ImageNet-1k scale. Medical
  fine-tuning always happens at the small end. Does a ViT pretrained on 300M
  natural images beat a CNN pretrained on the same images once both are
  fine-tuned on five hundred scans, or does the low-data disadvantage reappear
  at fine-tuning time as well as at pretraining time?
- The paper removes convolutional weight sharing but keeps grid locality. Which
  of the two is the part that costs data? Varying them independently — attention
  with shared weights across positions, or a ViT over non-grid or permuted
  patches — would separate them, and I have not found that experiment run
  cleanly.
- If the headline claim requires a private corpus, which of this paper's
  findings survive when the largest *public* pretraining set is substituted, and
  has anyone established that systematically? That is a survey question I can
  answer, and the answer is load-bearing for anything I build on top of a
  pretrained ViT.

## Source and attribution

- **Paper:** An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale
- **Authors:** Alexey Dosovitskiy, Lucas Beyer, Alexander Kolesnikov, Dirk Weissenborn, Xiaohua Zhai, Thomas Unterthiner, Mostafa Dehghani, Matthias Minderer, Georg Heigold, Sylvain Gelly, Jakob Uszkoreit, Neil Houlsby
- **Published in:** International Conference on Learning Representations (ICLR), 2021
- **arXiv:** [arXiv:2010.11929](https://arxiv.org/abs/2010.11929)

The summary above is my own words, written from reading the paper. It is not the authors' abstract, it is not a translation of one, and no figure, table or passage of the original is reproduced here. Credit for the work belongs to the authors listed above; go and read them.

Citekey `dosovitskiy2021vit`. Prose here is CC BY 4.0 — see [`summaries/LICENSE`](../LICENSE), and [`COPYRIGHT.md`](../../COPYRIGHT.md) for the authoritative path-to-licence map.
