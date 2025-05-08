# Temel Python imajını kullan (python:3.9-slim, uygulamanızın Python 3.9 ile uyumlu olduğunu varsayarak)
FROM python:3.9-slim

# Build sırasında apt-get komutlarının kullanıcıdan girdi beklemesini engelle
ENV DEBIAN_FRONTEND=noninteractive

# Sistem paketlerini güncelle ve Chrome, ChromeDriver ve diğer bağımlılıkları kur
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    # Chrome'un çalışması için gerekli temel kütüphaneler:
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    libatspi2.0-0 \
    xvfb \ # X Virtual FrameBuffer, headless ortamlar için önemlidir
    --no-install-recommends \
    # Google Chrome'u kur
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable --no-install-recommends \
    && echo "--- Chrome Kurulum Kontrolü ---" \
    && google-chrome --version \
    && echo "Chrome'un bulunduğu yol (which google-chrome): $(which google-chrome)" \
    \
    # ChromeDriver'ı kur
    && echo "--- ChromeDriver Kurulumu Başlıyor ---" \
    # Chrome ana sürümünü al (örneğin 124.0.6367.201 -> 124)
    && CHROME_MAJOR_VERSION=$(google-chrome --version | sed 's/.*Google Chrome \([0-9]*\).*/\1/') \
    && echo "Tespit edilen Chrome Ana Sürümü: $CHROME_MAJOR_VERSION" \
    # Chrome for Testing JSON endpoint'lerinden uygun ChromeDriver sürümünü bul
    # Bu endpoint genellikle en son kararlı sürümlerle uyumlu sürümleri listeler.
    # CHROME_MAJOR_VERSION'a göre en yakın ve stabil sürümü bulmaya çalışır.
    # Not: Bu URL ve JSON yapısı Google tarafından değiştirilebilir.
    && CHROMEDRIVER_INFO_URL="https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" \
    && echo "ChromeDriver bilgi URL'si: $CHROMEDRIVER_INFO_URL" \
    # En son STABLE sürümü veya CHROME_MAJOR_VERSION ile eşleşen bir sürümü bulmaya çalışır.
    # Bu komut, JSON'dan uygun chromedriver URL'sini çeker.
    # Basitlik adına, direkt en son STABLE sürümünü almayı deneyebiliriz, genellikle geriye dönük uyumlulukları olur.
    # VEYA spesifik major version için LATEST_RELEASE dosyasını kullanabiliriz:
    && LATEST_CHROMEDRIVER_URL_PREFIX="https_chromedriver.storage.googleapis.com" \ # Bu eski bir prefix, yeni olan "https://storage.googleapis.com/chrome-for-testing-public/"
    && CHROMEDRIVER_VERSION=$(curl -sS "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}") \
    && echo "Tespit edilen ChromeDriver Sürümü ($CHROME_MAJOR_VERSION için): $CHROMEDRIVER_VERSION" \
    && if [ -z "$CHROMEDRIVER_VERSION" ]; then \
        echo "Uyarı: Belirli Chrome ana sürümü için LATEST_RELEASE bulunamadı. En son kararlı sürüm denenecek."; \
        CHROMEDRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE); \
        echo "En son kararlı ChromeDriver Sürümü: $CHROMEDRIVER_VERSION"; \
    fi \
    && wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d /usr/bin \
    && chmod +x /usr/bin/chromedriver \
    && rm chromedriver_linux64.zip \
    && echo "--- ChromeDriver Kurulum Kontrolü ---" \
    && chromedriver --version \
    && echo "ChromeDriver'ın bulunduğu yol (which chromedriver): $(which chromedriver)" \
    \
    # Kurulum sonrası temizlik
    && apt-get purge -y --auto-remove wget gnupg curl unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/google-chrome.list

# Uygulama için çalışma dizini oluştur ve varsayılan yap
WORKDIR /app

# Bağımlılık dosyasını kopyala
COPY requirements.txt .

# Python bağımlılıklarını yükle
RUN pip install --no-cache-dir -r requirements.txt \
    && echo "Python bağımlılıkları başarıyla yüklendi."

# Proje dosyalarının geri kalanını kopyala
COPY . .

# Uygulamanın çalıştırılacağı port (eğer bir web servisi ise, bot için gerekmeyebilir)
# ENV PORT 8080
# EXPOSE 8080

# Uygulamayı başlatma komutu
CMD ["python", "main.py"]
