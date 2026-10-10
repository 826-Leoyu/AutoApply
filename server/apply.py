from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from server.models import Job, Profile
from server.store import append_log, upsert_job

FIELD_RULES: list[tuple[list[str], str]] = [
    (["firstname", "first-name", "first_name", "given-name", "givenname"], "first"),
    (["lastname", "last-name", "last_name", "family-name", "surname"], "last"),
    (["fullname", "full-name", "full_name", "candidate-name", "name"], "full"),
    (["email", "e-mail"], "email"),
    (["phone", "tel", "mobile", "cell"], "phone"),
    (["city", "locality"], "city"),
    (["province", "state", "region"], "province"),
    (["postal", "zip", "postcode"], "postal"),
    (["country"], "country"),
    (["address", "street"], "address"),
    (["linkedin"], "linkedin"),
    (["website", "portfolio", "url"], "website"),
    (["password", "passwd"], "password"),
    (["work authorization", "work status", "citizenship", "permit", "eligible"], "status"),
]


def _value(profile: Profile, kind: str) -> str:
    parts = (profile.full_name or "").split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""
    mapping = {
        "first": first,
        "last": last,
        "full": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "city": profile.city,
        "province": profile.province,
        "postal": profile.postal_code,
        "country": profile.country,
        "address": profile.address,
        "linkedin": profile.linkedin,
        "website": profile.website,
        "password": profile.password,
        "status": profile.work_status,
    }
    return mapping.get(kind, "")


def _blob(locator_info: dict) -> str:
    bits = [
        locator_info.get("name") or "",
        locator_info.get("id") or "",
        locator_info.get("placeholder") or "",
        locator_info.get("aria-label") or "",
        locator_info.get("autocomplete") or "",
        locator_info.get("type") or "",
    ]
    return " ".join(bits).lower()


async def apply_to_job(job: Job, profile: Profile) -> Job:
    job.status = "applying"
    append_log(job, f"打开投递页 {job.url}")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(job.url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(800)
            cover_text = ""
            if job.cover_path:
                from server.resume_pdf import extract_resume_text

                cover_text = extract_resume_text(Path(job.cover_path))
            filled = await _fill_inputs(page, profile, cover_text)
            append_log(job, f"已尝试填写 {filled} 个字段")
            uploaded = await _upload_files(page, job)
            append_log(job, f"已尝试上传 {uploaded} 个文件")
            job.status = "needs_review"
            append_log(job, "浏览器已打开。请你检查、过验证码，再亲手点提交。关闭窗口即结束本次投递辅助。")
            upsert_job(job)
            try:
                await page.wait_for_event("close", timeout=15 * 60 * 1000)
            except PlaywrightTimeout:
                append_log(job, "等待超时，浏览器将关闭。若未提交请重新点「开始投递」。")
        except Exception as exc:  # noqa: BLE001 - surface to the job record
            job.status = "error"
            job.error = str(exc)
            append_log(job, f"投递辅助失败：{exc}")
        finally:
            await context.close()
            await browser.close()
    if job.status == "needs_review":
        job.status = "ready"
        append_log(job, "投递窗口已关闭，岗位回到可再次投递状态。")
    return upsert_job(job)


async def _fill_inputs(page, profile: Profile, cover_text: str = "") -> int:
    filled = 0
    locators = page.locator("input, textarea, select")
    count = await locators.count()
    for index in range(count):
        item = locators.nth(index)
        try:
            if not await item.is_visible():
                continue
            info = {
                "name": await item.get_attribute("name"),
                "id": await item.get_attribute("id"),
                "placeholder": await item.get_attribute("placeholder"),
                "aria-label": await item.get_attribute("aria-label"),
                "autocomplete": await item.get_attribute("autocomplete"),
                "type": await item.get_attribute("type"),
            }
            label_text = ""
            identity = info.get("id")
            if identity:
                label = page.locator(f"label[for='{identity}']")
                if await label.count():
                    label_text = (await label.first.inner_text()).strip()
            blob = _blob(info) + " " + label_text.lower()
            input_type = (info.get("type") or "text").lower()
            if input_type in {"hidden", "submit", "button", "checkbox", "radio", "file"}:
                continue
            tag = await item.evaluate("el => el.tagName.toLowerCase()")
            if cover_text and tag == "textarea" and any(word in blob for word in ("cover", "letter", "motivation")):
                await item.fill(cover_text)
                filled += 1
                continue
            kind = next((k for keys, k in FIELD_RULES if any(key in blob for key in keys)), None)
            if not kind:
                continue
            value = _value(profile, kind)
            if not value:
                continue
            if tag == "select":
                try:
                    await item.select_option(label=value)
                except Exception:
                    await item.select_option(value=value)
            else:
                await item.fill(value)
            filled += 1
        except Exception:
            continue
    return filled


async def _upload_files(page, job: Job) -> int:
    uploaded = 0
    locators = page.locator("input[type='file']")
    count = await locators.count()
    resume = Path(job.resume_path) if job.resume_path else None
    cover = Path(job.cover_path) if job.cover_path else None
    for index in range(count):
        item = locators.nth(index)
        info = ((await item.get_attribute("name")) or "") + " " + ((await item.get_attribute("id")) or "")
        info += " " + ((await item.get_attribute("accept")) or "")
        blob = info.lower()
        path: Path | None = None
        if cover and any(word in blob for word in ("cover", "letter", "motivation")):
            path = cover
        elif resume:
            path = resume
        if path and path.exists():
            await item.set_input_files(str(path))
            uploaded += 1
    return uploaded


def run_apply(job: Job, profile: Profile) -> Job:
    return asyncio.run(apply_to_job(job, profile))
