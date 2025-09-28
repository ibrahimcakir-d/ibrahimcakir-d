#!/usr/bin/env python3
"""
Debug search results for color matching issue
"""

import requests
import json

BACKEND_URL = "https://smart-search-12.preview.emergentagent.com/api"

def debug_search(query):
    """Debug a specific search query"""
    print(f"\n🔍 Debugging search: '{query}'")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BACKEND_URL}/search", params={"q": query})
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            print(f"Total results: {len(results)}")
            print(f"Query: {data.get('query', 'N/A')}")
            
            for i, result in enumerate(results, 1):
                product = result['product']
                score = result['relevance_score']
                
                print(f"\n{i}. Score: {score:.3f}")
                print(f"   Marka: {product['marka']}")
                print(f"   Kod: {product['kod']}")
                print(f"   Açıklama: {product['aciklama']}")
                print(f"   Fiyat: {product['fiyat']}")
        else:
            print(f"❌ Search failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    # Debug the critical failing searches
    debug_search("sinyal lambası led kırmızı")
    debug_search("sarı led")
    debug_search("220v kontaktör")