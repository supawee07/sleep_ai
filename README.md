# 🛌 Sleep AI Chatbot

### ระบบ Chatbot แนะนำการนอนด้วย RAG (Retrieval-Augmented Generation)

---

## 📌 ภาพรวมโปรเจค

Sleep AI Chatbot เป็นระบบ AI ที่ช่วยตอบคำถามเกี่ยวกับ “การนอนหลับ” โดยใช้เทคนิค **RAG (Retrieval-Augmented Generation)** ซึ่งทำให้ AI ไม่ได้ตอบมั่ว แต่ตอบจากข้อมูลจริง (dataset)

ระบบนี้พัฒนาด้วย:

* ⚙️ FastAPI (Backend)
* 🧠 RAG + Embedding (LangChain + Chroma)
* 💾 MySQL (เก็บ user + chat history)
* 🌐 HTML + Tailwind (Frontend)

---

## 🧠 หลักการทำงานของระบบ

```
Dataset (.md)
→ Chunk (แบ่งข้อความ)
→ Embedding (แปลงเป็น vector)
→ เก็บใน Chroma DB

User ถาม
→ ค้นหา chunk ที่เกี่ยวข้อง
→ ส่ง context + question เข้า LLM
→ ตอบกลับแบบ bullet
```

---

## 🏗 โครงสร้างโปรเจค

```
sleep_ai/
│
├── ingest.py              # สร้าง vector database (RAG)
├── main.py                # Backend (FastAPI)
├── requirements.txt       # dependencies
├── data/                  # dataset (.md)
├── login.html             # หน้า login
├── chat.html              # หน้า chat
├── .gitignore
```

---

## ⚙️ การติดตั้ง (Installation)

### 1. Clone โปรเจค

```bash
git clone https://github.com/supawee07/sleep_ai.git
cd sleep_ai
```

---

### 2. ติดตั้ง Python Libraries

```bash
pip install -r requirements.txt
```

---

### 3. สร้างไฟล์ `.env`

สร้างไฟล์ `.env` แล้วใส่:

```env
API_KEY=your_api_key
GOOGLE_CLIENT_ID=your_google_client_id
```

---

### 4. สร้าง Vector Database (สำคัญมาก)

```bash
python ingest.py
```

จะได้:

```
chroma_db/
```

---

### 5. ตั้งค่า MySQL

เปิด MySQL (เช่น XAMPP) แล้วสร้าง database:

```sql
CREATE DATABASE sleep_ai;
```

---

### 6. รัน Backend

```bash
uvicorn main:app --reload
```

เปิดที่:

```
http://127.0.0.1:8000
```

---

### 7. เปิด Frontend

เปิดไฟล์:

```
login.html
หรือ
chat.html
```

---

## 🚀 วิธีใช้งาน (Usage)

1. เปิดระบบ
2. Login (Google / email)
3. พิมพ์คำถามเกี่ยวกับการนอน เช่น:

```
ง่วงมากทำยังไงดี
นอนไม่หลับเพราะเครียด
ตื่นกลางดึกบ่อยเกิดจากอะไร
```

---

## 🎯 ฟีเจอร์หลัก

* ✅ ตอบคำถามเรื่องการนอนโดยเฉพาะ
* ✅ ใช้ RAG → ตอบจาก dataset จริง
* ✅ บังคับคำตอบเป็น bullet
* ✅ มีระบบ login + chat history
* ✅ รองรับภาษาไทย

---

## ⚠️ ข้อจำกัดของระบบ

* ❌ ตอบได้เฉพาะเรื่อง “การนอน”
* ❌ ถ้า dataset ไม่ครอบคลุม → อาจตอบทั่วไป
* ❌ ต้อง run `ingest.py` ก่อนใช้งาน

---

## 🧪 ตัวอย่างคำถาม

| คำถาม        | ผลลัพธ์            |
| ------------ | ------------------ |
| ง่วงตอนทำงาน | แนะนำงีบ / ลุกเดิน |
| นอนไม่หลับ   | แนะนำ relaxation   |
| นอนดึก       | อธิบายผลกระทบ      |

---

## 🧩 เทคโนโลยีที่ใช้

* FastAPI
* LangChain
* HuggingFace Embeddings
* ChromaDB
* MySQL
* HTML + Tailwind CSS

---

## 👨‍💻 ผู้พัฒนา

* Supawee Phusawang

---

## 📚 หมายเหตุ

โปรเจคนี้จัดทำเพื่อการศึกษาเกี่ยวกับ:

* RAG (Retrieval-Augmented Generation)
* AI Chatbot
* Backend API
* Database Integration

---

## 🔥 วิธีรันแบบสั้น

```bash
pip install -r requirements.txt
python ingest.py
uvicorn main:app --reload
```

---

## 📌 สรุป

โปรเจคนี้แสดงให้เห็นการนำ AI + RAG มาใช้แก้ปัญหาจริง
โดยทำให้ Chatbot “ตอบจากข้อมูลจริง” ไม่ใช่เดาสุ่ม

---
