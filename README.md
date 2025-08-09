# Async SEO Analyzer

Async-first SEO analyzer inspired by `pyseoanalyzer`, designed to fetch and analyze pages concurrently for faster crawls.

## Features
- Async HTTP fetching with concurrency limits
- robots.txt and crawl-delay compliance
- Optional sitemap seeding (XML/TXT)
- Page analysis parity: headings, meta, OG tags, anchor/image checks
- Fast tokenization and n-grams using NumPy stride windows
- ThreadPoolExecutor offload for HTML parsing and analysis
- CLI and Python API
- Basic metrics (fetch/parse time, pages, skipped non-HTML)

## Install

```bash
pip install -e .
```

Dev extras (tests):
```bash
pip install -e '.[dev]'
```

### Install from a ZIP/Tarball

1) Download the source archive (GitHub → Code → Download ZIP or a release asset)
2) Unpack the archive, then in the project root:
```bash
python -m venv .venv
source .venv/bin/activate
# user install
pip install -e .
# or with dev/test tools
pip install -e '.[dev]'
```

### Install by Cloning the Repository

```bash
git clone https://github.com/your-org/async-seo-analyzer.git
cd async-seo-analyzer
python -m venv .venv
source .venv/bin/activate
pip install -e .
# optional dev deps
pip install -e '.[dev]'
```

## CLI

```bash
python -m async_seo_analyzer.__main__ URL [options]
```

Common options:
- `--follow-links` Follow internal links
- `--max-depth` Depth when following links (default: 3)
- `--concurrency` Max concurrent fetches (default: 20)
- `--workers` Thread pool size for CPU tasks (default: auto)
- `-s/--sitemap` Optional sitemap URL to seed
- `-f/--output-format` json or html (json default)

Example:
```bash
python -m async_seo_analyzer.__main__ https://example.com --follow-links --max-depth 1 --workers 4 -f json
```

## Python API

```python
from async_seo_analyzer import analyze
result = analyze("https://example.com", follow_links=True, max_depth=1, workers=4)
```

Result keys:
- `pages`: List of per-page dicts (title, description, warnings, wordcount, n-grams, content_hash)
- `duplicate_pages`: Groups of URLs with identical content_hash
- `keywords`: Site-level keywords from words and n-grams (count > 4)
- `errors`: Reserved for future
- `total_time`: Seconds elapsed
- `crawl_metrics`: { fetch_ms_total, parse_ms_total, pages, skipped_non_html }

## Docker

Build image:
```bash
docker build -t async-seo-analyzer -f DOCKERFILE .
```

Run:
```bash
docker run --rm async-seo-analyzer https://example.com --follow-links --max-depth 1 -f json
```

Compose:
```bash
docker compose run --rm analyzer https://example.com --follow-links --max-depth 1 -f json
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

See `CONTRIBUTING.md` for more info.