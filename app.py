from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import base64
import json
import re
from urllib.parse import quote
import statistics
from io import BytesIO

app = Flask(__name__)
CORS(app)

def identify_product_huggingface(image_data):
    """
    Use Hugging Face free API to identify product from image
    No API key needed! Completely free forever.
    Uses multiple models with retry logic for reliability.
    """
    try:
        import base64
        import time
        
        # Remove data URL prefix if present
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_data)
        
        print(f"Image size: {len(image_bytes)} bytes")
        
        headers = {"Content-Type": "application/octet-stream"}
        
        product_name = ""
        labels = []
        
        # Try Method 1: BLIP Image Captioning (best for products)
        print("Trying BLIP image captioning...")
        caption_url = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
        
        for attempt in range(3):  # Retry up to 3 times
            try:
                caption_response = requests.post(caption_url, headers=headers, data=image_bytes, timeout=30)
                print(f"BLIP response status: {caption_response.status_code}")
                
                if caption_response.status_code == 503:
                    # Model is loading
                    wait_time = 5 + (attempt * 3)
                    print(f"Model loading, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                if caption_response.status_code == 200:
                    caption_data = caption_response.json()
                    print(f"BLIP response: {caption_data}")
                    
                    if isinstance(caption_data, list) and len(caption_data) > 0:
                        product_name = caption_data[0].get('generated_text', '').strip()
                    elif isinstance(caption_data, dict):
                        product_name = caption_data.get('generated_text', '').strip()
                        # Handle error field
                        if not product_name and 'error' in caption_data:
                            print(f"BLIP error: {caption_data['error']}")
                    
                    if product_name:
                        print(f"Got product name from BLIP: {product_name}")
                        break
                else:
                    print(f"BLIP failed with status {caption_response.status_code}: {caption_response.text[:200]}")
                    
            except requests.exceptions.Timeout:
                print(f"BLIP timeout on attempt {attempt + 1}")
                if attempt < 2:
                    time.sleep(2)
                    continue
            except Exception as e:
                print(f"BLIP error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    time.sleep(2)
                    continue
        
        # Extract labels from product name
        if product_name:
            words = product_name.lower().split()
            common_words = {'a', 'an', 'the', 'is', 'are', 'with', 'on', 'of', 'and', 'or', 'in', 'at', 'to', 'for'}
            labels = [w.capitalize() for w in words if w not in common_words and len(w) > 2][:5]
        
        # Try Method 2: Object Detection (if caption failed)
        if not product_name:
            print("BLIP failed, trying object detection...")
            object_url = "https://api-inference.huggingface.co/models/facebook/detr-resnet-50"
            
            try:
                object_response = requests.post(object_url, headers=headers, data=image_bytes, timeout=30)
                print(f"Object detection response status: {object_response.status_code}")
                
                if object_response.status_code == 200:
                    objects = object_response.json()
                    print(f"Object detection response: {objects}")
                    
                    if isinstance(objects, list) and len(objects) > 0:
                        # Get the most confident detection
                        sorted_objects = sorted(objects, key=lambda x: x.get('score', 0), reverse=True)
                        top_object = sorted_objects[0]
                        product_name = top_object.get('label', '').replace('_', ' ').title()
                        labels = [obj.get('label', '').replace('_', ' ').title() 
                                 for obj in sorted_objects[:5] if obj.get('score', 0) > 0.5]
                        print(f"Got product name from object detection: {product_name}")
                else:
                    print(f"Object detection failed: {object_response.text[:200]}")
            except Exception as e:
                print(f"Object detection error: {e}")
        
        # If all methods failed, return a helpful error
        if not product_name:
            print("All AI methods failed")
            return {
                "success": False,
                "error": "AI could not identify the product. Please use manual search.",
                "product_name": "",
                "labels": [],
                "search_query": "",
                "debug_info": "All Hugging Face models failed or are loading. Try again in 30 seconds or use manual search."
            }
        
        print(f"Final result - Product: {product_name}, Labels: {labels}")
        
        return {
            "success": True,
            "product_name": product_name,
            "labels": labels,
            "search_query": product_name
        }
        
    except Exception as e:
        print(f"Hugging Face critical error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": f"AI analysis failed: {str(e)}",
            "product_name": "",
            "labels": [],
            "search_query": "",
            "debug_info": str(e)
        }

def scrape_ricardo(search_query):
    """Scrape Ricardo.ch for product listings"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://www.ricardo.ch/de/s/{quote(search_query)}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = []
        
        # Ricardo's structure may vary, adjust selectors as needed
        items = soup.find_all('article', class_=re.compile('.*ArticlePreview.*'))[:10]
        
        for item in items:
            try:
                title_elem = item.find('h3') or item.find('a', class_=re.compile('.*title.*'))
                price_elem = item.find('span', class_=re.compile('.*price.*'))
                
                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True)
                    
                    # Extract numeric price
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace("'", ""))
                    if price_match:
                        price = float(price_match.group().replace(',', ''))
                        listings.append({
                            'title': title,
                            'price': price,
                            'platform': 'Ricardo'
                        })
            except:
                continue
        
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
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = []
        
        # Tutti's structure
        items = soup.find_all('div', class_=re.compile('.*listing.*|.*item.*'))[:10]
        
        for item in items:
            try:
                title_elem = item.find('h2') or item.find('h3') or item.find('a', class_=re.compile('.*title.*'))
                price_elem = item.find('span', class_=re.compile('.*price.*')) or item.find('p', class_=re.compile('.*price.*'))
                
                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True)
                    
                    # Extract numeric price
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace("'", ""))
                    if price_match:
                        price = float(price_match.group().replace(',', ''))
                        listings.append({
                            'title': title,
                            'price': price,
                            'platform': 'Tutti'
                        })
            except:
                continue
        
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
        
        # Search sold items on eBay Switzerland
        url = f"https://www.ebay.ch/sch/i.html?_nkw={quote(search_query)}&LH_Sold=1&LH_Complete=1"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = []
        
        # eBay listing structure
        items = soup.find_all('div', class_='s-item__info')[:10]
        
        for item in items:
            try:
                title_elem = item.find('div', class_='s-item__title')
                price_elem = item.find('span', class_='s-item__price')
                
                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True)
                    
                    # Extract numeric price
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace("'", ""))
                    if price_match:
                        price = float(price_match.group().replace(',', ''))
                        listings.append({
                            'title': title,
                            'price': price,
                            'platform': 'eBay',
                            'sold': True
                        })
            except:
                continue
        
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

@app.route('/api/analyze', methods=['POST'])
def analyze_product():
    """Main endpoint to analyze product from image"""
    try:
        data = request.json
        image_data = data.get('image', '')
        manual_query = data.get('query', '')
        
        result = {
            'recognition': {},
            'listings': {
                'ricardo': [],
                'tutti': [],
                'ebay': []
            },
            'stats': {},
            'all_listings': []
        }
        
        # Step 1: Identify product (or use manual query)
        if manual_query:
            search_query = manual_query
            result['recognition'] = {
                'success': True,
                'product_name': manual_query,
                'search_query': manual_query,
                'manual': True
            }
        else:
            if not image_data:
                return jsonify({
                    'error': 'No image data provided',
                    'result': result
                }), 400
            
            print("\n" + "="*60)
            print("Starting image analysis with Hugging Face...")
            print("="*60)
            
            recognition = identify_product_huggingface(image_data)
            result['recognition'] = recognition
            search_query = recognition.get('search_query', '')
            
            print(f"Recognition result: {recognition}")
            
            # If AI failed, return helpful error
            if not recognition.get('success', False):
                error_msg = recognition.get('error', 'AI analysis failed')
                debug_info = recognition.get('debug_info', '')
                return jsonify({
                    'error': error_msg,
                    'debug_info': debug_info,
                    'result': result,
                    'suggestion': 'The AI models may be loading (first time takes 30-60 seconds). Please try again or use manual search.'
                }), 200  # Return 200 so frontend can handle gracefully
        
        if not search_query:
            return jsonify({
                'error': 'Could not identify product. Please try manual search.',
                'result': result
            }), 200
        
        # Step 2: Search all platforms
        print(f"\n{'='*60}")
        print(f"Searching for: {search_query}")
        print(f"{'='*60}")
        
        ricardo_listings = scrape_ricardo(search_query)
        tutti_listings = scrape_tutti(search_query)
        ebay_listings = scrape_ebay(search_query)
        
        result['listings']['ricardo'] = ricardo_listings
        result['listings']['tutti'] = tutti_listings
        result['listings']['ebay'] = ebay_listings
        
        # Step 3: Combine and calculate stats
        all_listings = ricardo_listings + tutti_listings + ebay_listings
        result['all_listings'] = all_listings
        
        # Calculate stats per platform and overall
        result['stats'] = {
            'overall': calculate_price_stats(all_listings),
            'ricardo': calculate_price_stats(ricardo_listings),
            'tutti': calculate_price_stats(tutti_listings),
            'ebay': calculate_price_stats(ebay_listings)
        }
        
        print(f"\nResults: {len(all_listings)} total listings found")
        print(f"{'='*60}\n")
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f"ERROR in analyze_product: {e}")
        traceback.print_exc()
        return jsonify({
            'error': f'Server error: {str(e)}',
            'debug': traceback.format_exc()
        }), 500

@app.route('/api/search', methods=['POST'])
def manual_search():
    """Endpoint for manual search without image"""
    try:
        data = request.json
        search_query = data.get('query', '')
        
        if not search_query:
            return jsonify({'error': 'Search query required'}), 400
        
        result = {
            'search_query': search_query,
            'listings': {
                'ricardo': scrape_ricardo(search_query),
                'tutti': scrape_tutti(search_query),
                'ebay': scrape_ebay(search_query)
            }
        }
        
        all_listings = result['listings']['ricardo'] + result['listings']['tutti'] + result['listings']['ebay']
        result['all_listings'] = all_listings
        result['stats'] = {
            'overall': calculate_price_stats(all_listings),
            'ricardo': calculate_price_stats(result['listings']['ricardo']),
            'tutti': calculate_price_stats(result['listings']['tutti']),
            'ebay': calculate_price_stats(result['listings']['ebay'])
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
