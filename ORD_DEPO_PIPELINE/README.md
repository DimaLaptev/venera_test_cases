# ORD_DEPO_PIPELINE

Самодостаточный сервис сборки отчётов **Ord_Quantity** и **СВОД_поДЕПО**
с запуском в Docker и триггером по письму:

- `Ord <YYYY_MM>` → Ord_Quantity
- `Svod <YYYY_MM>` → СВОД_поДЕПО (REGION выгружается по API)
- `Svod <YYYY_MM> dir` → СВОД_поДЕПО, файлы `_SVOD/REGION` без скачивания по API

Требуется **Python 3.8+** (образ Docker — `python:3.8-slim`).

## Быстрый старт (локально без Docker)

```bash
cd ORD_DEPO_PIPELINE
export REPORTS_DEPO_DIRECTORY=..   # каталог с 2026_01
python scripts/run_pipeline.py --period 2026_01
python scripts/run_svod_pipeline.py --period 2026_05
```

Для Ord нужна книга-основа `{period}/{period}_Ord_Quantity.xlsx`.
Для Svod — входы в `{period}/_SVOD/` (перед сборкой копируются `GPB/R`, `RSD/R`,
`RSD/REP` и выгружается REGION по API ЛК; подробности в [`svod/README.md`](svod/README.md)).

## Почта

Сервис `scripts/mail_poller.py` раз в минуту (или `MAIL_POLL_INTERVAL_SEC`)
опрашивает IMAP (`MAIL_SERVER_NAME` + `MAIL_1_*`). Темы `Ord <…>` / `Svod <…>`
(для СВОД опционально `dir` — не качать REGION по API) запускают сборку
под `REPORTS_DEPO_DIRECTORY`.
При ошибке отправителю уходит SMTP-отбивка.

Для smoke без сети: `MAIL_MOCK=1`.

Техдолг по IMAP reconnect/retry: [`TECH_DEBT.md`](TECH_DEBT.md).

## Docker

Прод:

```bash
cd ORD_DEPO_PIPELINE
# заполнить .env (см. .env_example)
docker compose up -d --build
```

Локально (корень репозитория монтируется в `/mnt/share`):

```bash
cd ORD_DEPO_PIPELINE
docker compose -f docker-compose.local.yaml build
docker compose -f docker-compose.local.yaml run --rm --entrypoint python ord_depo \
  scripts/run_pipeline.py --period 2026_01
docker compose -f docker-compose.local.yaml run --rm --entrypoint python ord_depo \
  scripts/run_svod_pipeline.py --period 2026_06
```

## Справочник ENC / SVOD

Файл `Справочник.xlsx` берётся из
`{REPORTS_DEPO_DIRECTORY}/depo_validation/Справочник.xlsx`
(для Ord также: `--sprav-workbook`).
