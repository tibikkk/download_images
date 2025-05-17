import os
import re
import shutil
import queue
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

class CrawlError(Exception):
    pass

def is_internal_link(link, base_netloc):
    parsed = urlparse(link)
    return parsed.netloc in ('', base_netloc)

def categorize_path(path):
    parts = path.strip('/').split('/')
    return parts[0] if parts and parts[0] else 'root'

def fetch_page(session, url):
    resp = session.get(url, timeout=8)
    resp.raise_for_status()
    return resp.text

def download_image(session, img_url, dest):
    r = session.get(img_url, timeout=8)
    r.raise_for_status()
    with open(dest, 'wb') as f:
        f.write(r.content)
    return True

def crawl_and_download(start_url, output_dir):
    """Crawls start_url, downloads only PNG/JPG images into output_dir/<category>/... Returns count."""
    # clean
    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)

    parsed = urlparse(start_url)
    base_netloc = parsed.netloc
    visited = {start_url}
    q = queue.Queue()
    q.put(start_url)

    session = requests.Session()
    session.headers.update({'User-Agent': 'ImageCrawler/1.0'})

    downloaded = 0
    tasks = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        while not q.empty():
            page = q.get()
            try:
                html = fetch_page(session, page)
            except requests.HTTPError as e:
                if e.response.status_code == 403:
                    raise CrawlError(f'Access forbidden: {page}')
                continue
            except Exception:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if not src:
                    continue
                img_url = urljoin(page, src)
                p = urlparse(img_url)
                if p.scheme not in ('http', 'https'):
                    continue
                # filter only png/jpg/jpeg
                if not p.path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue

                folder = categorize_path(p.path)
                dirpath = os.path.join(output_dir, folder)
                os.makedirs(dirpath, exist_ok=True)

                name = os.path.basename(p.path) or re.sub(r'\W+', '_', img_url)
                dest = os.path.join(dirpath, name)
                if os.path.exists(dest):
                    continue

                tasks.append(executor.submit(download_image, session, img_url, dest))

            for a in soup.find_all('a', href=True):
                href = urljoin(page, a['href']).split('#')[0].rstrip('/')
                if href not in visited and is_internal_link(href, base_netloc):
                    visited.add(href)
                    q.put(href)

        for f in as_completed(tasks):
            try:
                if f.result():
                    downloaded += 1
            except:
                pass

    return downloaded