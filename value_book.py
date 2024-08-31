from loguru import logger
import aiohttp
import asyncio
from urllib.parse import urljoin
from typing import Optional, List
import re
from selectolax.parser import HTMLParser
import sys

# Remove default logger
logger.remove()

# Add logger to a file on disk
logger.add("fichier.log", rotation="500kb", level="WARNING")

# Display logs in the console
logger.add(sys.stderr, level="INFO")

BASE_URL = "https://books.toscrape.com/"


async def get_book_price(url: str, session: aiohttp.ClientSession) -> float:
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            text = await response.text()  # Correction: Added parentheses

        tree = HTMLParser(text)
        price = extract_price_from_page(tree)
        stock = extract_stock_quantity_from_page(tree)
        return price * stock
    except aiohttp.ClientError as e:
        logger.error(f"Erreur lors de la requête HTTP: {e}")
        return 0.0


def extract_price_from_page(tree: HTMLParser) -> float:
    try:
        if price_node := tree.css_first('p.price_color'):
            price_text = price_node.text().strip()
            price_str = re.findall(r'[0-9.]+', price_text)
            return float(price_str[0])
        else:
            logger.error("Aucun noeud trouvé pour l'attribut 'p.price_color'")
            return 0.0
    except (ValueError, IndexError) as e:
        logger.error(f"Erreur lors de l'extraction du prix: {e}")
        return 0.0


def extract_stock_quantity_from_page(tree: HTMLParser) -> int:
    try:
        if stock_node := tree.css_first('p.instock.availability'):
            stock_node_text = stock_node.text().strip()
            return int(re.findall(r'[0-9]+', stock_node_text)[0])
        else:
            logger.error(
                "Aucun noeud trouvé pour l'attribut 'p.instock.availability'")
            return 0
    except (ValueError, IndexError) as e:
        logger.error(f"Erreur lors de l'extraction de la quantité: {e}")
        return 0


def get_all_books_urls_on_page(url: str, tree: HTMLParser) -> List[str]:
    try:
        books_urls_nodes = tree.css("h3 > a")
        return [urljoin(url, link.attributes.get('href')) for link in books_urls_nodes if 'href' in link.attributes]
    except Exception as e:
        logger.error(f"Une erreur lors de l'extraction des URLs: {e}")
        return []


async def get_next_page_url(category_url: str, tree: HTMLParser) -> Optional[str]:
    next_page_node = tree.css_first('li.next > a')
    if next_page_node and 'href' in next_page_node.attributes:
        return urljoin(category_url, next_page_node.attributes['href'])

    logger.info("Aucun bouton next sur cette page")
    return None


async def get_all_books_urls(url: str, session: aiohttp.ClientSession) -> List[str]:
    urls = []

    while url:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                text = await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Une erreur HTTP s'est produite sur l'url : {url}")
            break

        tree = HTMLParser(text)
        books_urls_on_page = get_all_books_urls_on_page(url, tree=tree)
        urls.extend(books_urls_on_page)

        url = await get_next_page_url(url, tree)

    return urls


async def main():
    async with aiohttp.ClientSession() as session:
        all_books_urls = await get_all_books_urls(BASE_URL, session)
        tasks = [get_book_price(url, session) for url in all_books_urls]
        total_price = sum(await asyncio.gather(*tasks))
        logger.info(f"Prix total de tous les livres: {total_price}")
        return total_price

if __name__ == '__main__':
    asyncio.run(main())
