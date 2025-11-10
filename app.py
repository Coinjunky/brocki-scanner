from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import statistics
import os

# Import JSON-based scrapers
from scrapers import fetch_ricardo_all, fetch_tutti_all, fetch_ebay_sold_all

app = Flask(__name__)
CORS(app)

# -----------------------------
# Hugging Face AI Product Recognition
# -----------------------------
def identify_product_huggingface(image_data):
    try:
        import time
        # Remove data URL prefix
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        image_bytes = base64.b64decode(image_data)

        headers = {"Content-Type": "application/octet-stream"}
        product_name = ""
        labels = []

        # Method 1: BLIP Image Captioning
        caption_url = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
        for attempt in range(3):
            try:
                resp = requests.post(caption_url, headers=headers, data=image_bytes, timeout=30)
                if resp.status_code == 503:  # Model loading
                    time.sleep(5 + attempt * 3)
                    continue
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        product_name = data[0].get('generated_text', '').strip()
                    elif isinstance(data, dict):
                        product_name = data.get('generated_text', '').strip()
                    if product_name:
                        break
            except:
                time.sleep(2)
                continue

        # Labels extraction
        if product_name:
            words = product_name.lower().split()
            common_words = {'a','an','the','is','are','with','on','of','and','or','in','at','to','for'}
            labels = [w.capitalize() for w in words if w not in common_words and len(w) > 2][:5]

        # Method 2: Object detection fallback
        if not product_name:
            object_url = "https://api-inference.huggingface.co/models/facebook/detr-resnet-50"
            try:
                resp = requests.post(object_url, headers=headers, data=image_bytes, timeout=30)
                if resp.status_code == 200:
                    objs = resp.json()
                    if isinstance(objs, list) and objs:
                        top = sorted(objs, key=lambda x: x.get('score',0), reverse=True)[0]
                        product_name = top.get('label','').replace('_',' ').title()
                        labels = [o.get('label','').replace('_',' ').title() for o in objs[:5] if o.get('score',0)>0.5]
            except:
                pass

        if not product_name:
            return {"success": False,"error":"AI could not identify product.","product_name":"","labels":[],"search_query":"","debug_info":"Models failed or loading"}

        return {"success": True,"product_name":product_name,"labels":labels,"search_query":product_name}

    except Exception as e:
        return {"success": False,"error":str(e),"product_name":"","labels":[],"search_query":"","debug_info":str(e)}

# -----------------------------
# Price Stats
# -----------------------------
def calculate_price_stats(listings):
    if not listings:
        return {'min':0,'max':0,'median':0,'average':0,'count':0}
    prices = [item['price'] for item in listings]
    return {
        'min': round(min(prices),2),
        'max': round(max(prices),2),
        'median': round(statistics.median(prices),2),
        'average': round(statistics.mean(prices),2),
        'count': len(prices)
    }

# -----------------------------
# API Endpoints
# -----------------------------
@app.route('/api/analyze', methods=['POST'])
def analyze_product():
    data = request.json
    image_data = data.get('image','')
    manual_query = data.get('query','')
    result = {'recognition':{},'listings':{'ricardo':[],'tutti':[],'ebay':[]},'stats':{},'all_listings':[]}

    # Identify product
    if manual_query:
        search_query = manual_query
        result['recognition'] = {'success':True,'product_name':manual_query,'search_query':manual_query,'manual':True}
    else:
        if not image_data:
            return jsonify({'error':'No image data provided','result':result}),400
        recognition = identify_product_huggingface(image_data)
        result['recognition'] = recognition
        search_query = recognition.get('search_query','')
        if not recognition.get('success',False):
            return jsonify({'error':recognition.get('error','AI failed'),'debug_info':recognition.get('debug_info',''),'result':result}),200
        if not search_query:
            return jsonify({'error':'Could not identify product','result':result}),200

    # Fetch listings from JSON APIs
    ricardo_listings = fetch_ricardo_all(search_query, max_results=50)
    tutti_listings = fetch_tutti_all(search_query, max_results=50)
    ebay_listings = fetch_ebay_sold_all(search_query, max_results=50, app_id=os.environ.get('EBAY_APP_ID','YOUR_EBAY_APP_ID'))

    result['listings']['ricardo'] = ricardo_listings
    result['listings']['tutti'] = tutti_listings
    result['listings']['ebay'] = ebay_listings

    all_listings = ricardo_listings + tutti_listings + ebay_listings
    result['all_listings'] = all_listings
    result['stats'] = {
        'overall': calculate_price_stats(all_listings),
        'ricardo': calculate_price_stats(ricardo_listings),
        'tutti': calculate_price_stats(tutti_listings),
        'ebay': calculate_price_stats(ebay_listings)
    }

    return jsonify(result)

@app.route('/api/search', methods=['POST'])
def manual_search():
    data = request.json
    search_query = data.get('query','')
    if not search_query:
        return jsonify({'error':'Search query required'}),400

    ricardo_listings = fetch_ricardo_all(search_query, max_results=50)
    tutti_listings = fetch_tutti_all(search_query, max_results=50)
    ebay_listings = fetch_ebay_sold_all(search_query, max_results=50, app_id=os.environ.get('EBAY_APP_ID','YOUR_EBAY_APP_ID'))

    all_listings = ricardo_listings + tutti_listings + ebay_listings
    result = {
        'search_query': search_query,
        'listings': {'ricardo':ricardo_listings,'tutti':tutti_listings,'ebay':ebay_listings},
        'all_listings': all_listings,
        'stats':{
            'overall': calculate_price_stats(all_listings),
            'ricardo': calculate_price_stats(ricardo_listings),
            'tutti': calculate_price_stats(tutti_listings),
            'ebay': calculate_price_stats(ebay_listings)
        }
    }
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status':'healthy'})

# -----------------------------
# Run server
# -----------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT',10000))
    app.run(host='0.0.0.0', port=port, debug=False)
