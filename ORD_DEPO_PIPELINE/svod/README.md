# SVOD DEPO (внутри ORD_DEPO_PIPELINE)

Сборка `СВОД_поДЕПО.xlsx` и `СВОД_поДЕПО_ДОМ.xlsx` для периода `YYYY_MM`
под `REPORTS_DEPO_DIRECTORY/<period>/_SVOD/`.

## Запуск через ORD

```bash
# prepare (GPB/R, RSD/R, RSD/REP, REGION по API) + сборка
python scripts/run_svod_pipeline.py --period 2026_05

# или только сборка (файлы уже в _SVOD/)
python scripts/run_svod_pipeline.py --period 2026_05 --skip-prepare
```

Тема письма: `Svod <2026_05>` (см. `scripts/mail_poller.py`).

## Пути

| Что | Путь |
|-----|------|
| Входы | `{reports}/{period}/_SVOD/{GPB,RSD_MSG,RSD_EXL,REGION,VTBSD}` |
| Справочник | `{reports}/depo_validation/Справочник.xlsx` |
| Пред. месяц | `{reports}/{prev}/_SVOD/СВОД_поДЕПО*.xlsx` |
| Выход | `{reports}/{period}/_SVOD/СВОД_поДЕПО*.xlsx` |

Перед сборкой копируются:
- `{period}/GPB/R` → `_SVOD/GPB` (имя содержит последнюю дату месяца)
- `{period}/RSD/R` → `_SVOD/RSD_MSG` (то же)
- `{period}/RSD/REP` → `_SVOD/RSD_EXL` (всё содержимое)
- CASD API ЛК Region (`REGION_LK_*` в `.env`) → `_SVOD/REGION` (Excel для колонки «Состояние»)

## Документация

- [`memory/SVOD_DEPO_spec.md`](memory/SVOD_DEPO_spec.md)
- [`memory/DO_column_mapping.md`](memory/DO_column_mapping.md)
- [`memory/VTB_codifier_rules.md`](memory/VTB_codifier_rules.md)
