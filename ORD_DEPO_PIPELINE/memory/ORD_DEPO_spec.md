# ORD_DEPO — спецификация сервиса

## Назначение

Сборка книги `{period}_Ord_Quantity.xlsx` из каталога периода `YYYY_MM`
под `REPORTS_DEPO_DIRECTORY`.

## Триггеры

1. CLI: `python scripts/run_pipeline.py --period 2026_05`
2. Почта: тема `Ord <2026_05>` на ящик `GPB_VALIDATION_RECIPIENT` / `MAIL_1_*`

## Цепочка сборки (внутри пайплайна)

`fill_ord_period.py`: Dks → REPs → СВОД_операций → ORD Количество поручений

Схема колонок: [Ord_Quantity_headers.json](Ord_Quantity_headers.json),
[Ord_Quantity_sheet_spec.md](Ord_Quantity_sheet_spec.md).

## Env

Требуется **Python 3.8+** (Docker: `python:3.8-slim`).

| Переменная | Назначение |
|------------|------------|
| `REPORTS_DEPO_DIRECTORY` | Корень с каталогами `2026_05`, … |
| `GPB_VALIDATION_RECIPIENT` | Адрес ящика для опроса |
| `MAIL_SERVER_NAME` | Хост IMAP/SMTP |
| `MAIL_1_USERNAME` / `MAIL_1_PASSWORD` / `MAIL_1_ADDRESS` | Учётка |
| `MAIL_POLL_INTERVAL_SEC` | Интервал опроса (default 60) |
| `MAIL_MOCK` | `1` — без сети, отбивки в `tmp/mail_mock/` |
