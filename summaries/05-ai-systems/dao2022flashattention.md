---
citekey: dao2022flashattention
title: 'FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness'
authors:
  - Tri Dao
  - Daniel Y. Fu
  - Stefano Ermon
  - Atri Rudra
  - Christopher Ré
year: 2022
venue: NeurIPS
venue_type: conference
arxiv: '2205.14135'
url: https://arxiv.org/abs/2205.14135
tracks:
  - T05
tags:
  - domain/ai-systems
  - arch/transformer
  - meta/seminal
---

# FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness

## TL;DR

Attention on a GPU is not slow because it does too much arithmetic. It is slow
because it writes an N×N score matrix out to HBM and reads it back several
times, and HBM is roughly two orders of magnitude slower than the on-chip SRAM
where the arithmetic actually happens. FlashAttention stops that matrix from
ever existing in HBM: it tiles Q, K and V into blocks that fit in SRAM, computes
softmax incrementally from running maximum and sum statistics, and recomputes
scores in the backward pass instead of storing them. Nothing is approximated,
and attention memory drops from quadratic to linear in sequence length.

## Contributions

Four claims. Three and a half are demonstrated.

1. **An IO-aware exact attention algorithm.** Tiling plus recomputation, so the
   N×N score matrix is never materialised in HBM. Demonstrated, and the
   exactness claim is structural rather than empirical, which is the strongest
   form it could take.
2. **An IO-complexity analysis with a matching lower bound.** The algorithm uses
   O(N²d²/M) HBM accesses against Θ(Nd + N²) for a standard implementation,
   where M is the SRAM size, and they argue no exact attention algorithm can do
   asymptotically better across all values of M. Demonstrated as analysis. The
   constant factors that decide real performance sit outside it.
3. **Wall-clock and memory wins on real training runs**, not microbenchmarks.
   Demonstrated.
4. **"New capabilities": longer context yields better models.** This is the
   half. Longer context does help, but the causal chain runs kernel → affordable
   context → better model, and the paper's own comparisons cannot separate the
   second arrow from the first. See Results.

## Method

Two ideas, each old on its own. The contribution is that they compose with no
accuracy cost.

**The memory hierarchy is the object of study.** On an A100 40GB, HBM is 40 GB at
roughly 1.5–2.0 TB/s while on-chip SRAM totals about 20 MB across 108 SMs at
roughly 19 TB/s. Standard attention does: read Q,K, write S = QKᵀ, read S, write
P = softmax(S), read P,V, write O. Every one of those N×N round trips is HBM
traffic, and softmax, masking and dropout are pointwise operations that are
entirely bandwidth-bound.

**Tiling.** Split Q into blocks of B_r rows and K,V into blocks of B_c columns,
sized so that a Q block, a K block, a V block and the B_r×B_c score tile fit in
SRAM simultaneously. Outer loop over K,V blocks, inner loop over Q blocks. For
each pair, load into SRAM, form the score tile there, update the output
accumulator in place, and never write the tile back.

**Online softmax is what makes tiling legal.** Softmax is not naively
decomposable because the normaliser spans a whole row. So carry two per-row
statistics beside the output accumulator: m, the running maximum, and ℓ, the
running sum of exponentials. When a new tile arrives with its own local m' and
ℓ', rescale the accumulated output by exp(m_old − m_new) and fold in the new
block. This is the Milakov and Gimelshein online-softmax trick applied one level
up, exact in real arithmetic, and the running maximum is also what stops the
exponentials overflowing in fp16.

**Recomputation replaces storage in the backward pass.** The backward pass needs
P = softmax(S). Rather than keeping the N×N matrix from the forward pass, keep
only O, m and ℓ, all O(N), and recompute each score tile in SRAM when its
gradient is needed. That trades extra FLOPs for eliminated HBM traffic, which is
the right trade exactly because the kernel is bandwidth-bound. It is also why
the backward pass is the harder engineering problem, and where v1 leaves the
most performance on the table.

**It is one fused CUDA kernel.** Not a graph of PyTorch ops, not a compiler pass.
That is the source of both the performance and the main limitation.

**Block-sparse FlashAttention** is the same machinery under a block mask, so
whole tiles are skipped rather than computed and then masked. IO cost falls with
the sparsity fraction, and this is the variant that reaches 64K.

## Datasets

None of these have a card under `datasets/` yet. The directory does not exist in
this workspace, so RD24's "every dataset reference resolves to a card" is not
satisfiable today, and I have deliberately not written a `datasets:` frontmatter
key that would dangle. What the paper uses:

- **OpenWebText** for the GPT-2 training runs.
- **Wikipedia + BookCorpus** for BERT-large, MLPerf-style.
- **Long Range Arena** (ListOps, Text, Retrieval, Image, Pathfinder, Path-X) for
  the long-sequence benchmarks, plus **Path-256** at 64K.
- **MIMIC-III** and **ECtHR** for long-document classification.

MIMIC-III is the one that matters to me and the one with teeth: PhysioNet
credentialed access under a signed DUA, which under RD24 means a card with
`access: credentialed` and `redistribution: forbidden` before any experiment of
mine may reference it. Worth noticing that the paper's only clinical evidence
sits on the dataset a card would gate hardest.

## Results

Headline numbers, each against the baseline the authors themselves name:

| Claim | Baseline | Margin |
|---|---|---|
| BERT-large training, seq 512 | MLPerf 1.1 training speed record | **15%** end-to-end wall-clock |
| GPT-2 training, seq 1K | HuggingFace implementation | **3×** |
| Long Range Arena, seq 1K–4K | standard attention | **2.4×** |
| GPT-2 perplexity, 4K context | the same model at 1K context | **0.7** better perplexity |
| Long-document classification | shorter-context baseline | **6.4** points |

Two capability results are not speedups at all: the first Transformers to beat
chance on **Path-X** at 16K (**61.4%**) and on **Path-256** at 64K (**63.1%**).
Those are the numbers I would quote to someone who thinks this is only an
engineering paper. Attention memory goes from quadratic to linear in N, which in
practice is the order-of-magnitude saving that decides whether a model fits at
all.

Against Megatron-LM's already-fused kernels the GPT-2 margin is much smaller
than against HuggingFace. I did not record the exact ratio and will not invent
one. The qualitative point stands and matters: the 3× headline is measured
against an unfused baseline, and a well-engineered baseline closes a large part
of the gap.

**The comparison they did not run.** The 0.7 perplexity gain compares
FlashAttention at 4K context against a baseline at 1K context. That measures
what longer context buys, not what the kernel buys, and the honest control is
missing: 4K context with standard attention, however slow, on a smaller model or
fewer steps. Exactness is argued analytically so the two should agree, but
"agrees in real arithmetic" and "agrees in fp16 under a different summation
order" are different statements, and this is the one experiment that would have
closed the gap. I also did not find an ablation separating the contribution of
tiling from that of recomputation, which is what a reader needs in order to
predict how much of the win survives on hardware with a different SRAM-to-HBM
ratio.

## Limitations

**Admitted.** The kernel is hand-written CUDA, and a new attention variant means
a new kernel written by someone who can write kernels. They are explicit that
this should be compiled from a higher-level language rather than typed, and that
no such compiler exists. The IO analysis is also single-GPU: multi-node
communication is a different level of the hierarchy and is left open.

**Not admitted, and worth holding onto.**

- The whole win is conditional on being memory-bandwidth-bound. Recomputation
  in the backward pass costs extra FLOPs, so in a compute-bound regime — short
  sequences, small batches, or newer hardware where the arithmetic-to-bandwidth
  ratio has shifted — the trade goes the other way. The paper presents the
  result as a general property of attention rather than as a property of a
  regime.
- The asymptotics assume the tiles fit in SRAM, which quietly bounds the head
  dimension. The original kernel supports head dims up to 128, and the O(N²d²/M)
  expression stops being the interesting term when d grows.
- The baselines vary enormously in engineering quality. Three times faster than
  HuggingFace's unfused PyTorch is a much weaker statement than fifteen percent
  faster than an MLPerf record, and the abstract presents them in the same list.
- "Exact" means "not an approximation of attention", not "bitwise identical".
  Tiled online softmax in fp16 sums in a different order, so outputs differ in
  the last bits. That is almost certainly harmless and it is not the same claim
  a reader hears.
- Hindsight, but load-bearing: FlashAttention-2 (Dao, 2023) exists because v1
  leaves a great deal of the A100's peak throughput unused, mostly through how
  work is partitioned between warps. The v1 kernel is far from the hardware
  ceiling it argues about, which does not weaken the IO argument but does mean
  the reported speedups are not the ceiling either.

## Threats to validity

Every measurement is wall-clock on one GPU generation, and every constant in the
argument — block sizes, occupancy, the SRAM budget M itself — is A100-specific.
The paper does not report what happens on a card with a materially different M,
which is exactly the card a student owns. Seeds are not the issue here: the
quality numbers ride on single training runs because a second GPT-2 run is
expensive, so the 0.7 perplexity delta carries no variance estimate. The speed
results are robust in a way the quality results are not, and the paper's framing
does not separate them.

## Reproducibility

- **Code available:** yes, <https://github.com/Dao-AILab/flash-attention>
  (published under the HazyResearch organisation at the time of the paper). The
  repository carries the BERT and GPT-2 training scripts, not only the kernel.
- **Weights available:** not the point of the paper, and I found no released
  checkpoints for the trained models. The artefact everyone reuses is the
  kernel, which long ago landed inside PyTorch behind
  `torch.nn.functional.scaled_dot_product_attention`.
- **Compute reported:** A100 40GB throughout, with wall-clock training times
  rather than GPU-hours. Multi-GPU runs are on a single node. I did not record
  the exact GPU count and will not guess it.
- **Would I be able to reproduce this?** The kernel, no. Writing and debugging
  CUDA of that quality is months of work in a skill I do not have, and the paper
  is candid that this is hand-written rather than generated. The benchmarks,
  yes, and cheaply: runtime and peak memory for attention at 512 / 1K / 2K / 4K
  against a deliberately unfused PyTorch implementation on one consumer GPU is
  an afternoon. That is the right first T05 experiment, because it turns the
  memory-bound claim into something I have measured rather than read.

## Questions

- The IO analysis has exactly one interesting boundary, SRAM against HBM. For a
  3D medical volume the binding boundary is often host-to-device, because a 512³
  volume does not fit in HBM at all. Does the same accounting yield a useful
  algorithm when the level that matters is PCIe, or does the argument collapse
  because the bandwidth ratio is nothing like 100:1?
- Sequence length here comes from tokens with causal structure. Over a patch
  grid on a volume, locality is spatial and three-dimensional. What is the right
  block shape when neighbours in the attention matrix are not neighbours in the
  sequence, and does block-sparse FlashAttention under a 3D-locality mask beat a
  sliding-window design at equal wall-clock rather than at equal FLOPs?
- Now that full-resolution attention is affordable on one card, is longer context
  the best use of that memory budget in a small-data medical regime, or would the
  same bytes buy more as larger batches and heavier augmentation? I have not
  found anyone running that trade-off explicitly, and it is cheap to run.
- Does IO-awareness as a method pay anywhere else in a medical pipeline? DICOM
  decode, resampling and patch extraction are all bandwidth-bound and none has
  had this quality of treatment. Is attention the real bottleneck, or the
  bottleneck that was fashionable enough to attract this engineering?
- Exactness here means "not an approximation of attention", not "bitwise
  identical to the unfused kernel". At 16K in fp16, how large is the numerical
  divergence in practice, and is there a task where it changes a decision?

## Source and attribution

- **Paper:** FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness
- **Authors:** Tri Dao, Daniel Y. Fu, Stefano Ermon, Atri Rudra, Christopher Ré
- **Published in:** Advances in Neural Information Processing Systems (NeurIPS), 2022
- **arXiv:** [arXiv:2205.14135](https://arxiv.org/abs/2205.14135)

The summary above is my own words, written from reading the paper. It is not the authors' abstract, it is not a translation of one, and no figure, table or passage of the original is reproduced here. Credit for the work belongs to the authors listed above; go and read them.

Citekey `dao2022flashattention`. Prose here is CC BY 4.0 — see [`summaries/LICENSE`](../LICENSE), and [`COPYRIGHT.md`](../../COPYRIGHT.md) for the authoritative path-to-licence map.
