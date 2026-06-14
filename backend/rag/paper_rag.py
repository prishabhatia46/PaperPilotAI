from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import asyncio
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

_embeddings = None
def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
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
    
    def _call():
        eli5 = llm.invoke(f"Explain this paper in 3 simple sentences for a beginner. No jargon. No labels or numbering. Just plain sentences.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content
        technical = llm.invoke(f"Summarize key technical contributions in 3 sentences. No labels or numbering. Just plain sentences.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content
        limitations = llm.invoke(f"List 2 limitations of this paper in plain sentences. No labels or numbering.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content
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