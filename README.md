# api-scout 🔍

Search and **live-verify** free public APIs from the [public-apis](https://github.com/public-apis/public-apis) list.

The public-apis list is a goldmine — but it is community-curated, and entries can be dead,
deprecated, or behind changed auth policies at any time. **api-scout** lets you filter the
list locally in milliseconds, then *actually probe every candidate over the network* and
tell you which ones still work, before you waste time integrating a dead endpoint.

## Features

- ⚡ **Local search** — parse the README into structured entries, filter by category / keyword / auth / HTTPS / CORS
- 🌐 **Live verification** — concurrently probe each API (URL-deduplicated, polite concurrency)
- ⚙️ **Two engines** — `threads` (requests) by default, or `async` (aiohttp) for large batches;
  async is ~1.6x faster and scales to much higher concurrency without GIL contention
- 🏷️ **Result taxonomy** — `OK` / `REACHABLE` / `ERROR` / `TIMEOUT` / `DEAD`, with response time and a body snippet
- 📦 **Three output formats** — terminal table, JSON (for pipelines), Markdown (for docs)
- 🧪 **Unit tested** — parser and verifier covered, network fully mocked

## Quick start

```bash
pip install -r requirements.txt

# point at a public-apis checkout (auto-detected: ../public-apis/README.md or ./README.md)
python main.py --keyword weather --limit 10          # list mode, no network
python main.py --category Weather --verify          # list + live check
python main.py --auth no --cors yes --verify        # browser-callable candidates only
python main.py --verify --format json --output verified.json
```

## CLI reference

| Option | Description |
|---|---|
| `--source PATH` | path to public-apis README.md (auto-detected by default) |
| `--keyword KW` | filter by keyword in name/description |
| `--category CAT` | filter by category, e.g. `Weather` |
| `--auth` | `no` / `apikey` / `oauth` / `x-mashape-key` / `user-agent` |
| `--cors` | `yes` / `no` / `unknown` |
| `--https` | `yes` / `no` |
| `--limit N` | show at most N entries |
| `--verify` | live-check each API (concurrent) |
| `--engine` | `threads` (default, requests) or `async` (aiohttp, faster at scale) |
| `--workers N` | verify concurrency (default 16) |
| `--timeout S` | per-request timeout (default 6 s) |
| `--format` | `table` / `json` / `markdown` |
| `--output FILE` | write the result to a file |

## Sample output

List mode (no network):

```
$ python main.py --keyword weather --limit 8
1678 APIs in list, 8 after filters

Name          Category        Auth    HTTPS  CORS
------------  --------------  ------  -----  -------
IQAir         Environment     apiKey  Yes    Unknown
InfraNode     Open Data       apiKey  Yes    Unknown
K-Data Gate   Open Data       apiKey  Yes    Unknown
AviationAPI   Transportation  No      Yes    No
OpenVan       Transportation  No      Yes    Yes
Weatherstack  Weather         apiKey  Yes    Unknown
7Timer!       Weather         No      No     Unknown
AccuWeather   Weather         apiKey  No     Unknown
```

Verify mode (live network probes):

```
$ python main.py --category Animals --verify --limit 8
1678 APIs in list, 8 after filters

Verifying 8 APIs (workers=8, timeout=6.0s)...
Result: OK=7, REACHABLE=1, ERROR=0, TIMEOUT=0, DEAD=0

Name       Category  Status     ms    Note
---------  --------  ---------  ----  -------------------------------------------
AdoptAPet  Animals   REACHABLE  229   HTTP 403 (needs key/params or path changed)
Axolotl    Animals   OK         1127  HTTP 200
Cat Facts  Animals   OK         590   HTTP 200
Cataas     Animals   OK         1232  HTTP 200
Cats       Animals   OK         1679  HTTP 200
Dog Facts  Animals   OK         592   HTTP 200
Dog Facts  Animals   OK         1139  HTTP 200
```

## How verification classifies results

| Status | Meaning |
|---|---|
| `OK` | HTTP 2xx — usable |
| `REACHABLE` | HTTP 4xx — server is alive, but likely needs a key/params, or the path changed |
| `ERROR` | HTTP 5xx — server-side failure |
| `TIMEOUT` | no response in time — rate-limited or slow |
| `DEAD` | could not connect (DNS / refused / SSL) |

Verification details:

- URLs are **deduplicated** — an entry listed twice is probed once
- `stream=True` + `iter_content()` — reads only a small chunk (auto-decompressed), never downloads whole payloads
- snippets are sanitized (non-UTF-8 bytes → `?`) so output is safe on any console encoding
- the process is polite: bounded concurrency, per-request timeout

## Project structure

```
api-scout/
├── main.py                  # CLI entry point (argparse)
├── scout/
│   ├── parser.py            # README markdown -> structured ApiEntry list
│   ├── verifier.py          # concurrent live probing + result taxonomy
│   └── report.py            # table / JSON / markdown rendering
├── tests/
│   ├── test_parser.py       # parser unit tests (no network)
│   └── test_verifier.py     # verifier unit tests (network mocked)
├── requirements.txt
└── README.md
```

## Tests

```bash
python -m unittest discover -s tests -v
```

The verifier tests mock `requests.get`, so the suite runs offline in ~0.01 s.

## Weekly verification report (GitHub Actions)

[`.github/workflows/weekly_verify.yml`](.github/workflows/weekly_verify.yml) runs every
Monday 03:00 UTC (and on demand via **Actions → Run workflow**):

1. fetches the latest public-apis README
2. verifies **all ~1,700 endpoints** (`weekly_report.py`)
3. commits `report.md` + `verified.json` back to the repo
4. also uploads them as a downloadable artifact

`report.md` contains a summary table plus 🔴 dead/broken, 🟡 reachable-but-may-need-auth,
and ✅ working-API sections. Local quick run:

```bash
python weekly_report.py --limit 30   # verify only the first 30 entries
```

## Web UI

A Flask + vanilla-JS dashboard (`web/`):

```bash
pip install -r requirements.txt
python web/app.py
# open http://127.0.0.1:5055
```

- filter by keyword / category / auth / CORS, then click **✓ Verify live** to probe
  up to 100 endpoints at once and see status badges (OK / REACHABLE / ERROR / TIMEOUT / DEAD)
- reads the local `public-apis` clone when present, otherwise fetches the latest README
  from GitHub (1 h cache)
- API endpoints: `GET /api/categories`, `GET /api/apis`, `POST /api/verify`

## Roadmap ideas

- [ ] async verifier with `aiohttp` (faster, fewer threads)
- [ ] `--health` mode: categorize `apiKey` APIs into "free tier" vs "signup required"
- [ ] GitHub Action that re-verifies the whole list weekly and files issues for dead links
- [ ] Web UI: filter + verify from the browser

## License

MIT
