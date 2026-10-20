"""
Движок: запускает ваши SKILL.md из .claude/skills через Anthropic API с веб-поиском.

Логика скиллов не дублируется — каждый запуск читает актуальный SKILL.md,
поэтому правки скиллов в VS Code автоматически попадают в веб-приложение
(после git push).
"""
from __future__ import annotations

import datetime as dt
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import anthropic

SKILLS_DIR = Path(__file__).parent / ".claude" / "skills"
WEB_SEARCH_TOOL = "web_search_20250305"
DEFAULT_MODEL = "claude-sonnet-5-5"

LogFn = Callable[[str], None]


# --------------------------------------------------------------------------- #
# Каталог команд, доступных в вебе
# --------------------------------------------------------------------------- #
# Ключ = имя папки скилла. group: stocks | fx. input — тип поля ввода в форме.
COMMANDS: dict[str, dict] = {
    # --- Акции ---
    "trade-quick":       dict(group="stocks", label="⚡ Quick — снимок за минуту",           input="ticker",      searches=6),
    "trade-analyze":     dict(group="stocks", label="🧭 Analyze — полный анализ (5 агентов)", input="ticker",      searches=6),
    "trade-fundamental": dict(group="stocks", label="📊 Fundamental — фундаментал",          input="ticker",      searches=10),
    "trade-technical":   dict(group="stocks", label="📈 Technical — теханализ",              input="ticker",      searches=10),
    "trade-sentiment":   dict(group="stocks", label="📰 Sentiment — новости и настроения",    input="ticker",      searches=10),
    "trade-earnings":    dict(group="stocks", label="🗓 Earnings — перед отчётностью",        input="ticker",      searches=10),
    "trade-options":     dict(group="stocks", label="🎯 Options — опционные стратегии",       input="ticker_view", searches=10),
    "trade-risk":        dict(group="stocks", label="🛡 Risk — риск и размер позиции",        input="ticker",      searches=10),
    "trade-thesis":      dict(group="stocks", label="💡 Thesis — инвестиционный тезис",       input="ticker",      searches=10),
    "trade-compare":     dict(group="stocks", label="⚖️ Compare — сравнить две акции",        input="two_tickers", searches=12),
    "trade-sector":      dict(group="stocks", label="🏭 Sector — анализ сектора",             input="text",        searches=12,
                              placeholder="Technology / XLE / rotation"),
    "trade-screen":      dict(group="stocks", label="🔎 Screen — скринер",                    input="text",        searches=12,
                              placeholder="growth / value / dividend / momentum / custom: ..."),
    "trade-watchlist":   dict(group="stocks", label="👀 Watchlist — оценить список тикеров",  input="tickers",     searches=12),
    "trade-portfolio":   dict(group="stocks", label="💼 Portfolio — разбор портфеля",         input="portfolio",   searches=12),
    # --- FX и макро ---
    "fx-quick":          dict(group="fx", label="⚡ FX Quick — снимок пары",                   input="pairs",       searches=8),
    "fx-analyze":        dict(group="fx", label="🧭 FX Analyze — полный анализ пары (5 агентов)", input="pair",    searches=6),
    "fx-carry":          dict(group="fx", label="💰 Carry — форварды и carry-to-vol",         input="carry",       searches=12),
    "fx-vol":            dict(group="fx", label="🎯 FX Vol — вола, скью, опционные структуры", input="pair_view",  searches=10),
    "macro-cb":          dict(group="fx", label="🏦 Центробанк — ставка и ожидания",           input="banks",       searches=10),
    "macro-country":     dict(group="fx", label="🌍 Страна — макро-дашборд",                   input="countries",   searches=12),
    "macro-calendar":    dict(group="fx", label="🗓 Календарь событий",                        input="calendar",    searches=10),
    "macro-regime":      dict(group="fx", label="🧪 Режим рынка — risk-on/off, кросс-активы",  input="universe",    searches=14),
    "fx-scan":           dict(group="fx", label="🔎 FX Scan — рейтинг валют",                  input="scan",        searches=14),
}


def skill_text(name: str) -> str:
    return (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")


def available_commands(group: str | None = None) -> dict[str, dict]:
    return {k: v for k, v in COMMANDS.items()
            if (SKILLS_DIR / k / "SKILL.md").exists() and (group is None or v["group"] == group)}


def slash_command(name: str, args: str) -> str:
    """trade-quick NVDA → '/trade quick NVDA' (как в ваших скиллах); fx-quick → '/fx-quick'."""
    cmd = f"/trade {name[6:]}" if name.startswith("trade-") else f"/{name}"
    return f"{cmd} {args}".strip()


# --------------------------------------------------------------------------- #
# Адаптер: Claude Code → веб
# --------------------------------------------------------------------------- #
def runtime_note(lang: str) -> str:
    today = dt.date.today().strftime("%B %d, %Y")
    language = ("Write the whole report in Russian (keep tickers, metric names like P/E, "
                "and numbers as is)." if lang == "ru" else "Write the report in English.")
    return f"""
=====================================================================
RUNTIME ENVIRONMENT — these rules OVERRIDE any conflicting instruction above.
You are running inside a web application, not Claude Code.
- Your only tool is web_search. There is NO file system, NO Bash/Python, NO Agent/subagent tool,
  NO Alpha Vantage, NO WebFetch.
- Where the skill says "write the file X.md", output that file's complete markdown content as
  your final answer instead. Where it says "display in the terminal", output it as markdown.
- Where the skill says to launch subagents, do that work yourself, sequentially.
- Where the skill says to run Python, do the arithmetic yourself and show the key inputs.
- Today's date is {today}. Use web_search for every market number (price, ratios, estimates,
  ownership, options data). Prefer primary/reputable sources and state the as-of date.
- NEVER invent numbers. If a figure cannot be found, write "Data not available".
- Your final answer must contain ONLY the finished report in markdown — no narration of your
  search process, no "let me search", no questions back to the user.
- {language}
=====================================================================
"""


# --------------------------------------------------------------------------- #
# Вызов модели
# --------------------------------------------------------------------------- #
class Engine:
    def __init__(self, api_key: str, model: str | None = None, max_parallel: int = 3):
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=6, timeout=600)
        self.model = model or DEFAULT_MODEL
        self.max_parallel = max_parallel
        self.usage = {"input": 0, "output": 0, "searches": 0}

    def _call(self, system: str, user: str, max_searches: int, max_tokens: int = 12000,
              log: LogFn | None = None, tag: str = "") -> str:
        messages = [{"role": "user", "content": user}]
        tools = [{"type": WEB_SEARCH_TOOL, "name": "web_search", "max_uses": max_searches}]
        final_text: list[str] = []
        for _ in range(8):  # pause_turn continuation
            resp = self.client.messages.create(
                model=self.model, max_tokens=max_tokens, system=system,
                messages=messages, tools=tools,
            )
            self._account(resp)
            # Текст после последнего результата поиска = итоговый отчёт
            chunk: list[str] = []
            for block in resp.content:
                btype = getattr(block, "type", "")
                if btype == "server_tool_use":
                    q = (getattr(block, "input", {}) or {}).get("query", "")
                    if log and q:
                        log(f"{tag}🔍 {q}")
                    chunk = []
                elif btype == "web_search_tool_result":
                    chunk = []
                elif btype == "text":
                    chunk.append(block.text)
            if chunk:
                final_text = chunk
            if resp.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": resp.content})
                continue
            break
        return "".join(final_text).strip()

    def _account(self, resp) -> None:
        u = resp.usage
        self.usage["input"] += (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
        self.usage["output"] += u.output_tokens or 0
        stu = getattr(u, "server_tool_use", None)
        if stu is not None:
            self.usage["searches"] += getattr(stu, "web_search_requests", 0) or 0

    # ------------------------------------------------------------------- #
    def run(self, command: str, args: str, lang: str = "en", log: LogFn | None = None) -> str:
        log = log or (lambda _m: None)
        text = skill_text(command)
        if "### PHASE 1" in text and len(_agent_prompts(text)) >= 2:
            return self._run_orchestrator(command, text, args.split()[0], lang, log)
        cfg = COMMANDS[command]
        system = text + runtime_note(lang)
        user = slash_command(command, args)
        if command == "trade-portfolio":
            user = f"/trade portfolio\n\nMy holdings:\n{args}"
        log(f"▶ {user.splitlines()[0]}")
        return self._call(system, user, cfg["searches"], max_tokens=16000, log=log)

    # -------- оркестратор: discovery → N агентов параллельно → синтез --------
    def _run_orchestrator(self, command: str, text: str, subject: str, lang: str, log: LogFn) -> str:
        phase1 = _section(text, "### PHASE 1", "### PHASE 2")
        phase3 = _section(text, "### PHASE 3", "## Error Handling")
        rules = _section(text, "## Important Rules", None)
        conventions = _section(text, "## Pair Conventions", "## Execution Flow")
        agent_prompts = _agent_prompts(text)
        subs = _placeholders(subject)

        def fill(s: str) -> str:
            for k, v in subs.items():
                s = s.replace(k, v)
            return s

        if not phase1 or not phase3:
            log("Структура оркестратора не распознана — запускаю одним проходом")
            return self._call(text + runtime_note(lang), slash_command(command, subject), 15,
                              max_tokens=16000, log=log)

        log("Фаза 1/3 — сбор базовых данных")
        brief = self._call(
            "You are the discovery step of a market analysis pipeline.\n" + conventions + "\n" + fill(phase1)
            + runtime_note("en") + "\nOutput ONLY the DISCOVERY_BRIEF as a structured markdown block.",
            f"Subject: {subject}", max_searches=8, max_tokens=6000, log=log, tag="[discovery] ",
        )

        log(f"Фаза 2/3 — {len(agent_prompts)} агентов параллельно")
        def run_agent(item):
            name, prompt = item
            p = fill(prompt).replace("<insert DISCOVERY_BRIEF here>", brief)
            out = self._call("You are a specialist analyst.\n" + conventions + runtime_note("en"), p,
                             max_searches=6, max_tokens=8000, log=log, tag=f"[{name}] ")
            log(f"✓ {name} готов")
            return f"<agent name=\"{name}\">\n{out}\n</agent>"
        with ThreadPoolExecutor(max_workers=self.max_parallel) as ex:
            results = list(ex.map(run_agent, agent_prompts))

        log("Фаза 3/3 — синтез отчёта")
        system = ("You are the synthesis step of the orchestrator.\n" + conventions + "\n"
                  + fill(phase3) + "\n" + rules + runtime_note(lang)
                  + "\nDo not search again unless a critical number is missing.")
        user = (f"SUBJECT: {subject}\n\nDISCOVERY_BRIEF:\n{brief}\n\nAGENT RESULTS:\n\n"
                + "\n\n".join(results) + "\n\nProduce the complete final report markdown now.")
        return self._call(system, user, max_searches=2, max_tokens=16000, log=log, tag="[synthesis] ")


def _placeholders(subject: str) -> dict[str, str]:
    subs = {"<TICKER>": subject, "<PAIR>": subject}
    if re.fullmatch(r"[A-Z]{6}", subject):
        subs.update({"<BASE>": subject[:3], "<QUOTE>": subject[3:]})
    return subs


def _section(text: str, start: str, end: str | None) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start)) if end else -1
    return text[i: j if j > 0 else len(text)].strip()


def _agent_prompts(text: str) -> list[tuple[str, str]]:
    """Достаёт промпты агентов из блоков ```...Agent tool prompt:...``` в trade-analyze."""
    out = []
    for m in re.finditer(r"####\s*Agent\s*\d+:\s*([^\n(]+)[^\n]*\n+```[^\n]*\n(.*?)```", text, re.S):
        name = m.group(1).strip()
        body = m.group(2).replace("Agent tool prompt:", "", 1).strip()
        out.append((name, body))
    return out


def estimate_cost_usd(usage: dict) -> float:
    # Ориентир для Sonnet: $3 / 1M input, $15 / 1M output, $10 / 1000 поисков
    return usage["input"] * 3e-6 + usage["output"] * 15e-6 + usage["searches"] * 0.01
