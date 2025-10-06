# --- Stage 1: Base Image ---
# อัปเกรด Python เป็น 3.11-slim เพื่อให้รองรับ Numpy 2.3.3 และ package ใหม่อื่นๆ
FROM python:3.11-slim

# --- Metadata ---
LABEL author="PONGAPAT"
LABEL description="A Docker image for a YOLO object detection API using Flask."

# --- System Dependencies ---
# ติดตั้ง dependencies ที่จำเป็นสำหรับ OpenCV, libraries อื่นๆ และ Supervisor
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# --- Python Environment ---
# ตั้งค่า working directory ภายใน container
WORKDIR /app

# คัดลอกไฟล์ requirements.txt เข้ามาก่อน เพื่อใช้ประโยชน์จาก Docker layer caching
COPY requirements.txt .

# ติดตั้ง Python packages ทั้งหมด
RUN pip install --no-cache-dir -r requirements.txt

# --- Application ---
# คัดลอกโค้ดทั้งหมดและไฟล์ config ของ supervisor เข้ามาใน /app
COPY . .

# บอกให้ Docker รู้ว่า container จะทำงานที่ port 8080
EXPOSE 8080

# --- Command to Run ---
# คำสั่งสำหรับรัน Supervisor ซึ่งจะไปสั่งรัน gunicorn และ line.py ต่อไป
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]