# Техдолг (tech debt) — ORD_DEPO_PIPELINE

## IMAP: reconnect / retry при обрыве сессии

**Статус:** открыто  
**Область:** `scripts/mail_poller.py`, `src/mail/imap_client.py`  
**Симптом:** `imaplib.IMAP4.abort: command: FETCH => Connection is closed. 13`  
(и аналогичные abort на `SEARCH` / `STORE`)

### Контекст

При опросе почты (до сборки Ord_Quantity / СВОД_поДЕПО) IMAP-сервер может закрыть
соединение (таймаут, сеть, лимит сессии, ответ `BYE`). Сейчас `fetch_unseen()` /
`mark_seen()` не переподключаются: цикл `process_once` падает, traceback печатается
в `run_loop`, письмо может остаться `UNSEEN` до следующего интервала опроса.

Корневая причина обычно инфраструктурная; в коде не хватает устойчивости к обрыву.

### Что сделать

1. Обернуть IMAP-операции (`connect`, `fetch_unseen`, `mark_seen`) в retry
   (2–3 попытки с паузой) на `imaplib.IMAP4.abort` / `IMAP4.error`.
2. При обрыве: `close()` → новый `connect()` → повторить команду.
3. Не смешивать с логикой сборки отчёта (`runner` / Excel) — это только mail trigger.

### Заметки

- Долгая сборка уже вынесена **после** `fetch` + `mark_seen` (см. комментарий в
  `process_once`), чтобы сессия не рвалась на pipeline; retry нужен и на этапе
  самого `FETCH`.

## SMTP: письмо об успешной сборке

**Статус:** открыто  
**Область:** `scripts/mail_poller.py`, `src/mail/smtp_client.py`  
**Симптом:** после успешного Ord / СВОД пользователь не получает SMTP-уведомление

### Контекст

Сейчас SMTP шлёт только отбивку об ошибке (`send_error_reply`): при `result.ok == False`
или exception в сборке, на `From` письма-триггера (fallback — `GPB_VALIDATION_RECIPIENT`).
При успехе — только лог в stdout, без письма.

### Что сделать

1. Добавить `send_success_reply` (или общий helper) в `SmtpClient`: тема вида
   `Re: Ord/Svod <period>` / `Re: {original_subject}`, тело — краткое подтверждение
   успешной сборки (путь к книге / `result.message` по необходимости).
2. В `mail_poller.process_once` при `result.ok` вызывать отправку на тот же `to_addr`,
   что и для ошибок (`mail.from_addr` или `cfg.mail.recipient`).
3. Поддержать `MAIL_MOCK` (запись в `tmp/mail_mock/`), по аналогии с error-отбивкой.
4. Уточнить: нужно ли письмо и при CLI-запуске (`run_pipeline`) — по умолчанию
   только mail trigger, как у ошибок.
