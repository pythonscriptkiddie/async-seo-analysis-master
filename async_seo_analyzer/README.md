# Async SEO Analyzer

Async-first SEO analyzer inspired by `pyseoanalyzer`, designed to fetch and analyze pages concurrently for faster crawls.

Status: scaffold with single-page analysis. Next steps: sitemap seeding, internal link following with concurrency limits, and parity with `pyseoanalyzer` output.

Install (editable):

```
pip install -e ./async_seo_analyzer
```

CLI:

```
async-seo-analyzer https://example.com --output-format json
```