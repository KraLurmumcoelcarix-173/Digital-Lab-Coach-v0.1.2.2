# Release & Course-Deployment Guide (Last updated: 9/21/26)

The operational runbook for shipping DLC to a class. Written for the
instructor teaching undergraduates with Digital; students never need to read this file.
Assumes you have been working on a fork of DLC in order to fit it to your classroom.
Version numbers below are examples — use your own tag.

## What you have

Three pieces:

1. **A release zip** 
   Students: download → unzip → double-click `START_HERE` → paste the
   course URL + token in Settings → point at `Digital.jar` → debug
   circuit. Windows uses `START_HERE.bat`, macOS/Linux uses `./start.sh`.

2. **The course proxy** 
   a small server holding YOUR API key, with per-machine daily limits, 
   a whole-server daily circuit breaker, telemetry ingest, and the admin dashboard.

3. **Two secrets**: the course token students paste once, and the
   admin token only you hold that opens the admin dashboard.

Prerequisites: all tests in your fork are green (`uv run pytest -q`
with `DIGITAL_JAR` set so the jar-gated tests run too).

## 1. Build the zip and cut the GitHub release

1. Bump `version` in `pyproject.toml` and the Status line at the top of
   the README, commit.

2. Build the student zip:
   ```bash
   uv run python scripts/make_release_zip.py
   ```

3. Tag and push:
   ```bash
   git tag v0.1.2.2
   git push origin v0.1.2.2
   ```
4. On GitHub: **Releases → Draft a new release** → choose tag,
   title, and attach `dist/DigitalLabCoach.zip` as a release asset. 
   Keep the filename exactly `DigitalLabCoach.zip` - the README Download
   button URL depends on it and will keep working for every future version. 
   Publish.

5. Click the README's **Download** button to confirm it serves your zip.

## 2. Generate the course secrets and fill in the course card

Run once:

```bash
python -c "import secrets; print('course-' + secrets.token_urlsafe(18))"
python -c "import secrets; print('admin-'  + secrets.token_urlsafe(18))"
```

The first line is the **course token** (students get it), the second the
**admin token** (only you). Now fill in this card and keep it in a private
note **outside any git folder**. Every later step reads a value from it,
and nothing else in this guide asks you to remember anything.

| Course card | Your value | Used where |
|---|---|---|
| API key | `sk-ant-…` | proxy variable `ANTHROPIC_API_KEY` - never leaves the proxy |
| Course token | `course-…` | proxy variable `DLC_COURSE_TOKEN`; **students paste it** |
| Admin token | `admin-…` | proxy variable `DLC_ADMIN_TOKEN`; only you, on the dashboard |
| Ledger file | Windows `C:\dlc-proxy\dlc_proxy.db` · macOS `$HOME/dlc-proxy/dlc_proxy.db` | proxy variable `DLC_PROXY_DB`: a folder **outside** the repo; it holds the telemetry |
| LAN address of the proxy machine | `192.168.…` / `10.…` (step 3.3) | inside the two URLs below |
| Course server URL | `http://<LAN address>:8321` | **students paste it** under Settings → Course server |
| Admin dashboard | `http://<LAN address>:8321/admin/view` | you, with the admin token |

## 3. Run the course proxy on your own machine (Option A)

Use the built-in proxy if and only if you are collecting student data for 
classroom improvement study and you have had IRB permission from your 
department, else adjust the code in proxy/ to fit in the classroom.

The proxy holds your API key, enforces per-machine daily limits that
survive re-downloads, collects the anonymized telemetry, and serves the
admin dashboard. Endpoint reference: [../proxy/README.md](../proxy/README.md).

Option A means the proxy runs on your own laptop. It is right for a smoke
test and for one section on the same network; the laptop has to stay awake,
on the network, with the terminal window open, the whole time students work.
For anything more, see [Option B](#4-option-b--a-server-that-is-always-on).

### 3.1 Start it

Open **one** terminal window in your DLC fork and paste the block for your
OS, with the values from the course card. The variables belong to that one
window: set them and start the proxy in the same window, and keep it open as
closing it stops the proxy. `Ctrl+C` stops it on purpose.

**Windows - Command Prompt** (the prompt reads `C:\…>`; no quotes, no spaces
around `=`):

```bat
cd C:\path\to\your\DLC\fork
set ANTHROPIC_API_KEY=sk-ant-...
set DLC_COURSE_TOKEN=course-...
set DLC_ADMIN_TOKEN=admin-...
set DLC_PROXY_DB=C:\dlc-proxy\dlc_proxy.db
uv run uvicorn proxy.dlc_proxy:app --host 0.0.0.0 --port 8321
```

**Windows - PowerShell** (the prompt reads `PS C:\…>`):

```powershell
cd C:\path\to\your\DLC\fork
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:DLC_COURSE_TOKEN = "course-..."
$env:DLC_ADMIN_TOKEN = "admin-..."
$env:DLC_PROXY_DB = "C:\dlc-proxy\dlc_proxy.db"
uv run uvicorn proxy.dlc_proxy:app --host 0.0.0.0 --port 8321
```

**macOS / Linux - Terminal**:

```bash
cd ~/path/to/your/DLC/fork
export ANTHROPIC_API_KEY=sk-ant-...
export DLC_COURSE_TOKEN=course-...
export DLC_ADMIN_TOKEN=admin-...
export DLC_PROXY_DB=$HOME/dlc-proxy/dlc_proxy.db
uv run uvicorn proxy.dlc_proxy:app --host 0.0.0.0 --port 8321
```

`--host 0.0.0.0` means "answer on every network interface of this machine", 
which is what lets other laptops reach the proxy. The ledger folder is created if it does not exist.

A clean start prints no `WARNING:` line. Each missing value prints one,
naming the variable, so read the terminal once before going on.

### 3.2 Check it

In a second terminal on the same machine:

```bash
curl http://localhost:8321/v1/health
```

Four fields matter:

| Field | `true` means | `false` means |
|---|---|---|
| `course_token_set` | students can connect | the proxy **refuses every student request** until you set `DLC_COURSE_TOKEN` and restart |
| `admin_token_set` | the dashboard will open | it rejects every admin token, the right one included |
| `key_configured` | AI calls can go out | students see *"the course server has no API key configured — tell your instructor"* |
| `key_format_ok` | the key starts with `sk-` | the key was pasted wrong; AI calls fail with 401 |

The proxy fails closed: with no course token it serves nobody, so a missing
variable can never leave it open to whoever finds the URL, and a student
whose AI features work is a student who really holds the token. Whatever the
terminal says at startup, this output is the state of the running proxy.

### 3.3 Find the address students use

`localhost` in the check above means "this computer", it works only on the
proxy machine, and on a student's laptop it points at their own laptop. Every
other computer needs the proxy machine's address on the network. Run this
**on the proxy machine**:

| OS | Command | What to read |
|---|---|---|
| Windows | `ipconfig` | the **IPv4 Address** under the adapter you are actually connected through (Wi-Fi or Ethernet, not a disconnected one) |
| macOS | `ipconfig getifaddr en0` | the one line it prints (try `en1` if you are on Ethernet) |
| Linux | `hostname -I` | the first value |

It looks like `192.168.1.23`, `10.0.0.14` or `172.16.4.9`. Write it on the
course card: the course server URL is `http://<that address>:8321`, and the
dashboard is the same with `/admin/view`. That URL is what you announce.

### 3.4 Test it from a second computer

This is the test that matters, and it takes five minutes.

1. **On the proxy machine** (optional, proves the proxy and the key): open
   DLC → Settings → Course server, paste `http://localhost:8321` and the
   course token. It should answer *connected — token accepted ✓*. Run one
   AI feature.
2. **On a second laptop, on the same Wi-Fi**, with a fresh download of the
   zip: open DLC → Settings → Course server. If it already shows a
   connection from earlier, press **Disconnect** first. Paste
   `http://<LAN address>:8321` and the course token → *connected — token
   accepted ✓*. Run one AI feature. Then open the dashboard URL in a
   browser, enter the admin token: the second laptop is listed under
   Machines.
3. **Still on the second laptop**, try `http://localhost:8321` with the
   course token. Settings answers *saved, but the course server can't be
   reached right now…* and every AI feature says it cannot reach the course
   server. That is correct - `localhost` is that laptop - and it is also
   why nobody can use the AI features without the real URL and the token.
   A wrong token is answered with *server reachable but the token was
   REJECTED*.

When step 2 fails while step 1 worked, it is one of the four things below.

### 3.5 What breaks Option A

- **The firewall.** Windows Defender blocks port 8321 until you allow it
  (the prompt appears at the first launch; allow it on private *and* public
  networks as campus Wi-Fi counts as public). macOS asks once whether to
  accept incoming connections.
- **The address moves.** The router hands it out and can change it on
  reboot or when the machine joins a different network. Check `ipconfig` /
  `ipconfig getifaddr en0` again before each class, or reserve a fixed
  address on the router.
- **Client isolation.** Campus Wi-Fi often stops laptops reaching each other
  at all. If `curl http://<LAN address>:8321/v1/health` works on the proxy
  machine but fails from the second laptop, this is usually why, and only
  Option B gets around it.
- **Sleep.** A laptop that closes its lid stops serving. On macOS run the
  proxy as `caffeinate -i uv run uvicorn …`; on Windows set the power plan
  to never sleep while plugged in.

And one limit that is not a fault: a LAN address is reachable only from the
same network. From home, a coffee shop or mobile data, students get *can't be
reached*. The campus VPN may put them on the campus network, but do not
promise it. Off-campus use is what Option B is for.

### Spend protection (three layers by default, feel free to modify)

| Layer | Default | Tune with |
|---|---|---|
| Per-student daily caps | Mode A 1/day, Mode B 2/day | `dlc/l3/limits.py` `CAPS`; enforced only when the student app runs with `DLC_ENFORCE_LIMITS=1` (the release launchers set it) |
| Per-machine proxy backstop | modeA 4, modeB 4, grade 2, explain 2 calls/day | `CALL_BUDGETS` in `proxy/dlc_proxy.py` |
| Whole-server circuit breaker | 600 calls/day AND $20 est./day | env `DLC_GLOBAL_DAILY_CALLS`, `DLC_GLOBAL_DAILY_USD` |

The README's *Where to change what* table lists every other knob
(models, timeout, manifests, official tests, ROM payload, solutions
folder).

If the breaker is triggered, every AI request answers "the course server has
reached its daily capacity" until midnight (server time).

## 4. Option B — a server that is always on

Any ~$5/month VPS (1 vCPU / 1 GB) is plenty, and students can reach it from
anywhere.

1. Clone the repo on the VM, install uv, `uv sync`.
2. Put the env vars in a systemd unit so the proxy survives reboots:
   ```ini
   # /etc/systemd/system/dlc-proxy.service
   [Unit]
   Description=DLC course proxy
   After=network.target
   [Service]
   WorkingDirectory=/opt/dlc
   Environment=ANTHROPIC_API_KEY=sk-ant-...
   Environment=DLC_COURSE_TOKEN=...
   Environment=DLC_ADMIN_TOKEN=...
   Environment=DLC_PROXY_DB=/opt/dlc-proxy/dlc_proxy.db
   ExecStart=/root/.local/bin/uv run uvicorn proxy.dlc_proxy:app --host 127.0.0.1 --port 8321
   Restart=on-failure
   [Install]
   WantedBy=multi-user.target
   ```
   `systemctl enable --now dlc-proxy`
3. **HTTPS** (so tokens are never sent in the clear): put
   [Caddy](https://caddyserver.com) in front — a 2-line Caddyfile gets an
   automatic Let's Encrypt certificate:
   ```
   dlc.your-domain.edu {
       reverse_proxy 127.0.0.1:8321
   }
   ```
   Students then use `https://dlc.your-domain.edu` as the course URL.

Here the proxy is bound to `127.0.0.1` on purpose: only Caddy, on the same
machine, talks to it. Run the same health check on the VM, and the same
second-computer test from anywhere.

## 5. Watch the admin dashboard (optional)

Open the dashboard URL from the course card (or your HTTPS URL +
`/admin/view`) in a browser and enter the **admin token** once:

- machines with install_id hashed, events, today's LLM calls vs cap, today's and
  all-time estimated spend, breaker state, key health;
- the machines table (first/last seen, per-machine event and call counts);
- per-day activity and per-day LLM usage by machine and feature.

Raw data: `/admin/summary`, `/admin/daily`, `/admin/export.csv?table=events|machines|llm_calls`.

## 6. Announce to students

The course server URL and the course token from the card, plus the README's
Quick start. You got this lol.

## 7. Rotating the course token

Any time necessary:

1. Generate a new course token (step 2 command) and update the card.
2. Restart the proxy with the new `DLC_COURSE_TOKEN`.
3. Announce the new token; students paste it in Settings → Course server.

No re-release, no re-download; identities, history, and limits are
untouched.

## 8. End-of-release checklist

- [ ] Suite green (`uv run pytest -q`, with `DIGITAL_JAR` set) on the tagged commit.
- [ ] Release published; download + `START_HERE` tested on a clean machine.
- [ ] Proxy started with no `WARNING:` line; `/v1/health` shows
      `course_token_set`, `admin_token_set`, `key_configured`,
      `key_format_ok` all `true`.
- [ ] The second-computer test (3.4) passed: LAN URL + token connects and
      runs one AI feature, the dashboard lists the machine, and `localhost`
      on that laptop is refused.
- [ ] **Rotate the development API key** and set the new one only in the
      proxy variables.
