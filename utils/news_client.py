import logging
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from xml.etree import ElementTree

import requests

logger = logging.getLogger(__name__)

RSS_FEEDS = (
    ("최신", "http://www.yonhapnewstv.co.kr/browse/feed/"),
    ("경제", "http://www.yonhapnewstv.co.kr/category/news/economy/feed/"),
)


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _HTMLTextParser()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def _child_text(element: ElementTree.Element, name: str) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == name:
            return (child.text or "").strip()
    return ""


def _published_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        published = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            published = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    if published.tzinfo is None:
        published = published.astimezone()
    return published


def _matches_company(article_text: str, company_name: str, symbol: str) -> bool:
    normalized_text = article_text.casefold()
    terms = {company_name.strip(), symbol.strip()}
    terms.update(
        word for word in re.split(r"\s+", company_name.strip()) if len(word) >= 2
    )
    terms.discard("")
    terms.discard("종목")
    return any(term.casefold() in normalized_text for term in terms)


def _fetch_feed(category: str, url: str) -> list[dict[str, Any]]:
    response = requests.get(
        url,
        headers={"User-Agent": "python-basic-bloomberg-public/1.0"},
        timeout=15,
    )
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    articles: list[dict[str, Any]] = []

    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue

        title = _child_text(item, "title")
        link = _child_text(item, "link")
        if not link:
            link_element = next(
                (child for child in item if child.tag.rsplit("}", 1)[-1] == "link"),
                None,
            )
            if link_element is not None:
                link = link_element.attrib.get("href", "").strip()

        published_at = next(
            (
                _child_text(item, name)
                for name in ("pubDate", "published", "updated", "date")
                if _child_text(item, name)
            ),
            "",
        )
        description = _plain_text(
            _child_text(item, "description")
            or _child_text(item, "encoded")
            or _child_text(item, "summary")
        )
        published = _published_datetime(published_at)
        if not title or not link or published is None:
            continue
        if not link.startswith(("http://", "https://")):
            continue

        articles.append(
            {
                "title": _plain_text(title),
                "link": link,
                "source_name": f"연합뉴스TV · {category}",
                "published_at": published.astimezone().strftime("%Y-%m-%d %H:%M"),
                "_published": published,
                "description": description,
            }
        )

    return articles


def fetch_company_news(
    *,
    company_name: str,
    symbol: str = "",
    max_items: int = 5,
    days: int = 7,
) -> list[dict[str, Any]]:
    keyword = company_name.strip() or symbol.strip()
    if not keyword or max_items <= 0 or days <= 0:
        return []

    cutoff = datetime.now().astimezone() - timedelta(days=days)
    articles: list[dict[str, Any]] = []
    feed_errors: list[str] = []
    successful_feeds = 0

    for category, url in RSS_FEEDS:
        try:
            feed_articles = _fetch_feed(category, url)
            successful_feeds += 1
        except (requests.RequestException, ElementTree.ParseError, OSError) as error:
            logger.warning("연합뉴스TV %s RSS 수집 실패: %s", category, error)
            feed_errors.append(f"{category}: {error}")
            continue

        for article in feed_articles:
            published = article.pop("_published")
            if published < cutoff or not _matches_company(
                f"{article['title']} {article['description']}", company_name, symbol
            ):
                continue
            articles.append({**article, "_published": published})

    if successful_feeds == 0:
        raise RuntimeError("RSS 피드를 가져오지 못했습니다. " + " / ".join(feed_errors))

    unique_articles: dict[str, dict[str, Any]] = {}
    for article in sorted(
        articles,
        key=lambda item: item["_published"],
        reverse=True,
    ):
        unique_articles.setdefault(article["link"], article)

    results = list(unique_articles.values())[:max_items]
    for article in results:
        article.pop("_published")
    return results
