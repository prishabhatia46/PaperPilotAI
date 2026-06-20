import arxiv
import requests
import time
import os
from typing import List, Dict

def search_arxiv_papers(query: str, max_results: int = 5, offset: int = 0) -> List[Dict]:
    client = arxiv.Client(page_size=10, delay_seconds=3, num_retries=2)
    search = arxiv.Search(
        query=query,
        max_results=max_results + offset,
        sort_by=arxiv.SortCriterion.Relevance
    )
    papers = []
    try:
        all_results = list(client.results(search))
        for result in all_results[offset:offset + max_results]:
            citation_count = 0
            papers.append({
                "id": result.entry_id,
                "title": result.title,
                "authors": [a.name for a in result.authors[:3]],
                "abstract": result.summary,
                "pdf_url": result.pdf_url,
                "published": str(result.published.year),
                "categories": result.categories,
                "citation_count": citation_count
            })
            time.sleep(0.2)
    except Exception as e:
        print(f"ArXiv error: {e}")
    return papers

def fetch_paper_from_url(url: str) -> Dict:
    try:
        # Extract arxiv ID from different URL formats
        arxiv_id = ""
        if "arxiv.org/abs/" in url:
            arxiv_id = url.split("arxiv.org/abs/")[-1].split("v")[0].strip()
        elif "arxiv.org/pdf/" in url:
            arxiv_id = url.split("arxiv.org/pdf/")[-1].replace(".pdf", "").split("v")[0].strip()
        
        if not arxiv_id:
            return None
            
        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(client.results(search))
        if results:
            result = results[0]
            return {
                "id": result.entry_id,
                "title": result.title,
                "authors": [a.name for a in result.authors[:3]],
                "abstract": result.summary,
                "pdf_url": result.pdf_url,
                "published": str(result.published.year),
                "categories": result.categories,
                "citation_count": get_citation_count(result.title)
            }
    except Exception as e:
        print(f"URL fetch error: {e}")
    return None

def get_citation_count(title: str) -> int:
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": title, "fields": "citationCount", "limit": 1}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("data"):
            return data["data"][0].get("citationCount", 0)
    except:
        pass
    return 0

def search_semantic_scholar(query: str, max_results: int = 5) -> List[Dict]:
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": 50,
            "fields": "title,authors,abstract,year,citationCount,externalIds,openAccessPdf",
            "sort": "citationCount:desc"
        }
        api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        headers = {"x-api-key": api_key} if api_key else {}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        
        papers = []
        for p in data.get("data", []):
            if not p.get("abstract"):
                continue
            
            pdf_url = ""
            if p.get("openAccessPdf"):
                pdf_url = p["openAccessPdf"].get("url", "")
            elif p.get("externalIds", {}).get("ArXiv"):
                pdf_url = f"https://arxiv.org/pdf/{p['externalIds']['ArXiv']}"
            elif p.get("externalIds", {}).get("DOI"):
                pdf_url = f"https://doi.org/{p['externalIds']['DOI']}"
            elif p.get("externalIds", {}).get("ACM"):
                pdf_url = f"https://dl.acm.org/doi/{p['externalIds']['ACM']}"
            if "localhost" in pdf_url or "127.0.0.1" in pdf_url:
               pdf_url = ""
            
            papers.append({
                "id": p.get("paperId", ""),
                "title": p.get("title", ""),
                "authors": [a["name"] for a in p.get("authors", [])[:3]],
                "abstract": p.get("abstract", ""),
                "pdf_url": pdf_url,
                "published": str(p.get("year", "2024")),
                "categories": [],
                "citation_count": p.get("citationCount", 0)
            })
        
        papers = sorted(papers, key=lambda x: x["citation_count"], reverse=True)
        return papers[:max_results]
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
        return []

def search_openalex(query: str, max_results: int = 8) -> List[Dict]:
    try:
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per-page": max_results,
            "sort": "cited_by_count:desc",
           "filter": "open_access.is_oa:true",
            "select": "title,authorships,abstract_inverted_index,publication_year,cited_by_count,primary_location,id"
        }
        response = requests.get(url, params=params, headers={"User-Agent": "PaperPilotAI/1.0"}, timeout=15)
        data = response.json()
        
        papers = []
        for p in data.get("results", []):
            abstract = ""
            inv = p.get("abstract_inverted_index", {})
            if inv:
                words = {pos: word for word, positions in inv.items() for pos in positions}
                abstract = " ".join(words[i] for i in sorted(words.keys()))
            
            if not abstract:
                continue
            
            pdf_url = ""
            loc = p.get("primary_location", {})
            if loc and loc.get("pdf_url"):
                pdf_url = loc["pdf_url"]
            elif loc and loc.get("landing_page_url"):
                pdf_url = loc["landing_page_url"]
            
            authors = [a["author"]["display_name"] for a in p.get("authorships", [])[:3] if a.get("author")]
            
            papers.append({
                "id": p.get("id", ""),
                "title": p.get("title", ""),
                "authors": authors,
                "abstract": abstract,
                "pdf_url": pdf_url,
                "published": str(p.get("publication_year", "2024")),
                "categories": [],
                "citation_count": p.get("cited_by_count", 0)
            })
        
        return papers
    except Exception as e:
        print(f"OpenAlex error: {e}")
        return []
def get_bulk_citations(papers: list) -> list:
    
    try:
        titles = [p["title"] for p in papers]
        url = "https://api.semanticscholar.org/graph/v1/paper/batch"
        
        # Pehle paper IDs dhundho
        results = []
        for title in titles:
            try:
                r = requests.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={"query": title, "fields": "citationCount", "limit": 1},
                    timeout=3
                )
                data = r.json()
                if data.get("data"):
                    results.append(data["data"][0].get("citationCount", 0))
                else:
                    results.append(0)
            except:
                results.append(0)
        
        for i, paper in enumerate(papers):
            if i < len(results):
                paper["citation_count"] = results[i]
    except:
        pass
    return papers