 # scrapers.py
import requests
import time

# -------------------------
# 1️⃣ Ricardo (Switzerland)
# -------------------------
def fetch_ricardo_all(search_term, max_results=100, per_page=20, delay=0.5):
    all_items = []
    page = 1
    while len(all_items) < max_results:
        url = "https://api.ricardo.ch/search/products"
        params = {"query": search_term, "limit": per_page, "page": page}
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print("Ricardo API error:", response.status_code)
            break
        data = response.json().get("products", [])
        if not data:
            break
        all_items.extend(data)
        page += 1
        time.sleep(delay)  # polite delay to avoid hammering API
    return all_items[:max_results]

# -------------------------
# 2️⃣ Tutti (Switzerland)
# -------------------------
def fetch_tutti_all(search_term, max_results=100, per_page=20, delay=0.5):
    all_items = []
    page = 0
    while len(all_items) < max_results:
        url = "https://api.tutti.ch/v2/search"
        params = {"q": search_term, "limit": per_page, "offset": page * per_page}
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print("Tutti API error:", response.status_code)
            break
        data = response.json().get("ads", [])
        if not data:
            break
        all_items.extend(data)
        page += 1
        time.sleep(delay)
    return all_items[:max_results]

# -------------------------
# 3️⃣ eBay sold listings
# -------------------------
def fetch_ebay_sold_all(search_term, max_results=100, entries_per_page=20, delay=0.5, app_id="YOUR_APP_ID"):
    """
    Note: Replace YOUR_APP_ID with your actual eBay AppID.
    """
    all_items = []
    page = 1
    while len(all_items) < max_results:
        url = "https://svcs.ebay.com/services/search/FindingService/v1"
        headers = {
            "X-EBAY-SOA-OPERATION-NAME": "findCompletedItems",
            "X-EBAY-SOA-SERVICE-VERSION": "1.0.0",
            "X-EBAY-SOA-SECURITY-APPNAME": app_id,
            "X-EBAY-SOA-REQUEST-DATA-FORMAT": "JSON"
        }
        payload = {
            "keywords": search_term,
            "paginationInput": {"entriesPerPage": entries_per_page, "pageNumber": page},
            "itemFilter": [{"name": "SoldItemsOnly", "value": "true"}],
            "outputSelector": ["SellerInfo", "PictureURLLarge"]
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print("eBay API error:", response.status_code)
            break
        try:
            items = response.json()["findCompletedItemsResponse"][0].get("searchResult", [{}])[0].get("item", [])
        except Exception as e:
            print("eBay JSON parsing error:", e)
            break
        if not items:
            break
        all_items.extend(items)
        page += 1
        time.sleep(delay)
    return all_items[:max_results]
