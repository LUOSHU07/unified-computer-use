# unified-computer-use

Unified local computer-use runtime: drive a browser (Edge/Chrome via Playwright) and Windows desktop apps (via UI Automation) through **one JSON Action/Observation protocol**, with human-in-the-loop gates.

## What it is

One CLI (`scripts/ucu.py`) and one protocol (`scripts/protocol.py`) cover both browser and desktop GUI automation:

- **Browser** — `navigate` / `click` / `fill` / `read` / `snapshot` / `evaluate` / `screenshot` (Playwright + system Edge/Chrome; `@eN` token-efficient element refs)
- **Desktop** — `launch` / `fill` / `read` / `click` / `snapshot` (Windows UI Automation, ValuePattern/InvokePattern, no mouse simulation)
- **Human-in-the-loop** — `borrow_confirm` / `request_help` / `cooperate`
- **Two modes** — in-process (`ucu run`) and persistent daemon (`ucu serve` + `ucu call`)

## Install

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```

Requires Python 3.10+, `playwright`, and (for desktop) `uiautomation` on Windows. The browser driver auto-detects system Edge/Chrome — no browser download needed.

## Usage

```bash
python scripts/ucu.py doctor

# one-shot, in-process
python scripts/ucu.py run --json '{"type":"navigate","target":"https://example.com"}'
python scripts/ucu.py run --driver desktop --json '{"type":"read"}'
echo '{"type":"snapshot"}' | python scripts/ucu.py run

# daemon (persistent; avoids per-action browser/app startup cost)
python scripts/ucu.py serve --port 52810
python scripts/ucu.py call --json '{"type":"snapshot"}'
```

Output is always one JSON object on stdout: `{"ok":true,"observation":{...}}` or `{"ok":false,"error":"..."}` (exit 0/1). Any agent that can run a shell can drive it.

## Action protocol

Twelve action types share one schema across browser and desktop. Full reference: [`references/action-protocol.md`](references/action-protocol.md).

## Verify

```bash
python scripts/verify.py   # protocol round-trip + browser→notepad e2e + CLI smoke
```

## License

MIT
