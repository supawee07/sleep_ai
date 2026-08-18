from fastapi.middleware.cors import CORSMiddleware

import re
import os
import requests
import uuid
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


# ===== ENV =====
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# ===== LLM =====
url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8000", # OpenRouter บังคับใส่ (ใส่เป็น localhost ได้)
    "X-Title": "Lifespan Plus App"           # ชื่อแอปของคุณ
}

# ===== RAG =====
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-base"
)

vectorstore = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# ===== DB =====
engine = create_engine(
    "mysql+pymysql://root:@localhost/sleep_ai?charset=utf8mb4"
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class GoogleLoginRequest(BaseModel):
    token: str


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255))
    token = Column(String(255))
    name = Column(String(255))
    picture = Column(String(255))


class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    message = Column(Text)
    answer = Column(Text)


Base.metadata.create_all(bind=engine)

# ===== APP =====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    query: str
    email: str


# ===== ROOT =====
@app.get("/")
def root():
    return {
        "message": "Lifespan+ Sleep AI API",
        "endpoints": {
            "docs": "/docs",
            "login": "POST /login",
            "google_login": "POST /google-login",
            "chat": "POST /chat",
            "history": "GET /history",
            "logout": "POST /logout"
        }
    }


# ===== LOGIN =====
@app.post("/google-login")
def google_login(data: GoogleLoginRequest):
    db = SessionLocal()

    try:
        idinfo = id_token.verify_oauth2_token(
            data.token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = idinfo["email"]

        user = db.query(User).filter_by(email=email).first()

        if not user:
            user = User(
                email=email,
                token=str(uuid.uuid4())
            )
            db.add(user)
        else:
            user.token = str(uuid.uuid4())

        db.commit()

        return {
            "token": user.token,
            "email": user.email
        }

    except Exception as e:
        raise HTTPException(401, f"Invalid Google token: {str(e)}")

    finally:
        db.close()

@app.post("/login")
def login(data: LoginRequest):
    db = SessionLocal()

    try:
        token = str(uuid.uuid4())

        user = User(email=data.email, token=token)
        db.add(user)
        db.commit()

        return {"token": token, "email": data.email}

    finally:
        db.close()


# ===== HISTORY =====
@app.get("/history")
def history(email: str):
    db = SessionLocal()

    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(404, "user not found")

    chats = db.query(Chat).filter_by(user_id=user.id).all()

    return [
        {"message": c.message, "answer": c.answer}
        for c in chats
    ]


# ===== CHAT =====
@app.post("/chat")
def chat(data: ChatRequest):
    db = SessionLocal()

    user = db.query(User).filter_by(email=data.email).first()
    if not user:
        raise HTTPException(404, "user not found")

    query = data.query

    sleep_keywords = ["นอน", "หลับ", "ง่วง", "sleep", "insomnia", "พักผ่อน"]
    has_sleep = any(word in query for word in sleep_keywords)

    prefix = ""

    if has_sleep and len(query.split()) > 1:
        prefix = "ฉันเป็นAIช่วยตอบเรื่องการนอน ฉันตอบเรื่องการนอนได้นะ\n"
        # query = "ง่วงนอน ทำอย่างไร"

    if not has_sleep:
        answer = "ขอโทษด้วยค่ะ/ครับ ฉันเป็นAI ที่ช่วยตอบคำถามเรื่องการนอนหลับเท่านั้น"

    else:
        docs = retriever.invoke(query)

        context = "\n\n".join([
            doc.page_content[:500]
            for doc in docs
        ])

        if len(context.strip()) < 50:
            answer = "- งีบสั้น ๆ 15-20 นาที\n- ลุกเดินหรือยืดตัว\n- ดื่มน้ำ"

        else:
            prompt = f"""
คุณเป็น AI ด้านการนอนหลับ

กฎ:
- ตอบสั้น กระชับ
- ไม่เกิน 5 ข้อ
- ทุกบรรทัดต้องขึ้นต้นด้วย "- "
- ห้ามใช้ markdown เช่น **, |, ###, ตาราง
- ห้ามอธิบายยาว
- ห้ามมีข้อความนอก bullet
- ตอบเป็นภาษาธรรมดาเท่านั้น

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:
"""

            # เพิ่ม timeout เพื่อไม่ให้รอเก้อถ้าระบบฝั่งนู้นค้าง
            try:
                res = requests.post(url, headers=headers, json={
                    "model": "openai/gpt-oss-120b:free",
                    "messages": [{"role": "user", "content": prompt}]
                }, timeout=30)
                
                # ถ้า API ตอบกลับเป็น Error (เช่น 429) มันจะกระโดดไป except ทันที
                res.raise_for_status() 
                
                # ตัวแปร data_res จะถูกสร้างก็ต่อเมื่อบรรทัดบนผ่านฉลุย
                data_res = res.json()
                
                # 👇 บล็อกนี้ต้องย่อหน้าเข้ามาอยู่ใน try นะครับ
                if "choices" in data_res:
                    answer = data_res["choices"][0]["message"]["content"]
                    
                    if "ขอโทษ" not in answer:
                        lines = [line.strip() for line in answer.split("\n") if line.strip()]
                        clean_lines = []
                        for line in lines:
                            line = re.sub(r"[*#|>`\-]+", "", line)
                            line = line.lstrip("0123456789. ")
                            if not line.startswith("-"):
                                line = "- " + line.strip()
                            clean_lines.append(line)
                        answer = "\n".join(clean_lines[:3])
                else:
                    answer = "ขอโทษครับ ระบบ AI ปลายทางขัดข้องชั่วคราว"
                    
            # 👇 เพิ่มตัวดัก Error 429 (Too Many Requests)
            except requests.exceptions.HTTPError as e:
                print(f"❌ API Error (ติด Limit OpenRouter): {e}")
                answer = "ขอโทษครับ ตอนนี้ระบบ AI (ฟรี) มีผู้ใช้งานหนาแน่น โปรดรอสักครู่แล้วลองถามใหม่นะครับ"
                
            except requests.exceptions.Timeout:
                print("❌ ERROR: OpenRouter Timeout")
                answer = "ขอโทษครับ ระบบใช้เวลานานเกินไป โปรดลองใหม่อีกครั้ง"
                
            except Exception as e:
                print(f"❌ ERROR: {e}")
                answer = "ขอโทษครับ เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์"

        # === โค้ดด้านล่างอยู่ระดับเดียวกับ try ===
        if not answer.strip():
            answer = "- งีบสั้น ๆ 15-20 นาที\n- ลุกเดิน\n- ดื่มน้ำ"
            # เช็คว่ามีคำว่า 'choices' ส่งกลับมาจริงๆ ก่อนค่อยดึงข้อมูล
            if "choices" in data_res:
                answer = data_res["choices"][0]["message"]["content"]
            else:
                # ถ้าไม่มี ให้แสดงใน Terminal ว่าเกิดอะไรขึ้น จะได้แก้ถูกจุด
                print(f"❌ API Error Response: {data_res}")
                answer = "ขออภัยครับ ตอนนี้ไม่สามารถเชื่อมต่อกับระบบ AI ได้ (API ขัดข้อง)"

            # ===== CLEAN BULLET (แก้ตรงนี้นิดเดียว) =====
            if "ขอโทษ" not in answer:
                lines = [line.strip() for line in answer.split("\n") if line.strip()]
                clean_lines = []

                for line in lines:
                    # ลบ markdown/table
                    line = re.sub(r"[*#|>`\-]+", "", line)

                    line = line.lstrip("0123456789. ")

                    if not line.startswith("-"):
                        line = "- " + line.strip()

                    clean_lines.append(line)

                answer = "\n".join(clean_lines[:3])


    answer = prefix + answer

    chat = Chat(
        user_id=user.id,
        message=data.query,
        answer=answer
    )
    db.add(chat)
    db.commit()

    return {"answer": answer}


# ===== LOGOUT =====
@app.post("/logout")
def logout(token: str):
    db = SessionLocal()
    user = db.query(User).filter_by(token=token).first()

    if user:
        db.delete(user)
        db.commit()

    return {"message": "logout success"}