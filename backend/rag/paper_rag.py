from langchain_chroma import Chroma
from fastembed import TextEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import asyncio
import os
class _FastEmbedWrapper:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts):
        return [e.tolist() for e in self.model.embed(texts)]

    def embed_query(self, text):
        return list(self.model.embed([text]))[0].tolist()

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

_embeddings = None
def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = _FastEmbedWrapper(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings

def get_vectorstore():
    return Chroma(
        collection_name="research_papers",
        embedding_function=get_embeddings(),
        persist_directory="./chroma_db"
    )

def ingest_papers(papers: list):
    if not papers:
        return None
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    documents = []
    for paper in papers:
        if not paper.get("abstract"):
            continue
        chunks = splitter.split_text(paper["abstract"])
        for chunk in chunks:
            documents.append(Document(
                page_content=chunk,
                metadata={"paper_id": paper["id"], "title": paper["title"], "pdf_url": paper["pdf_url"]}
            ))
    if not documents:
        return None
    vectorstore = get_vectorstore()
    vectorstore.add_documents(documents)
    return vectorstore

async def ensure_abstract(paper: dict, llm) -> dict:
    if not paper.get("abstract") or len(paper["abstract"]) < 50:
        loop = asyncio.get_event_loop()
        def _infer():
            return llm.invoke(f"""Based on this research paper title, write a 3-4 sentence abstract describing what this paper is likely about.
Title: {paper['title']}
Write only the abstract, nothing else.""").content
        paper["abstract"] = await loop.run_in_executor(None, _infer)
    return paper

async def explain_single(paper: dict, llm) -> dict:
    loop = asyncio.get_event_loop()

    context = retrieve_paper_chunks(paper.get("title", ""))
    if not context:
        context = paper['abstract'][:400]

    def _call():
        eli5 = llm.invoke(f"Explain this paper in 3 simple sentences for a beginner. No jargon. No labels or numbering. Just plain sentences.\nTitle: {paper['title']}\nContext: {context}").content
        technical = llm.invoke(f"Summarize key technical contributions in 3 sentences. No labels or numbering. Just plain sentences.\nTitle: {paper['title']}\nContext: {context}").content
        limitations = llm.invoke(f"List 2 limitations of this paper in plain sentences. No labels or numbering.\nTitle: {paper['title']}\nContext: {context}").content
        return eli5.strip(), technical.strip(), limitations.strip()

    eli5, technical, limitations = await loop.run_in_executor(None, _call)
    return {
        "eli5": eli5,
        "technical_summary": technical,
        "limitations": limitations,
        "keywords": ""
    }

async def generate_explanations_parallel(papers: list) -> list:
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
    
    papers = list(await asyncio.gather(*[ensure_abstract(paper, llm) for paper in papers]))
    
    tasks = [explain_single(paper, llm) for paper in papers]
    results = await asyncio.gather(*tasks)
    for paper, result in zip(papers, results):
        paper.update(result)
    return papers
def retrieve_papers_from_chromadb(query: str, threshold: int = 3) -> list:
    """
    Query se ChromaDB mein search karo.
    Agar enough papers mile toh return karo, warna empty list.
    """
    try:
        vectorstore = get_vectorstore()
        docs = vectorstore.similarity_search(query, k=10)
        
        if len(docs) < threshold:
            return []  # Enough papers nahi mile → API use karo
        
        # Unique papers nikalo metadata se
        seen = set()
        papers = []
        for doc in docs:
            pid = doc.metadata.get("paper_id")
            if pid and pid not in seen:
                seen.add(pid)
                papers.append({
                    "id": pid,
                    "title": doc.metadata.get("title", ""),
                    "pdf_url": doc.metadata.get("pdf_url", ""),
                    "abstract": doc.page_content,
                    "citation_count": 0,
                    "published": "",
                    "source": "chromadb"
                })
        return papers
    except:
        return []
def retrieve_chat_context(paper_title: str, question: str, k: int = 3) -> str:
    """
    /chat ke liye: question embed karke ChromaDB se
    isi paper (title se filter) ke top-k relevant chunks nikalo.
    Kuch na mile toh empty string return karo (caller abstract fallback kare).
    """
    try:
        vectorstore = get_vectorstore()
        docs = vectorstore.similarity_search(
            question,
            k=k,
            filter={"title": paper_title}
        )
        if not docs:
            return ""
        return "\n\n".join(doc.page_content for doc in docs)
    except:
        return ""
def retrieve_paper_chunks(paper_title: str, k: int = 3) -> str:
    """
    Explainer Agent ke liye: raw abstract bhejne ki jagah,
    ChromaDB se is paper (title se filter) ke top-k stored chunks nikalo.
    Kuch na mile toh empty string return karo (caller abstract fallback kare).
    """
    try:
        vectorstore = get_vectorstore()
        result = vectorstore.get(where={"title": paper_title}, limit=k)
        docs = result.get("documents", [])
        if not docs:
            return ""
        return "\n\n".join(docs[:k])
    except:
        return ""