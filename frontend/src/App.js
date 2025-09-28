import React, { useState, useCallback, useRef } from 'react';
import './App.css';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [productsCount, setProductsCount] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  // Search products
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/search?q=${encodeURIComponent(searchQuery.trim())}`);
      if (!response.ok) {
        throw new Error('Search failed');
      }
      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (error) {
      console.error('Search error:', error);
      setUploadStatus('Arama sırasında hata oluştu');
    }
    setIsLoading(false);
  }, [searchQuery, BACKEND_URL]);

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  // Upload Excel file
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
      setUploadStatus('Lütfen sadece Excel dosyası (.xlsx veya .xls) seçin');
      return;
    }

    setIsUploading(true);
    setUploadStatus('Dosya yükleniyor...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${BACKEND_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setUploadStatus(`✅ ${data.message}`);
      setProductsCount(data.products_count);
      
      // Clear search results after successful upload
      setSearchResults([]);
      setSearchQuery('');
      
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus(`❌ Yükleme hatası: ${error.message}`);
    }
    setIsUploading(false);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Get products count on component mount
  React.useEffect(() => {
    const getProductsCount = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/products/count`);
        if (response.ok) {
          const data = await response.json();
          setProductsCount(data.count);
        }
      } catch (error) {
        console.error('Error getting products count:', error);
      }
    };
    getProductsCount();
  }, [BACKEND_URL]);

  return (
    <div className="App">
      {/* Header */}
      <header className="hero-section">
        <div className="hero-content">
          <div className="hero-image">
            <img 
              src="https://images.unsplash.com/photo-1657256031790-e898b7b3f3eb" 
              alt="Search Interface"
              className="hero-img"
            />
          </div>
          <div className="hero-text">
            <h1>Akıllı Ürün Arama Motoru</h1>
            <p>Excel verilerinizi yükleyin ve akıllı arama ile hızlıca ürünleri bulun</p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Upload Section */}
        <div className="upload-section">
          <div className="upload-card">
            <h2>📊 Excel Dosyası Yükle</h2>
            <p>Sütun sırası: A=Marka, B=Kod, C=Açıklama, D=Fiyat</p>
            
            <div className="file-upload-area">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".xlsx,.xls"
                className="file-input"
                disabled={isUploading}
              />
              <div className="file-upload-text">
                {isUploading ? '📤 Yükleniyor...' : '📁 Excel dosyası seçin'}
              </div>
            </div>

            {uploadStatus && (
              <div className={`upload-status ${uploadStatus.includes('❌') ? 'error' : 'success'}`}>
                {uploadStatus}
              </div>
            )}

            <div className="products-count">
              Veritabanında {productsCount.toLocaleString('tr-TR')} ürün var
            </div>
          </div>
        </div>

        {/* Search Section */}
        <div className="search-section">
          <div className="search-card">
            <h2>🔍 Ürün Ara</h2>
            <div className="search-box">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Örn: sinyal lambası sarı 220V LED"
                className="search-input"
                disabled={isLoading}
              />
              <button 
                onClick={handleSearch}
                className="search-button"
                disabled={isLoading || !searchQuery.trim()}
              >
                {isLoading ? '🔄' : '🔍'}
                {isLoading ? 'Aranıyor...' : 'Ara'}
              </button>
            </div>

            <div className="search-tips">
              <p>💡 <strong>Arama İpuçları:</strong> Ürün özelliklerini yazın (renk, voltaj, tip, vb.)</p>
            </div>
          </div>
        </div>

        {/* Results Section */}
        {searchResults.length > 0 && (
          <div className="results-section">
            <div className="results-header">
              <h3>📋 Arama Sonuçları ({searchResults.length} ürün bulundu)</h3>
              <p>En uygun sonuçlar önce gösteriliyor</p>
            </div>
            
            <div className="results-grid">
              {searchResults.map((result, index) => (
                <div key={result.product.id} className="result-card">
                  <div className="result-header">
                    <div className="result-rank">#{index + 1}</div>
                    <div className="relevance-score">
                      🎯 Uygunluk: {(result.relevance_score * 100).toFixed(0)}%
                    </div>
                  </div>
                  
                  <div className="result-content">
                    <div className="brand">
                      <strong>🏷️ Marka:</strong> {result.product.marka}
                    </div>
                    <div className="description">
                      <strong>📝 Açıklama:</strong> {result.product.aciklama}
                    </div>
                    <div className="price">
                      <strong>💰 Fiyat:</strong> {result.product.fiyat}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {searchQuery && searchResults.length === 0 && !isLoading && (
          <div className="no-results">
            <div className="no-results-card">
              <h3>🚫 Sonuç Bulunamadı</h3>
              <p>Aramanız için uygun ürün bulunamadı.</p>
              <div className="search-suggestions">
                <p><strong>Öneriler:</strong></p>
                <ul>
                  <li>Daha genel terimler kullanın</li>
                  <li>Yazım hatalarını kontrol edin</li>
                  <li>Farklı anahtar kelimeler deneyin</li>
                  <li>Türkçe karakterleri kullanın</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <p>© 2024 Akıllı Ürün Arama Motoru - Excel verilerinizi kolayca arayın</p>
        </div>
      </footer>
    </div>
  );
}

export default App;