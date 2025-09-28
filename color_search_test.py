#!/usr/bin/env python3
"""
Color-Specific Search Testing for Turkish Search Engine
Tests the improved search algorithm with stricter matching criteria for colors
"""

import requests
import json
import pandas as pd
import io
from typing import Dict, List, Any

# Backend URL from frontend .env
BACKEND_URL = "https://smart-search-12.preview.emergentagent.com/api"

class ColorSearchTest:
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
    
    def create_color_test_data(self) -> bytes:
        """Create Excel data with specific color products for testing"""
        data = {
            'Marka': [
                'Siemens',      # Yellow LED signal light
                'Schneider',    # Red LED signal light  
                'ABB',          # Green LED signal light
                'Phoenix',      # Blue LED signal light
                'Weidmuller',   # Red lamp (not LED)
                'Omron',        # Yellow lamp (not LED)
                'Pilz',         # Red emergency stop
                'Turck',        # 220V contactor
                'Siemens',      # 24V relay
                'ABB'           # Non-color related product
            ],
            'Kod': [
                'SIE-LED-24V-Y',
                'SCH-LED-24V-R', 
                'ABB-LED-24V-G',
                'PHX-LED-24V-B',
                'WEI-LAMP-R-220V',
                'OMR-LAMP-Y-24V',
                'PIL-ESTOP-R',
                'TUR-CNT-220V',
                'SIE-REL-24V',
                'ABB-SENSOR-M18'
            ],
            'Açıklama': [
                'Sinyal lambası, plastik, sarı, LEDli, 24V DC',           # Yellow LED signal
                'Sinyal lambası, plastik, kırmızı, LEDli, 24V DC',       # Red LED signal
                'Sinyal lambası, plastik, yeşil, LEDli, 24V DC',         # Green LED signal  
                'Sinyal lambası, plastik, mavi, LEDli, 24V DC',          # Blue LED signal
                'Kırmızı lamba, halojen, 220V AC',                       # Red lamp (not LED)
                'Sarı lamba, akkor, 24V DC',                             # Yellow lamp (not LED)
                'Acil stop butonu, mantar kafa, kırmızı',                # Red emergency stop
                'Kontaktör, 3 fazlı, 25A, 220V AC bobinli',             # 220V contactor
                'Güvenlik rölesi, 2NO+2NC, 24V AC/DC',                  # 24V relay
                'Endüktif sensör, M18, PNP, NO, 8mm algılama'           # Non-color sensor
            ],
            'Fiyat': [
                '125.50 TL',
                '130.00 TL',
                '128.75 TL', 
                '132.30 TL',
                '85.00 TL',
                '78.45 TL',
                '180.90 TL',
                '450.75 TL',
                '890.00 TL',
                '275.00 TL'
            ]
        }
        
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Products')
        excel_buffer.seek(0)
        
        return excel_buffer.getvalue()
    
    def upload_test_data(self):
        """Upload color test data to the system"""
        try:
            # Clear existing data first
            clear_response = requests.delete(f"{self.base_url}/products")
            if clear_response.status_code != 200:
                self.log_test("Data Setup - Clear", False, f"Failed to clear existing data: {clear_response.status_code}")
                return False
            
            # Upload new test data
            excel_data = self.create_color_test_data()
            files = {
                'file': ('color_test_products.xlsx', excel_data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            response = requests.post(f"{self.base_url}/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                expected_count = 10  # Number of products in test data
                actual_count = data.get('products_count', 0)
                
                if actual_count == expected_count:
                    self.log_test("Data Setup - Upload", True, f"Successfully uploaded {actual_count} color test products")
                    return True
                else:
                    self.log_test("Data Setup - Upload", False, f"Expected {expected_count} products, got {actual_count}")
                    return False
            else:
                self.log_test("Data Setup - Upload", False, f"Upload failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Data Setup - Upload", False, f"Upload error: {str(e)}")
            return False
    
    def test_critical_color_searches(self):
        """Test the critical color-specific searches mentioned in the review"""
        critical_tests = [
            {
                "query": "sinyal lambası led kırmızı",
                "should_contain": ["kırmızı", "LEDli"],
                "should_not_contain": ["sarı"],
                "description": "Should return ONLY red LED signal lights, NOT yellow ones",
                "max_results": 2  # Should be very specific
            },
            {
                "query": "sarı led", 
                "should_contain": ["sarı", "LEDli"],
                "should_not_contain": ["kırmızı", "yeşil", "mavi"],
                "description": "Should return ONLY yellow LED products",
                "max_results": 2
            },
            {
                "query": "kırmızı lamba",
                "should_contain": ["kırmızı"],
                "should_not_contain": ["sarı", "yeşil", "mavi"],
                "description": "Should return ONLY red light products (LED or regular)",
                "max_results": 3
            }
        ]
        
        for test_case in critical_tests:
            try:
                response = requests.get(f"{self.base_url}/search", params={"q": test_case["query"]})
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    # Check if we got reasonable number of results (precision test)
                    if len(results) > test_case["max_results"]:
                        self.log_test(f"CRITICAL: '{test_case['query']}'", False, 
                                    f"Too many results ({len(results)}), expected max {test_case['max_results']}. Search not precise enough.")
                        continue
                    
                    if not results:
                        self.log_test(f"CRITICAL: '{test_case['query']}'", False, 
                                    f"No results returned. Expected to find products with: {test_case['should_contain']}")
                        continue
                    
                    # Check each result for correct content
                    all_valid = True
                    invalid_results = []
                    
                    for i, result in enumerate(results):
                        product_desc = result['product']['aciklama'].lower()
                        product_brand = result['product']['marka'].lower()
                        product_code = result['product']['kod'].lower()
                        full_text = f"{product_desc} {product_brand} {product_code}"
                        
                        # Check if result contains required terms
                        contains_required = all(term.lower() in full_text for term in test_case["should_contain"])
                        
                        # Check if result contains forbidden terms
                        contains_forbidden = any(term.lower() in full_text for term in test_case["should_not_contain"])
                        
                        if not contains_required or contains_forbidden:
                            all_valid = False
                            invalid_results.append({
                                "position": i + 1,
                                "description": result['product']['aciklama'],
                                "score": result['relevance_score'],
                                "contains_required": contains_required,
                                "contains_forbidden": contains_forbidden
                            })
                    
                    if all_valid:
                        self.log_test(f"CRITICAL: '{test_case['query']}'", True, 
                                    f"✅ Perfect precision! {len(results)} relevant results, no irrelevant ones")
                    else:
                        self.log_test(f"CRITICAL: '{test_case['query']}'", False, 
                                    f"❌ Found {len(invalid_results)} irrelevant results out of {len(results)} total", 
                                    invalid_results)
                else:
                    self.log_test(f"CRITICAL: '{test_case['query']}'", False, 
                                f"Search failed with status {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"CRITICAL: '{test_case['query']}'", False, f"Search error: {str(e)}")
    
    def test_voltage_specific_searches(self):
        """Test voltage-specific searches"""
        voltage_tests = [
            {
                "query": "220v kontaktör",
                "should_contain": ["220v", "kontaktör"],
                "should_not_contain": ["24v"],
                "description": "Should return only 220V contactors"
            },
            {
                "query": "24v röle", 
                "should_contain": ["24v"],
                "should_not_contain": ["220v"],
                "description": "Should return only 24V relays"
            }
        ]
        
        for test_case in voltage_tests:
            try:
                response = requests.get(f"{self.base_url}/search", params={"q": test_case["query"]})
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    if not results:
                        self.log_test(f"Voltage Test: '{test_case['query']}'", False, "No results returned")
                        continue
                    
                    # Check each result
                    all_valid = True
                    for result in results:
                        full_text = f"{result['product']['aciklama']} {result['product']['marka']} {result['product']['kod']}".lower()
                        
                        contains_required = all(term.lower() in full_text for term in test_case["should_contain"])
                        contains_forbidden = any(term.lower() in full_text for term in test_case["should_not_contain"])
                        
                        if not contains_required or contains_forbidden:
                            all_valid = False
                            break
                    
                    if all_valid:
                        self.log_test(f"Voltage Test: '{test_case['query']}'", True, 
                                    f"All {len(results)} results match voltage criteria")
                    else:
                        self.log_test(f"Voltage Test: '{test_case['query']}'", False, 
                                    "Some results don't match voltage criteria")
                else:
                    self.log_test(f"Voltage Test: '{test_case['query']}'", False, 
                                f"Search failed with status {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Voltage Test: '{test_case['query']}'", False, f"Search error: {str(e)}")
    
    def test_precision_improvements(self):
        """Test that search precision has improved with minimum threshold"""
        try:
            # Test a very generic query that should return fewer results now
            response = requests.get(f"{self.base_url}/search", params={"q": "lamba"})
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # With stricter matching, we should get fewer but more relevant results
                if len(results) <= 5:  # Reasonable number for "lamba" query
                    # Check that all results have decent relevance scores
                    min_score = min(result['relevance_score'] for result in results) if results else 0
                    if min_score >= 0.25:  # Our new minimum threshold
                        self.log_test("Precision Improvement", True, 
                                    f"Good precision: {len(results)} results, min score: {min_score:.2f}")
                    else:
                        self.log_test("Precision Improvement", False, 
                                    f"Low relevance scores: min score {min_score:.2f} below 0.25 threshold")
                else:
                    self.log_test("Precision Improvement", False, 
                                f"Too many results ({len(results)}) for generic query - precision not improved")
            else:
                self.log_test("Precision Improvement", False, 
                            f"Search failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Precision Improvement", False, f"Precision test error: {str(e)}")
    
    def test_turkish_normalization(self):
        """Test that Turkish character normalization still works"""
        normalization_tests = [
            {
                "query": "güvenlik",  # With Turkish characters
                "alt_query": "guvenlik",  # Without Turkish characters
                "description": "Turkish ğ and ü normalization"
            },
            {
                "query": "röle",
                "alt_query": "role", 
                "description": "Turkish ö normalization"
            }
        ]
        
        for test_case in normalization_tests:
            try:
                # Search with Turkish characters
                response1 = requests.get(f"{self.base_url}/search", params={"q": test_case["query"]})
                # Search without Turkish characters  
                response2 = requests.get(f"{self.base_url}/search", params={"q": test_case["alt_query"]})
                
                if response1.status_code == 200 and response2.status_code == 200:
                    data1 = response1.json()
                    data2 = response2.json()
                    
                    results1 = data1.get('results', [])
                    results2 = data2.get('results', [])
                    
                    # Both searches should return similar results (normalization working)
                    if len(results1) > 0 and len(results2) > 0:
                        self.log_test(f"Turkish Normalization: {test_case['description']}", True, 
                                    f"Both queries returned results: {len(results1)} vs {len(results2)}")
                    elif len(results1) == 0 and len(results2) == 0:
                        self.log_test(f"Turkish Normalization: {test_case['description']}", True, 
                                    "Both queries returned no results (consistent)")
                    else:
                        self.log_test(f"Turkish Normalization: {test_case['description']}", False, 
                                    f"Inconsistent results: {len(results1)} vs {len(results2)}")
                else:
                    self.log_test(f"Turkish Normalization: {test_case['description']}", False, 
                                "One or both searches failed")
                    
            except Exception as e:
                self.log_test(f"Turkish Normalization: {test_case['description']}", False, f"Error: {str(e)}")
    
    def run_color_tests(self):
        """Run all color-specific tests"""
        print("🎨 Starting Color-Specific Search Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 70)
        
        # Setup test data
        if not self.upload_test_data():
            print("❌ Failed to setup test data. Aborting tests.")
            return False
        
        print("\n🔍 Running Critical Color Search Tests...")
        self.test_critical_color_searches()
        
        print("\n⚡ Running Voltage-Specific Tests...")
        self.test_voltage_specific_searches()
        
        print("\n🎯 Running Precision Improvement Tests...")
        self.test_precision_improvements()
        
        print("\n🇹🇷 Running Turkish Normalization Tests...")
        self.test_turkish_normalization()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 COLOR SEARCH TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show critical test results
        critical_tests = [r for r in self.test_results if "CRITICAL" in r['test']]
        critical_passed = sum(1 for r in critical_tests if r['success'])
        
        print(f"\n🚨 CRITICAL TESTS: {critical_passed}/{len(critical_tests)} passed")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        return passed == total and critical_passed == len(critical_tests)

if __name__ == "__main__":
    tester = ColorSearchTest()
    success = tester.run_color_tests()
    
    if success:
        print("\n🎉 All color search tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the details above.")