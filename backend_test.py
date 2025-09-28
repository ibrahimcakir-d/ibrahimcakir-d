#!/usr/bin/env python3
"""
Backend Testing for Excel-based Turkish Search Engine
Tests all API endpoints with Turkish data and fuzzy matching
"""

import requests
import json
import pandas as pd
import io
import os
from typing import Dict, List, Any

# Backend URL from frontend .env
BACKEND_URL = "https://smart-search-12.preview.emergentagent.com/api"

class ExcelSearchEngineTest:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def create_sample_excel_data(self) -> bytes:
        """Create sample Excel data with Turkish product information"""
        data = {
            'Marka': [
                'Siemens',
                'Schneider Electric', 
                'ABB',
                'Phoenix Contact',
                'Weidmuller',
                'Omron',
                'Pilz',
                'Turck'
            ],
            'Kod': [
                'SIE-LED-24V-Y',
                'SCH-REL-24V-SF',
                'ABB-CNT-25A-3P',
                'PHX-TRM-2.5-BL',
                'WEI-IND-M18-8MM',
                'OMR-PHT-100MM',
                'PIL-EST-RED-MT',
                'TUR-CAP-M30-15MM'
            ],
            'Açıklama': [
                'Sinyal lambası, plastik, sarı, LEDli, 24V DC',
                'Güvenlik rölesi, 2NO+2NC, 24V AC/DC',
                'Kontaktör, 3 fazlı, 25A, 230V AC bobinli',
                'Terminal blok, çok katlı, 2.5mm², mavi',
                'Endüktif sensör, M18, PNP, NO, 8mm algılama',
                'Fotoelektrik sensör, diffüz, 100mm menzil',
                'Acil stop butonu, mantar kafa, kırmızı',
                'Yakınlık sensörü, kapasitif, M30, 15mm'
            ],
            'Fiyat': [
                '125.50 TL',
                '890.00 TL', 
                '450.75 TL',
                '12.30 TL',
                '275.00 TL',
                '320.45 TL',
                '180.90 TL',
                '195.60 TL'
            ]
        }
        
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Products')
        excel_buffer.seek(0)
        
        return excel_buffer.getvalue()
    
    def create_invalid_excel_data(self) -> bytes:
        """Create Excel with missing required columns"""
        data = {
            'Brand': ['Test Brand'],  # Wrong column name
            'Code': ['TEST-001'],  # Wrong column name
            'Description': ['Test Description'],  # Wrong column name  
            'Cost': ['100 TL']  # Wrong column name - should be 4 columns but wrong names
        }
        
        df = pd.DataFrame(data)
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Products')
        excel_buffer.seek(0)
        
        return excel_buffer.getvalue()
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        try:
            response = requests.get(f"{self.base_url.replace('/api', '')}/")
            if response.status_code == 200:
                # Root endpoint serves frontend HTML, not JSON
                if 'html' in response.headers.get('content-type', '').lower():
                    self.log_test("Root Endpoint", True, "Root endpoint serves frontend HTML correctly")
                else:
                    # Try to parse as JSON (for API root)
                    try:
                        data = response.json()
                        self.log_test("Root Endpoint", True, f"Root endpoint accessible: {data.get('message', 'No message')}")
                    except:
                        self.log_test("Root Endpoint", True, "Root endpoint accessible (non-JSON response)")
            else:
                self.log_test("Root Endpoint", False, f"Root endpoint failed with status {response.status_code}")
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Root endpoint error: {str(e)}")
    
    def test_excel_upload_valid(self):
        """Test Excel upload with valid file"""
        try:
            excel_data = self.create_sample_excel_data()
            
            files = {
                'file': ('test_products.xlsx', excel_data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            response = requests.post(f"{self.base_url}/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                expected_count = 8  # Number of products in sample data
                actual_count = data.get('products_count', 0)
                
                if actual_count == expected_count:
                    self.log_test("Excel Upload Valid", True, f"Successfully uploaded {actual_count} products", data)
                else:
                    self.log_test("Excel Upload Valid", False, f"Expected {expected_count} products, got {actual_count}", data)
            else:
                self.log_test("Excel Upload Valid", False, f"Upload failed with status {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Excel Upload Valid", False, f"Upload error: {str(e)}")
    
    def test_excel_upload_invalid_format(self):
        """Test Excel upload with invalid file format"""
        try:
            # Create a text file instead of Excel
            text_data = b"This is not an Excel file"
            
            files = {
                'file': ('test.txt', text_data, 'text/plain')
            }
            
            response = requests.post(f"{self.base_url}/upload", files=files)
            
            if response.status_code == 400:
                self.log_test("Excel Upload Invalid Format", True, "Correctly rejected non-Excel file")
            else:
                self.log_test("Excel Upload Invalid Format", False, f"Should reject non-Excel files, got status {response.status_code}")
                
        except Exception as e:
            self.log_test("Excel Upload Invalid Format", False, f"Invalid format test error: {str(e)}")
    
    def test_excel_upload_missing_columns(self):
        """Test Excel upload with missing required columns"""
        try:
            excel_data = self.create_invalid_excel_data()
            
            files = {
                'file': ('invalid_products.xlsx', excel_data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            response = requests.post(f"{self.base_url}/upload", files=files)
            
            # Should either succeed (if auto-mapping works) or fail with 400
            if response.status_code in [200, 400]:
                if response.status_code == 400:
                    self.log_test("Excel Upload Missing Columns", True, "Correctly handled missing columns")
                else:
                    # Auto-mapping worked
                    data = response.json()
                    self.log_test("Excel Upload Missing Columns", True, f"Auto-mapped columns, uploaded {data.get('products_count', 0)} products")
            else:
                self.log_test("Excel Upload Missing Columns", False, f"Unexpected status {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Excel Upload Missing Columns", False, f"Missing columns test error: {str(e)}")
    
    def test_search_turkish_fuzzy(self):
        """Test Turkish search with fuzzy matching"""
        test_cases = [
            {
                "query": "sarı led",
                "expected_match": "Sinyal lambası, plastik, sarı, LEDli",
                "description": "Should match 'sarı' and 'LEDli' in description"
            },
            {
                "query": "güvenlik röle",
                "expected_match": "Güvenlik rölesi",
                "description": "Should match Turkish characters ğ and ö"
            },
            {
                "query": "kontaktor 25A",
                "expected_match": "Kontaktör, 3 fazlı, 25A",
                "description": "Should match kontaktör and 25A"
            },
            {
                "query": "sensör endüktif",
                "expected_match": "Endüktif sensör",
                "description": "Should match Turkish ü character"
            },
            {
                "query": "acil stop",
                "expected_match": "Acil stop butonu",
                "description": "Should match exact Turkish words"
            }
        ]
        
        for test_case in test_cases:
            try:
                response = requests.get(f"{self.base_url}/search", params={"q": test_case["query"]})
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    if results:
                        # Check if expected match is in top results
                        found_match = False
                        for result in results[:3]:  # Check top 3 results
                            product_desc = result['product']['aciklama']
                            if test_case["expected_match"].lower() in product_desc.lower():
                                found_match = True
                                break
                        
                        if found_match:
                            self.log_test(f"Search Turkish Fuzzy: '{test_case['query']}'", True, 
                                        f"Found expected match. Total results: {len(results)}")
                        else:
                            self.log_test(f"Search Turkish Fuzzy: '{test_case['query']}'", False, 
                                        f"Expected match not found in top results. Got {len(results)} results")
                    else:
                        self.log_test(f"Search Turkish Fuzzy: '{test_case['query']}'", False, "No search results returned")
                else:
                    self.log_test(f"Search Turkish Fuzzy: '{test_case['query']}'", False, 
                                f"Search failed with status {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Search Turkish Fuzzy: '{test_case['query']}'", False, f"Search error: {str(e)}")
    
    def test_search_edge_cases(self):
        """Test search edge cases"""
        edge_cases = [
            {"query": "", "description": "Empty query", "expect_422": True},
            {"query": "   ", "description": "Whitespace only query"},
            {"query": "xyz123nonexistent", "description": "Non-existent term"},
            {"query": "çğıöşü", "description": "Turkish special characters only"},
            {"query": "a", "description": "Single character"},
            {"query": "ab", "description": "Two characters (should be filtered)"}
        ]
        
        for case in edge_cases:
            try:
                response = requests.get(f"{self.base_url}/search", params={"q": case["query"]})
                
                # Check if we expect a 422 status for this case
                if case.get("expect_422", False):
                    if response.status_code == 422:
                        self.log_test(f"Search Edge Case: {case['description']}", True, 
                                    f"Query '{case['query']}' correctly rejected with 422 status")
                    else:
                        self.log_test(f"Search Edge Case: {case['description']}", False, 
                                    f"Expected 422 status, got {response.status_code}")
                elif response.status_code == 200:
                    data = response.json()
                    results_count = data.get('total_count', 0)
                    self.log_test(f"Search Edge Case: {case['description']}", True, 
                                f"Query '{case['query']}' returned {results_count} results")
                else:
                    self.log_test(f"Search Edge Case: {case['description']}", False, 
                                f"Query failed with status {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Search Edge Case: {case['description']}", False, f"Error: {str(e)}")
    
    def test_search_relevance_scoring(self):
        """Test search relevance scoring and ranking"""
        try:
            # Search for a term that should match multiple products
            response = requests.get(f"{self.base_url}/search", params={"q": "sensör"})
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if len(results) >= 2:
                    # Check if results are sorted by relevance score (highest first)
                    scores = [result['relevance_score'] for result in results]
                    is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
                    
                    if is_sorted:
                        self.log_test("Search Relevance Scoring", True, 
                                    f"Results properly sorted by relevance. Top score: {scores[0]:.2f}")
                    else:
                        self.log_test("Search Relevance Scoring", False, 
                                    f"Results not sorted by relevance. Scores: {scores}")
                else:
                    self.log_test("Search Relevance Scoring", False, 
                                f"Not enough results to test sorting. Got {len(results)} results")
            else:
                self.log_test("Search Relevance Scoring", False, 
                            f"Search failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Search Relevance Scoring", False, f"Relevance scoring test error: {str(e)}")
    
    def test_products_count(self):
        """Test product count endpoint"""
        try:
            response = requests.get(f"{self.base_url}/products/count")
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', -1)
                
                if count >= 0:
                    self.log_test("Products Count", True, f"Product count endpoint returned: {count}")
                else:
                    self.log_test("Products Count", False, "Count endpoint returned invalid count")
            else:
                self.log_test("Products Count", False, f"Count endpoint failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Products Count", False, f"Count endpoint error: {str(e)}")
    
    def test_clear_products(self):
        """Test clear products endpoint"""
        try:
            response = requests.delete(f"{self.base_url}/products")
            
            if response.status_code == 200:
                data = response.json()
                message = data.get('message', '')
                self.log_test("Clear Products", True, f"Clear products successful: {message}")
                
                # Verify products were cleared
                count_response = requests.get(f"{self.base_url}/products/count")
                if count_response.status_code == 200:
                    count_data = count_response.json()
                    if count_data.get('count', -1) == 0:
                        self.log_test("Clear Products Verification", True, "Products successfully cleared")
                    else:
                        self.log_test("Clear Products Verification", False, 
                                    f"Products not cleared, count: {count_data.get('count')}")
            else:
                self.log_test("Clear Products", False, f"Clear failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Clear Products", False, f"Clear products error: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Excel Search Engine Backend Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        self.test_root_endpoint()
        self.test_clear_products()  # Clear any existing data first
        self.test_excel_upload_valid()
        self.test_excel_upload_invalid_format()
        # Note: Skip missing columns test as it overwrites good data
        # self.test_excel_upload_missing_columns()
        self.test_search_turkish_fuzzy()
        self.test_search_edge_cases()
        self.test_search_relevance_scoring()
        self.test_products_count()
        # Test missing columns after search tests
        self.test_excel_upload_missing_columns()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        return passed == total

if __name__ == "__main__":
    tester = ExcelSearchEngineTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the details above.")