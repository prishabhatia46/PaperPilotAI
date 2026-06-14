from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

async def generate_path(state: dict) -> dict:
    papers = state["explained_papers"]
    query = state["query"]
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
    
    titles = [f"{i+1}. {p['title']} ({p['difficulty']['level']})" 
              for i, p in enumerate(papers)]
    
    path_prompt = f"""
    Topic: {query}
    Papers: {chr(10).join(titles)}
    
    Create a step by step learning path. Which paper to read first and why.
    Format: Step 1: [paper title] - [reason]
    """
    learning_path = llm.invoke(path_prompt).content
    
    abstracts = " ".join([p["abstract"] for p in papers[:5]])
    gaps_prompt = f"""
    Based on these research papers on "{query}":
    {abstracts[:2000]}
    
    Identify 3 specific research gaps not yet explored.
    Format: Gap: [specific area]
    """
    gaps_text = llm.invoke(gaps_prompt).content
    gaps = [line.replace("Gap:", "").strip() 
            for line in gaps_text.split("\n") 
            if "Gap:" in line]
    
    return {
        "learning_path": {"steps": learning_path},
        "research_gaps": gaps
    }