import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
from pypdf import PdfReader

MENU_USER_AGENT = "NutriFlowAI/0.1 menu-discovery"
MENU_TIMEOUT_SECONDS = 10.0
MENU_LINK_TERMS = ("menu", "ementa", "carta", "cardapio", "food", "comida")
_PRICE_PATTERN = re.compile(r"(?P<price>\d{1,3}(?:[.,]\d{2}))\s*(?P<currency>€|eur)\b?", re.I)
_KCAL_PATTERN = re.compile(r"(?P<kcal>\d{2,4}(?:[.,]\d+)?)\s*kcal\b", re.I)


class RestaurantMenuScraperError(ValueError):
    pass


@dataclass(frozen=True)
class ScrapedMenuItem:
    name: str
    description: str | None
    price: Decimal | None
    currency: str
    energy_kcal: Decimal | None
    source_url: str


@dataclass(frozen=True)
class ScrapedRestaurantMenu:
    website: str
    pages_scanned: tuple[str, ...]
    items: tuple[ScrapedMenuItem, ...]


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _price(text: str) -> tuple[Decimal | None, str]:
    match = _PRICE_PATTERN.search(text)
    if match is None:
        return None, "EUR"
    value = _decimal(match.group("price"))
    return value, "EUR"


def _energy(text: str) -> Decimal | None:
    match = _KCAL_PATTERN.search(text)
    return None if match is None else _decimal(match.group("kcal"))


def _is_public_address(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return parsed.is_global


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RestaurantMenuScraperError("Restaurant menu URL must use public HTTP(S).")
    hostname = parsed.hostname.casefold()
    if hostname == "localhost" or hostname.endswith(".local"):
        raise RestaurantMenuScraperError("Restaurant menu URL cannot target a local host.")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            addresses = socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise RestaurantMenuScraperError("Restaurant website could not be resolved.") from exc
        if not addresses or any(not _is_public_address(item[4][0]) for item in addresses):
            raise RestaurantMenuScraperError("Restaurant website resolved to a non-public address.")
    else:
        if not literal.is_global:
            raise RestaurantMenuScraperError("Restaurant menu URL cannot target a private address.")


def _fetch_bytes(url: str) -> tuple[bytes, str]:
    _validate_public_url(url)
    request = Request(
        url,
        headers={"Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5", "User-Agent": MENU_USER_AGENT},
    )
    try:
        with urlopen(request, timeout=MENU_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get_content_type()
            return response.read(2_000_000), content_type
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RestaurantMenuScraperError("Restaurant menu page is unavailable.") from exc


def _robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        body, _ = _fetch_bytes(robots_url)
    except RestaurantMenuScraperError:
        return True
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(body.decode("utf-8", errors="ignore").splitlines())
    return parser.can_fetch(MENU_USER_AGENT, url)


def _json_ld_nodes(value: object):
    if isinstance(value, list):
        for item in value:
            yield from _json_ld_nodes(item)
        return
    if not isinstance(value, dict):
        return
    yield value
    graph = value.get("@graph")
    if graph is not None:
        yield from _json_ld_nodes(graph)
    for key in ("hasMenuSection", "hasMenuItem", "itemListElement", "mainEntity", "item"):
        child = value.get(key)
        if child is not None:
            yield from _json_ld_nodes(child)


def _type_names(value: object) -> set[str]:
    if isinstance(value, str):
        return {value.casefold()}
    if isinstance(value, list):
        return {item.casefold() for item in value if isinstance(item, str)}
    return set()


def _offer(node: dict[str, object]) -> tuple[Decimal | None, str]:
    raw = node.get("offers")
    if isinstance(raw, list):
        raw = next((item for item in raw if isinstance(item, dict)), None)
    if not isinstance(raw, dict):
        return None, "EUR"
    price = _decimal(raw.get("price"))
    currency = _clean_text(raw.get("priceCurrency")) or "EUR"
    return price, currency.upper()


def _json_ld_energy(node: dict[str, object]) -> Decimal | None:
    nutrition = node.get("nutrition")
    if not isinstance(nutrition, dict):
        return None
    calories = nutrition.get("calories")
    if isinstance(calories, (int, float, Decimal)):
        return _decimal(calories)
    return _energy(str(calories or ""))


def _parse_json_ld(soup: BeautifulSoup, source_url: str) -> list[ScrapedMenuItem]:
    result: list[ScrapedMenuItem] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _json_ld_nodes(payload):
            types = _type_names(node.get("@type"))
            if not types.intersection({"menuitem", "product"}):
                continue
            name = _clean_text(node.get("name"))
            if name is None or len(name) > 160:
                continue
            price, currency = _offer(node)
            result.append(
                ScrapedMenuItem(
                    name=name,
                    description=_clean_text(node.get("description")),
                    price=price,
                    currency=currency,
                    energy_kcal=_json_ld_energy(node),
                    source_url=source_url,
                )
            )
    return result


def _parse_html_blocks(soup: BeautifulSoup, source_url: str) -> list[ScrapedMenuItem]:
    selectors = (
        "[itemtype*='MenuItem']",
        "[itemtype*='Product']",
        ".menu-item",
        ".menu-product",
        ".dish",
        "article.product",
    )
    result: list[ScrapedMenuItem] = []
    seen_blocks: set[int] = set()
    for selector in selectors:
        for block in soup.select(selector):
            identity = id(block)
            if identity in seen_blocks:
                continue
            seen_blocks.add(identity)
            name_node = block.select_one("[itemprop='name'], h2, h3, h4, .name, .title")
            name = _clean_text(name_node.get_text(" ") if name_node is not None else None)
            if name is None or len(name) > 160:
                continue
            block_text = " ".join(block.stripped_strings)
            raw_price = block.select_one("[itemprop='price'], .price")
            price = _decimal(raw_price.get("content")) if raw_price is not None else None
            currency = "EUR"
            if price is None:
                price, currency = _price(block_text)
            description_node = block.select_one("[itemprop='description'], .description, p")
            description = _clean_text(
                description_node.get_text(" ") if description_node is not None else None
            )
            result.append(
                ScrapedMenuItem(
                    name=name,
                    description=description,
                    price=price,
                    currency=currency,
                    energy_kcal=_energy(block_text),
                    source_url=source_url,
                )
            )
    return result


def parse_html_menu(html: str, *, source_url: str) -> tuple[ScrapedMenuItem, ...]:
    soup = BeautifulSoup(html, "html.parser")
    items = _parse_json_ld(soup, source_url) + _parse_html_blocks(soup, source_url)
    return _dedupe_items(items)


def parse_pdf_menu(data: bytes, *, source_url: str) -> tuple[ScrapedMenuItem, ...]:
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise RestaurantMenuScraperError("Restaurant PDF menu could not be read.") from exc
    items: list[ScrapedMenuItem] = []
    for line in text.splitlines():
        normalized = " ".join(line.split())
        match = _PRICE_PATTERN.search(normalized)
        if match is None:
            continue
        name = normalized[: match.start()].strip(" .-–—")
        if not name or len(name) > 160:
            continue
        price, currency = _price(normalized)
        items.append(
            ScrapedMenuItem(
                name=name,
                description=None,
                price=price,
                currency=currency,
                energy_kcal=_energy(normalized),
                source_url=source_url,
            )
        )
    return _dedupe_items(items)


def _dedupe_items(items: list[ScrapedMenuItem]) -> tuple[ScrapedMenuItem, ...]:
    result: list[ScrapedMenuItem] = []
    seen: set[tuple[str, Decimal | None]] = set()
    for item in items:
        key = (item.name.casefold(), item.price)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)


def _menu_links(html: str, *, page_url: str, website_host: str) -> tuple[str, ...]:
    soup = BeautifulSoup(html, "html.parser")
    result: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        text = " ".join(anchor.stripped_strings).casefold()
        combined = f"{href.casefold()} {text}"
        if not any(term in combined for term in MENU_LINK_TERMS) and not href.casefold().endswith(
            ".pdf"
        ):
            continue
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme in {"http", "https"} and parsed.hostname == website_host:
            result.append(absolute)
    return tuple(dict.fromkeys(result))


def scrape_restaurant_menu(
    website: str,
    *,
    max_pages: int = 4,
    max_items: int = 80,
) -> ScrapedRestaurantMenu:
    _validate_public_url(website)
    parsed_website = urlparse(website)
    host = parsed_website.hostname
    if host is None:
        raise RestaurantMenuScraperError("Restaurant website has no hostname.")

    queue = [website]
    scanned: list[str] = []
    collected: list[ScrapedMenuItem] = []
    while queue and len(scanned) < max_pages and len(collected) < max_items:
        url = queue.pop(0)
        if url in scanned or not _robots_allows(url):
            continue
        data, content_type = _fetch_bytes(url)
        scanned.append(url)
        if content_type == "application/pdf" or urlparse(url).path.casefold().endswith(".pdf"):
            collected.extend(parse_pdf_menu(data, source_url=url))
            continue
        html = data.decode("utf-8", errors="ignore")
        collected.extend(parse_html_menu(html, source_url=url))
        for link in _menu_links(html, page_url=url, website_host=host):
            if link not in scanned and link not in queue:
                queue.append(link)

    return ScrapedRestaurantMenu(
        website=website,
        pages_scanned=tuple(scanned),
        items=_dedupe_items(collected)[:max_items],
    )
