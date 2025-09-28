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
    """Calculate relevance score based on keyword matches in description, brand, and code"""
    # Normalize all text fields
    normalized_desc = normalize_text(description)
    normalized_brand = normalize_text(brand) 
    normalized_code = normalize_text(code)
    
    # Split into words
    desc_words = normalized_desc.split()
    brand_words = normalized_brand.split()
    code_words = normalized_code.split()
    all_words = desc_words + brand_words + code_words
    
    matches = 0.0
    total_query_words = len([w for w in query_words if len(w) > 1])  # Only count meaningful words
    
    if total_query_words == 0:
        return 0.0
    
    for query_word in query_words:
        if len(query_word) <= 1:  # Skip very short words
            continue
            
        # Check for exact matches (highest score)
        if query_word in all_words:
            matches += 1.0
            continue
            
        # Check for partial matches in description (medium score)
        found_partial = False
        for desc_word in desc_words:
            if len(desc_word) > 2 and (query_word in desc_word or desc_word in query_word):
                matches += 0.7
                found_partial = True
                break
        
        if found_partial:
            continue
            
        # Check for partial matches in brand/code (lower score)  
        for word in brand_words + code_words:
            if len(word) > 2 and (query_word in word or word in query_word):
                matches += 0.5
                break
    
    return min(matches / total_query_words, 1.0)  # Cap at 1.0

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
        
        # Use pandas to read Excel
        try:
            df = pd.read_excel(contents)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")
        
        # Validate columns
        required_columns = ['marka', 'aciklama', 'fiyat']
        df.columns = df.columns.str.lower()
        
        missing_columns = []
        for col in required_columns:
            if col not in df.columns:
                # Try to find similar column names
                if len(df.columns) >= 3:
                    df.columns = ['marka', 'aciklama', 'fiyat']
                    break
                else:
                    missing_columns.append(col)
        
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"Missing columns: {missing_columns}")
        
        # Clear existing products
        await db.products.delete_many({})
        
        # Process and insert products
        products = []
        upload_date = datetime.now().isoformat()
        
        for index, row in df.iterrows():
            if pd.isna(row['marka']) or pd.isna(row['aciklama']) or pd.isna(row['fiyat']):
                continue
                
            product = {
                "id": str(uuid.uuid4()),
                "marka": str(row['marka']).strip(),
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
        query_words = [word for word in normalized_query.split() if len(word) > 2]
        
        if not query_words:
            return SearchResponse(
                results=[],
                total_count=0,
                query=q
            )
        
        # Get all products
        cursor = db.products.find({})
        products = await cursor.to_list(length=None)
        
        # Calculate relevance scores
        scored_results = []
        for product_data in products:
            score = calculate_relevance_score(query_words, product_data['aciklama'])
            if score > 0:  # Only include products with some relevance
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