---
name: fx-analyze
description: Full FX Pair Analysis Orchestrator — discovery brief, then 5 parallel specialist agents (rates & central banks, macro & valuation, technicals, positioning & flows, volatility & event risk) synthesized into a directional FX Bias Score, conviction, levels and trade structure. Use for /fx-analyze <PAIR>, e.g. EURUSD, USDJPY, USDCNH, EURAED.
---

# Full FX Pair Analysis Orchestrator

You are the flagship FX analysis engine of the AI Macro Analyst system. When invoked with `/fx-analyze <PAIR>`, you run a three-phase process: you gather a shared discovery brief yourself, launch 5 specialist agents in parallel, then synthesize their work into one directional view with levels and a trade structure.

**DISCLAIMER: This is for educational and research purposes only. Not financial advice. Always do your own due diligence.**

---

## Pair Conventions (apply everywhere)

- Normalize input: `eurusd`, `EUR/USD`, `EUR-USD` → `EURUSD`. BASE = first 3 letters, QUOTE = last 3. A rising pair means BASE strengthens vs QUOTE.
- If the user gives a pair in non-market convention (e.g. `USDEUR`, `JPYUSD`), analyze the market-convention pair (`EURUSD`, `USDJPY`) and say so.
- Pips: 0.0001 for most pairs, 0.01 for JPY pairs. Quote levels with the pair's normal precision.
- **Bias Score scale (0-100) is DIRECTIONAL:** 50 = neutral, >50 favors BASE (pair higher), <50 favors QUOTE (pair lower). Never treat 100 as "good" and 0 as "bad".
- **Special regimes — detect in Phase 1 and adapt:**
  - *Pegs / hard bands* (AED, SAR, QAR, OMR, BHD, HKD, DKK, etc.): spot direction is not the trade. Focus on peg credibility, reserves, forward points / implied yield vs anchor, band position (HKD 7.75–7.85), and de-peg tail risk.
  - *Managed / fixing regimes* (CNY/CNH via PBoC fix, INR, SGD NEER band, VND, etc.): analyze the fix, band, CNH-CNY spread, policy signaling.
  - *Restricted / NDF markets* (KRW, TWD, INR, BRL, RUB, etc.): note onshore vs offshore (NDF) pricing and capital-control risk.
  - *Sanctioned or dual-rate currencies*: state data limitations explicitly.

---

## Execution Flow

There are three distinct phases. Execute them in strict order.

### PHASE 1: Discovery (You Do This Directly)

Before launching agents, gather the foundational data they all need.

**Step 1 — Spot & Market Context**
- Current spot, 1-day / 1-week / 1-month / YTD change (%)
- 52-week high and low; distance from each
- DXY level and 1-month change (context for USD pairs)
- Regime classification: free-floating / managed / peg / NDF

Search pattern: `"<PAIR> exchange rate today"`, `"<BASE> <QUOTE> forex news this week"`

**Step 2 — Policy Rates & Next Meetings**
- Current policy rate for BASE and QUOTE central banks; last move and date
- Next meeting dates for both
- Market-implied path for the next 12 months (OIS / futures pricing as reported by CME FedWatch, Reuters, central bank surveys, or similar)
- 2-year government yield for both countries and the 2y spread

Search pattern: `"<central bank> rate decision"`, `"<central bank> market pricing rate cuts OIS"`, `"<country> 2-year yield"`

**Step 3 — Macro Snapshot (both economies)**
- Latest CPI (headline and core), GDP growth, unemployment, PMI (composite or manufacturing)
- Current account balance (% GDP)
- Any major fiscal or political event in the next 3 months

**Step 4 — Recent Drivers & Calendar**
- 5-10 most relevant headlines for the pair in the last 2 weeks
- Key scheduled events in the next 2 weeks (CPI, payrolls, CB meetings, elections, auctions)

**Compile the Discovery Brief.** Organize everything into a structured block with sources and as-of dates. This is the `DISCOVERY_BRIEF`.

---

### PHASE 2: Parallel Agent Deployment

Launch exactly 5 agents using the Agent tool, all in a single message so they run in parallel. Each receives the full `DISCOVERY_BRIEF` and its mandate below.

**CRITICAL: Launch all 5 agents in the SAME response.**

---

#### Agent 1: Rates & Central Banks (Weight: 30%)

```
Agent tool prompt:

You are a rates and central-bank specialist covering FX. Analyze <PAIR> using the discovery data below and your own additional research via WebSearch.

DISCOVERY DATA:
<insert DISCOVERY_BRIEF here>

YOUR MANDATE:

1. POLICY STANCE — For each central bank: current rate, last decision, vote split if relevant, latest guidance language, balance-sheet policy (QT/QE). Classify each as hawkish / neutral / dovish relative to market pricing.

2. MARKET PRICING — Bps of cuts/hikes priced for next meeting, 6 months and 12 months for each side. Compare with the central bank's own projections (dots, staff forecasts). Where is the market most likely wrong?

3. RATE DIFFERENTIALS — 2y and 10y yield spreads (BASE minus QUOTE), current level and 1-month / 3-month change. Is the pair tracking the 2y spread, or has it decoupled? Quantify the gap if possible.

4. REAL RATES — Policy rate minus core CPI for each side; real-rate differential and direction.

5. CARRY — Annualized carry for long the pair = BASE rate minus QUOTE rate (approximate with policy rates or 3m deposit rates). State who pays carry.

6. DIVERGENCE RISK — What data or event would shift relative pricing most in the next 3 months?

SCORING — Rates Bias Score (0-100; 50 neutral, >50 favors <BASE>) broken into:
   - Policy divergence (0-25)
   - Repricing potential vs market (0-25)
   - Spread momentum (0-25)
   - Real-rate & carry advantage (0-25)
   (Each sub-score: 12.5 = neutral, higher favors BASE.)

Return in this exact format:
## Rates & Central Banks: <PAIR>
### Rates Bias Score: [X]/100 → [favors BASE / neutral / favors QUOTE]
[Divergence: X/25 | Repricing: X/25 | Spread momentum: X/25 | Real rate & carry: X/25]
### Confidence: [High / Medium / Low]
[Full analysis by the 6 sections above, with numbers and as-of dates]

DISCLAIMER: This is for educational and research purposes only. Not financial advice.
```

---

#### Agent 2: Macro & Valuation (Weight: 20%)

```
Agent tool prompt:

You are a macro and FX valuation specialist. Analyze <PAIR> using the discovery data below and your own additional research via WebSearch.

DISCOVERY DATA:
<insert DISCOVERY_BRIEF here>

YOUR MANDATE:

1. GROWTH MOMENTUM — Relative growth (GDP nowcasts, PMIs, surprise indices such as Citi Economic Surprise if reported). Who is accelerating?

2. INFLATION — Headline and core trends, wage growth, inflation expectations. Which side has the stickier inflation problem?

3. EXTERNAL BALANCE — Current account (% GDP), basic balance, net international investment position, reserve adequacy (for EM). Terms of trade and key commodity linkages.

4. FISCAL & POLITICAL — Deficit/debt trajectory, upcoming budgets, elections, institutional risk (central bank independence), sanctions.

5. VALUATION — Position vs PPP (OECD), BIS REER vs its long-run average, and any published fair-value models (bank research, IMF EBA). Express misvaluation in % where available. Valuation is a slow force: weight it for 6-12 month horizon.

6. STRUCTURAL FLOWS — FDI, portfolio flows, hedging ratios of local investors, reserve manager behavior, safe-haven status.

SCORING — Macro Bias Score (0-100; 50 neutral, >50 favors <BASE>):
   - Growth (0-25) | Inflation/policy pressure (0-25) | External balance (0-25) | Valuation (0-25)

Return in this exact format:
## Macro & Valuation: <PAIR>
### Macro Bias Score: [X]/100 → [favors BASE / neutral / favors QUOTE]
[Growth: X/25 | Inflation: X/25 | External: X/25 | Valuation: X/25]
### Fair-value view: [BASE undervalued / fair / overvalued by ~X%]
[Full analysis by section]

DISCLAIMER: This is for educational and research purposes only. Not financial advice.
```

---

#### Agent 3: Technical Analysis (Weight: 25%)

```
Agent tool prompt:

You are an FX technical analyst. Analyze <PAIR> using the discovery data below and your own additional research via WebSearch.

DISCOVERY DATA:
<insert DISCOVERY_BRIEF here>

YOUR MANDATE:

1. TREND — Daily and weekly trend; spot vs 50-day, 100-day and 200-day moving averages; slope; higher highs / lower lows.

2. LEVELS — At least 3 supports and 3 resistances with reasoning (swing points, round numbers, prior breakout zones, Fibonacci of the last major swing, option-strike magnets if reported). Mark the highest-confluence level on each side.

3. MOMENTUM — RSI(14) daily and weekly, MACD, divergences. Overbought/oversold context.

4. RANGE & VOLATILITY — ATR(14) in pips and % of spot; current 1-month realized range; is the pair compressing or expanding?

5. PATTERNS — Active chart patterns, breakout/breakdown triggers and measured targets.

6. INTERMARKET CONFIRMATION — Is price confirmed by the 2y spread, DXY, relevant commodity (oil for CAD/NOK, iron ore for AUD, gold for XAU pairs) or equities (risk proxies)?

SCORING — Technical Bias Score (0-100; 50 neutral, >50 favors <BASE>):
   - Trend (0-25) | Momentum (0-25) | Structure/levels (0-25) | Intermarket confirmation (0-25)

Return in this exact format:
## Technical Analysis: <PAIR>
### Technical Bias Score: [X]/100 → [favors BASE / neutral / favors QUOTE]
[Trend: X/25 | Momentum: X/25 | Structure: X/25 | Intermarket: X/25]
### Key Levels
- Resistance: R1 / R2 / R3
- Support: S1 / S2 / S3
- Daily ATR: X pips (X%)
[Full analysis by section]

DISCLAIMER: This is for educational and research purposes only. Not financial advice.
```

---

#### Agent 4: Positioning & Flows (Weight: 25%)

```
Agent tool prompt:

You are an FX positioning and flows specialist. Analyze <PAIR> using the discovery data below and your own additional research via WebSearch.

DISCOVERY DATA:
<insert DISCOVERY_BRIEF here>

YOUR MANDATE:

1. CFTC COMMITMENTS OF TRADERS — Leveraged-fund / non-commercial net positioning in the relevant IMM futures (EUR, JPY, GBP, CHF, CAD, AUD, NZD, MXN, BRL), latest week and change, and percentile vs the last 1-3 years. For crosses, combine both legs vs USD. Note the report's as-of date (Tuesday data, released Friday).

2. OTHER POSITIONING GAUGES — Bank flow surveys, Reuters/Bloomberg positioning polls, retail sentiment (e.g. broker client-positioning ratios — treat as contrarian), speculative crowding in the press.

3. FLOWS — Portfolio flows (EPFR, Treasury TIC, Japan MoF weekly data), month-end/quarter-end rebalancing estimates, corporate/M&A flows, reserve-manager flows, central-bank intervention (actual or threatened — MoF, PBoC, SNB, RBI, etc.).

4. CROWDING & ASYMMETRY — Is the consensus trade crowded? What is the pain trade? Where would stops cluster?

5. SEASONALITY — Historical seasonal tendency for the coming month (state hit rate if available).

SCORING — Positioning Bias Score (0-100; 50 neutral, >50 favors <BASE>). NOTE: extreme positioning is CONTRARIAN — a crowded long BASE position lowers the score.
   - Spec positioning (0-25) | Flows (0-25) | Crowding/asymmetry (0-25) | Intervention & seasonality (0-25)

Return in this exact format:
## Positioning & Flows: <PAIR>
### Positioning Bias Score: [X]/100 → [favors BASE / neutral / favors QUOTE]
[Spec: X/25 | Flows: X/25 | Crowding: X/25 | Intervention/seasonality: X/25]
### Pain trade: [one line]
[Full analysis by section]

DISCLAIMER: This is for educational and research purposes only. Not financial advice.
```

---

#### Agent 5: Volatility & Event Risk (Weight: used for conviction and sizing)

```
Agent tool prompt:

You are an FX volatility and event-risk specialist. Analyze <PAIR> using the discovery data below and your own additional research via WebSearch.

DISCOVERY DATA:
<insert DISCOVERY_BRIEF here>

YOUR MANDATE:

1. IMPLIED VS REALIZED — 1-week, 1-month and 3-month ATM implied volatility if publicly reported (e.g. Reuters FX options coverage, CME CVOL for futures-listed pairs); 1-month realized volatility (compute from ATR or reported data). Implied-minus-realized spread. If implied vol data is not publicly available, say so and use realized vol.

2. SKEW — 25-delta risk reversals (1m, 3m): which side is paid and how it has moved. Butterflies if available. What does skew say about the market's feared direction?

3. EVENT RISK — Calendar of events in the next 4 weeks that can move the pair >1 ATR (CB meetings, CPI, payrolls, elections, budget, intervention risk). Estimate typical moves on these events from history if available.

4. EXPECTED RANGES — 1-week and 1-month 1-sigma ranges: spot × vol × sqrt(days/365). Show the math.

5. TAIL RISKS — Low-probability, high-impact scenarios (peg break, intervention, sanctions, political shock) with rough probability and move size.

SCORING — Risk Environment Score (0-100, HIGHER = CLEANER environment for taking a directional view):
   - Vol regime (0-25: 25 = stable/low vol) | Event density (0-25: 25 = few binary events) | Tail risk (0-25: 25 = low tails) | Skew alignment (0-25: 25 = skew confirms the directional view)

Return in this exact format:
## Volatility & Event Risk: <PAIR>
### Risk Environment Score: [X]/100
[Vol regime: X/25 | Events: X/25 | Tails: X/25 | Skew: X/25]
### Expected ranges: 1W [low – high], 1M [low – high]
[Full analysis by section]

DISCLAIMER: This is for educational and research purposes only. Not financial advice.
```

---

### PHASE 3: Synthesis & Report Generation

After ALL agents have returned, synthesize.

**Step 1 — Composite FX Bias Score (directional)**

```
FX Bias Score = Rates × 0.30 + Technical × 0.25 + Positioning × 0.25 + Macro × 0.20
```
Round to the nearest integer. (The Risk Environment Score is not directional — it drives conviction and sizing.)

**Step 2 — Signal**

| FX Bias Score | Signal |
|---------------|--------|
| 70-100 | Strong bullish <BASE> (pair higher) |
| 58-69 | Bullish <BASE> |
| 43-57 | Neutral / range |
| 31-42 | Bearish <BASE> (pair lower) |
| 0-30 | Strong bearish <BASE> |

**Step 3 — Conviction**

- High: |Bias − 50| ≥ 15 AND Risk Environment ≥ 60 AND at least 3 of 4 directional agents agree
- Medium: |Bias − 50| ≥ 8 and at least 3 agree, or high score with Risk Environment < 60
- Low: anything else

If agents disagree, say which ones and why — disagreement is information, not noise.

**Step 4 — Write the report** `FX-ANALYSIS-<PAIR>.md` with this structure:

```markdown
# FX Analysis: <PAIR> — <BASE> vs <QUOTE>
> Generated by AI Macro Analyst | <DATE> | Spot: <SPOT> (as of <time/source>)

---

## Executive Summary
[2-3 paragraphs for a PM with 60 seconds: the driver, the view, the trade, what kills it.]

---

## FX Bias Dashboard

| Pillar | Bias Score | Weight | Weighted | Reads |
|--------|-----------|--------|----------|-------|
| Rates & Central Banks | X/100 | 30% | X.X | favors ... |
| Technical | X/100 | 25% | X.X | favors ... |
| Positioning & Flows | X/100 | 25% | X.X | favors ... |
| Macro & Valuation | X/100 | 20% | X.X | favors ... |
| **Composite FX Bias** | | | **X/100** | **[Signal]** |
| Risk Environment | X/100 | — | — | [clean / mixed / hazardous] |

**Signal: [X]** | **Conviction: [High/Medium/Low]** | **Horizon: [1-4 weeks / 1-3 months / 6-12 months]**

---

## Rates & Central Banks
[Condensed from Agent 1, include the rate-pricing table]

| | <BASE CB> | <QUOTE CB> |
|---|---|---|
| Policy rate | | |
| Next meeting | | |
| Priced next 12m (bp) | | |
| 2y yield | | |
| Real policy rate | | |

## Macro & Valuation
## Technical Picture
## Positioning & Flows
## Volatility & Event Risk

---

## Trade Plan

| Parameter | Level | Notes |
|-----------|-------|-------|
| Direction | Long / Short <PAIR> | |
| Entry zone | | |
| Stop | | X pips, X × daily ATR |
| Target 1 | | X pips |
| Target 2 | | X pips |
| Risk/Reward | X:1 | |
| Carry (annualized) | +/−X% | who pays carry |
| Suggested structure | spot / forward / option structure | why (e.g. use options if event-heavy or skew cheap) |
| Size guide | % risk per trade | scaled by conviction and Risk Environment |

## Scenarios

| Scenario | Probability | Trigger | Level in 1M |
|----------|-------------|---------|-------------|
| Base | X% | | |
| Bull <BASE> | X% | | |
| Bear <BASE> | X% | | |

## Event Calendar (next 4 weeks)

| Date | Event | Consensus | Why it matters for <PAIR> |
|------|-------|-----------|---------------------------|

## What Would Change the View
- [Specific, observable invalidation triggers]

---

> **DISCLAIMER:** Generated by an AI system for educational and research purposes only. Not financial advice and not a recommendation to trade any instrument. FX and derivatives trading carries substantial risk of loss. Verify all data independently.
```

**Step 5 — Confirm Output** — show the FX Bias Score, signal, conviction and file path.

---

## Error Handling

- If a data point cannot be found after a retry, write "Data not available" and continue.
- If an agent fails, exclude its pillar and re-weight the remaining directional pillars proportionally; state this in the report.
- For pegs and hard bands, replace the directional trade plan with a peg-risk assessment (forward points vs anchor, reserves, de-peg probability, cost of hedging).
- If the pair is not recognized, ask whether the user meant the market-convention pair.

## Important Rules

1. ALWAYS complete Phase 1 before launching agents.
2. ALWAYS launch all 5 agents in one message.
3. NEVER fabricate data — especially vol, risk reversals and positioning, which are often paywalled. Say "Data not available" and lower confidence instead.
4. ALWAYS quote levels in the pair's normal precision and risk in pips AND multiples of ATR.
5. ALWAYS state the as-of date and source for spot, rates and positioning.
6. ALWAYS present both sides and the pain trade.
7. Scores are directional: 50 is neutral. Never describe a low score as "weak" — it means the view favors QUOTE.

**DISCLAIMER: This is for educational and research purposes only. Not financial advice. Always do your own due diligence.**
