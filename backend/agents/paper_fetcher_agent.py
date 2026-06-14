from backend.tools.arxiv_tool import search_arxiv_papers, search_semantic_scholar
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

async def fetch_papers(state: dict) -> dict:
    query = state["query"]
    
    arxiv_papers = search_arxiv_papers(query, max_results=5)
    semantic_papers = search_semantic_scholar(query, max_results=5)
    
    seen_titles = set()
    combined = []
    
    for p in semantic_papers:
        title_key = p["title"].lower()[:50]
        if title_key not in seen_titles and p.get("abstract"):
            seen_titles.add(title_key)
            combined.append(p)
    
    for p in arxiv_papers:
        title_key = p["title"].lower()[:50]
        if title_key not in seen_titles and p.get("abstract"):
            seen_titles.add(title_key)
            combined.append(p)
    
    # Groq se irrelevant papers filter karo
    if combined:
        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
        titles = "\n".join([f"{i}. {p['title']}" for i, p in enumerate(combined)])
        response = llm.invoke(f"""Given the search query: "{query}"
        
These papers were fetched:
{titles}

Which paper numbers are IRRELEVANT to the query? Reply with ONLY comma-separated numbers of irrelevant papers, or "none" if all are relevant.
Example: "2,4,7" or "none"
Be strict — only remove clearly unrelated papers.""").content.strip()
        
        if response.lower() != "none":
            try:
                irrelevant_indices = [int(x.strip()) for x in response.split(",") if x.strip().isdigit()]
                combined = [p for i, p in enumerate(combined) if i not in irrelevant_indices]
                if len(combined) < 4:
                     combined = [p for p in (semantic_papers + arxiv_papers) if p.get("abstract")][:8]
            except:
                pass
    
    return {"papers": combined[:8]}