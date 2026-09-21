# DLC course proxy

One small server the instructor runs. It does three jobs:

1. **Key custody** — your Anthropic API key lives only here (env var).
   Students' tools relay LLM calls through `/v1/llm`; 

2. **Machine-keyed limits that survive re-downloads** — every install
   reports an anonymous id derived from the OS machine identifier. The
   proxy enforces per-day call budgets per feature (Mode A, Mode B,
   grading, explain) as the wipe-proof backstop behind the client's
   own per-analysis limits.

3. **Telemetry ingest** — students' local event spools sync here. 
   `/admin/summary` shows machines, event counts and an LLM spend estimate.

## Run it

The per-OS commands, the address students paste, and the checks to run
before class are in the instructor guide,
[../docs/RELEASE_GUIDE.md](../docs/RELEASE_GUIDE.md) §3. The short form:
four variables in one terminal window, then

```bash
uv run uvicorn proxy.dlc_proxy:app --host 0.0.0.0 --port 8321
```

| Variable | Meaning |
|---|---|
| `ANTHROPIC_API_KEY` | the key the relay uses; no endpoint ever returns it |
| `DLC_COURSE_TOKEN` | what students paste. Unset, the proxy refuses every `/v1/llm` and `/v1/events` request (503) |
| `DLC_ADMIN_TOKEN` | opens `/admin/*`. Unset, every admin request is refused |
| `DLC_PROXY_DB` | the SQLite ledger (default `./dlc_proxy.db`); keep it outside the repo |

`GET /v1/health` reports `course_token_set`, `admin_token_set`,
`key_configured` and `key_format_ok`; all four must read `true` before
class. Students paste `http://<proxy machine's LAN address>:8321` (or your
HTTPS URL) plus the course token under Settings → Course server; the tool
stores them in `~/.dlc/config.json` as `proxy_url` / `proxy_token`.

## Endpoints

| Route | What |
|---|---|
| `POST /v1/llm` | LLM relay (course-token gated): checks the machine's daily budget, attaches your key, forwards through the same client wrapper the tool uses, logs usage. With no key on the proxy it answers "no API key configured — tell your instructor" and spends nothing. |
| `POST /v1/events` | Telemetry batch ingest, deduped on (machine, row id); stamps each machine's authoritative first-seen date. |
| `GET /v1/health` | Liveness, counts, and the four configuration flags above. |
| `GET /admin/view` | The dashboard; asks for the admin token once. Its JSON feeds are `/admin/summary`, `/admin/daily`, `/admin/events`, `/admin/llm_texts`, `/admin/stats` (`?token=…` or header `X-DLC-Admin-Token`). |
| `GET /admin/export.csv?token=…&table=events\|machines\|llm_calls` | Raw CSVs for the evaluation pipeline. |

## Notes

- Per-machine budgets live in `CALL_BUDGETS` at the top of `dlc_proxy.py`
  (per machine, per server-day, per feature); the whole-class breaker is
  `DLC_GLOBAL_DAILY_CALLS` (600) and `DLC_GLOBAL_DAILY_USD` (20) in the
  environment. The README's *Changing the limits* section shows all three
  layers side by side.
- Storage is one SQLite file — back it up by copying it. The release zip
  never includes `.db` files, but keep the ledger outside the repo anyway.
- HTTPS: for a real semester put the proxy behind campus HTTPS or a
  reverse proxy (Try Caddy). Plain HTTP is fine for the second-computer smoke test.
- Keep the repo on the proxy host up to date with your fork — the relay
  reuses `dlc/llm/client.py` (same request shaping, timeouts, and
  reasoning-model handling as the tool itself).
