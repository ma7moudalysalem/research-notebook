---
citekey: vaswani2017attention
title: Attention Is All You Need
authors:
  - Ashish Vaswani
  - Noam Shazeer
  - Niki Parmar
  - Jakob Uszkoreit
  - Llion Jones
  - Aidan N. Gomez
  - Lukasz Kaiser
  - Illia Polosukhin
year: 2017
venue: NeurIPS
venue_type: conference
arxiv: '1706.03762'
url: https://arxiv.org/abs/1706.03762
tracks:
  - Foundation Models
tags:
  - arch/transformer
  - domain/foundation-models
  - meta/seminal
  - method/supervised
  - modality/text
  - task/generation
---

# Attention Is All You Need

## TL;DR

A sequence-to-sequence model built only from attention and feed-forward layers,
with recurrence and convolution deleted entirely. Removing the sequential
dependency is what makes the whole training run parallel across positions, so
the model reaches better translation quality in a fraction of the wall-clock
time of the recurrent systems it replaced. The lasting contribution is not the
translation result, it is that the architecture turned out to be task-agnostic:
almost everything I will build on descends from this block.

## Contributions

They **claim**:

1. An encoder-decoder architecture using only attention, with no recurrence and
   no convolution.
2. Multi-head scaled dot-product attention as the single reusable primitive,
   used in three roles: encoder self-attention, masked decoder self-attention,
   and encoder-decoder cross-attention.
3. State-of-the-art BLEU on WMT 2014 English-German and English-French at a
   small fraction of the training cost of the previous best models.
4. That the architecture generalises beyond translation, demonstrated on
   English constituency parsing.

They **demonstrate** 1, 2 and 3 convincingly. Claim 4 is demonstrated thinly:
one task, one section, and the parsing result is good rather than dominant. But
that thin section is the one that turned out to matter most, which is worth
remembering when judging what a paper "showed" versus what it started.

A fifth thing is claimed only in passing, in the visualisations: that attention
heads pick up syntactic and coreference structure. That is asserted from
pictures and never measured.

## Method

Encoder and decoder are each a stack of N = 6 identical layers, `d_model` = 512
throughout so residual connections type-check without projections.

**Scaled dot-product attention.** `Attention(Q, K, V) = softmax(QKᵀ / √d_k) V`.
The `√d_k` is not cosmetic: without it the dot products grow with dimension, the
softmax saturates, and the gradient through it vanishes. This is a
variance-control argument, the same one that governs weight initialisation.

**Multi-head attention.** Project `Q, K, V` into h = 8 subspaces of size
`d_k = d_v = d_model / h = 64`, run attention in each, concatenate, project
back. Same total cost as one full-width head, but the heads can attend to
different things at the same position.

**Encoder layer.** Multi-head self-attention, then a position-wise
feed-forward network (two linear layers with a ReLU between, inner width
`d_ff` = 2048, applied identically and independently at every position). Each
sublayer is wrapped as `LayerNorm(x + Sublayer(x))` — post-LN. That placement
is load-bearing and the paper does not say so; see Limitations.

**Decoder layer.** Three sublayers: masked self-attention (future positions set
to −∞ before the softmax, which is what preserves autoregression), then
cross-attention where queries come from the decoder and keys and values from
the encoder output, then the same feed-forward network. Cross-attention is the
only place the two sequences meet, and it is the mechanism every later
vision-language model reuses.

**Positions.** No recurrence means no positional information, so fixed
sinusoidal encodings of geometrically increasing wavelength are added to the
input embeddings. Learned positional embeddings were ablated and performed
essentially identically; sinusoids were kept on the argument that they might
extrapolate to longer sequences than seen in training.

**Training regime**, which matters as much as the architecture:

- Adam, β₁ = 0.9, β₂ = 0.98, with the warmup schedule
  `lr = d_model^-0.5 · min(step^-0.5, step · warmup^-1.5)`, warmup = 4000 steps.
  Learning rate rises linearly then decays with the inverse square root.
- Dropout 0.1 on every sublayer output and on the embedding-plus-position sum.
- Label smoothing 0.1, which the paper notes hurts perplexity and helps BLEU.
- Input embedding, output embedding and the pre-softmax projection share one
  weight matrix.
- Batches assembled by approximate sequence length, roughly 25,000 source and
  25,000 target tokens each.
- Reported BLEU comes from averaging the last checkpoints (5 for base, 20 for
  big) and beam search with beam 4, length penalty 0.6.

Base model 65M parameters, big model 213M. Both trained on 8 NVIDIA P100 GPUs:
base for 100,000 steps (about 12 hours), big for 300,000 steps (about 3.5 days).

The whiteboard version: two stacks of six blocks; each block is
`attention → add+norm → FFN → add+norm`; the decoder blocks have an extra
attention that reads the encoder; sinusoids added at the bottom; a learning-rate
warmup that you cannot remove.

## Datasets

- **WMT 2014 English-German**, about 4.5M sentence pairs, byte-pair encoding
  with a 37,000-token vocabulary shared between source and target.
- **WMT 2014 English-French**, about 36M sentence pairs, 32,000 word-piece
  vocabulary.
- **Penn Treebank WSJ** for the constituency-parsing experiment (about 40K
  training sentences), plus a larger semi-supervised corpus of roughly 17M
  sentences.

No dataset cards exist for these yet, so nothing is wikilinked here. A card is
owed before any of these is referenced from an experiment's frontmatter, and
none of the three is a dataset I expect to use, so writing the cards now would
be ceremony.

## Results

Translation, newstest2014, BLEU:

| Model | EN-DE | EN-FR |
|---|---|---|
| Previous best single models (GNMT+RL, ConvS2S, MoE) | roughly 24.6–26.0 | roughly 39–41 |
| Previous best ensembles | 26.36 | roughly 41.2 |
| Transformer (base, 65M) | 27.3 | — |
| Transformer (big, 213M) | **28.4** | **41.8** |

So the big model beats the previous best *ensemble* on EN-DE by about 2 BLEU,
and the 65M base model beats it by roughly 1 BLEU while training for twelve
hours. The cost argument is the stronger half of the result: the paper puts the
big model at around 2.3 × 10¹⁹ training FLOPs, an order of magnitude below the
models it beats.

Note for citation hygiene: the EN-FR big-model figure moved between arXiv
versions (the first version reports a slightly lower number, around 41.0). Check
the edition you cite rather than trusting a number copied from a blog post.

Ablations (their Table 3), the useful part:

- Single-head attention is about 0.9 BLEU worse than the 8-head setting;
  32 heads is also worse. There is an interior optimum, and it is not argued
  for, only measured.
- Reducing `d_k` hurts, which they read as evidence that dot-product
  compatibility is too crude a similarity function.
- Bigger is better, dropout is necessary, learned positional embeddings ≈
  sinusoidal.

Constituency parsing, WSJ section 23 F1: about 91.3 training on WSJ only, about
92.7 with the semi-supervised corpus. Competitive with, not better than, the
best task-specific parsers of the time, from a four-layer model with almost no
tuning.

**The comparison they did not run.** There is no controlled architecture
comparison. Every recurrent and convolutional baseline in Table 2 is a number
lifted from another paper, trained by other people under other budgets with
other regularisation. The Transformer's numbers come bundled with warmup, label
smoothing, shared embeddings, checkpoint averaging and a shared BPE vocabulary.
Nothing in the paper separates "attention is better than recurrence" from "this
training recipe is better than the 2016 training recipe". A single LSTM trained
with the identical recipe and budget would have settled it, and it is absent.
That absence has been quietly inherited by the entire literature that cites this
as proof that attention beats recurrence.

## Limitations

Admitted:

- Only two language pairs, both high-resource.
- Extending to modalities other than text, and to long inputs, is named as
  future work rather than shown.

Not admitted, and more interesting:

- **Quadratic cost is presented as an advantage.** Their complexity table
  compares `O(n²·d)` self-attention against `O(n·d²)` recurrence and observes
  self-attention wins when `n < d`. For 25-token sentences with `d_model` = 512
  that is true. For a 3D volume, a whole-slide image or a long document it is
  false, and the entire efficient-attention literature exists because of a cost
  this paper frames as a selling point.
- **Post-LN needs the warmup schedule to train at all.** The warmup is
  presented as a hyperparameter. It is closer to a structural requirement: with
  LayerNorm after the residual addition, removing warmup makes these models
  diverge routinely. Pre-LN was the later fix. Someone reading this paper as the
  specification will build something that will not train and will not know why.
- **The interpretability claim is decorative.** Attention maps that "appear to
  relate to syntactic structure" is an eyeball result over hand-picked heads. It
  should be read as a hypothesis, and the later literature on whether attention
  weights explain anything is largely a reaction to how confidently this kind of
  figure was received.
- **BLEU only.** No human evaluation, on a task where BLEU is a known-weak
  proxy and a 1-point difference is not obviously perceptible.

## Threats to validity

- **Single runs.** No seed variance is reported anywhere. Every headline number
  is n = 1, and a 0.5 BLEU gap is inside the range seeds move on WMT.
- **Unequal tuning.** The baselines were tuned by their own authors for their
  own architectures; the Transformer was tuned here. That asymmetry always
  favours the new model, and there is no way to size it from the paper.
- **Checkpoint averaging** is folded into the reported numbers and is a
  variance-reduction trick available to the baselines too.
- **Test set.** newstest2014 is a standard held-out set and there is no sign it
  was touched, but the ablations in Table 3 are reported on the *development*
  set, which is the correct choice and worth copying.

## Reproducibility

- **Code available:** yes — `tensorflow/tensor2tensor` shipped the architecture
  and the exact training configs. It is now archived and pinned to old
  TensorFlow, so running it as-is in 2026 is an environment archaeology
  exercise; there are many faithful modern reimplementations.
- **Weights available:** I could not confirm that the specific checkpoints
  behind Table 2 are still retrievable. Pretrained tensor2tensor translation
  models were published, but I have not verified they are the paper's.
- **Compute reported:** unusually well. 8 P100s, 12 hours for base and 3.5 days
  for big, plus FLOP estimates for every model in the comparison table. This
  transparency is a large part of why the cost argument lands.
- **Would I be able to reproduce this?** The base model, plausibly. Twelve hours
  on 8 P100s is roughly a few days on one modern consumer GPU with mixed
  precision, and the architecture is a few hundred lines. The real cost is WMT14
  preprocessing and BPE, which is where reproduction attempts actually die. The
  big model is out of reach and not worth reaching for.

## Questions

- The complexity table's `n < d` condition is the hinge. At what sequence length
  does dense attention actually lose to a linear-attention or state-space
  alternative *on the hardware I have*, once constant factors and memory
  bandwidth are included rather than asymptotics? This is measurable in a day
  and I have never seen the crossover reported for 3D medical volumes.
- Is the warmup requirement a property of post-LN residual placement, or of the
  softmax's sensitivity to initialisation scale? Pre-LN answers part of it. What
  is the equivalent statement for *cross*-attention, where the two streams have
  different scales and different training histories?
- Cross-attention is a single stack operating at one resolution. U-Net's skip
  connections say that dense prediction on images needs alignment at several
  resolutions. Does joining a 3D volume to a free-text report need multi-scale
  cross-attention, or is one bottleneck-level join sufficient?
- The sinusoidal-versus-learned ablation shows position encoding barely matters
  at 25 tokens. Does that survive in a domain where absolute position is
  physically meaningful — slice index, voxel spacing, laterality — or does the
  finding silently assume position is only relative?
- What would it take to falsify the attention-as-explanation claim in a clinical
  setting, where "the model attended to the lesion" is a statement a radiologist
  can actually disagree with? A protocol for that is a paper in itself and I
  have not found one I believe.

## Source and attribution

- **Paper:** Attention Is All You Need
- **Authors:** Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin
- **Published in:** Advances in Neural Information Processing Systems (NIPS), 2017
- **arXiv:** [arXiv:1706.03762](https://arxiv.org/abs/1706.03762)

The summary above is my own words, written from reading the paper. It is not the authors' abstract, it is not a translation of one, and no figure, table or passage of the original is reproduced here. Credit for the work belongs to the authors listed above; go and read them.

Citekey `vaswani2017attention`. Prose here is CC BY 4.0 and the code in this repository is MIT; [`COPYRIGHT.md`](../../COPYRIGHT.md) is the authoritative path-to-licence map, and the `summaries/LICENSE` marker repeats it for this directory.
