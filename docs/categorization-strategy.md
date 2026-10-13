# Categorization strategy

Goal: categorize bank movements with a small local model and get better with every correction the user makes,
without data leaving the machine.

## What we do and why

The problem is personalized text classification over noisy strings with few labels, so the model should be the
last resort, not the first.

1. **Deterministic memory first.** Corrections become rules keyed by a normalized merchant. Rules are exact,
   free, explainable and repeatable. Commercial and patented systems put user rules before the learned
   classifier for the same reasons, and keep personal corrections apart from population-level ones
   (Toshl: "spending categories that learn from you").
2. **Retrieval-based in-context learning for the rest.** Instead of the same fixed examples, put the labeled
   examples most similar to the input in the prompt. Liu et al. (KATE, 2021) show that similarity-retrieved examples
   beat random ones; Intuit's QuickBooks work (Dong et al., ECML-PKDD 2025) reports that nearest-neighbor
   retrieval over a user's own history is a strong baseline for transaction categorization.
3. **Selective prediction.** Treat the model confidence as a reason to ask the user, not as truth.
   Selective classification (Geifman & El-Yaniv, NeurIPS 2017) abstains below a confidence threshold;
   token probabilities need calibration to be trusted (Platt scaling, "Efficiently Deploying LLMs with
   Controlled Risk", 2024). The review queue is that abstention, and corrections feed the memory.
4. **Active learning loop.** Asking the user about the least certain rows is where each label is worth most
   (surveys: Schröder & Niekler 2020; "From Selection to Generation: LLM-based Active Learning", 2025).

## Semantic similarity: does it make sense here?

Similarity is used at two levels, and they need different tools:

- **Near-duplicates** (same merchant, different noise, typos, abbreviations): character n-gram TF-IDF is a strong,
  cheap baseline for short noisy strings and needs no model; published comparisons point to hybrids rather than a
  clear winner. This is what the app uses. It runs in microseconds, so it is a step before the model.
- **Generalization to merchants never seen** ("Panadería X" is like "Horno Y"): this needs semantics. With few
  labels it does not work: on a synthetic set of 23 labeled merchants (one label each, categories known), the
  nearest label gave the right category 35 % of the time with n-grams and 35 % with an embedding model
  (`all-minilm`), because different merchants of one category rarely look alike. The local LLM brings world
  knowledge that nearest-neighbour lookup lacks at this size.
- Candidates if it is ever worth it (Ollama): `bge-m3` (multilingual, about 1.2 GB), `nomic-embed-text`
  (274 MB, mostly English). Raw merchant names are a hard input: a transformer on merchant names alone reached
  about 57 % macro F1 in a bank study (Hierarchical Classification of Financial Transactions, 2023).
- Decide with your data, not in general: `uv run python scripts/eval_similarity.py --embed-model bge-m3` compares
  both on your hand-made labels and prints aggregates only. Revisit embeddings when there are a few hundred labels.

## Measured with synthetic data (known categories, the real local model)

Category accuracy on merchants **not** among the labels (24 invented merchants with bank-style noise, 2 random
splits; small samples, treat as indicative):

| labeled merchants | generic examples only | last 8 labels (old) | retrieved + generic (new) |
|---|---|---|---|
| 3 | 57.5 % | 65.0 % | 65.0 % |
| 8 | 53.3 % | 66.7 % | 70.0 % |
| 14 | 44.4 % | 83.3 % | 83.3 % |

Mean confidence on right answers was 0.82-0.84 against 0.40-0.45 on wrong ones with the new prompt, so the
0.6 threshold separates them reasonably on this set. Merchants already in memory are always right by construction.

## Known limits (measured)

- Token probabilities are overconfident: in a synthetic test the 3B model answered a wrong category with 0.9
  confidence and a correct one with 0.3. The threshold is therefore a starting point; adjust it by looking at
  the share of flagged rows that were wrong.
- The merchant key is a heuristic (prefix removal, first three tokens). Two merchants can collide and the
  newest correction wins.

## Next steps when the corpus grows

- Embedding retrieval (a local embedding model) in place of word overlap for similar-example selection.
- A small supervised head over sentence embeddings (SetFit, Tunstall et al. 2022) trained on the user's labels
  once there are a few hundred; it gives calibrated probabilities and no prompt cost.
- Fine-tuning the LLM only if the corpus reaches thousands of examples; it is the heaviest option.

## References

- Liu et al., "What Makes Good In-Context Examples for GPT-3?", 2021 (arXiv 2101.06804).
- Dong et al., "Transaction Categorization with Relational Deep Learning in QuickBooks", ECML-PKDD 2025 (arXiv 2506.09234).
- Lesner et al., "Large Scale Personalized Categorization of Financial Transactions", AAAI-19 (IAAI).
- Geifman & El-Yaniv, "Selective Classification for Deep Neural Networks", NeurIPS 2017 (arXiv 1705.08500).
- "Efficiently Deploying LLMs with Controlled Risk", 2024 (arXiv 2410.02173).
- Tunstall et al., "Efficient Few-Shot Learning Without Prompts" (SetFit), 2022 (arXiv 2209.11055).
- Schröder & Niekler, "A Survey of Active Learning for Text Classification using Deep Neural Networks", 2020 (arXiv 2008.07267).
- "From Selection to Generation: A Survey of LLM-based Active Learning", 2025 (arXiv 2502.11767).
- Plaid engineering blog, "Making sense of messy data" (merchant normalization).
