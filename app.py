from flask import Flask, render_template_string, request, send_file
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import os
from datetime import datetime
import threading
import matplotlib.pyplot as plt
import schedule
import time

app = Flask(__name__)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Bestseller Tracker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f6f9;
            color: #333;
            padding: 40px;
        }
        h2 {
            color: #2c3e50;
            margin-bottom: 30px;
        }
        form {
            background-color: #fff;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }
        h3 {
            margin-top: 0;
        }
        select, button {
            padding: 10px;
            margin-top: 10px;
            font-size: 14px;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #2980b9;
        }
        ol {
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }
        li {
            margin-bottom: 15px;
        }
        img {
            margin-top: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        form[action="/download"],
        form[action="/chart"] {
            display: inline-block;
            margin-top: 10px;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <h2>Select Category by Brand</h2> 

    <form method="post">
        <h3>Cotton On - Womenswear</h3>
        <input type="hidden" name="brand" value="cottonon">
        <select name="category">
            <option value="tops" {% if selected_brand == 'cottonon' and selected_category == 'tops' %}selected{% endif %}>Tops</option>
            <option value="fleece-and-sweats" {% if selected_brand == 'cottonon' and selected_category == 'fleece-and-sweats' %}selected{% endif %}>Fleece & Sweats</option>
            <option value="graphic-t-shirts" {% if selected_brand == 'cottonon' and selected_category == 'graphic-t-shirts' %}selected{% endif %}>Graphic T-shirts</option>
            <option value="dresses" {% if selected_brand == 'cottonon' and selected_category == 'dresses' %}selected{% endif %}>Dresses</option>
        </select>
        <button type="submit">Fetch Cotton On</button>
    </form>

    <form method="post">
        <h3>Cotton On - Activewear</h3>
        <input type="hidden" name="brand" value="cottonon_active">
        <select name="category">
            <option value="tank&top" {% if selected_brand == 'cottonon_active' and selected_category == 'tank&top' %}selected{% endif %}>Tank & Top</option>
            <option value="sweats" {% if selected_brand == 'cottonon_active' and selected_category == 'sweats' %}selected{% endif %}>Sweats</option>
            <option value="shorts" {% if selected_brand == 'cottonon_active' and selected_category == 'shorts' %}selected{% endif %}>Shorts</option>
        </select>
        <button type="submit">Fetch Activewear</button>
    </form>

    <form method="post">
        <h3>Supre</h3>
        <input type="hidden" name="brand" value="supre">
        <select name="category">
            <option value="tops" {% if selected_brand == 'supre' and selected_category == 'tops' %}selected{% endif %}>Tops</option>
            <option value="dresses" {% if selected_brand == 'supre' and selected_category == 'dresses' %}selected{% endif %}>Dresses</option>
            <option value="hoodies" {% if selected_brand == 'supre' and selected_category == 'hoodies' %}selected{% endif %}>Hoodies</option>
            <option value="all" {% if selected_brand == 'supre' and selected_category == 'all' %}selected{% endif %}>All</option>
        </select>
        <button type="submit">Fetch Supre</button>
    </form>

    {% if products %}
        <h3>Top 10 Products:</h3>
        <ol>
        {% for item in products %}
            <li>
                <strong>{{ item['Title'] }}</strong> - ${{ item['Price'] }}<br>
                <a href="{{ item['Link'] }}" target="_blank">View Product</a><br>
                {% if item['Image'] %}<img src="{{ item['Image'] }}" width="200">{% endif %}
            </li>
        {% endfor %}
        </ol>
        <form method="get" action="/download">
            <input type="hidden" name="brand" value="{{ selected_brand }}">
            <input type="hidden" name="category" value="{{ selected_category }}">
            <button type="submit">Download CSV</button>
        </form>
        <form method="get" action="/chart">
            <input type="hidden" name="brand" value="{{ selected_brand }}">
            <input type="hidden" name="category" value="{{ selected_category }}">
            <button type="submit">Show Price Chart</button>
        </form>
    {% endif %}
</body>
</html>
"""



@app.route('/', methods=['GET', 'POST'])
def index():
    products = []
    selected_brand = None
    selected_category = None

    category_map = {
        "cottonon": {
            "tops": "https://cottonon.com/AU/co/women/womens-clothing/womens-tops/",
            "fleece-and-sweats": "https://cottonon.com/AU/women/fleece-and-sweats/",
            "graphic-t-shirts": "https://cottonon.com/AU/co/women/womens-clothing/womens-tops/womens-graphic-t-shirts/",
            "dresses": "https://cottonon.com/AU/women/dresses/"
        },
        "cottonon_active": {
            "sweats": "https://cottonon.com/AU/co/women/womens-activewear/womens-gym-active-fleece/",
            "shorts": "https://cottonon.com/AU/co/women/womens-activewear/gym-shorts/",
            "tank&top": "https://cottonon.com/AU/co/women/womens-activewear/womens-gym-tops/"
        },
        "supre": {
            "tops": "https://cottonon.com/AU/supre/s-clothing/s-clothing-tops/",
            "dresses": "https://cottonon.com/AU/supre/s-clothing/s-clothing-dresses/",
            "hoodies": "https://cottonon.com/AU/supre/s-clothing/s-clothing-outerwear/s-clothing-jumpers/",
            "all": "https://cottonon.com/AU/supre/s-clothing/#start=1"
        }
    }

    if request.method == 'POST':
        selected_brand = request.form.get("brand")
        selected_category = request.form.get("category")
        url = category_map.get(selected_brand, {}).get(selected_category)

        if url:
            products = fetch_products(url)
            df = pd.DataFrame(products)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{selected_brand}_{selected_category}_{timestamp}.csv"
            df.to_csv(os.path.join(DATA_DIR, filename), index=False)

    return render_template_string(HTML_TEMPLATE,
                                  products=products,
                                  selected_brand=selected_brand or '',
                                  selected_category=selected_category or '')


@app.route('/download')
def download():
    brand = request.args.get("brand")
    category = request.args.get("category")
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith(f"{brand}_{category}_")], reverse=True)
    if files:
        return send_file(os.path.join(DATA_DIR, files[0]), as_attachment=True)
    return "No file found."


@app.route('/chart')
def chart():
    brand = request.args.get("brand")
    category = request.args.get("category")
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith(f"{brand}_{category}_")], reverse=True)
    if files:
        df = pd.read_csv(os.path.join(DATA_DIR, files[0]))
        plt.figure(figsize=(10, 6))
        plt.barh(df['Title'], df['Price'])
        plt.xlabel("Price")
        plt.title(f"{brand} - {category} Price Chart")
        plt.tight_layout()
        chart_path = os.path.join(DATA_DIR, "chart.png")
        plt.savefig(chart_path)
        return send_file(chart_path, mimetype='image/png')
    return "No chart data available."


def fetch_products(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    products = []
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        print(f"[DEBUG] Fetching from: {url}")
        print(f"[DEBUG] Status Code: {response.status_code}")
        print(f"[DEBUG] Response Length: {len(response.text)}")
        product_tiles = soup.select(".product-tile, .product-grid-tile, .grid-tile")
        product_tiles = product_tiles[::2]

        for tile in product_tiles:
            title_tag = tile.select_one(".product-name")
            price_tag = tile.select_one(".product-sales-price, .product-standard-price")
            link_tag = tile.select_one("a")
            image_tag = tile.select_one("img")

            if title_tag and price_tag and link_tag:
                title = title_tag.get_text(strip=True)
                price = price_tag.get_text(strip=True).replace("$", "").strip()
                try:
                    price_float = float(price)
                except ValueError:
                    price_float = 0.0
                link = urljoin("https://cottonon.com", link_tag.get("href"))
                image_url = image_tag.get("src") if image_tag else ""
                products.append({"Title": title, "Price": price_float, "Link": link, "Image": image_url})

    except Exception as e:
        products = [{"Title": "Failed to fetch", "Price": 0.0, "Link": url, "Image": "", "Error": str(e)}]

    return products[:10]

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
