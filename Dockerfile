# 1. Gunakan image Python ringan
FROM python:3.10-slim

# 2. Tentukan variabel lingkungan untuk Flask
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Tentukan direktori kerja di dalam kontainer
WORKDIR /app

# 4. Salin dan install requirements terlebih dahulu (agar caching efisien)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Salin semua file proyek
COPY . .

# 6. Expose port Flask (opsional, tapi baik untuk dokumentasi)
EXPOSE 5000

# 7. Jalankan aplikasi
CMD ["python", "app.py"]
