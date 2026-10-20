# AI Markets Analyst

**Equity, FX and macro research on demand — as Claude Code skills and as a mobile web app.**

Pick a command, enter a ticker or currency pair, and get an institutional-style report in 1–6 minutes: scored, sourced, with levels, scenarios and a downloadable PDF. The same `SKILL.md` files power both the Claude Code slash commands in VS Code and the Streamlit web app, so there is one source of truth for the methodology.

<p align="center">
  <img src="docs/screenshots/stocks.png" width="250" alt="Equities tab">
  &nbsp;
  <img src="docs/screenshots/fx.png" width="250" alt="FX and macro tab">
  &nbsp;
  <img src="docs/screenshots/report.png" width="250" alt="Report view">
</p>

---

## What's inside

**24 skills** in two groups:

### Equities — `trade-*`

| Command | What it does |
|---|---|
| `/trade-quick <TICKER>` | 60-second snapshot: signal, key factors, levels |
| `/trade-analyze <TICKER>` | Flagship: discovery → 5 parallel agents (technical, fundamental, sentiment, risk, thesis) → composite **Trade Score** and grade |
| `/trade-fundamental <TICKER>` | Valuation, growth, profitability, balance sheet, moat — Fundamental Score |
| `/trade-technical <TICKER>` | Trend, momentum, volume, patterns, support/resistance — Technical Score |
| `/trade-sentiment <TICKER>` | News, social, analysts, institutions, insiders, short interest |
| `/trade-earnings <TICKER>` | Pre-earnings setup: history, expected move, key metrics |
| `/trade-options <TICKER> [view]` | IV rank, expected move, flow, strategy recommendations |
| `/trade-risk <TICKER>` | Volatility, drawdowns, liquidity, position sizing (Kelly, vol-adjusted) |
| `/trade-thesis <TICKER>` | Bull/bear case, catalysts, entry/exit, asymmetry |
| `/trade-compare <T1> <T2>` | Head-to-head scored comparison |
| `/trade-sector <SECTOR>` | Sector rotation, momentum, money flows |
| `/trade-screen <criteria>` | Growth / value / dividend / momentum / custom screens |
| `/trade-watchlist` | Scored watchlist with alerts |
| `/trade-portfolio` | Allocation, risk, income, rebalancing |
| `/trade-report-pdf` | Compiles all `TRADE-*.md` into a branded PDF |

### FX & Macro — `fx-*`, `macro-*`

| Command | What it does |
|---|---|
| `/fx-quick <PAIR…>` | One-card snapshot per pair: rates, carry, trend, levels, positioning, next catalyst |
| `/fx-analyze <PAIR>` | Flagship: discovery → 5 parallel agents (rates & CBs, macro & valuation, technicals, positioning & flows, vol & event risk) → directional **FX Bias Score**, conviction, trade plan |
| `/fx-carry <PAIR \| G10 \| EM>` | CIP forwards, implied yields, carry-to-vol, breakevens, ranked carry ideas |
| `/fx-vol <PAIR> [view]` | ATM vs realized vol, skew, expected ranges, option structures |
| `/macro-cb <BANK…>` | Central bank stance, market pricing vs projections, next-meeting probabilities |
| `/macro-country <COUNTRY…>` | Macro dashboard, cycle phase, Macro Momentum Score |
| `/macro-calendar [window]` | Event calendar in GST/UTC with scenario maps for top events |
| `/macro-regime` | Cross-asset regime probabilities and the currency map for that regime |
| `/fx-scan [G10 \| EM \| ALL]` | Cross-sectional FX scoreboard: carry, momentum, valuation, repricing |

FX skills handle pegs (AED, SAR, HKD), managed/fixing regimes (CNH, SGD) and NDF markets explicitly instead of forcing a directional call.

---

## How it works

```mermaid
flowchart LR
    U[Phone / browser] -->|command + ticker| A[Streamlit app]
    V[VS Code] -->|/slash command| C[Claude Code]
    A --> E[engine.py]
    E -->|reads| S[".claude/skills/*/SKILL.md"]
    C -->|reads| S
    E -->|Claude API + web search| M[(Claude)]
    M --> R[Markdown report]
    R --> P[PDF export]
```

- **Single-pass skills** run as one Claude call with the skill as the system prompt.
- **Orchestrator skills** (`trade-analyze`, `fx-analyze`, or any skill with `PHASE 1/2/3` and `#### Agent N` blocks) run as a pipeline: a discovery brief, then N specialist agents in parallel, then a synthesis step that computes the composite score.
- A runtime adapter tells the model it is in a web context (no files, no subagent tool, web search only) and enforces "never invent numbers — write *Data not available*".
- Each report gets its own URL (`?job=…`), survives the phone screen locking, and identical requests within 6 hours are served from cache.

## Scoring

| System | Scale | Composite |
|---|---|---|
| Trade Score (equities) | 0–100, higher = better | Technical 25% · Fundamental 25% · Sentiment 20% · Risk 15% · Thesis 15% → grade A+ … F |
| FX Bias Score | 0–100, **directional**: 50 neutral, >50 favors base currency | Rates 30% · Technical 25% · Positioning 25% · Macro 20%; the Risk Environment score drives conviction and sizing |

---

## Quick start

### In VS Code (Claude Code)

```bash
git clone https://github.com/xttron2033/StocksProject.git
```
Open the folder in VS Code and type `/trade-analyze NVDA` or `/fx-analyze EURUSD` in the Claude Code chat. Skills load automatically from `.claude/skills/`.

### Web app, locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # add your Anthropic API key
streamlit run app.py
```

### Web app, hosted

Free deployment on Streamlit Community Cloud in about 15 minutes: see **[DEPLOY.md](DEPLOY.md)** (in Russian).

---

## Repository layout

```
.claude/
  skills/            24 SKILL.md files — the methodology
  settings.json      Claude Code tool permissions
.streamlit/
  config.toml        theme
  secrets.toml.example
app.py               Streamlit UI: forms, job queue, report view, limits
engine.py            skill runner: single-pass + parallel orchestrator, web-search adapter
pdf_export.py        Markdown → branded PDF (WeasyPrint)
requirements.txt     Python dependencies
packages.txt         system packages for Streamlit Cloud (Pango, DejaVu fonts)
DEPLOY.md            deployment guide
```

## Configuration (`.streamlit/secrets.toml`)

| Key | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | required |
| `APP_PASSWORD` | empty | optional access code for the web app |
| `DAILY_LIMIT` | `30` | max reports per day across all users |
| `MODEL` | `claude-sonnet-5-5` | e.g. `claude-haiku-5-5` for cheaper, faster runs |
| `MAX_PARALLEL` | `3` | parallel agents in orchestrator skills; lower it if you hit rate limits |

## Data & limitations

- Market data comes from live web search at run time. Every figure should carry a source and as-of date; missing data is labeled, not estimated.
- Interbank FX vol surfaces, risk reversals and some positioning data are not public, so `fx-vol` relies on reported figures and CME CVOL where available.
- Indicative cost per report on Sonnet: quick ≈ $0.1–0.3, single skill ≈ $0.3–0.8, full analyze ≈ $1–3. The app shows an estimate under each report.

---

> **Disclaimer.** For educational and research purposes only. Nothing in this repository or its output is investment advice or a recommendation to buy or sell any security, currency or derivative. AI-generated analysis can be wrong or out of date — verify independently.

© 2026 Egor Zhilnikov. All rights reserved.
