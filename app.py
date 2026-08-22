"""
Тренировки — простой Streamlit-апп.

Что делает:
- спрашивает имя (у каждого своя история: мама, дочка и т.д.);
- предлагает тренировку из workouts.json методом LRU
  (чаще выпадают те, что давно не делались или не делались вовсе);
- по кнопке «Сделала» дописывает запись в history.json на GitHub;
- при следующем заходе подтягивает обновлённую историю с GitHub.

Хранение истории: файл history.json в том же GitHub-репозитории,
пишется через GitHub REST API (PUT .../contents/history.json).

Секреты (Streamlit → Settings → Secrets), пример в конце файла.
"""

import json
import base64
import random
from datetime import datetime, date

import requests
import streamlit as st

# ----------------------------------------------------------------------
# Конфиг из секретов
# ----------------------------------------------------------------------
GH_TOKEN = st.secrets["github"]["token"]
GH_OWNER = st.secrets["github"]["owner"]          # твой логин на GitHub
GH_REPO = st.secrets["github"]["repo"]            # имя репозитория
GH_BRANCH = st.secrets["github"].get("branch", "main")
HISTORY_PATH = st.secrets["github"].get("history_path", "history.json")

API = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{HISTORY_PATH}"
HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# LRU: из скольких «самых несвежих» тренировок выбираем случайную.
# Чем меньше — тем строже «давно не делала»; чем больше — тем разнообразнее.
LRU_POOL = 6


# ----------------------------------------------------------------------
# Данные тренировок (локальный файл в репо)
# ----------------------------------------------------------------------
@st.cache_data
def load_workouts():
    with open("workouts.json", encoding="utf-8") as f:
        data = json.load(f)
    return data["workouts"], data.get("meta", {})


# ----------------------------------------------------------------------
# История на GitHub
# ----------------------------------------------------------------------
def read_history():
    """Возвращает (history_dict, sha). sha=None если файла ещё нет."""
    r = requests.get(API, headers=HEADERS, params={"ref": GH_BRANCH})
    if r.status_code == 200:
        payload = r.json()
        content = base64.b64decode(payload["content"]).decode("utf-8")
        try:
            hist = json.loads(content) if content.strip() else {}
        except json.JSONDecodeError:
            hist = {}
        return hist, payload["sha"]
    elif r.status_code == 404:
        return {}, None  # файла ещё нет — создадим при первой записи
    else:
        raise RuntimeError(f"GitHub read error {r.status_code}: {r.text}")


def write_history(hist, sha, message):
    """Коммитит history.json на GitHub. Возвращает новый sha."""
    body = {
        "message": message,
        "content": base64.b64encode(
            json.dumps(hist, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii"),
        "branch": GH_BRANCH,
    }
    if sha:
        body["sha"] = sha  # обязателен при обновлении существующего файла
    r = requests.put(API, headers=HEADERS, data=json.dumps(body))
    if r.status_code in (200, 201):
        return r.json()["content"]["sha"]
    raise RuntimeError(f"GitHub write error {r.status_code}: {r.text}")


# ----------------------------------------------------------------------
# LRU-подбор
# ----------------------------------------------------------------------
def last_done_map(hist, user):
    """{workout_id: 'YYYY-MM-DD' последнего выполнения} для пользователя."""
    out = {}
    for rec in hist.get(user, []):
        wid = rec["workout_id"]
        d = rec["date"]
        if wid not in out or d > out[wid]:
            out[wid] = d
    return out

def pick_workout(workouts, hist, user):
    done = last_done_map(hist, user)
    # ключ сортировки: сначала никогда не деланные (дата = ''), потом по возрастанию даты
    ranked = sorted(workouts, key=lambda w: done.get(w["id"], ""))
    pool = ranked[:LRU_POOL] if len(ranked) >= LRU_POOL else ranked
    return random.choice(pool), done


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.set_page_config(page_title="Тренировки", page_icon="💪")
st.title("Тренировки 💪💀")

workouts, meta = load_workouts()

# --- имя пользователя ---
if "user" not in st.session_state:
    st.session_state.user = ""

if not st.session_state.user:
    st.subheader("Кто занимается?")
    name = st.text_input("Имя", placeholder="например, Лиза")
    if st.button("Войти", type="primary") and name.strip():
        st.session_state.user = name.strip()
        st.rerun()
    st.stop()

user = st.session_state.user
st.caption(f"Пользователь: **{user}**")
col_a, col_b = st.columns([1, 1])
if col_b.button("Сменить пользователя"):
    for k in ("user", "current", "history", "sha"):
        st.session_state.pop(k, None)
    st.rerun()

# --- грузим историю один раз за сессию ---
if "history" not in st.session_state:
    try:
        st.session_state.history, st.session_state.sha = read_history()
    except Exception as e:
        st.error(f"Не удалось прочитать историю с GitHub: {e}")
        st.stop()

hist = st.session_state.history

# --- подобрать тренировку ---
if col_a.button("🎲 Дай тренировку", type="primary") or "current" not in st.session_state:
    w, _ = pick_workout(workouts, hist, user)
    st.session_state.current = w

w = st.session_state.current
done = last_done_map(hist, user)

# --- карточка тренировки ---
st.divider()
st.subheader(w["title"])
last = done.get(w["id"])
if last:
    st.caption(f"В прошлый раз ты делала это: {last}")
else:
    st.caption("Ты это ещё не делала 🎉")

st.text(w["display"])

# --- отметить выполнение ---
st.divider()
if st.button("✅ Сделала!", type="primary"):
    rec = {
        "date": date.today().isoformat(),
        "workout_id": w["id"],
        "title": w["title"],
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    hist.setdefault(user, []).append(rec)
    try:
        new_sha = write_history(
            hist, st.session_state.sha,
            message=f"{user}: {rec['date']} {w['id']}",
        )
        st.session_state.sha = new_sha
        st.success("Записала в историю на GitHub! Молодец 🙌")
        st.session_state.pop("current", None)  # следующий заход = новый подбор
    except Exception as e:
        # откатываем локально, чтобы не разошлось с гитхабом
        hist[user].pop()
        st.error(f"Не смогла записать на GitHub: {e}")

# --- история пользователя ---
with st.expander(f"История ({len(hist.get(user, []))})"):
    recs = sorted(hist.get(user, []), key=lambda r: r["date"], reverse=True)
    if not recs:
        st.write("Пока пусто.")
    for r in recs:
        st.write(f"• {r['date']} — {r.get('title', r['workout_id'])}")

st.caption(
    f"Всего тренировок в базе: {len(workouts)} · "
    f"период: {meta.get('period', '—')}"
)
