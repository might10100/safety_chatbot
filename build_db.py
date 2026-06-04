"""
build_db.py
data/ 의 모든 PDF → 텍스트 추출(PyMuPDF) → 청킹 → FAISS 벡터 DB 구축
실행: python3 build_db.py
"""
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DATA_DIR    = "data"
DB_DIR      = "db"
EMBED_MODEL = "jhgan/ko-sroberta-multitask"


def extract_pdf(path):
    """PyMuPDF(fitz)로 페이지별 텍스트 추출. 실패 시 PyPDF2 폴백."""
    pages = []
    try:
        import fitz
        doc = fitz.open(path)
        for i, page in enumerate(doc):
            t = page.get_text("text")
            if t and t.strip():
                pages.append((i + 1, t))
        doc.close()
        if pages:
            return pages
    except Exception as e:
        print(f"      (PyMuPDF 실패: {e})")
    try:
        import PyPDF2
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages):
                t = page.extract_text()
                if t and t.strip():
                    pages.append((i + 1, t))
    except Exception as e:
        print(f"      (PyPDF2 실패: {e})")
    return pages


print("=" * 50)
print("① PDF 텍스트 추출 중 (PyMuPDF)...")
texts, metadatas = [], []
pdf_files = sorted(f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf"))
print(f"   총 {len(pdf_files)}개 PDF 발견")

empty = []
for filename in pdf_files:
    path = os.path.join(DATA_DIR, filename)
    pages = extract_pdf(path)
    if not pages:
        empty.append(filename)
        print(f"   ❌ {filename} — 추출 0페이지")
        continue
    for pno, text in pages:
        texts.append(text)
        metadatas.append({"source": filename, "page": pno})
    print(f"   ✅ {filename} ({len(pages)}p)")

print(f"\n   총 {len(texts)}페이지 추출 완료")
if empty:
    print(f"   ⚠️ 추출 실패 {len(empty)}개: {empty}")

print("\n② 텍스트 청킹 중...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=100,
    separators=["\n제", "\n\n", "\n", ". ", " ", ""],
)
docs = splitter.create_documents(texts, metadatas=metadatas)
print(f"   총 {len(docs)}개 청크 생성 완료")

print("\n③ 임베딩 모델 로딩 중...")
embeddings = HuggingFaceEmbeddings(
    model_name=EMBED_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
print("   임베딩 모델 로드 완료")

print("\n④ FAISS 벡터 DB 구축 중...")
os.makedirs(DB_DIR, exist_ok=True)
db = FAISS.from_documents(docs, embeddings)
db.save_local(DB_DIR)
print(f"   ✅ DB 저장 완료 → {DB_DIR}/")
print(f"\n✅ DB 구축 완료! 총 {len(docs)}개 청크 저장.")
