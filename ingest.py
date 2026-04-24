import os
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DATA_PATH = "data"
DB_PATH = "chroma_db"

# =========================
# 🔥 1. SPLIT MARKDOWN (สำคัญมาก)
# =========================
def split_md_by_section(text, source):
    # แยกตามหัวข้อ ##
    sections = re.split(r'\n## ', text)

    docs = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue

        docs.append(
    Document(
        page_content=sec,
        metadata={
            "source": source,
            "section": sec[:50]
        }
    )
)

    return docs


# =========================
# 📂 2. LOAD FILE + SPLIT
# =========================
documents = []

for root, _, files in os.walk(DATA_PATH):
    for file in files:
        if file.endswith(".md"):
            path = os.path.join(root, file)

            with open(path, "r", encoding="utf-8") as f:
                text = f.read()  # ❌ ห้าม replace \n

            # 🔥 split ตามหัวข้อ
            docs = split_md_by_section(text, path)
            documents.extend(docs)

print(f"📄 Loaded {len(documents)} sections")


# =========================
# ✂️ 3. SPLIT ย่อยอีกครั้ง (กันยาวเกิน)
# =========================
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", " ", ""]
)

texts = splitter.split_documents(documents)

print(f"✂️ Total chunks: {len(texts)}")


# =========================
# 🧠 4. EMBEDDING
# =========================
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-base"
)


# =========================
# 💾 5. BUILD VECTOR DB
# =========================
vectorstore = Chroma.from_documents(
    documents=texts,
    embedding=embeddings,
    persist_directory=DB_PATH
)

vectorstore.persist()

print("✅ Vector DB ready (optimized for RAG)")