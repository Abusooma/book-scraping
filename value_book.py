from loguru import logger
from urllib.parse import urljoin
from typing import Optional, List
import re
import requests
from selectolax.parser import HTMLParser
import sys

# Enlever le logger par defaut
logger.remove()

# Ajouter le logger dans un fichier dans le disque
logger.add("fichier.log", rotation="500kb", level="WARNING")

# Affichage des log dans la console
logger.add(sys.stderr, level="INFO")

BASE_URL = "https://books.toscrape.com/"

def get_book_price(url: str) -> float:
    try:
        response = requests.get(url)
        response.raise_for_status()

        tree = HTMLParser(response.text)
        price = extract_price_from_page(tree)
        stock = extract_stock_quantity_from_page(tree)
        return price * stock
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête HTTP: {e}")
        return 0.0

def extract_price_from_page(tree: HTMLParser) -> float:
    try:
        price_node = tree.css_first('p.price_color')
        if price_node:
            price_text = price_node.text().strip()
            price_str = re.findall(r'[0-9.]+', price_text)
            return float(price_str[0])
        else:
            logger.error("Aucun noeud trouvé pour l'attribut 'p.price_color' ")
            return 0.0
    except ValueError as e:
        logger.error("Le prix trouvé n'est pas un nombre")
        return 0.0
    except IndexError as e:
        logger.error("Le prix trouvé est une liste vide")
        return 0.0
    except Exception as e:
        logger.error(f"Erreur est survenue lors de la recuperation du prix: {e}")
        return 0.0


def extract_stock_quantity_from_page(tree: HTMLParser) -> int:
    try:
        stock_node = tree.css_first('p.instock.availability')
        if stock_node:
            stock_node_text = stock_node.text().strip()
            return int(re.findall(r'[0-9]+', stock_node_text)[0])
    except ValueError as e:
        logger.error("Le format du stock est invalide")
        return 0
    except IndexError as e:
        logger.error("Le regex a retourné une liste vide")
        return 0
    except Exception as e:
        logger.error(f"Une erreur generale s'est produite lors de l'extraction de la quantité: {e}")
        return 0
    

def get_all_books_urls_on_page(tree: HTMLParser) -> List[str]:
    try:
        books_urls_nodes = tree.css("h3 > a")
        return [urljoin(BASE_URL, link.attributes.get('href')) for link in books_urls_nodes if 'href' in link.attributes]     
    except Exception as e:
        logger.error(f"Une erreur lors de l'extraction des URLS {e}")
        return []
    

def get_next_page_url(category_url: str, tree: HTMLParser) -> Optional[str]:
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Une Erreur HTTP est survenue {e}")
        return None
    
    tree = HTMLParser(response.text)
    next_page_node = tree.css_first('li.next > a')
    if next_page_node and 'href' in next_page_node.attributes:
        return urljoin(category_url, next_page_node.attributes['href'])
    
    logger.info("Aucun bouton next sur cette page")
    return None

def get_all_books_urls(url: str) -> List[str]:
    urls = []

    while True:
        try:
            r = requests.get(url)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Une erreur HTTP s'est produite sur l'url : {url}")
            continue

        tree = HTMLParser(r.text)
        books_urls_on_page = get_all_books_urls_on_page(tree=tree)
        urls.extend(books_urls_on_page)

        next_page_url = get_next_page_url(url, tree)

        if not next_page_url:
            break

        url = next_page_url
    
    return urls




if __name__ == '__main__':
    url = "https://books.toscrape.com/catalogue/category/books/sequential-art_5/page-2.html"
    response = requests.get(url)
    tree = HTMLParser(response.text)
    print(get_next_page_url(category_url=url, tree=tree))
   