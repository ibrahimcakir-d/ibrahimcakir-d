#!/usr/bin/env python3
"""
Test the search algorithm logic to understand the scoring issues
"""

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
    import re
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def calculate_relevance_score_debug(query_words, description, brand, code):
    """Debug version of the relevance score calculation"""
    print(f"\n🔍 Debugging score calculation:")
    print(f"Query words: {query_words}")
    print(f"Description: {description}")
    
    # Normalize all text fields
    normalized_desc = normalize_text(description)
    normalized_brand = normalize_text(brand) 
    normalized_code = normalize_text(code)
    
    print(f"Normalized desc: '{normalized_desc}'")
    print(f"Normalized brand: '{normalized_brand}'")
    print(f"Normalized code: '{normalized_code}'")
    
    # Split into words
    desc_words = normalized_desc.split()
    brand_words = normalized_brand.split()
    code_words = normalized_code.split()
    all_words = desc_words + brand_words + code_words
    all_text = f"{normalized_desc} {normalized_brand} {normalized_code}"
    
    print(f"All words: {all_words}")
    print(f"All text: '{all_text}'")
    
    # Define critical keywords that need exact matches
    color_keywords = ['sari', 'kirmizi', 'yesil', 'mavi', 'beyaz', 'siyah', 'turuncu', 'mor']
    voltage_keywords = ['220v', '24v', '12v', '110v', '380v']
    
    matches = 0.0
    critical_mismatches = 0
    total_query_words = len([w for w in query_words if len(w) > 1])
    
    print(f"Total query words (>1 char): {total_query_words}")
    
    if total_query_words == 0:
        return 0.0
    
    for query_word in query_words:
        if len(query_word) <= 1:
            continue
            
        print(f"\nProcessing query word: '{query_word}'")
        
        # For critical keywords (colors, voltages), require exact or very close matches
        if query_word in color_keywords or query_word in voltage_keywords:
            print(f"  → Critical keyword (color/voltage)")
            if query_word in all_words:
                matches += 1.0  # Exact match for critical keywords
                print(f"  → Exact match found! matches += 1.0 (total: {matches})")
            elif query_word in all_text:
                matches += 0.8  # Partial match for critical keywords
                print(f"  → Partial match found! matches += 0.8 (total: {matches})")
            else:
                critical_mismatches += 1  # Missing critical keyword
                print(f"  → MISSING critical keyword! critical_mismatches += 1 (total: {critical_mismatches})")
            continue
        
        # For regular keywords
        print(f"  → Regular keyword")
        if query_word in all_words:
            matches += 1.0  # Exact word match
            print(f"  → Exact match found! matches += 1.0 (total: {matches})")
        elif query_word in all_text:
            matches += 0.6  # Substring match
            print(f"  → Substring match found! matches += 0.6 (total: {matches})")
        else:
            # Check for partial matches with minimum length requirement
            found_partial = False
            for word in all_words:
                if len(word) > 3 and len(query_word) > 3:
                    if query_word in word or word in query_word:
                        matches += 0.3  # Reduced score for partial matches
                        found_partial = True
                        print(f"  → Partial match with '{word}'! matches += 0.3 (total: {matches})")
                        break
            if not found_partial:
                print(f"  → NO match found for '{query_word}'")
    
    # Calculate base score
    base_score = matches / total_query_words if total_query_words > 0 else 0.0
    print(f"\nBase score: {matches} / {total_query_words} = {base_score}")
    
    # Apply penalties for critical mismatches
    if critical_mismatches > 0:
        penalty = critical_mismatches * 0.5
        base_score = max(0, base_score - penalty)
        print(f"Critical mismatches penalty: {critical_mismatches} * 0.5 = {penalty}")
        print(f"Final score after penalty: {base_score}")
    
    final_score = min(base_score, 1.0)
    print(f"Final score (capped at 1.0): {final_score}")
    
    return final_score

if __name__ == "__main__":
    # Test the problematic cases
    print("=" * 60)
    print("TESTING: 'sarı led' vs 'Sarı lamba, akkor, 24V DC'")
    print("=" * 60)
    
    query_words = normalize_text("sarı led").split()
    score = calculate_relevance_score_debug(
        query_words,
        "Sarı lamba, akkor, 24V DC",
        "Omron", 
        "OMR-LAMP-Y-24V"
    )
    
    print("=" * 60)
    print("TESTING: 'sinyal lambası led kırmızı' vs 'Kırmızı lamba, halojen, 220V AC'")
    print("=" * 60)
    
    query_words = normalize_text("sinyal lambası led kırmızı").split()
    score = calculate_relevance_score_debug(
        query_words,
        "Kırmızı lamba, halojen, 220V AC",
        "Weidmuller",
        "WEI-LAMP-R-220V"
    )