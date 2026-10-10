from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from server.jd import HEADERS

SEARCH_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch"


def scan_jobs(keywords: str, location: str = "Canada", limit: int = 8) -> list[dict[str, str]]:
    params = {
        "searchstring": keywords,
        "locationstring": location,
        "sort": "D",
        "fage": "2",
    }
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
        response = client.get(SEARCH_URL, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        results: list[dict[str, str]] = []
        for article in soup.select("article, .result, .job-result, a.resultJobItem"):
            link = article if article.name == "a" else article.find("a", href=True)
            if not link or not link.get("href"):
                continue
            href = urljoin("https://www.jobbank.gc.ca", link["href"])
            if "jobposting" not in href and "jobsearch" not in href:
                continue
            title = link.get_text(" ", strip=True)
            if not title or len(title) < 4:
                heading = article.find(["h3", "h2", "h4"])
                title = heading.get_text(" ", strip=True) if heading else title
            company_el = article.find(class_=re.compile(r"business|company|employer", re.I))
            location_el = article.find(class_=re.compile(r"location|city", re.I))
            item = {
                "url": href.split("?")[0],
                "title": title[:160],
                "company": company_el.get_text(" ", strip=True)[:120] if company_el else "",
                "location": location_el.get_text(" ", strip=True)[:120] if location_el else location,
                "source": "jobbank",
            }
            if item["url"] in {row["url"] for row in results}:
                continue
            results.append(item)
            if len(results) >= limit:
                break

        if not results:
            for link in soup.select("a[href*='jobposting']"):
                href = urljoin("https://www.jobbank.gc.ca", link["href"])
                title = link.get_text(" ", strip=True)
                if not title:
                    continue
                results.append(
                    {
                        "url": href.split("?")[0],
                        "title": title[:160],
                        "company": "",
                        "location": location,
                        "source": "jobbank",
                    }
                )
                if len(results) >= limit:
                    break
        return results


def resolve_apply_url(job_url: str) -> str:
    """Prefer the employer apply link when Job Bank points off-site."""
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
        response = client.get(job_url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    for link in soup.select("a[href]"):
        text = link.get_text(" ", strip=True).lower()
        href = link["href"]
        if "jobbank.gc.ca" in href:
            continue
        if any(word in text for word in ("apply", "postuler", "website", "site web", "employer")):
            if href.startswith("http"):
                return href
    return job_url
