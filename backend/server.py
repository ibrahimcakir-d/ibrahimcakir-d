from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
import os
import pandas as pd
import uuid
import re
import unicodedata
from datetime import datetime

# Database configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DATABASE_NAME = "search_engine_db"

# FastAPI app
app = FastAPI(title="Excel Search Engine API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB client
client = AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]

# Pydantic models
class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    marka: str
    kod: str
    aciklama: str
    fiyat: str
    normalized_aciklama: str
    upload_date: str

class SearchResult(BaseModel):
    product: Product
    relevance_score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_count: int
    query: str

class UploadResponse(BaseModel):
    message: str
    products_count: int
    upload_date: str

def normalize_text(text: str) -> str:
    """Normalize text for better search matching"""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove Turkish accents and special characters
    replacements = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'â': 'a', 'î': 'i', 'û': 'u', 'é': 'e'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Remove punctuation and extra spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def calculate_relevance_score(query_words: List[str], description: str, brand: str, code: str) -> float:
    """Calculate relevance score with very strict matching - ALL query terms must be satisfied"""
    # Normalize all text fields
    normalized_desc = normalize_text(description)
    normalized_brand = normalize_text(brand) 
    normalized_code = normalize_text(code)
    all_text = f"{normalized_desc} {normalized_brand} {normalized_code}"
    
    # Define critical keywords categories
    color_keywords = ['sari', 'kirmizi', 'yesil', 'mavi', 'beyaz', 'siyah', 'turuncu', 'mor']
    voltage_keywords = ['220v', '24v', '12v', '110v', '380v', '220', '24', '12', '110', '380']
    product_type_keywords = ['led', 'ledi', 'ledli', 'kontaktor', 'role', 'sensor', 'sensor', 'buton', 'lamba', 'isik']
    
    query_colors = [w for w in query_words if w in color_keywords]
    query_voltages = [w for w in query_words if w in voltage_keywords] 
    query_product_types = [w for w in query_words if w in product_type_keywords]
    query_other = [w for w in query_words if w not in color_keywords + voltage_keywords + product_type_keywords and len(w) > 1]
    
    # Check if ALL categories present in query are also present in product
    total_matches = 0.0
    total_required = 0.0
    
    # Colors - if query has colors, product MUST have matching colors
    if query_colors:
        color_found = False
        for color in query_colors:
            if color in all_text:
                color_found = True
                total_matches += 1.0
                break
        
        total_required += 1.0
        if not color_found:
            return 0.0  # Immediate fail if color doesn't match
    
    # Voltages - if query has voltages, product MUST have matching voltages
    if query_voltages:
        voltage_found = False
        for voltage in query_voltages:
            if voltage in all_text:
                voltage_found = True
                total_matches += 1.0
                break
        
        total_required += 1.0
        if not voltage_found:
            return 0.0  # Immediate fail if voltage doesn't match
    
    # Product types - if query has product types, product MUST have them
    if query_product_types:
        product_type_score = 0.0
        for ptype in query_product_types:
            if ptype in all_text:
                product_type_score += 1.0
            else:
                # Check for related terms
                related_terms = {
                    'led': ['led', 'ledi', 'ledli'],
                    'kontaktor': ['kontaktor', 'contactor'],
                    'role': ['role', 'rele', 'relay'],
                    'sensor': ['sensor', 'sensor'],
                    'lamba': ['lamba', 'isik', 'light']
                }
                found_related = False
                for main_term, related_list in related_terms.items():
                    if ptype == main_term:
                        for related in related_list:
                            if related in all_text:
                                product_type_score += 0.8
                                found_related = True
                                break
                        if found_related:
                            break
        
        if len(query_product_types) > 0:
            product_type_match_ratio = product_type_score / len(query_product_types)
            if product_type_match_ratio < 0.7:  # At least 70% of product types must match
                return 0.0
            total_matches += product_type_match_ratio
            total_required += 1.0
    
    # Other general terms - at least 50% should match
    if query_other:
        other_matches = 0.0
        for term in query_other:
            if term in all_text:
                other_matches += 1.0
            else:
                # Partial matching for general terms
                words = all_text.split()
                for word in words:
                    if len(word) > 3 and len(term) > 3 and (term in word or word in term):
                        other_matches += 0.5
                        break
        
        other_match_ratio = other_matches / len(query_other)
        if other_match_ratio < 0.5:  # At least 50% of other terms must match
            return 0.0
        
        total_matches += other_match_ratio
        total_required += 1.0
    
    # Calculate final score
    if total_required == 0:
        return 0.0
    
    return min(total_matches / total_required, 1.0)

@app.get("/")
async def root():
    return {"message": "Excel Search Engine API"}

@app.post("/api/upload", response_model=UploadResponse)
async def upload_excel(file: UploadFile = File(...)):
    """Upload and process Excel file"""
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files are allowed")
        
        # Read Excel file
        contents = await file.read()
        
        # Use pandas to read Excel with BytesIO to avoid deprecation warning
        from io import BytesIO
        try:
            df = pd.read_excel(BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")
        
        # Validate columns - expect 4 columns: Marka, Kod, Açıklama, Fiyat
        if len(df.columns) >= 4:
            df.columns = ['marka', 'kod', 'aciklama', 'fiyat']
        else:
            # Try to find columns by name
            df.columns = df.columns.str.lower()
            required_columns = ['marka', 'kod', 'aciklama', 'fiyat']
            missing_columns = []
            for col in required_columns:
                if col not in df.columns:
                    missing_columns.append(col)
            
            if missing_columns:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Excel dosyası 4 sütun içermelidir: Marka, Kod, Açıklama, Fiyat. Eksik sütunlar: {missing_columns}"
                )
        
        # Clear existing products
        await db.products.delete_many({})
        
        # Process and insert products
        products = []
        upload_date = datetime.now().isoformat()
        
        for index, row in df.iterrows():
            if pd.isna(row['marka']) or pd.isna(row['kod']) or pd.isna(row['aciklama']) or pd.isna(row['fiyat']):
                continue
                
            product = {
                "id": str(uuid.uuid4()),
                "marka": str(row['marka']).strip(),
                "kod": str(row['kod']).strip(), 
                "aciklama": str(row['aciklama']).strip(),
                "fiyat": str(row['fiyat']).strip(),
                "normalized_aciklama": normalize_text(str(row['aciklama'])),
                "upload_date": upload_date
            }
            products.append(product)
        
        if products:
            await db.products.insert_many(products)
        
        return UploadResponse(
            message=f"Successfully uploaded {len(products)} products",
            products_count=len(products),
            upload_date=upload_date
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/search", response_model=SearchResponse)
async def search_products(q: str = Query(..., min_length=1)):
    """Search products by query"""
    try:
        # Normalize and tokenize query
        normalized_query = normalize_text(q)
        query_words = [word for word in normalized_query.split() if len(word) > 1]  # Changed from > 2 to > 1
        
        if not query_words:
            return SearchResponse(
                results=[],
                total_count=0,
                query=q
            )
        
        # Get all products
        cursor = db.products.find({})
        products = await cursor.to_list(length=None)
        
        # Calculate relevance scores with strict threshold
        scored_results = []
        for product_data in products:
            score = calculate_relevance_score(
                query_words, 
                product_data['aciklama'],
                product_data['marka'],
                product_data['kod']
            )
            # Only include products with meaningful relevance (strict threshold)
            if score > 0.5:  # Increased to 0.5 for very strict matching
                product = Product(**product_data)
                scored_results.append(SearchResult(
                    product=product,
                    relevance_score=score
                ))
        
        # Sort by relevance score (highest first)
        scored_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return SearchResponse(
            results=scored_results,
            total_count=len(scored_results),
            query=q
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/api/products/count")
async def get_products_count():
    """Get total number of products in database"""
    try:
        count = await db.products.count_documents({})
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting products: {str(e)}")

@app.delete("/api/products")
async def clear_products():
    """Clear all products from database"""
    try:
        result = await db.products.delete_many({})
        return {"message": f"Deleted {result.deleted_count} products"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing products: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)