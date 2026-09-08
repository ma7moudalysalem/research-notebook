---
citekey: radford2021clip
title: Learning Transferable Visual Models From Natural Language Supervision
authors:
  - Alec Radford
  - Jong Wook Kim
  - Chris Hallacy
  - Aditya Ramesh
  - Gabriel Goh
  - Sandhini Agarwal
  - Girish Sastry
  - Amanda Askell
  - Pamela Mishkin
  - Jack Clark
  - Gretchen Krueger
  - Ilya Sutskever
year: 2021
venue: ICML
venue_type: conference
arxiv: '2103.00020'
url: https://arxiv.org/abs/2103.00020v1
tracks:
  - T04
tags:
  - arch/transformer
  - arch/vit
  - data/large-scale
  - domain/multimodal
  - meta/seminal
  - method/contrastive
  - method/transfer-learning
  - modality/image
  - modality/text
  - task/classification
  - task/representation-learning
  - task/retrieval
---

# Learning Transferable Visual Models From Natural Language Supervision

<!-- READING PROTOCOL. Three passes, after Keshav, *How to Read a Paper*
     (ACM SIGCOMM CCR 37(3), 2007). Pass 1 is five minutes: title, abstract,
     headings, conclusions - enough to decide whether to continue. Pass 2 is an
     hour: figures, tables, and the argument, skipping proofs. Pass 3 is a
     re-implementation in your head, questioning every assumption.

     Fill the sections as the passes happen. `status: read` is only legal once
     TL;DR, Method, Results, Limitations and Questions are all genuinely
     written (RD13) - the checker enforces it, and "TODO" does not count.

     This is an HTML comment rather than a blockquote on purpose: it is
     instruction to the author, not content. As a blockquote it counted as an
     87-word quotation and made every single promotion refuse. -->

## TL;DR

Train an image encoder and a text encoder jointly, on 400 million image-text
pairs scraped from the web, with nothing but a contrastive objective that asks
which caption goes with which image inside a batch. At test time you build a
classifier by *writing down the class names as sentences*, so the label set is
chosen at inference rather than baked into the weights. The headline is that
this matches a supervised ImageNet ResNet-50 on ImageNet without touching its
1.28M labels; the more useful finding, for me, is precisely where it fails.

## Why I am reading this

Because if the thesis goes anywhere near medical vision-language — scans paired
with radiology reports — this is the paper everything is measured against, and
every medical variant (ConVIRT, GLoRIA, BioViL, MedCLIP, BiomedCLIP) is a
reaction to it. Two specific things I wanted: the actual failure profile on
specialised imagery, because that is the honest prior for a medical
application; and the data-scale numbers, because "400 million pairs" and "a
hospital's report archive" are not the same order of magnitude and I need to
know how the method degrades between them.

A detail worth carrying: the paper names ConVIRT (Zhang et al., a chest X-ray
image-text contrastive method) as its closest prior work and describes its own
approach as a simplified version of it trained from scratch. The medical version
came *first*. That reframes the medical literature from "applying CLIP to
medicine" to "CLIP is the scaled-up version of a medical idea", which is a much
better sentence to have in a proposal.

## Contributions

They **claim**:

1. Natural language supervision at web scale is a viable replacement for
   curated labels for learning general visual representations.
2. A contrastive objective is dramatically more compute-efficient than
   predicting the caption text, which is what makes the scale affordable.
3. Zero-shot transfer via prompted text classifiers is competitive with fully
   supervised baselines across a broad 27-dataset suite.
4. The resulting models are substantially more robust to natural distribution
   shift than ImageNet-supervised models of equal ImageNet accuracy.
5. A broad study of scaling, few-shot behaviour, data overlap, and the social
   biases the approach inherits.

**Demonstrated well:** 3, 4 and 5. The evaluation is unusually thorough and the
robustness result is the most surprising and best-supported claim in the paper.

**Demonstrated weakly:** 2. The efficiency comparison (bag-of-words prediction
roughly 3× more efficient than transformer caption prediction; contrastive
roughly 4× more efficient again) is measured at small scale, early in training,
with a ResNet-50 image tower. It is then used to justify a design decision at
1000× that scale. That extrapolation is never checked.

**Not separable at all:** 1. The objective and the 400M-pair private dataset were
introduced together and are never varied independently, so "language supervision
works" and "this particular web corpus works" cannot be told apart from anything
in the paper. See Limitations.

## Method

Two towers, one loss, one inference trick.

**The data.** WIT (WebImageText): 400 million image-text pairs. Built by
searching for roughly 500,000 queries, with up to 20,000 pairs per query to keep
it approximately class-balanced. The query list and the corpus are not released,
and this is the single most consequential fact in the paper.

**Image encoder.** Two families, trained separately. ResNets with the usual
modernisations plus attention pooling in place of global average pooling
(RN50, RN101, and RN50x4/x16/x64 scaled EfficientNet-style in width, depth and
resolution together), and Vision Transformers (ViT-B/32, ViT-B/16, ViT-L/14),
i.e. dosovitskiy2021vit as-is. ViT-L/14 was additionally fine-tuned for one
epoch at 336px, and that `ViT-L/14@336px` model produces the headline numbers.

**Text encoder.** A 12-layer, 512-wide, 8-head causal Transformer, about 63M
parameters — vaswani2017attention's decoder stack with the cross-attention
removed. Lower-cased BPE, 49,152-token vocabulary, sequences capped at 76 tokens
between `[SOS]` and `[EOS]`. The representation is the activation at `[EOS]` in
the top layer, layer-normalised and linearly projected.

**The loss.** Both towers project into a shared embedding space; embeddings are
L2-normalised. For a batch of N pairs, compute the N×N matrix of cosine
similarities, multiply by a learned temperature, and apply cross-entropy along
both axes — image-to-text and text-to-image — averaged. The N matched pairs are
positives, the N²−N mismatched pairs are negatives. The temperature is learned
directly as a log-parameterised scalar and clipped so the logits cannot be
scaled past 100, which is a stability guard rather than a modelling choice.

The batch **is** the loss. Batch size 32,768, because the difficulty of the task
and therefore the quality of the signal is set by how many negatives you have.

**Training.** 32 epochs over the 400M pairs. Adam with decoupled weight decay, a
cosine learning-rate schedule, mixed precision. RN50x64 took 18 days on 592 V100
GPUs; ViT-L/14 took 12 days on 256 V100s.

**Zero-shot inference.** Embed every class name inside a prompt template ("a
photo of a {label}", plus per-dataset variants), take the cosine similarity to
the image embedding, softmax. Prompt engineering and ensembling roughly 80
templates buys close to 5 points of ImageNet accuracy over bare class names.
That is the size of many published state-of-the-art increments, and it is
entirely hand-work at inference time.

The whiteboard version: two encoders, one dot-product matrix, a diagonal you
push up and everything else you push down; at test time you swap the training
captions for the class names you happen to care about.

## Datasets

- **WIT / WebImageText** — 400M image-text pairs, proprietary, never released.
  No card is possible; there is nothing to verify.
- **The 27-dataset transfer suite** — ImageNet and variants, plus a wide range
  of fine-grained and specialised sets. The ones that matter to me are
  **PatchCamelyon** (histopathology, lymph-node metastasis), **MNIST**,
  **EuroSAT**, **GTSRB** and **KITTI distance**, because they are where it
  breaks.
- **Distribution-shift family** — ImageNetV2, ImageNet-R, ImageNet-A,
  ImageNet Sketch, ObjectNet, ImageNet-Vid, YouTube-BB.

No dataset cards are written yet and none is wikilinked here. Under RD24 a card
is owed before any of these is named in an experiment's frontmatter;
PatchCamelyon is the one I actually expect to need, so it is the one to write
first.

## Results

**Zero-shot ImageNet.** `ViT-L/14@336px` reaches about **76.2% top-1** with zero
labelled ImageNet examples, matching the original supervised ResNet-50 (about
76.1%) which saw all 1.28M of them. That is the number everyone quotes, and it
is a fair one.

**Against a supervised linear probe.** Zero-shot CLIP matches or beats a fully
supervised linear classifier fitted on ResNet-50 features on **16 of the 27**
evaluation datasets. Note what the baseline is: a linear probe on a frozen
ImageNet ResNet-50, not a fine-tuned task-specific model. It is a reasonable
baseline, not a strong one.

**Robustness.** This is the strongest result. ImageNet-supervised models lose far
more accuracy under natural distribution shift than their ImageNet accuracy
predicts. Zero-shot CLIP closes up to about **75%** of that effective-robustness
gap. Crucially, the gain largely disappears when CLIP is adapted to ImageNet
with a supervised linear probe: fitting the target distribution buys ImageNet
accuracy and gives back the robustness. That trade is the most transferable
lesson in the paper.

**Where it fails, which is the part I care about.** Zero-shot performance is at
or near chance on several specialised tasks. **PatchCamelyon** — tumour
detection in histopathology patches — is essentially chance. MNIST is around
88%, worse than logistic regression on raw pixels, on a dataset a first-year
student solves. Counting, and KITTI distance-to-nearest-car, are near chance.
The pattern is consistent: tasks whose concepts are not the kind of thing web
captions describe, and images unlike anything on the web.

**Few-shot.** Zero-shot CLIP is roughly equal to a **4-shot** linear probe *on
its own features*. The authors flag this as counter-intuitive, and they are
right: a human goes from zero to one example with an enormous jump, and this
model's own representation needs four labelled examples per class to catch up
with what its text encoder already knew. That gap is a research programme, not a
footnote.

**Scaling.** Zero-shot performance scales smoothly with training compute across
a roughly 44× range, though individual datasets are noisy. The smooth aggregate
plus the noisy per-dataset behaviour is exactly why a single-dataset result from
any of these models should be distrusted.

**The comparisons they did not run.**

1. **The objective, held at fixed data.** Nobody has ever seen the contrastive
   objective and a caption-prediction objective compared at full scale on the
   same 400M pairs. The efficiency claim rests on a small-scale proxy.
2. **The data, held at fixed objective.** Because WIT is not released, the
   contribution of the corpus cannot be separated from the contribution of the
   method. LAION later made a version of this experiment possible from outside;
   the paper itself makes it impossible.
3. **A supervised control at matched compute.** There is no
   "train the same ViT supervised on as many labelled images as this compute
   could buy" line anywhere.
4. **Prompt sensitivity as a distribution.** Prompt engineering is reported as a
   gain, never as a variance. No spread over prompt wordings is given, which is
   the number a downstream user actually needs.

## Limitations

Admitted, and admitted well — the limitations section here is better than most:

- Zero-shot CLIP sits around ResNet-50 level, not overall state of the art, and
  they estimate roughly **1000× more compute** would be needed to close that
  with this recipe. They call that infeasible, which it is.
- Weak on fine-grained discrimination, abstract and systematic tasks (counting),
  and genuinely out-of-distribution imagery.
- Zero-shot is limited to concepts you can name in the label set; the model
  cannot generate a description.
- Poor data efficiency: 32 epochs over 400M pairs is roughly 12.8 billion image
  presentations.
- Social bias inherited from web text, with a FairFace analysis showing
  demographically skewed misclassification, and an explicit discussion of
  surveillance uses.
- They used full validation sets to guide design choices, including prompt
  engineering, which is a form of test-set adaptation.

Not admitted, or under-weighted:

- **"Zero-shot" is a claim about labels, not about concepts.** The overlap
  analysis is pixel-level near-duplicate detection. It says the *images* were
  not in the training set. It cannot say the *concepts and their captions* were
  absent, and for a 400M-pair web corpus they almost certainly were present. The
  honest framing is "no task-specific labels", not "no exposure".
- **The robustness result is measured on one family of shifts.** All of them are
  ImageNet-derived. A scanner-vendor change, a stain-protocol change or a
  paediatric-versus-adult cohort shift is a different kind of shift, and nothing
  in this paper licenses transferring the conclusion there. I expect this
  inference to be made constantly in medical papers citing it, and it is not
  supported.
- **The headline framing hides per-task human labour.** Every zero-shot number
  requires someone to write the label set, choose a prompt template, and
  ensemble 80 of them. Calling that "no training data" is true and misleading in
  the same breath.
- **Irreproducibility is treated as a fact of life rather than a scientific
  problem.** A central claim that only a handful of organisations can check is a
  weaker claim, and the paper does not say so.
- **Every number is n = 1.** A 12-day 256-GPU run is not repeated with another
  seed, so no variance is available for any headline result.

## Threats to validity

- **Test-set adaptation.** Admitted: validation sets guided prompt design and
  hyperparameters. The reported zero-shot numbers are therefore not
  distribution-free estimates, they are lightly tuned ones.
- **Overlap analysis is model-based.** Near-duplicate detection uses a learned
  detector with its own error profile, and it only addresses pixels.
- **Evaluation-suite selection.** The 27-dataset suite was assembled by the
  authors and partly grew during the project. A suite chosen alongside the
  method is not an independent test of it.
- **Protocol favours the candidate.** Linear probing on frozen features is the
  evaluation CLIP's representation is best suited to, and it disadvantages
  baselines whose value is realised through fine-tuning.
- **Seeds.** None. At this compute, error bars are unaffordable, which is a real
  constraint and also a real limitation on how much any single gap means.

## Reproducibility

- **Code available:** partially — `github.com/openai/CLIP` publishes model
  definitions, the tokeniser and inference code. **Training code was not
  released.** OpenCLIP (LAION) is the community reimplementation and is what I
  would actually use.
- **Weights available:** yes, and generously — RN50, RN101, RN50x4/x16/x64,
  ViT-B/32, ViT-B/16, ViT-L/14 and ViT-L/14@336px. This is why the paper had the
  impact it did: the artefact was usable the week it appeared.
- **Compute reported:** yes, and precisely. 592 V100s for 18 days (RN50x64), 256
  V100s for 12 days (ViT-L/14). Honest, and the honesty is what makes the
  1000×-more-compute admission credible.
- **Would I be able to reproduce this?** The claims split cleanly in two.
  *Pretraining:* no, and neither can anyone outside a handful of labs — the data
  is private and the compute is six figures. *Everything downstream:* yes, on
  one GPU. Zero-shot evaluation, linear probes, prompt-sensitivity studies and
  the few-shot crossover are all reproducible from released weights in hours,
  and the prompt-variance measurement the paper skipped is a weekend of work.
  That split is worth being explicit about, because "I cannot reproduce CLIP" is
  usually a statement about pretraining being used to excuse not checking the
  transfer claims, which are checkable.

## Questions

- Zero-shot CLIP is at chance on PatchCamelyon. Is that a **concept** failure
  (web captions never describe a micrometastasis, so the text tower has no
  representation to match) or an **encoder** failure (the image tower has never
  seen a 96×96 H&E patch)? The two hypotheses predict different fixes — paired
  report data versus domain-adapted visual pretraining — and they are separable
  by holding one tower frozen at a time. This is the first experiment I would
  run.
- Contrastive image-text pretraining wants 400M pairs. A large hospital archive
  is order 10⁵–10⁶ studies. **Where is the crossover** below which contrastive
  language supervision loses to plain supervised pretraining on the same images,
  and does prompt ensembling or report-sentence sampling move it?
- The temperature is one global learned scalar, and the loss assumes every
  off-diagonal pair is a true negative. In a medical batch, many "negatives" are
  other normal scans that are genuinely near-identical in the relevant sense.
  How large is that false-negative rate in practice, and does it need a soft
  target, a sampling strategy, or a report-similarity-aware denominator?
- What is the medical-imaging analogue of the effective-robustness measurement,
  built on scanner, site and protocol shift rather than the ImageNet shift
  family? And does image-text pretraining buy any of it, or was CLIP's
  robustness a property of WIT's breadth that no clinical corpus will have?
- Prompt wording moves ImageNet accuracy by several points. In a clinical
  deployment, who writes the prompt, and is the **variance across clinically
  reasonable phrasings** a safety-relevant quantity rather than an engineering
  annoyance? I have not found this measured for any medical VLM, and it is
  cheap to measure.

## Interesting ideas

- The deepest idea is an inversion: this is a **retrieval** system trained on a
  retrieval loss and then reinterpreted as a classifier by writing the class
  names as queries. The classifier is *constructed at inference from text*. That
  decouples the label space from the weights, and it transfers to any domain
  where paired free text exists — which is exactly what a radiology archive is.
- Their reason for choosing the contrastive loss is pragmatic and worth
  generalising: predicting exact caption words wastes capacity modelling
  phrasing you do not care about. The move is "weaken the objective until it
  asks only for the information you need". A radiology report is largely
  boilerplate; the same argument applies with more force there.
- The robustness-then-lost-on-adaptation result is a clean statement of a
  general trade: fitting the target distribution buys in-distribution accuracy
  and spends out-of-distribution robustness. If that holds for medical
  fine-tuning it is directly a thesis-shaped question.
- Zero-shot equalling a 4-shot probe on its own features is a cheap, portable
  diagnostic. Running that same crossover on a medical encoder tells me how much
  the text tower actually knows, in one afternoon.

## Relation to my work

This is the closest paper to a thesis I have read so far, which is why it is
rated 5. Coming from medical imaging, the useful reading is not "CLIP works" but
"CLIP tells me exactly which part of the medical problem is hard": the
concept-coverage gap on specialised imagery, not the architecture.

Concretely, it changes what I do next in three ways.

1. **Read ConVIRT and BioViL next**, in that order, because CLIP names ConVIRT
   as its ancestor and the medical line is therefore the main line, not a
   derivative one. That reordering matters for how a proposal is framed.
2. **Run the cheap experiment before committing to a direction.** Zero-shot CLIP
   and an open medical CLIP variant on a public chest X-ray or histopathology
   benchmark, from released weights, on one GPU. The result decides whether the
   thesis-shaped gap is *data scale* or *domain*, and I should not write a
   proposal that assumes one without measuring.
3. **Stop treating the robustness claim as transferable.** If I cite it, cite it
   as measured on ImageNet-family shift, and say so. The temptation to write
   "CLIP-style pretraining is robust to distribution shift" in a medical
   introduction is strong and would be a claim the source does not support.

Not yet `publish: candidate` — that is a Monday-review decision (RD27), and this
note wants a second pass on the results table first. It is the obvious first
candidate when it comes.

## Concept notes extracted

- zero-shot-is-a-claim-about-labels-not-about-exposure — the distinction the
  overlap analysis cannot address, and the one that decides how much "zero-shot"
  should impress me.
- adapting-to-a-target-distribution-spends-out-of-distribution-robustness —
  CLIP's clean demonstration of a trade that should govern how I fine-tune.
- the-contrastive-batch-is-the-loss — why batch size is an architectural
  decision here, and what that implies when negatives are not truly negative.
- prompt-engineering-is-uncounted-supervision — roughly five ImageNet points
  of hand-work reported as a gain rather than as a cost.

## Implementation notes

Only relevant if I run the transfer experiments above, which I intend to.

- Use **OpenCLIP**, not the OpenAI repo, for anything involving training or
  fine-tuning. The original release has no training code.
- Normalise both embeddings before the dot product, and remember the temperature
  is *learned and exponentiated*. Reimplementations that treat it as a fixed
  hyperparameter get systematically different results and the difference is
  quiet.
- The batch is a global batch. Reproducing contrastive behaviour on one GPU
  needs gradient accumulation with cached features or a memory bank, and neither
  is equivalent to a true 32,768 batch. Any small-batch result I get is a
  different experiment and must be labelled as one.
- Preprocessing is not incidental: the released models expect their own
  normalisation constants and centre-crop resolution, and `@336px` is a
  different model, not a resize. Medical images at 16-bit dynamic range have to
  be windowed to 8-bit RGB before they are even admissible, and that windowing
  choice is a hyperparameter nobody reports.
- Zero-shot evaluation needs the prompt set recorded alongside the number.
  A CLIP zero-shot result without its prompts is not reproducible, including by
  me, six months later.

## Source and attribution

- **Paper:** Learning Transferable Visual Models From Natural Language Supervision
- **Authors:** Alec Radford, Jong Wook Kim, Chris Hallacy, Aditya Ramesh, Gabriel Goh, Sandhini Agarwal, Girish Sastry, Amanda Askell, Pamela Mishkin, Jack Clark, Gretchen Krueger, Ilya Sutskever
- **Published in:** International Conference on Machine Learning (ICML), 2021
- **arXiv:** [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)

The summary above is my own words, written from reading the paper. It is not the authors' abstract, it is not a translation of one, and no figure, table or passage of the original is reproduced here. Credit for the work belongs to the authors listed above; go and read them.

Citekey `radford2021clip`. Prose in this directory is CC BY 4.0; see `LICENSE` beside this file.
