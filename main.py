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
API_KEY = os.getenv("API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# ===== LLM =====
url = "https://minddatatech.com/llm-api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
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
- ไม่เกิน 3 ข้อ
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

            res = requests.post(url, headers=headers, json={
                "model": "gpt-oss:20b",
                "messages": [{"role": "user", "content": prompt}]
            })

            data_res = res.json()
            answer = data_res["choices"][0]["message"]["content"]

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

        if not answer.strip():
            answer = "- งีบสั้น ๆ 15-20 นาที\n- ลุกเดิน\n- ดื่มน้ำ"

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