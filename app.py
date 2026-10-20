"""
AI Trading Analyst — веб-версия скиллов /trade-*, /fx-*, /macro-* для телефона.
Запуск локально:  streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
import time
import uuid
from pathlib import Path

import streamlit as st

from engine import Engine, available_commands, estimate_cost_usd
from pdf_export import markdown_to_pdf

st.set_page_config(page_title="AI Markets Analyst", page_icon="📊", layout="centered")

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
CACHE_HOURS = 6
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")


def secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


API_KEY = secret("ANTHROPIC_API_KEY")
APP_PASSWORD = secret("APP_PASSWORD", "")
DAILY_LIMIT = int(secret("DAILY_LIMIT", 30))
MODEL = secret("MODEL", None)
MAX_PARALLEL = int(secret("MAX_PARALLEL", 3))


# --------------------------------------------------------------------------- #
# Хранилище задач (общее для всех посетителей, живёт пока работает сервер)
# --------------------------------------------------------------------------- #
@st.cache_resource
def store():
    return {"jobs": {}, "lock": threading.Lock(), "daily": {}}


def load_job(job_id: str) -> dict | None:
    s = store()
    if job_id in s["jobs"]:
        return s["jobs"][job_id]
    f = REPORTS_DIR / f"{job_id}.json"
    if f.exists():
        job = json.loads(f.read_text(encoding="utf-8"))
        s["jobs"][job_id] = job
        return job
    return None


def find_cached(command: str, args: str, lang: str) -> str | None:
    cutoff = time.time() - CACHE_HOURS * 3600
    for j in store()["jobs"].values():
        if (j["command"], j["args"], j["lang"]) == (command, args, lang) \
                and j["status"] in ("running", "done") and j["started"] > cutoff:
            return j["id"]
    return None


def used_today() -> int:
    return store()["daily"].get(dt.date.today().isoformat(), 0)


def start_job(command: str, args: str, lang: str) -> str:
    s = store()
    job_id = uuid.uuid4().hex[:10]
    job = dict(id=job_id, command=command, args=args, lang=lang, status="running",
               log=[], result="", error="", started=time.time(), finished=None, usage=None)
    with s["lock"]:
        s["jobs"][job_id] = job
        today = dt.date.today().isoformat()
        s["daily"][today] = s["daily"].get(today, 0) + 1

    def worker():
        engine = Engine(API_KEY, model=MODEL, max_parallel=MAX_PARALLEL)
        try:
            job["result"] = engine.run(command, args, lang, log=lambda m: job["log"].append(m))
            if not job["result"]:
                raise RuntimeError("Модель вернула пустой ответ")
            job["status"] = "done"
        except Exception as e:  # noqa: BLE001
            job["status"] = "error"
            job["error"] = f"{type(e).__name__}: {e}"
            with s["lock"]:  # неудачный запуск не съедает дневной лимит
                today = dt.date.today().isoformat()
                s["daily"][today] = max(0, s["daily"].get(today, 1) - 1)
        finally:
            job["finished"] = time.time()
            job["usage"] = dict(engine.usage, cost_usd=round(estimate_cost_usd(engine.usage), 2))
            (REPORTS_DIR / f"{job_id}.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

    threading.Thread(target=worker, daemon=True).start()
    return job_id


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
st.markdown("""
<style>
  .block-container {padding-top: 1.5rem; max-width: 820px;}
</style>""", unsafe_allow_html=True)

st.markdown("## 📊 AI Markets Analyst")

if not API_KEY:
    st.error("Не задан ANTHROPIC_API_KEY в Secrets приложения.")
    st.stop()

# --- доступ по паролю (если задан) ---
if APP_PASSWORD and not st.session_state.get("authed"):
    pw = st.text_input("Код доступа", type="password")
    if st.button("Войти", type="primary", width="stretch"):
        if pw == APP_PASSWORD:
            st.session_state.authed = True
            st.rerun()
        st.error("Неверный код")
    st.stop()


def render_job(job: dict):
    label = available_commands().get(job["command"], {}).get("label", job["command"])
    st.caption(f"{label} · **{job['args'].splitlines()[0][:60]}**")

    if st.button("← Новый отчёт", width="stretch"):
        st.query_params.clear()
        st.rerun()

    if job["status"] == "running":
        elapsed = int(time.time() - job["started"])
        st.info(f"⏳ Готовлю отчёт… {elapsed // 60}:{elapsed % 60:02d}. "
                "Обычно 1–3 мин, полный анализ (Analyze) до 6 мин. Можно заблокировать телефон — "
                "отчёт будет по этой же ссылке.")
        for line in job["log"][-8:]:
            st.text(line)
        time.sleep(3)
        st.rerun()

    if job["status"] == "error":
        st.error("Не получилось собрать отчёт.")
        st.code(job["error"])
        return

    md = job["result"]
    title = f"{job['command'].upper()} {job['args'].splitlines()[0][:40]}"
    fname = re.sub(r"[^A-Za-z0-9]+", "-", f"{job['command']}-{job['args'][:30]}").strip("-").upper()

    c1, c2 = st.columns(2)
    try:
        c1.download_button("⬇️ PDF", markdown_to_pdf(md, title), f"{fname}.pdf",
                           "application/pdf", type="primary", width="stretch")
    except Exception as e:  # noqa: BLE001
        c1.caption(f"PDF недоступен: {e}")
    c2.download_button("⬇️ Markdown", md.encode("utf-8"), f"{fname}.md", "text/markdown", width="stretch")

    if job.get("usage"):
        u = job["usage"]
        secs = int((job["finished"] or time.time()) - job["started"])
        st.caption(f"⏱ {secs // 60}:{secs % 60:02d} · 🔍 {u['searches']} поисков · ≈ ${u['cost_usd']}")

    st.divider()
    st.markdown(md.replace("$", r"\$"))


# --- экран отчёта по ссылке ?job=... ---
job_id = st.query_params.get("job")
if job_id:
    job = load_job(job_id)
    if job:
        render_job(job)
        st.stop()
    st.warning("Отчёт не найден (сервер мог перезапуститься). Запустите заново.")
    st.query_params.clear()

# --- форма ---
BANKS = ["FED", "ECB", "BOJ", "BOE", "SNB", "BOC", "RBA", "RBNZ", "NORGES", "RIKSBANK",
         "PBOC", "CBRT", "CBR", "RBI", "BANXICO", "BCB", "SARB", "SAMA", "CBUAE"]
COUNTRIES = ["US", "EZ", "UK", "JP", "CN", "DE", "CH", "CA", "AU", "NZ", "NO", "SE",
             "TR", "RU", "IN", "BR", "MX", "ZA", "SA", "AE"]


def norm_pair(raw: str) -> str:
    return re.sub(r"[^A-Za-z]", "", raw).upper()


group = st.segmented_control("Раздел", ["stocks", "fx"], default="stocks",
                             format_func=lambda g: "📈 Акции" if g == "stocks" else "💱 FX и макро",
                             label_visibility="collapsed") or "stocks"
cmds = available_commands(group)
if not cmds:
    st.warning("В .claude/skills нет скиллов для этого раздела.")
    st.stop()
command = st.selectbox("Команда", list(cmds), format_func=lambda k: cmds[k]["label"])
kind = cmds[command]["input"]

args = ""
tickers: list[str] = []   # для проверки формата
pairs: list[str] = []
if kind in ("ticker", "ticker_view"):
    t = st.text_input("Тикер", placeholder="NVDA").strip().upper()
    tickers = [t] if t else []
    args = t
    if kind == "ticker_view":
        view = st.radio("Взгляд", ["neutral", "bullish", "bearish"], horizontal=True)
        args = f"{t} {view}" if t else ""
elif kind == "two_tickers":
    a, b = st.columns(2)
    t1 = a.text_input("Тикер 1", placeholder="AAPL").strip().upper()
    t2 = b.text_input("Тикер 2", placeholder="MSFT").strip().upper()
    tickers = [t1, t2]
    args = f"{t1} {t2}" if t1 and t2 else ""
elif kind == "tickers":
    tickers = st.text_input("Тикеры через пробел", placeholder="NVDA AMD TSM").upper().split()
    args = " ".join(tickers)
elif kind == "text":
    args = st.text_input("Параметр", placeholder=cmds[command].get("placeholder", "")).strip()
elif kind == "portfolio":
    args = st.text_area("Позиции (тикер, кол-во, цена покупки — по строке)",
                        placeholder="AAPL 50 172\nMSFT 20 390\nVOO 30 480", height=150).strip()
elif kind in ("pair", "pair_view"):
    p = norm_pair(st.text_input("Валютная пара", placeholder="EURUSD"))
    pairs = [p] if p else []
    args = p
    if kind == "pair_view" and p:
        view = st.radio("Взгляд", ["neutral", "bullish", "bearish"], horizontal=True)
        args = f"{p} {view}"
elif kind == "pairs":
    pairs = [norm_pair(x) for x in re.split(r"[\s,;]+", st.text_input(
        "Пары через пробел", placeholder="EURUSD USDJPY AUDUSD")) if x]
    args = " ".join(pairs)
elif kind == "carry":
    mode = st.radio("Что считать", ["G10", "EM", "Пара", "Свой список"], horizontal=True)
    if mode == "Пара":
        p = norm_pair(st.text_input("Валютная пара", placeholder="USDJPY"))
        pairs = [p] if p else []
        args = p
    elif mode == "Свой список":
        args = " ".join(st.text_input("Валюты через пробел", placeholder="MXN BRL ZAR TRY").upper().split())
    else:
        args = mode
elif kind == "banks":
    args = " ".join(st.multiselect("Центробанки (до 3)", BANKS, default=["FED"], max_selections=3))
elif kind == "countries":
    args = " ".join(st.multiselect("Страны (до 3)", COUNTRIES, default=["US"], max_selections=3))
elif kind == "calendar":
    window = st.radio("Период", ["this week", "next week", "2 weeks"], horizontal=True,
                      format_func={"this week": "Эта неделя", "next week": "След. неделя",
                                   "2 weeks": "2 недели"}.get)
    flt = " ".join(st.text_input("Фильтр по валютам/парам (необязательно)", placeholder="USD JPY EURUSD")
                   .upper().split())
    args = f"{window} {flt}".strip()
elif kind == "universe":
    args = st.radio("Акцент", ["GLOBAL", "G10", "EM"], horizontal=True)
elif kind == "scan":
    mode = st.radio("Набор валют", ["G10", "EM", "ALL", "Свой список"], horizontal=True)
    args = (" ".join(st.text_input("Валюты через пробел", placeholder="EUR GBP JPY MXN").upper().split())
            if mode == "Свой список" else mode)

lang = st.radio("Язык отчёта", ["ru", "en"], horizontal=True,
                format_func=lambda x: "Русский" if x == "ru" else "English")

left = DAILY_LIMIT - used_today()
if st.button("Получить отчёт", type="primary", disabled=left <= 0, width="stretch"):
    if not args:
        st.error("Заполните поле выше")
    elif any(not TICKER_RE.match(t) for t in tickers):
        st.error("Тикер выглядит некорректно")
    elif any(not re.fullmatch(r"[A-Z]{6}", p) for p in pairs):
        st.error("Пара должна состоять из двух кодов валют, например EURUSD или USD/JPY")
    else:
        jid = find_cached(command, args, lang) or start_job(command, args, lang)
        st.query_params["job"] = jid
        st.rerun()

st.caption(f"Осталось отчётов сегодня: {max(left, 0)} из {DAILY_LIMIT}. "
           "For educational/research purposes only. Not financial advice.")
