#!/usr/bin/env python3
"""
Find and probe Philips firmware links for your own model.

This is a careful helper around the historical curl workflow:
  1. fetch the public support page;
  2. extract download.p4c.philips.com links;
  3. probe a small list of model/language filename candidates with HEAD.

It does not bypass authentication, guess private URLs, or download vendor
firmware automatically. Use --download with a URL you have verified, or use curl.
The package is not redistributed by this repository.
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import Iterable, List
from urllib.parse import urljoin

import requests

DOWNLOAD_HOST_RE = re.compile(r"https://download\.p4c\.philips\.com[^\"'<> ]+")
DEFAULT_LANGS = ("eng", "tra")


def extract_download_links(html: str) -> List[str]:
    return sorted(set(DOWNLOAD_HOST_RE.findall(html)))


def candidate_names(model_slug: str, languages: Iterable[str] = DEFAULT_LANGS) -> List[str]:
    names = []
    for lang in languages:
        names.append(f"{model_slug}_pkg_{lang}.zip")
        names.append(f"{model_slug}_fw_{lang}.zip")
    return names


def probe(url: str, timeout: float = 20.0) -> tuple[int, str, str]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        return (
            response.status_code,
            response.headers.get("Content-Length", "?"),
            response.url,
        )
    except requests.RequestException as exc:
        return 0, "?", str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Find/probe Philips firmware links for your own TV.")
    parser.add_argument("--model", required=True, help="support-page slug, e.g. 55pus8000_12")
    parser.add_argument(
        "--support-url",
        help="override the support page URL (default: https://www.philips.com/c-w/support-main/<model>.html)",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=list(DEFAULT_LANGS),
        help="filename language suffixes to probe (default: eng tra)",
    )
    parser.add_argument("--probe", action="store_true", help="HEAD the candidate filenames")
    parser.add_argument("--download", metavar="URL", help="stream a verified URL to --output")
    parser.add_argument("-o", "--output", default="firmware.zip", help="download destination")
    args = parser.parse_args()

    if args.download:
        print(f"downloading {args.download} -> {args.output}")
        try:
            with requests.get(args.download, stream=True, timeout=60) as response:
                response.raise_for_status()
                total = response.headers.get("Content-Length", "?")
                print(f"HTTP {response.status_code}, Content-Length {total}")
                with open(args.output, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
        except requests.RequestException as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"saved {args.output}")
        return 0

    support_url = args.support_url or f"https://www.philips.com/c-w/support-main/{args.model}.html"
    print(f"support page: {support_url}")
    try:
        page = requests.get(support_url, timeout=30)
        page.raise_for_status()
    except requests.RequestException as exc:
        print(f"ERROR: could not fetch support page: {exc}", file=sys.stderr)
        return 1

    links = extract_download_links(page.text)
    if links:
        print("\nlinks found on the support page:")
        for link in links:
            print(f"  {link}")
    else:
        print("\nno download.p4c.philips.com links found on the page")

    if args.probe:
        print("\nprobing candidate filenames (HEAD):")
        base = "https://download.p4c.philips.com/files/5/"
        for name in candidate_names(args.model, args.languages):
            status, size, final = probe(urljoin(base, name))
            print(f"  {status:>3}  {size:>12}  {name}  {final}")

    print(
        "\nOnly use a package that matches your TV's Main SW ID. "
        "Verify the hash, keep a backup, and do not redistribute vendor firmware."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
