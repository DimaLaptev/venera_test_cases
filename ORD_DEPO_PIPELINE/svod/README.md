# SVOD DEPO (внутри ORD_DEPO_PIPELINE)

Сборка `СВОД_поДЕПО.xlsx` и `СВОД_поДЕПО_ДОМ.xlsx` для периода `YYYY_MM`
под `REPORTS_DEPO_DIRECTORY/<period>/SVOD/`.

## Запуск через ORD

```bash
# prepare (GPB/R, RSD/R, RSD/REP) + сборка
python scripts/run_svod_pipeline.py --period 2026_05

# или только сборка (файлы уже в SVOD/)
python scripts/run_svod_pipeline.py --period 2026_05 --skip-prepare
```

Тема письма: `Svod <2026_05>` (см. `scripts/mail_poller.py`).

## Пути

| Что | Путь |
|-----|------|
| Входы | `{reports}/{period}/SVOD/{GPB,RSD_MSG,RSD_EXL,REGION,VTBSD}` |
| Справочник | `{reports}/depo_validation/Справочник.xlsx` |
| Пред. месяц | `{reports}/{prev}/SVOD/СВОД_поДЕПО*.xlsx` |
| Выход | `{reports}/{period}/SVOD/СВОД_поДЕПО*.xlsx` |

Перед сборкой копируются:
- `{period}/GPB/R` → `SVOD/GPB` (имя содержит последнюю дату месяца)
- `{period}/RSD/R` → `SVOD/RSD_MSG` (то же)
- `{period}/RSD/REP` → `SVOD/RSD_EXL` (всё содержимое)

## Документация

- [`memory/SVOD_DEPO_spec.md`](memory/SVOD_DEPO_spec.md)
- [`memory/DO_column_mapping.md`](memory/DO_column_mapping.md)
- [`memory/VTB_codifier_rules.md`](memory/VTB_codifier_rules.md)
