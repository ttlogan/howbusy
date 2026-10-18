# howbusy

Live busyness report for a Qwen/GX10 LLM lane on the DGX front door. A
read-only, ad-hoc status snapshot for the vLLM + LiteLLM serving stack: it
shows lane load, GPU state, KV cache pressure, prefix-cache hit rate,
spec-decode acceptance, per-consumer throughput, and LiteLLM spend.

It is the CLI counterpart to the [sparkDash](#relation-to-sparkdash) dashboard
and reads the same LiteLLM probe key and spend data.

> Safe to run at any time. Every probe is a read with a short timeout. It never
> restarts, writes to, or tunes the serving stack.

## Example output

```
╭─────────────────────────── gx10-head · qwen3.8-flash-next-uncensored ───────────────────────────╮
│                                                                                                │
│  System       load 0.65 1.27 2.18 · DGX 53C                                                    │
│  GPU          NVIDIA GB10 0% · 51C · 11.51W                                                    │
│  Queue        running 0/12 · ctx 262144 · waiting 0 (capacity 0, deferred 0)                    │
│  Latency      TTFT mean 52.54s · queue mean 0.000s · 1 reqs                                    │
│  Throughput   gen ~0.0 tok/s · prompt ~0.0 tok/s · KV 0.0% · prefix 0.0%                       │
│  Consumers      idle                                                                           │
│                 vLLM backend 2                                                                 │
╰────────────────────────────── 19 Oct 2026 01:30:27 · DGX rank 0 ───────────────────────────────╯
```

## What it reports

| Line | Source |
|------|--------|
| System | `/proc/loadavg`, DGX thermal zones |
| GPU | `nvidia-smi` (name, util, temp, power per GPU) |
| Queue | vLLM `num_requests_running/waiting` and waiting-by-reason (`capacity`, `deferred`); `--max-num-seqs` and `--max-model-len` read from the serving process |
| Latency | vLLM `time_to_first_token_seconds` and `request_queue_time_seconds` (mean over sampled requests) |
| Throughput | vLLM engine log (generation/prompt tok/s), `kv_cache_usage_perc`, `prefix_cache_queries_total`/`hits_total` |
| Spec-decode | MTP acceptance rate / mean acceptance length (only while running) |
| Consumers | LiteLLM spend DB top keys by token rate, or live connections by peer IP; vLLM backend peer count |

## Requirements

- Python 3.10+
- `rich` for the panel rendering
- `psql` available (LiteLLM spend DB windowed query)
- `nvidia-smi`, `podman`, `ss`, `cat /proc/loadavg` on the target host
- Read access to `/etc/sparkdash/env` (LiteLLM probe key) and
  `/etc/litellm/config.yaml` (spend DB DSN); the probe key is read at runtime and
  **never** printed or committed

## Install

```bash
git clone https://github.com/ttlogan/howbusy.git
cd howbusy
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional: make it available on PATH
sudo ln -sf "$(pwd)/howbusy.py" /usr/local/bin/howbusy
```

## Usage

```bash
howbusy.py
```

No arguments. On the GX10 head node it probes the local vLLM (127.0.0.1:8000)
and LiteLLM (127.0.0.1:4000) front doors and prints a single panel.

## How it works

- **Consumer throughput** comes from a windowed `SELECT` on the LiteLLM spend DB
  (top keys by total tokens over the last `WINDOW_MIN` minutes).
- **Note:** spend rows are written at request *completion*, so during one long
  generation the per-key rate reads low/0 until that request finishes; the
  window length is shown in the label so the number is interpretable.
- **KV / prefix** numbers come off `/metrics` so they read correctly even when
  idle.
- Reads `--max-num-seqs` and `--max-model-len` from the running `vllm serve`
  process so the Queue line reflects the actual serving config.

## Relation to sparkDash

This tool and the [sparkDash](https://github.com/ttlogan/sparkDash) dashboard
both operate the same DGX front door and share the same LiteLLM probe key
(`/etc/sparkdash/env`) and LiteLLM spend data. sparkDash is the long-running
web dashboard (Node/express + WebSocket, nginx); `howbusy` is the quick,
no-dependency CLI snapshot for a terminal. This exact script is also vendored
at `sparkDash/tools/howbusy.py`.

## Development

```bash
pip install -r requirements.txt
pytest -q
```

Tests cover the vLLM `/metrics` parser (including regression for scientific
notation with a negative exponent) and the log-line helper. CI runs them on
every push and PR to `master` via GitHub Actions (see `.github/workflows/ci.yml`).

## Security

No secrets are committed. The LiteLLM probe key is read from
`/etc/sparkdash/env` at runtime and used only in the `Authorization` header of
requests to the localhost LiteLLM API. The script never echoes the key.

## License

MIT
