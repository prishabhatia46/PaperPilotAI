from backend.tools.arxiv_tool import search_arxiv_papers, search_semantic_scholar, search_openalex
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

async def fetch_papers(state: dict) -> dict:
    query = state["query"]
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
    
    combined = []
    seen_titles = set()
    
    openalex_papers = search_openalex(query, max_results=6)
    semantic_papers = search_semantic_scholar(query, max_results=5)
    arxiv_papers = search_arxiv_papers(query, max_results=3)
    
    for p in openalex_papers + semantic_papers + arxiv_papers:
        title_key = p["title"].lower()[:50]
        if title_key not in seen_titles and p.get("abstract"):
            seen_titles.add(title_key)
            combined.append(p)
    
    if not combined:
        return {"papers": []}
    
    # Strict relevance filter
    titles = "\n".join([f"{i}. {p['title']}" for i, p in enumerate(combined)])
    scores_resp = llm.invoke(f"""Query: "{query}"

Rate each paper's relevance to the query from 1-10.
Papers:
{titles}

Reply ONLY in this format, one per line:
0: 7
1: 3
2: 9
(index: score)""").content.strip()
    
    scored = []
    for line in scores_resp.split("\n"):
        try:
            idx, score = line.split(":")
            idx, score = int(idx.strip()), int(score.strip())
            if score >= 5 and idx < len(combined):
                combined[idx]["relevance_score"] = score
                scored.append(combined[idx])
        except:
            continue
    
    if len(scored) >= 2:
        combined = sorted(scored, key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    print(f"Papers after scoring: {len(combined)}")
    return {"papers": combined[:8]}