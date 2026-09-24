# Release & Course-Deployment Guide (Last updated: 9/24/26)

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
   It runs either on your own laptop ([Option A](#3-run-the-course-proxy-on-your-own-machine-option-a))
   or on Carolina CloudApps ([Option B](#4-option-b-the-proxy-on-carolina-cloudapps-openshift)).

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
| Ledger file | Option A: Windows `C:\dlc-proxy\dlc_proxy.db` · macOS `$HOME/dlc-proxy/dlc_proxy.db` · Option B: the volume `dlc-proxy-data` mounted at `/data` | proxy variable `DLC_PROXY_DB`: a folder **outside** the repo; it holds the telemetry |
| LAN address of the proxy machine (Option A only) | `192.168.…` / `10.…` (step 3.3) | inside the two URLs below |
| Course server URL | Option A: `http://<LAN address>:8321` · Option B: `https://dlc-proxy-<project>.apps.cloudapps.unc.edu` | **students paste it** under Settings → Course server |
| Admin dashboard | the course server URL + `/admin/view` | you, with the admin token |

The three proxy variables are the same for both options. Under Option A
you type them into a terminal window; under Option B they live in one
OpenShift Secret and never touch a file.

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
For anything more, see [Option B](#4-option-b-the-proxy-on-carolina-cloudapps-openshift).

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

## 4. Option B: the proxy on Carolina CloudApps (OpenShift)

[Carolina CloudApps](https://cloudapps.unc.edu) is UNC's Red Hat OpenShift
cluster, free to UNC affiliates. The proxy runs there as one container with
an HTTPS address that students reach from anywhere include campus Wi-Fi, home,
mobile data, and its ledger sits on a persistent volume that survives
restarts, redeploys and code updates. No laptop stays awake, no port is
opened, no certificate is managed. Any OpenShift 4 cluster works the same
way; the repo ships the two files it needs, `proxy/Dockerfile` (the
container) and `proxy/openshift/dlc-proxy.yaml`.

You need: a CloudApps account and a project (the console is
`console.apps.cloudapps.unc.edu`, Developer view; the project name below is
`<project>`), your fork on GitHub with `proxy/Dockerfile` on the branch you
deploy (a private fork also needs a Source Secret, a public one does not),
and the filled-in course card for key and token look up. Every step below 
is a console form; nothing is typed into a terminal.

### 4.1 The Secret: the only place the three values live

Left menu **Secrets** (check the project selector at the top shows your
project) → **Create → Key/value secret**:

- Secret name: `dlc-proxy-secrets`
- three keys, values from the course card: `ANTHROPIC_API_KEY`,
  `DLC_COURSE_TOKEN`, `DLC_ADMIN_TOKEN`

Create. The `builder-dockercfg-…`, `default-dockercfg-…` and
`deployer-dockercfg-…` secrets already in the list belong to the cluster;
leave them alone.

### 4.2 Import the proxy from GitHub

**+Add → Import from Git**, then top to bottom:

| Field | Value | Why |
|---|---|---|
| Git Repo URL | your fork, e.g. `https://github.com/<you>/<fork>` | wait for *Validated* |
| Show advanced Git options → Git reference | `master` | empty means "default branch", which works too, but be explicit |
| Context dir | `/` | the Dockerfile copies `pyproject.toml`, `uv.lock`, `dlc/` and `proxy/` from the repo root |
| Source Secret | none | public fork |
| the box *Builder Image detected* → **Edit Import Strategy** | choose **Dockerfile**, Dockerfile path `proxy/Dockerfile` | the console only looks for a Dockerfile at the repo root; ours is in `proxy/`. If there is no Dockerfile choice at all, the cluster forbids Dockerfile builds: ask its admins, or use Option A |
| Application name / Name | `dlc` / `dlc-proxy` | the name becomes every object's name and the hostname: `dlc-proxy-<project>.apps.cloudapps.unc.edu` |
| Build option | BuildConfig | |
| Show advanced Build option | leave the three boxes ticked, **leave its environment variables empty** | that block also feeds the build, and a Dockerfile build bakes the values into the image; the tokens belong at runtime only |
| Resource type | Deployment | |
| Show advanced Deployment option → Environment variables (runtime only) | **Add from ConfigMap or Secret** three times: Name `ANTHROPIC_API_KEY`, resource `dlc-proxy-secrets`, key `ANTHROPIC_API_KEY`; the same for `DLC_COURSE_TOKEN` and `DLC_ADMIN_TOKEN` | the Name box is what the proxy reads, so it must equal the key, case-sensitive. Leave *Auto deploy when new Image is available* ticked; keep 1 replica |
| Target port | `8080` | filled from the Dockerfile's `EXPOSE` |
| Create a route | ticked → Show advanced Routing options: **Secure Route** ticked, TLS termination **Edge**, Insecure traffic **Redirect**; hostname, path and all certificate boxes empty | Edge means the cluster holds a valid certificate and talks plain HTTP to the pod; empty certificate boxes mean the router's own wildcard certificate, zero maintenance |

**Create.** The console jumps to Topology; the build takes about a minute
(click the `dlc-proxy` circle → Resources tab → the build → View logs; it
ends with *Push successful*). A dark-blue ring means the pod is running.
The ↗ arrow on the circle opens the public URL, which answers
`{"detail":"Not Found"}` - the proxy has no home page. Add `/v1/health` to
that address for the real check. Do it now once: all four flags must
read `true`, which proves the Secret landed.

### 4.3 Storage

Until this step the ledger sits on the pod's throwaway disk, and every
redeploy would wipe it. Topology → click the circle → Actions → Add
Storage:

- **Create new claim**
- StorageClass: the one marked *(default)* (`snap` on CloudApps; the snap
  class keeps volume snapshots, which is free insurance for the ledger)
- PersistentVolumeClaim name `dlc-proxy-data`
- Access mode **Single user (RWO)**, Size **1 GiB**, Volume mode Filesystem
- Mount path `/data`, read-only unticked, Subpath empty

Save. The pod restarts once, and from now on `/data/dlc_proxy.db` lives on
the volume. Everything logged before this step is gone, so run the real
tests after it.

### 4.4 Recreate strategy (required)

Topology → circle → **Actions → Edit Deployment** (the form view, not
*Edit dlc-proxy*, which reopens the import page) → Deployment strategy →
Strategy type **Recreate** → Save.

Why: the default rolling update starts the new pod before stopping the old
one. With a single-user volume the new pod either hangs waiting for the
volume or, worse, two proxies write the same SQLite file. Recreate stops the
old pod first; each update costs about 20 seconds of downtime and loses
nothing.

Then **Actions → Add Health Checks** (Sample setup): a Readiness probe and a Liveness probe,
both HTTP GET, path `/v1/health`, port `8080`, timeout 3 s; readiness with
initial delay 5 s and period 15 s, liveness with initial delay 30 s and
period 60 s. Confirm each probe with its ✓, then Add. Readiness keeps
students off a pod that is still starting; liveness restarts a hung process
without you noticing. No startup probe: the proxy is up in two seconds.

### 4.5 Check it and fill in the course card

Open `https://dlc-proxy-<project>.apps.cloudapps.unc.edu/v1/health` in a
browser. The same four flags as 3.2 must read `true`, and `db_path` must be
`/data/dlc_proxy.db`. A `false` means the environment rows in Edit
Deployment are missing or misnamed.

Write on the course card: course server URL
`https://dlc-proxy-<project>.apps.cloudapps.unc.edu` (no port, no path),
dashboard = the same + `/admin/view`.

### 4.6 Day to day

- **Leave it alone.** The pod runs without the console open. If the cluster
  restarts it during maintenance, the volume keeps the ledger and the probes
  bring it back. The health URL is the five-second check before class.
- **Change the API key or rotate a token**: Secrets → `dlc-proxy-secrets` →
  Actions → **Edit Secret** → change the value → Save, then Topology →
  Actions → **Restart rollout**. The pod reads the Secret only when it
  starts, so without the restart the old value stays in use. About 20
  seconds of downtime; ledger, limits and student settings are untouched.
- **Update the proxy code**: push to the deployed branch, then left menu
  **Builds** → `dlc-proxy` → Actions → **Start build**. The finished image
  deploys itself (Recreate, 20 seconds), and the ledger stays: that is what
  the volume is for. Proxy-only changes never need a student re-release.
- **Raise or lower the whole-class breaker**: Edit Deployment → Environment
  variables → Add value `DLC_GLOBAL_DAILY_CALLS` / `DLC_GLOBAL_DAILY_USD`.
- **Back up**: the CSV exports in section 5 are the evaluation-ready copy;
  the snap storage class snapshots the volume itself.
- **Pause for the semester**: Topology → circle → Details tab → the ↓ arrow
  on the pod count to 0. The ledger stays on the volume; ↑ brings the proxy
  back with everything in place. Delete the project only after exporting.

### 4.7 The same setup from the `oc` command line

`proxy/openshift/dlc-proxy.yaml` creates the same objects (ImageStream,
BuildConfig from `proxy/Dockerfile`, 1 GiB volume, Recreate Deployment with
probes, Service, edge-TLS Route) for anyone who prefers the CLI. Set the
`uri` in the file to your fork, then:

```bash
oc login …                                      # from the console's "Copy login command"
oc project <project>
oc create secret generic dlc-proxy-secrets \
    --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
    --from-literal=DLC_COURSE_TOKEN=course-... \
    --from-literal=DLC_ADMIN_TOKEN=admin-...
oc apply -f proxy/openshift/dlc-proxy.yaml
oc start-build dlc-proxy --follow
oc get route dlc-proxy                          # the hostname students paste (https://…)
```

Do not apply the file on top of a deployment made through the console (4.2):
the names collide.

### 4.8 What breaks Option B

- **The build fails on its first line**, pulling `python:3.12-slim`: Docker
  Hub's pull limit or a blocked download. Start the build again a little
  later; if it keeps failing, the `FROM` line in `proxy/Dockerfile` is the
  place to change.
- **A health flag is `false`**: an environment row in Edit Deployment is
  missing or its Name differs from the Secret key.
- **The pod restarts in a loop after Add Storage**: the pod log (Resources
  tab → the pod → View logs) says why; a permission error on `/data` means
  the storage class does not suit a single-user volume — pick the other one.
- **Students get *can't be reached***: they pasted the URL with `http://`,
  a port, or `/admin/view` on the end. The URL is the bare `https://…` host.

## 5. Watch the admin dashboard (optional)

Open the dashboard URL from the course card (the course server URL +
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
2. Option A: restart the proxy with the new `DLC_COURSE_TOKEN`.
   Option B: Edit Secret, then Restart rollout (4.6).
3. Announce the new token; students paste it in Settings → Course server.

No re-release, no re-download; identities, history, and limits are
untouched.

## 8. End-of-release checklist

- [ ] Suite green (`uv run pytest -q`, with `DIGITAL_JAR` set) on the tagged commit.
- [ ] Release published; download + `START_HERE` tested on a clean machine.
- [ ] Proxy started with no `WARNING:` line (Option A) or built and running
      (Option B); `/v1/health` shows `course_token_set`, `admin_token_set`,
      `key_configured`, `key_format_ok` all `true`.
- [ ] Option A: the second-computer test (3.4) passed: LAN URL + token
      connects and runs one AI feature, the dashboard lists the machine, and
      `localhost` on that laptop is refused.
- [ ] Option B: the health URL answers on a phone on mobile data, one AI
      feature ran through the cluster, and the dashboard still lists it after
      a Restart rollout (4.5).
- [ ] **Rotate the development API key** and set the new one only in the
      proxy variables (Option B: Edit Secret + Restart rollout).
