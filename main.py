import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import concurrent.futures
import re

def get_filename_from_url(url):
    """Generates a valid filename from a URL."""
    parsed_url = urlparse(url)
    path = parsed_url.path.strip("/").replace("/", "_")
    if not path:
        path = "index"
    return f"htmls/{path}.html"

def download_and_save(url):
    """
    Downloads a single URL and saves its content to a file.
    """
    try:
        filename = get_filename_from_url(url)
        if os.path.exists(filename):
            return f"Skipping {url}, file already exists."

        print(f"Scraping {url}...")
        page_response = requests.get(url)
        page_response.raise_for_status()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(page_response.text)
        print(f"Saved to {filename}")
        return f"Successfully scraped {url}"
    except requests.exceptions.RequestException as e:
        return f"Error scraping {url}: {e}"
    except IOError as e:
        return f"Error saving file for {url}: {e}"

def scrape_courses_from_file(filepath):
    """
    Scrapes URLs from a text file and saves the content of each URL to a file.

    Args:
        filepath: The path to the text file containing the URLs.
    """
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        return

    soup = BeautifulSoup(content, "html.parser")
    urls = [a['href'] for a in soup.find_all('a', href=True)]

    if not os.path.exists("htmls"):
        os.makedirs("htmls")

    # Filter out URLs that have already been downloaded
    urls_to_download = []
    for url in urls:
        if not os.path.exists(get_filename_from_url(url)):
            urls_to_download.append(url)

    if not urls_to_download:
        print("All files have been downloaded.")
        return

    print(f"Found {len(urls_to_download)} URLs to download.")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(download_and_save, url): url for url in urls_to_download}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                print(result)
            except Exception as exc:
                print(f'{url} generated an exception: {exc}')

if __name__ == "__main__":
    courses_filepath = "courses.txt"
    scrape_courses_from_file(courses_filepath)