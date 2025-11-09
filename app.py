from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote
import statistics

app = Flask(__name__)
CORS(app)

def scrape_ricardo(search_query):
    """Scrape Ricardo.ch for product listings"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://www.ricardo.ch/de/s/{quote(search_query)}"
        print(f"Searching Ricardo: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = []
        items = soup.find_all('article', class_=re.compile('.*ArticlePreview.*'))[:10]
        
        if not items:
            items = soup.find_all('article')[:10]
        
        for item in items:
            try:
                title_elem = item.find('h3') or item.find('a', class_=re.compile('.*title.*'))
                price_elem = item.find('span', class_=re.compile('.*price.*')) or item.find('div', class_=re.compile('.*price.*'))
                
                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True)
                    
                    price_match = re.search(r'[\d,\']+\.?\d*', price_text)
                    if price_match:
                        price_str = price_match.group().replace("'", "").replace(',', '')
                        try:
                            price = float(price_str)
                            if price > 0:
                                listings.append({
                                    'title': title[:100],
                                    'price': price,
                                    'platform': 'Ricardo'
                                })
                        except:
                            continue
            except:
                continue
        
        print(f"Ricardo found: {len(listings)} listings")
        return listings
    except Exception as e:
        print(f"Ricardo scraping error: {e}")
        return []

def scrape_tutti(search_query):
    """Scrape Tutti.ch for product listings"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://www.tutti.ch/de/q/{quote(search_query)}"
        print(f"Searching Tutti: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = []
        items = soup.find_all('div', class_=re.compile('.*listing.*|.*item.*|.*card.*'))[:15]
        
        for item in items:
            try:
                title_elem = item.find('h2') or item.find('h3') or item.find('a', class_=re.compile('.*title.*'))
                price_elem = item.find('span', class_=re.compile('.*price.*')) or item.find('p', class_=re.compile('.*price.*'))
                
                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True)
                    
                    price_match = re.search(r'[\d,\']+\.?\d*', price_text)
                    if price_match:
                        price_str = price_match.group().replace("'", "").replace(',', '')
                        try:
                            price = float(price_str)
                            if price > 0:
                                listings.append({
                                    'title': title[:100],
                                    'price': price,
                                    'platform': 'Tutti'
                                })
                        except:
                            continue
            except:
                continue
        
        print(f"Tutti found: {len(listings)} listings")
        return listings
    except Exception as e:
        print(f"Tutti scraping error: {e}")
        return []

def scrape_ebay(search_query):
    """Scrape eBay for sold/completed listings"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://www.ebay.ch/sch/i.html?_nkw={quote(search_query)}&LH_Sold=1&LH_Complete=1"
        print(f"Searching eBay: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = []
        items = soup.find_all('div', class_='s-item__info')[:10]
        
        for item in items:
            try:
                title_elem = item.find('div', class_='s-item__title')
                price_elem = item.find('span', class_='s-item__price')
                
                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True)
                    
                    if 'Shop on eBay' in title:
                        continue
                    
                    price_match = re.search(r'[\d,\']+\.?\d*', price_text)
                    if price_match:
                        price_str = price_match.group().replace("'", "").replace(',', '')
                        try:
                            price = float(price_str)
                            if price > 0:
                                listings.append({
                                    'title': title[:100],
                                    'price': price,
                                    'platform': 'eBay',
                                    'sold': True
                                })
                        except:
                            continue
            except:
                continue
        
        print(f"eBay found: {len(listings)} listings")
        return listings
    except Exception as e:
        print(f"eBay scraping error: {e}")
        return []

def calculate_price_stats(listings):
    """Calculate price statistics from listings"""
    if not listings:
        return {
            'min': 0,
            'max': 0,
            'median': 0,
            'average': 0,
            'count': 0
        }
    
    prices = [item['price'] for item in listings]
    
    return {
        'min': round(min(prices), 2),
        'max': round(max(prices), 2),
        'median': round(statistics.median(prices), 2),
        'average': round(statistics.mean(prices), 2),
        'count': len(prices)
    }

@app.route('/api/search', methods=['POST'])
def search():
    """Main search endpoint"""
    try:
        data = request.json
        search_query = data.get('query', '').strip()
        
        if not search_query:
            return jsonify({'error': 'Search query required'}), 400
        
        print("=" * 60)
        print(f"NEW SEARCH: {search_query}")
        print("=" * 60)
        
        ricardo_listings = scrape_ricardo(search_query)
        tutti_listings = scrape_tutti(search_query)
        ebay_listings = scrape_ebay(search_query)
        
        all_listings = ricardo_listings + tutti_listings + ebay_listings
        
        result = {
            'search_query': search_query,
            'listings': {
                'ricardo': ricardo_listings,
                'tutti': tutti_listings,
                'ebay': ebay_listings
            },
            'all_listings': all_listings,
            'stats': {
                'overall': calculate_price_stats(all_listings),
                'ricardo': calculate_price_stats(ricardo_listings),
                'tutti': calculate_price_stats(tutti_listings),
                'ebay': calculate_price_stats(ebay_listings)
            }
        }
        
        print(f"\nRESULTS SUMMARY:")
        print(f"  Ricardo: {len(ricardo_listings)} listings")
        print(f"  Tutti: {len(tutti_listings)} listings")
        print(f"  eBay: {len(ebay_listings)} listings")
        print(f"  Total: {len(all_listings)} listings")
        
        if all_listings:
            stats = result['stats']['overall']
            print(f"  Price range: CHF {stats['min']} - CHF {stats['max']}")
            print(f"  Median: CHF {stats['median']}")
        
        print("=" * 60)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'version': 'simple'})

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'message': 'Brocki Scanner API',
        'endpoints': {
            '/api/search': 'POST - Search for products',
            '/health': 'GET - Health check'
        }
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
