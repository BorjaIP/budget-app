# Inspiration and credits

This app learns from other open-source personal finance projects. We read their documentation and look at how they
solve problems; the code here is our own. When an idea, a screen or a rule of thumb comes from one of them, say so in
the commit or pull request and keep this file up to date.

## Projects

| Project | License | What we draw from it |
|---|---|---|
| [Sure](https://github.com/we-promise/sure) | AGPL-3.0 | The card-based look (soft gray page, white rounded cards with a hairline border and a faint shadow). The cash-flow (Sankey) diagram and the category donut on the overview. Rules with conditions and actions. Recurring bills that are detected, then confirmed or dismissed. Withholding model answers below a confidence threshold, and its roadmap item "AI controls and transparency". Savings goals and MCP/API access are ideas we have not built. |
| [Maybe](https://github.com/maybe-finance/maybe) | AGPL-3.0 | The origin of Sure's design and data model (archived since July 2025; Sure is the community fork). Net worth and balance sheet by account type, and the in-app assistant with tools, are ideas we have not built. |
| [Actual Budget](https://github.com/actualbudget/actual) | MIT | Rules that are created from what the user corrects and stay visible and editable (our Reglas tab). Scheduled and upcoming payments (our "Próximos cargos"). The report set: net worth, cash flow, spending analysis. Linked transfers between accounts, reconciliation and budget templates are ideas we have not built. |
| [Firefly III](https://github.com/firefly-iii/firefly-iii) | AGPL-3.0 | Subscriptions with a minimum and a maximum expected amount and an expected date (our estimate for bills that vary, like electricity). The rule engine with triggers and actions. Piggy banks and tags are ideas we have not built. |

Also consulted for the categorization design (see `categorization-strategy.md` for the papers and the other
repositories we reviewed and discarded).

## How to use them

- **Credit.** Mention the project and link it in the commit or pull request that was inspired by it, and add or update its
  row above.
- **Ideas, not code.** This repository is MIT. Maybe, Sure and Firefly III are AGPL-3.0: do not copy or translate their
  code, templates or styles into this repository. Take the idea, the behavior or the layout principle and write it here.
  Actual is MIT, but still credit it and keep its copyright notice if any code is ever reused.
- **Check first-hand.** When a claim about what another project does goes into a document or a decision, read its
  documentation or code (the repositories above) instead of relying on memory.
- **Their data stays theirs.** Never copy screenshots, logos or trademarks. "Maybe" is a trademark of Maybe Finance Inc.
