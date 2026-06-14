from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import requests
import tempfile
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

from backend.agents.supervisor import run_scholar_pipeline
from backend.tools.arxiv_tool import search_arxiv_papers, fetch_paper_from_url
from backend.ml.classifier import classify_difficulty
from langchain_groq import ChatGroq

app = FastAPI(title="ScholarPath AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))

class SearchRequest(BaseModel):
    query: str
    offset: int = 0

class ChatRequest(BaseModel):
    question: str
    paper_title: str
    paper_abstract: str

class CompareRequest(BaseModel):
    paper1_title: str
    paper1_abstract: str
    paper2_title: str
    paper2_abstract: str

class QuizRequest(BaseModel):
    paper_title: str
    paper_abstract: str

class RelatedRequest(BaseModel):
    paper_title: str
    paper_abstract: str

class ExplainRequest(BaseModel):
    paper_title: str
    paper_abstract: str
    level: str

class PaperURLRequest(BaseModel):
    url: str

@app.get("/")
def root():
    return {"status": "ScholarPath AI running"}

@app.post("/search")
async def search_papers(request: SearchRequest):
    if request.offset == 0:
        # Decide which database to use
        decision = llm.invoke(f"""Is this query about CS, AI, ML, NLP, robotics, or any hard science?
Query: "{request.query}"
Reply with only: ARXIV or SEMANTIC""").content.strip().upper()
        
        if "ARXIV" in decision:
            result = await run_scholar_pipeline(request.query)
        else:
            from backend.tools.arxiv_tool import search_semantic_scholar
            from backend.rag.paper_rag import ingest_papers, generate_explanations_parallel
            from backend.ml.classifier import classify_difficulty
            
            papers = search_semantic_scholar(request.query, max_results=5)
            if not papers:
                result = await run_scholar_pipeline(request.query)
            else:
                for paper in papers:
                    paper["difficulty"] = classify_difficulty(paper["abstract"], paper["citation_count"], paper["published"])
                papers = await generate_explanations_parallel(papers)
                ingest_papers(papers)
                
                path = llm.invoke(f"""Create a 5-step learning path for: {request.query}
Papers: {[p['title'] for p in papers]}
Format: Step 1: [paper] - [reason]""").content
                
                gaps = llm.invoke(f"""Identify 3 research gaps for: {request.query}
Based on: {[p['abstract'][:200] for p in papers[:3]]}
Format: Gap: [specific area]""").content
                gap_list = [l.replace("Gap:","").strip() for l in gaps.split("\n") if "Gap:" in l]
                
                result = {
                    "explained_papers": papers,
                    "learning_path": {"steps": path},
                    "research_gaps": gap_list
                }
        
        return {
            "papers": result["explained_papers"],
            "learning_path": result["learning_path"],
            "research_gaps": result["research_gaps"]
        }
    else:
        from backend.tools.arxiv_tool import search_semantic_scholar
        papers = search_arxiv_papers(request.query, max_results=5, offset=request.offset)
        if not papers:
            papers = search_semantic_scholar(request.query, max_results=5)
        for paper in papers:
            paper["difficulty"] = classify_difficulty(paper["abstract"], paper["citation_count"], paper["published"])
            paper["eli5"] = ""
            paper["technical_summary"] = ""
            paper["limitations"] = ""
        return {"papers": papers, "learning_path": None, "research_gaps": None}

@app.post("/chat")
async def chat_about_paper(request: ChatRequest):
    response = llm.invoke(f"""You are a research paper expert. Answer clearly and concisely.
Paper Title: {request.paper_title}
Abstract: {request.paper_abstract}
Question: {request.question}
Answer in 2-3 sentences.""").content
    return {"answer": response}

@app.post("/compare")
async def compare_papers(request: CompareRequest):
    response = llm.invoke(f"""Compare these two research papers.
Paper 1: {request.paper1_title}
Abstract 1: {request.paper1_abstract[:300]}
Paper 2: {request.paper2_title}
Abstract 2: {request.paper2_abstract[:300]}
Format:
METHODOLOGY: [compare approaches]
CONTRIBUTIONS: [compare what each adds]
LIMITATIONS: [compare weaknesses]
VERDICT: [which is better for beginners, which for experts, and why]""").content
    return {"comparison": response}

@app.post("/quiz")
async def generate_quiz(request: QuizRequest):
    response = llm.invoke(f"""Generate 3 multiple choice questions to test understanding of this paper.
Title: {request.paper_title}
Abstract: {request.paper_abstract[:400]}
Format exactly:
Q: [question]
A) [option]
B) [option]
C) [option]
D) [option]
ANSWER: [correct letter]
EXPLANATION: [why correct]
---""").content
    return {"quiz": response}

@app.post("/related")
async def related_papers(request: RelatedRequest):
    papers = search_arxiv_papers(request.paper_title, max_results=4)
    related = []
    for p in papers:
        if p["title"] != request.paper_title:
            p["difficulty"] = classify_difficulty(p["abstract"], p["citation_count"], p["published"])
            related.append({"title": p["title"], "pdf_url": p["pdf_url"], "difficulty": p["difficulty"], "published": p["published"]})
    return {"related": related[:3]}

@app.post("/explain")
async def explain_for_level(request: ExplainRequest):
    prompts = {
        "child": "Explain this paper to a 10 year old using simple words and a fun analogy.",
        "student": "Explain this paper to an undergraduate student. Use some technical terms but keep it clear.",
        "expert": "Explain this paper to a PhD researcher. Be technically precise and highlight novel contributions."
    }
    prompt = prompts.get(request.level, prompts["student"])
    response = llm.invoke(f"""{prompt}
Title: {request.paper_title}
Abstract: {request.paper_abstract[:400]}
Reply with only the explanation.""").content
    return {"explanation": response}

@app.post("/analyze-url")
async def analyze_paper_url(request: PaperURLRequest):
    url = request.url.strip()
    
    # Try ArXiv first
    paper = None
    if "arxiv.org" in url:
        paper = fetch_paper_from_url(url)
    
    # If not ArXiv or failed, try PDF extraction
    if not paper:
        try:
            import pdfplumber
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return {"error": f"Could not download PDF (status {resp.status_code}). Try an ArXiv URL."}
            
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(resp.content)
                tmp_path = f.name
            
            text = ""
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages[:5]:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
            os.unlink(tmp_path)
            
            if not text.strip():
                return {"error": "Could not extract text from PDF."}
            
            # Build paper dict from extracted text
            title_resp = llm.invoke(f"Extract only the title of this research paper. Reply with just the title.\n\n{text[:1000]}").content
            abstract_resp = llm.invoke(f"Extract or summarize the abstract of this research paper in 3-4 sentences.\n\n{text[:2000]}").content
            
            paper = {
                "id": url,
                "title": title_resp.strip(),
                "authors": ["Unknown"],
                "abstract": abstract_resp.strip(),
                "pdf_url": url,
                "published": "2024",
                "categories": [],
                "citation_count": 0
            }
        except Exception as e:
            return {"error": f"Could not analyze URL: {str(e)}"}
    
    if not paper:
        return {"error": "Could not fetch paper. Try a direct ArXiv or PDF URL."}
    
    paper["difficulty"] = classify_difficulty(paper["abstract"], paper["citation_count"], paper["published"])
    
    # Generate explanations directly without ChromaDB
    eli5 = llm.invoke(f"Explain in 3 simple sentences for a beginner.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content
    technical = llm.invoke(f"Summarize key technical contributions in 3 sentences.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content
    limitations = llm.invoke(f"What are 2 limitations of this paper?\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content
    
    paper["eli5"] = eli5.strip()
    paper["technical_summary"] = technical.strip()
    paper["limitations"] = limitations.strip()
    
    # Related papers
    related_raw = search_arxiv_papers(paper["title"].split()[:4].__str__().replace("[","").replace("]","").replace("'",""), max_results=4)
    related = []
    for p in related_raw:
        if p["title"] != paper["title"]:
            p["difficulty"] = classify_difficulty(p["abstract"], p["citation_count"], p["published"])
            related.append(p)
    
    path_resp = llm.invoke(f"""Create a 5-step learning path to understand this paper:
Title: {paper['title']}
Abstract: {paper['abstract'][:400]}
Format: Step 1: [what to study] - [why]""").content
    
    return {
        "paper": paper,
        "related": related[:3],
        "learning_path": path_resp,
        "research_gaps": []
    }