import os
from pathlib import Path
import requests

def parse_links():
    '''
    Parse links and and write their text to a local folder.
    Currently uses Wikipedia API to download links.
    '''
    wiki_titles = [
        "batman",
        "Vincent van Gogh",
        "San Francisco",
        "iPhone",
        "Tesla Model S",
        "BTS",
    ]

    data_path = Path("data_wiki")

    for title in wiki_titles:
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "titles": title,
                "prop": "extracts",
                "explaintext": True,
            },
        ).json()
        page = next(iter(response["query"]["pages"].values()))
        wiki_text = page["extract"]

        if not data_path.exists():
            Path.mkdir(data_path)

        with open(data_path / f"{title}.txt", "w") as fp:
            fp.write(wiki_text)

if __name__ == "__main__":
    if not os.path.exists("./data"):
        os.mkdir("./data")
        
    # parse web pages and save to local folder
    parse_links()