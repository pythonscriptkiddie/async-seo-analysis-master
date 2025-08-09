#!/usr/bin/env python3
import argparse
import json
from . import __version__
from .analyzer import analyze


def main():
    parser = argparse.ArgumentParser(description="Analyze SEO aspects of a website (async).")
    parser.add_argument("site", help="URL of the site to analyze.")
    parser.add_argument("-s", "--sitemap", help="URL of the sitemap to seed the crawler with.")
    parser.add_argument(
        "-f",
        "--output-format",
        choices=["json", "html"],
        default="json",
        help="Output format.",
    )
    parser.add_argument("--analyze-headings", action="store_true", default=False)
    parser.add_argument("--analyze-extra-tags", action="store_true", default=False)
    parser.add_argument("--follow-links", action="store_true", default=False)
    parser.add_argument("--max-depth", type=int, default=3, help="Max crawl depth when following links.")
    parser.add_argument("--concurrency", type=int, default=20, help="Max concurrent fetches.")
    parser.add_argument("--workers", type=int, default=0, help="Thread pool workers for CPU-bound analysis (0 = auto).")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    result = analyze(
        args.site,
        sitemap_url=args.sitemap,
        analyze_headings=args.analyze_headings,
        analyze_extra_tags=args.analyze_extra_tags,
        follow_links=args.follow_links,
        max_depth=args.max_depth,
        concurrency=args.concurrency,
        workers=args.workers,
    )

    if args.output_format == "html":
        html = (
            "<html><head><meta charset='utf-8'><title>Async SEO Analyzer</title></head><body>"
            f"<h1>Results for {args.site}</h1>"
            f"<pre>{json.dumps(result, indent=2)}</pre>"
            "</body></html>"
        )
        print(html)
    else:
        print(json.dumps(result, indent=4, separators=(",", ": ")))


if __name__ == "__main__":
    main()