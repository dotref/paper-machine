import os
from pathlib import Path
import requests
import time
from PIL import Image
import matplotlib.pyplot as plt

import wikipedia
import urllib.request

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

def parse_images():
    '''
    Parse images and and write them to a local folder.
    Currently uses Wikipedia API to download images.
    '''

    image_path = Path("data_wiki")
    image_uuid = 0
    # image_metadata_dict stores images metadata including image uuid, filename and path
    image_metadata_dict = {}
    MAX_IMAGES_PER_WIKI = 30

    wiki_titles = [
        "San Francisco",
        "Batman",
        "Vincent van Gogh",
        "iPhone",
        "Tesla Model S",
        "BTS band",
    ]

    # create folder for images only
    if not image_path.exists():
        Path.mkdir(image_path)


    # Download images for wiki pages
    # Assing UUID for each image
    for title in wiki_titles:
        images_per_wiki = 0
        print(title)
        try:
            page_py = wikipedia.page(title)
            list_img_urls = page_py.images
            for url in list_img_urls:
                print(url)
                if url.endswith(".jpg") or url.endswith(".png"):
                    image_uuid += 1
                    image_file_name = title + "_" + url.split("/")[-1]

                    # img_path could be s3 path pointing to the raw image file in the future
                    image_metadata_dict[image_uuid] = {
                        "filename": image_file_name,
                        "img_path": "./" + str(image_path / f"{image_uuid}.jpg"),
                    }

                    time.sleep(2)

                    # download image
                    urllib.request.urlretrieve(url, image_path / f"{image_uuid}.jpg")

                    images_per_wiki += 1
                    # Limit the number of images downloaded per wiki page to 15
                    if images_per_wiki > MAX_IMAGES_PER_WIKI:
                        break
        except:
            print(str(Exception("No images found for Wikipedia page: ")) + title)
            continue
    
    return image_metadata_dict

def plot_images(image_paths):
    '''
    Plot images in a grid.
        image_paths: list of image paths
    '''
    images_shown = 0
    plt.figure(figsize=(16, 9))
    for img_path in image_paths:
        if os.path.isfile(img_path):
            image = Image.open(img_path)

            plt.subplot(2, 3, images_shown + 1)
            plt.imshow(image)
            plt.xticks([])
            plt.yticks([])

            images_shown += 1
            if images_shown >= 9:
                break

    plt.show()

if __name__ == "__main__":
    if not os.path.exists("./data_wiki"):
        os.mkdir("./data_wiki")
        
    # parse web pages and save to local folder
    parse_links()
    image_metadata_dict = parse_images()