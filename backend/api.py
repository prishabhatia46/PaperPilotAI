from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

from backend.agents.supervisor import run_scholar_pipeline
from backend.tools.arxiv_tool import search_arxiv_papers, fetch_paper_from_url, search_semantic_scholar
from backend.ml.classifier import classify_difficulty
from langchain_groq import ChatGroq

app = FastAPI(title="PaperPilot AI API")

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
    return {"status": "PaperPilot AI running"}

@app.post("/search")
async def search_papers(request: SearchRequest):
    if request.offset == 0:
        decision = llm.invoke(f"""Is this query about CS, AI, ML, NLP, robotics, or any hard science?
Query: "{request.query}"
Reply with only: ARXIV or SEMANTIC""").content.strip().upper()

        if "ARXIV" in decision:
            result = await run_scholar_pipeline(request.query)
        else:
            from backend.rag.paper_rag import ingest_papers, generate_explanations_parallel
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
                gap_list = [l.replace("Gap:", "").strip() for l in gaps.split("\n") if "Gap:" in l]
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
    related = []
    
    # LLM se smart query banao
    smart_query = llm.invoke(f"""Given this paper title, generate the best search query to find similar academic papers.
Title: "{request.paper_title}"
Abstract hint: "{request.paper_abstract[:200] if request.paper_abstract else ''}"

Rules:
- Extract the CORE topic/domain
- Use academic terms
- 3-5 words only
- Reply with ONLY the query

Examples:
"A look at mobile devices for English learning" -> "mobile learning language acquisition technology"
"Deep Residual Learning for Image Recognition" -> "deep residual networks image classification"
"COVID detection using chest X-ray" -> "COVID-19 chest X-ray deep learning detection"
""").content.strip().replace('"', '')

    print(f"Related query: {smart_query}")
    
    # Semantic Scholar try karo
    try:
        papers = search_semantic_scholar(smart_query, max_results=6)
        for p in papers:
            if p.get("title") != request.paper_title and p.get("abstract"):
                p["difficulty"] = classify_difficulty(p["abstract"], p["citation_count"], p["published"])
                related.append({
                    "title": p["title"],
                    "pdf_url": p["pdf_url"],
                    "difficulty": p["difficulty"],
                    "published": p["published"],
                    "abstract": p["abstract"]
                })
    except:
        pass
    
    # ArXiv fallback
    if not related:
        try:
            papers = search_arxiv_papers(smart_query, max_results=5)
            for p in papers:
                if p.get("title") != request.paper_title and p.get("abstract"):
                    p["difficulty"] = classify_difficulty(p["abstract"], p["citation_count"], p["published"])
                    related.append({
                        "title": p["title"],
                        "pdf_url": p["pdf_url"],
                        "difficulty": p["difficulty"],
                        "published": p["published"],
                        "abstract": p["abstract"]
                    })
        except Exception as e:
            print(f"ArXiv fallback error: {e}")
    
    # Relevance filter
    if related:
        titles_list = "\n".join([f"{i}. {p['title']}" for i, p in enumerate(related)])
        filter_resp = llm.invoke(f"""Main paper topic: "{request.paper_title}"
        
Fetched papers:
{titles_list}

Remove papers that are CLEARLY unrelated to the main topic.
Reply with comma-separated INDEX numbers to REMOVE, or "none".
Be strict.""").content.strip()
        
        if filter_resp.lower() != "none":
            try:
                bad = [int(x.strip()) for x in filter_resp.split(",") if x.strip().isdigit()]
                related = [p for i, p in enumerate(related) if i not in bad]
            except:
                pass
    # OpenAlex fallback if still empty or only 1 result
    if len(related) < 2:
        try:
            from backend.tools.arxiv_tool import search_openalex
            papers = search_openalex(smart_query, max_results=6)
            for p in papers:
                if p.get("title") != request.paper_title and p.get("abstract"):
                    p["difficulty"] = classify_difficulty(p["abstract"], p["citation_count"], p["published"])
                    related.append({
                        "title": p["title"],
                        "pdf_url": p["pdf_url"],
                        "difficulty": p["difficulty"],
                        "published": p["published"],
                        "abstract": p["abstract"]
                    })
        except Exception as e:
            print(f"OpenAlex error: {e}")

    return {"related": related[:3]}
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

    if not url.startswith('http'):
        return {"error": "Please enter a valid URL starting with http or https."}

    paper = None

    if "arxiv.org" in url:
        paper = fetch_paper_from_url(url)

    if not paper:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=15)

            if resp.status_code != 200:
                return {"error": f"Could not access URL (status {resp.status_code})."}

            content_type = resp.headers.get('content-type', '')

            if 'pdf' in content_type or url.endswith('.pdf'):
                try:
                    import pdfplumber
                    import tempfile
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
                except Exception as e:
                    return {"error": f"Could not read PDF: {str(e)}"}
            else:
                from html.parser import HTMLParser
                class TextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text = []
                        self.skip = False
                    def handle_starttag(self, tag, attrs):
                        if tag in ['script', 'style', 'nav', 'footer']:
                            self.skip = True
                    def handle_endtag(self, tag):
                        if tag in ['script', 'style', 'nav', 'footer']:
                            self.skip = False
                    def handle_data(self, data):
                        if not self.skip and data.strip():
                            self.text.append(data.strip())
                parser = TextExtractor()
                parser.feed(resp.text)
                text = " ".join(parser.text)[:5000]

            if not text.strip():
                return {"error": "Could not extract text from this URL."}

            title_resp = llm.invoke(f"Extract only the title of this research paper. Reply with just the title, nothing else.\n\n{text[:1000]}").content
            abstract_resp = llm.invoke(f"Extract or summarize the abstract of this research paper in 3-4 sentences.\n\n{text[:3000]}").content

            paper = {
                "id": url,
                "title": title_resp.strip(),
                "authors": ["See paper"],
                "abstract": abstract_resp.strip(),
                "pdf_url": url,
                "published": "2024",
                "categories": [],
                "citation_count": 0
            }
        except Exception as e:
            return {"error": f"Could not analyze URL: {str(e)}"}

    if not paper:
        return {"error": "Could not fetch paper. Try a direct PDF or ArXiv link."}

    paper["difficulty"] = classify_difficulty(paper["abstract"], paper["citation_count"], paper["published"])
    paper["eli5"] = llm.invoke(f"Explain in 3 simple sentences for a beginner. No labels.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content.strip()
    paper["technical_summary"] = llm.invoke(f"Summarize key technical contributions in 3 sentences. No labels.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content.strip()
    paper["limitations"] = llm.invoke(f"What are 2 limitations of this paper? No labels.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content.strip()

    related_raw = search_semantic_scholar(paper["title"], max_results=6)
    related = []
    for p in related_raw:
        if p.get("title") != paper["title"] and p.get("abstract"):
            p["difficulty"] = classify_difficulty(p["abstract"], p["citation_count"], p["published"])
            p["eli5"] = llm.invoke(f"Explain in 2 simple sentences for a beginner. No labels.\nTitle: {p['title']}\nAbstract: {p['abstract'][:300]}").content.strip()
            p["technical_summary"] = llm.invoke(f"Summarize key technical contributions in 2 sentences. No labels.\nTitle: {p['title']}\nAbstract: {p['abstract'][:300]}").content.strip()
            p["limitations"] = ""
            related.append(p)

    if related:
        titles_list = "\n".join([f"{i}. {p['title']}" for i, p in enumerate(related)])
        filter_resp = llm.invoke(f"""Main paper: "{paper['title']}"
Related papers:
{titles_list}
Which numbers are CLEARLY irrelevant? Reply comma-separated numbers or "none".""").content.strip()
        if filter_resp.lower() != "none":
            try:
                bad = [int(x.strip()) for x in filter_resp.split(",") if x.strip().isdigit()]
                related = [p for i, p in enumerate(related) if i not in bad]
            except:
                pass

    path_resp = llm.invoke(f"""Create a 5-step learning path to understand this paper:
Title: {paper['title']}
Abstract: {paper['abstract'][:400]}
Format: Step 1: [what to study] - [why]""").content

    return {
        "paper": paper,
        "related": related[:3],
        "learning_path": path_resp,
        "research_gaps": [llm.invoke(f"List 3 specific research gaps or future directions for this paper in plain sentences. No markdown.\nTitle: {paper['title']}\nAbstract: {paper['abstract'][:400]}").content.strip()]
    }