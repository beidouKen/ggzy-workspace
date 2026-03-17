"""
ggzy_detail_fetch.py — 全国公共资源交易平台详情页抽取工具

功能：
  1. 从 A-page（容器页）提取元数据 + 获取 B-page URL
  2. 从 B-page（内容页）提取正文、结构化字段、附件
  3. 返回统一的 DetailResult 结构

页面结构：
  A-page: /information/deal/html/a/{province}/{type}/{date}/{id}.html
    - h4.h4_o → 标题
    - p.p_o → 项目编号 / 信息来源
    - firstLastUrl → B-page 默认 URL

  B-page: /information/deal/html/b/{province}/{type}/{date}/{id}.html
    - h4.h4_o → 标题
    - p.p_o > span → 发布时间 / 信息来源
    - div#mycontent → 正文（table 或 HTML）
    - a[href] → 附件链接
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://www.ggzy.gov.cn"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE_URL}/deal/dealList.html",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ggzy_detail_fetch")


@dataclass
class Attachment:
    """附件信息。"""
    name: str
    url: str


@dataclass
class DetailResult:
    """详情页抽取结果。"""
    title: str = ""
    publish_date: str = ""
    region: str = ""
    issuer: str = ""
    agency: str = ""
    budget: str = ""
    content_text: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    project_code: str = ""
    source_platform: str = ""
    original_link: str = ""
    detail_url: str = ""
    b_page_url: str = ""
    structured_fields: dict[str, str] = field(default_factory=dict)


def _extract_date_from_meta(text: str) -> str:
    """从元数据文本中提取日期。"""
    patterns = [
        r"(?:发布时间|签署时间|公告时间)[：:]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)",
        r"(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""


def _extract_budget(text: str) -> str:
    """从正文中提取预算金额。"""
    patterns = [
        r"(?:预算金额|合同金额|最高限价|中标金额|成交金额|投资金额|控制价|招标控制价|总投资|工程造价|项目估算|概算总投资)[：:]\s*([0-9,.]+\s*(?:万?元|万))",
        r"(?:预算金额|合同金额|最高限价|中标金额|成交金额|投资金额|控制价|招标控制价)[：:]\s*([0-9,.]+)",
        # 多行: "预算金额：\n1980000.00 元"
        r"(?:预算金额|合同金额|最高限价|中标金额|成交金额)[：:]\s*\n\s*([0-9,.]+\s*(?:万?元|元|万)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""


def _extract_issuer(text: str) -> str:
    """提取采购人/招标人，支持同行和多行格式。"""
    # 同行: 采购人名称：xxx
    for pat in [
        r"(?:采购人名称|招标人名称|采购人|招标人|甲方|建设单位)[：:]\s*([^\n,，。；;]{2,60})",
    ]:
        m = re.search(pat, text)
        if m:
            val = m.group(1).strip()
            if val and val not in ("名称", "信息") and len(val) >= 2:
                return re.split(r"[,，。；;\s]", val)[0]

    # 多行: "采购人信息\n名称：\nxxx"
    m = re.search(r"采购人信息\s*\n\s*名称[：:]\s*\n\s*(.+)", text)
    if m:
        return m.group(1).strip()

    # 多行: "招标人\n名称：\nxxx" 或 "招标人信息\n名称：\nxxx"
    m = re.search(r"招标人(?:信息)?\s*\n\s*名称[：:]\s*\n\s*(.+)", text)
    if m:
        return m.group(1).strip()

    # 多行: "招标人：\nxxx" (换行在冒号后)
    m = re.search(r"(?:招标人|采购人|建设单位)[：:]\s*\n\s*([^\n]{2,60})", text)
    if m:
        val = m.group(1).strip()
        if val and not val.startswith(("名称", "地址", "联系")):
            return val

    return ""


def _extract_agency(text: str) -> str:
    """提取代理机构，支持同行和多行格式。"""
    for pat in [
        r"(?:代理机构名称|采购代理机构名称|代理机构|招标代理)[：:]\s*([^\n,，。；;]{2,60})",
    ]:
        m = re.search(pat, text)
        if m:
            val = m.group(1).strip()
            if val and val != "名称" and len(val) >= 2:
                return re.split(r"[,，。；;\s]", val)[0]

    # 多行: "采购代理机构信息\n名称：\nxxx"
    m = re.search(r"(?:采购)?代理机构信息\s*\n\s*名称[：:]\s*\n\s*(.+)", text)
    if m:
        return m.group(1).strip()

    return ""


def _parse_table_fields(table: Tag) -> dict[str, str]:
    """从 table.detail_Table 中提取 th/td 键值对。"""
    fields: dict[str, str] = {}
    for row in table.select("tr"):
        th = row.select_one("th")
        td = row.select_one("td")
        if th and td:
            key = th.get_text(strip=True)
            val = td.get_text(strip=True)
            if key and val:
                fields[key] = val
    return fields


def _extract_attachments(soup: BeautifulSoup) -> list[Attachment]:
    """提取附件链接。"""
    attachment_exts = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".7z")
    attachments: list[Attachment] = []
    seen_urls: set[str] = set()

    for a in soup.select("a[href]"):
        href = a.get("href", "")
        name = a.get_text(strip=True)

        is_attachment = False
        href_lower = href.lower()
        for ext in attachment_exts:
            if ext in href_lower:
                is_attachment = True
                break

        if not is_attachment and name:
            name_lower = name.lower()
            for ext in attachment_exts:
                if name_lower.endswith(ext):
                    is_attachment = True
                    break

        if is_attachment and href and href not in seen_urls:
            if not href.startswith("http"):
                href = BASE_URL + href
            attachments.append(Attachment(name=name or href.split("/")[-1], url=href))
            seen_urls.add(href)

    return attachments


def fetch_detail(
    detail_url: str,
    session: requests.Session | None = None,
    timeout: int = 15,
    retry_count: int = 3,
) -> DetailResult:
    """
    抽取单条公告的详情信息。

    Args:
        detail_url: A-page URL（列表页中的 detail_url）
        session: requests 会话
        timeout: 超时秒数
        retry_count: 重试次数

    Returns:
        DetailResult 结构化详情数据
    """
    http = session or requests.Session()
    http.headers.update(DEFAULT_HEADERS)

    result = DetailResult(detail_url=detail_url)

    # Step 1: Fetch A-page
    a_resp = _fetch_with_retry(http, detail_url, timeout, retry_count)
    a_resp.encoding = "utf-8"
    a_soup = BeautifulSoup(a_resp.text, "lxml")

    # Extract from A-page
    title_el = a_soup.select_one("h4.h4_o")
    if title_el:
        result.title = title_el.get_text(strip=True)

    meta_el = a_soup.select_one("p.p_o")
    if meta_el:
        spans = meta_el.find_all("span")
        for sp in spans:
            text = sp.get_text(strip=True)
            if "编号" in text:
                code = text.split("：")[-1].split(":")[-1].strip()
                result.project_code = code
            platform_label = sp.select_one("label#platformName")
            if platform_label:
                result.source_platform = platform_label.get_text(strip=True)

    # Find B-page URL
    first_url_match = re.search(r"firstLastUrl\s*=\s*'([^']+)'", a_resp.text)
    if not first_url_match:
        logger.warning("No B-page URL found for %s", detail_url)
        return result

    b_path = first_url_match.group(1)
    b_url = BASE_URL + b_path
    result.b_page_url = b_url

    # Step 2: Fetch B-page
    b_resp = _fetch_with_retry(http, b_url, timeout, retry_count)
    b_resp.encoding = "utf-8"
    b_soup = BeautifulSoup(b_resp.text, "lxml")

    # Extract publish date from B-page meta
    b_meta = b_soup.select_one("p.p_o")
    if b_meta:
        result.publish_date = _extract_date_from_meta(b_meta.get_text())
        platform_label = b_meta.select_one("label#platformName")
        if platform_label and not result.source_platform:
            result.source_platform = platform_label.get_text(strip=True)

    # Extract content from #mycontent
    content_el = b_soup.select_one("#mycontent")
    if content_el:
        # Check for structured table
        detail_table = content_el.select_one("table.detail_Table")
        if detail_table:
            result.structured_fields = _parse_table_fields(detail_table)

        result.content_text = content_el.get_text(separator="\n", strip=True)
    else:
        body = b_soup.find("body")
        if body:
            detail_div = body.select_one("div.detail")
            if detail_div:
                result.content_text = detail_div.get_text(separator="\n", strip=True)
            else:
                result.content_text = body.get_text(separator="\n", strip=True)

    # Extract specific fields from text
    full_text = result.content_text
    if not result.issuer:
        result.issuer = _extract_issuer(full_text)
        if not result.issuer and "采购人名称" in result.structured_fields:
            result.issuer = result.structured_fields["采购人名称"]
        if not result.issuer and "招标人" in result.structured_fields:
            result.issuer = result.structured_fields["招标人"]

    if not result.agency:
        result.agency = _extract_agency(full_text)
        if not result.agency:
            for key in result.structured_fields:
                if "代理" in key:
                    result.agency = result.structured_fields[key]
                    break

    if not result.budget:
        result.budget = _extract_budget(full_text)
        if not result.budget:
            for key in ("合同金额", "预算金额", "中标金额"):
                if key in result.structured_fields:
                    result.budget = result.structured_fields[key]
                    break

    # Extract original link
    for a in b_soup.select("a[href]"):
        text = a.get_text(strip=True)
        if "原文" in text and a.get("href", "").startswith("http"):
            result.original_link = a["href"]
            break

    # Extract attachments
    result.attachments = _extract_attachments(b_soup)

    logger.info(
        "Detail fetched: %s (fields: title=%s, date=%s, issuer=%s, budget=%s, attachments=%d)",
        detail_url[:60],
        bool(result.title),
        bool(result.publish_date),
        bool(result.issuer),
        bool(result.budget),
        len(result.attachments),
    )

    return result


def _fetch_with_retry(
    session: requests.Session,
    url: str,
    timeout: int,
    retry_count: int,
) -> requests.Response:
    """带重试的 HTTP GET。"""
    last_error: Exception | None = None
    for attempt in range(1, retry_count + 1):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("Attempt %d/%d for %s: %s", attempt, retry_count, url[:60], exc)
            if attempt < retry_count:
                time.sleep(1.5 * attempt)

    raise RuntimeError(f"Failed to fetch {url} after {retry_count} attempts: {last_error}")


def save_detail(result: DetailResult, output_path: Path) -> None:
    """保存详情数据到 JSON 文件。"""
    data = asdict(result)
    data["attachments"] = [asdict(a) for a in result.attachments]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved detail to %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="ggzy.gov.cn detail page extractor")
    parser.add_argument("url", help="Detail page URL (A-page URL)")
    parser.add_argument("--output", default="", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    result = fetch_detail(args.url)

    if args.json:
        data = asdict(result)
        data["attachments"] = [asdict(a) for a in result.attachments]
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"Title: {result.title}")
        print(f"Date: {result.publish_date}")
        print(f"Issuer: {result.issuer}")
        print(f"Agency: {result.agency}")
        print(f"Budget: {result.budget}")
        print(f"Platform: {result.source_platform}")
        print(f"Project Code: {result.project_code}")
        print(f"Content length: {len(result.content_text)} chars")
        print(f"Attachments: {len(result.attachments)}")
        for att in result.attachments:
            print(f"  - {att.name}: {att.url[:80]}")
        if result.structured_fields:
            print(f"Structured fields:")
            for k, v in result.structured_fields.items():
                print(f"  {k}: {v}")

    if args.output:
        save_detail(result, Path(args.output))


if __name__ == "__main__":
    main()
