import requests
from bs4 import BeautifulSoup

def fetch_content(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        return soup.get_text()
    except:
        return None