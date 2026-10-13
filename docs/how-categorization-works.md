# How a transaction gets its category

A transaction is categorized in the first of these steps that can decide, from the most reliable to the least.
Nothing leaves the machine: the model runs locally in Ollama.

```
transaction ──► 0. hand-made category?  ──yes──► keep it (never changed, not even by "Recategorizar")
      │ no
      ▼
   1. rule for this merchant? ───────────yes──► use the rule        source = "memory"
      │ no
      ▼
   2. almost identical to one you labeled? ─yes─► copy its category  source = "similar"
      │ no
      ▼
   3. local model, with your most similar examples ──► category, subcategory, confidence   source = "llm"
      │ confidence below LLM_CONFIDENCE_THRESHOLD, or no category
      ▼
      "Por revisar" (review queue)
```

| Step | Where | What it does |
|---|---|---|
| 0. Hand-made | `Expense.category_source == "manual"` | Rows the user tagged are excluded from every run. |
| 1. Rules | `MerchantLabel`, `llm/merchant.py::merchant_key` | The concept is reduced to a merchant key (prefixes, digits, cities and card numbers removed). If a rule exists for that key it is used. A rule is only used when its category fits the movement: income categories for positive amounts, expense categories for negative ones, saving categories and Otros for both. |
| 2. Similarity | `llm/retrieval.py` | Character 3-gram TF-IDF cosine against the labeled merchants. At 0.85 or more, and with no other close label (0.70) of a different category, the category is copied. |
| 3. Model | `llm/llm_call.py` | Two constrained answers (category, then subcategory) with the 8 most similar labeled examples in the prompt, temperature 0. The confidence is the product of both probabilities. With more than 30 categories only the plausible ones are offered (`llm/shortlist.py`). |

## Where rules come from

- **Automatically**: correcting a category by hand (the picker of a transaction, the bulk assignment or "Está bien" in the
  results dialog) saves a rule for that merchant (`DatabaseManager.learn_from_correction`). The rule is applied
  immediately to the other transactions of the merchant that were not tagged by hand, and the newest correction wins.
- **By hand**: Ajustes → Reglas → "Nueva regla" (`DatabaseManager.save_rule`).
- Editing a rule applies it again to the merchant's transactions; forgetting it sends the transactions it had
  categorized back to the review queue (`delete_rule`).

## When it runs

- After importing a file, for the new transactions.
- On "Recategorizar": every transaction that was not tagged by hand is reset and goes through the steps again (steps 1
  and 2 first, so the same merchants always get the same category). The previous categories can be restored with
  "Deshacer".
- When a category is corrected by hand, for the rest of that merchant (step 1 only).

Saving categories hold transfers to accounts the app does not see; those transactions are neither income nor spending in
any total, whatever step categorized them.
