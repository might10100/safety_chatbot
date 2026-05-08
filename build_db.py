"""
build_db.py
PDF 81개 → 텍스트 추출 → 청킹 → FAISS 벡터 DB 구축
실행: python3 build_db.py
"""
import os
import pickle
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DATA_DIR   = "data"   # PDF 폴더
DB_DIR     = "db"     # 저장 경로
EMBED_MODEL = "jhgan/ko-sroberta-multitask"

# ① PDF 텍스트 추출
print("=" * 50)
print("① PDF 텍스트 추출 중...")
texts, metadatas = [], []

pdf_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".pdf")]
print(f"   총 {len(pdf_files)}개 PDF 발견")

for filename in pdf_files:
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    texts.append(text)
                    metadatas.append({"source": filename, "page": page_num + 1})
        print(f"   ✅ {filename}")
    except Exception as e:
        print(f"   ❌ {filename} 오류: {e}")

print(f"\n   총 {len(texts)}페이지 추출 완료")

# ② 청킹 (500자, overlap 50)
print("\n② 텍스트 청킹 중...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " ", ""]
)
docs = splitter.create_documents(texts, metadatas=metadatas)
print(f"   총 {len(docs)}개 청크 생성 완료")

# ③ 임베딩 모델 로드
print("\n③ 임베딩 모델 로딩 중 (처음엔 다운로드로 시간 걸림)...")
embeddings = HuggingFaceEmbeddings(
    model_name=EMBED_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)
print("   임베딩 모델 로드 완료")

# ④ FAISS 저장
print("\n④ FAISS 벡터 DB 구축 중...")
os.makedirs(DB_DIR, exist_ok=True)
db = FAISS.from_documents(docs, embeddings)
db.save_local(DB_DIR)
print(f"   ✅ DB 저장 완료 → {DB_DIR}/")
print(f"   생성 파일: index.faiss, index.pkl")
print("\n✅ DB 구축 완료!")
print(f"   총 {len(docs)}개 법령 청크가 벡터 DB에 저장되었습니다.")
