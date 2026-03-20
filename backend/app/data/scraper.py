import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

def search_links(query, max_results=3):
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
        return [r["href"] for r in results]

def scrape_page(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # remove scripts/styles
        for tag in soup(["script", "style"]):
            tag.extract()

        text = soup.get_text(separator="\n")
        return text[:3000]  # limit size

    except:
        return ""

def get_topic_content(topic):
    query = f"{topic} system design explanation"
    links = search_links(query)

    content = ""
    for link in links:
        content += scrape_page(link) + "\n\n"

    return content