import os
import re
import urllib.request
import urllib.parse

# Path relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, 'src', 'assets', 'fonts')

fonts = [
    {
        'name': 'roboto',
        'cssUrl': 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap',
        'subDir': 'roboto'
    },
    {
        'name': 'material-icons',
        'cssUrl': 'https://fonts.googleapis.com/icon?family=Material+Icons',
        'subDir': 'material-icons'
    }
]

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def fetch_text(url):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')

def download_file(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req) as response:
        with open(dest, 'wb') as f:
            f.write(response.read())

def run():
    if not os.path.exists(FONTS_DIR):
        os.makedirs(FONTS_DIR)

    for font in fonts:
        print(f"Downloading {font['name']}...")
        css_path = os.path.join(FONTS_DIR, f"{font['name']}.css")
        css_content = fetch_text(font['cssUrl'])

        font_dir = os.path.join(FONTS_DIR, font['subDir'])
        if not os.path.exists(font_dir):
            os.makedirs(font_dir)

        urls = re.findall(r'url\((https://fonts\.gstatic\.com/[^\)]+)\)', css_content)

        for url in set(urls):
            filename = os.path.basename(url)
            dest = os.path.join(font_dir, filename)
            print(f"  Downloading {url}...")
            download_file(url, dest)
            css_content = css_content.replace(url, f"./{font['subDir']}/{filename}")

        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)

    print("All fonts downloaded and CSS updated.")

if __name__ == '__main__':
    run()
