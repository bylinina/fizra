# 💪 Тренировки

Мини-апп на Streamlit: предлагает тренировку из истории с тренером,
ведёт дневник выполнения на GitHub. Несколько пользователей (у каждого своя история).

## Файлы
- `app.py` — приложение
- `workouts.json` — 22 тренировки (июль 2024 — август 2026)
- `requirements.txt` — зависимости
- `history.json` — создастся сам при первой отметке «Сделала»

## Как запустить

### 1. Репозиторий
Залей все файлы в публичный GitHub-репозиторий (например, `workout-app`).

### 2. Personal Access Token
Нужен токен с правом записи в этот репозиторий:
- **Fine-grained token** (рекомендуется): Settings → Developer settings →
  Fine-grained tokens → выбери только этот репозиторий → Permissions →
  **Contents: Read and write**.
- либо **classic token** со scope `repo`.

### 3. Деплой на Streamlit Community Cloud
- share.streamlit.io → New app → укажи репозиторий и `app.py`.
- В **Settings → Secrets** вставь (подставь свои значения):

```toml
[github]
token = "ghp_твой_токен"
owner = "твой_логин_github"
repo  = "workout-app"
branch = "main"
history_path = "history.json"
```

Готово. Открываешь апп, вводишь имя, жмёшь «Дай тренировку».

## Локальный запуск (для проверки)
```bash
pip install -r requirements.txt
# создай .streamlit/secrets.toml с тем же содержимым, что выше
streamlit run app.py
```

## Настройки
В `app.py` вверху: `LRU_POOL` — из скольких «давно не деланных» тренировок
выбирается случайная (по умолчанию 6). Меньше — строже к свежести, больше — разнообразнее.
