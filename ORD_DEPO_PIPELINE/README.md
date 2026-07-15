# ORD_DEPO_PIPELINE

Самодостаточный сервис сборки отчёта **Ord_Quantity** с запуском в Docker и
триггером по письму (тема `Ord <YYYY_MM>`).

Требуется **Python 3.8+** (образ Docker — `python:3.8-slim`).

Снимок логики сборки на момент создания каталога (копии из корневых
`scripts/` / `src/` / `memory/`). Корневые исходники репозитория не меняются.

## Быстрый старт (локально без Docker)

```bash
cd ORD_DEPO_PIPELINE
export REPORTS_DEPO_DIRECTORY=..   # каталог с 2026_01
python scripts/run_pipeline.py --period 2026_01
```

Нужна книга-основа `{period}/{period}_Ord_Quantity.xlsx` со справочниками
«Счета депо» и «Коды» в каталоге периода.

## Почта

Сервис `scripts/mail_poller.py` раз в минуту (или `MAIL_POLL_INTERVAL_SEC`)
опрашивает IMAP (`MAIL_SERVER_NAME` + `MAIL_1_*`). Письмо с темой
`Ord <2026_05>` запускает сборку периода `2026_05` под `REPORTS_DEPO_DIRECTORY`.
При ошибке отправителю уходит SMTP-отбивка.

Для smoke без сети: `MAIL_MOCK=1`.

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
```

## Справочник ENC

Файл `Справочник.xlsx` берётся из
`{REPORTS_DEPO_DIRECTORY}/depo_validation/Справочник.xlsx`
(переопределение: `--sprav-workbook`).
