from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    )
}

TITLE_HINTS = re.compile(r"(job title|position|role)\s*[:\-]\s*(.+)", re.I)
COMPANY_HINTS = re.compile(r"(company|employer)\s*[:\-]\s*(.+)", re.I)


def fetch_page(url: str) -> tuple[str, str]:
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()
        return str(response.url), response.text


def extract_job_text(html: str, url: str = "") -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    heading = soup.find(["h1", "h2"])
    if heading:
        title = heading.get_text(" ", strip=True) or title

    company = ""
    company_el = soup.find(attrs={"class": re.compile(r"company|employer|org", re.I)})
    if company_el:
        company = company_el.get_text(" ", strip=True)[:120]

    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text[:12000]

    if not company:
        match = COMPANY_HINTS.search(text)
        if match:
            company = match.group(2).strip()[:120]
    if not title:
        match = TITLE_HINTS.search(text)
        if match:
            title = match.group(2).strip()[:160]

    needs_cover = bool(
        re.search(r"cover\s*letter|lettre de motivation", html, re.I)
    )
    return {
        "title": title[:160],
        "company": company[:120],
        "jd_text": text,
        "company_blurb": text[:800],
        "needs_cover_letter": needs_cover,
        "url": url,
    }
