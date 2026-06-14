from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from backend.agents.paper_fetcher_agent import fetch_papers
from backend.agents.classifier_agent import classify_papers
from backend.agents.explainer_agent import explain_papers
from backend.agents.learning_path_agent import generate_path

class ScholarState(TypedDict):
    query: str
    papers: List[dict]
    classified_papers: List[dict]
    explained_papers: List[dict]
    learning_path: dict
    research_gaps: List[str]

def build_graph():
    workflow = StateGraph(ScholarState)
    workflow.add_node("fetcher", fetch_papers)
    workflow.add_node("classifier", classify_papers)
    workflow.add_node("explainer", explain_papers)
    workflow.add_node("path_generator", generate_path)
    workflow.set_entry_point("fetcher")
    workflow.add_edge("fetcher", "classifier")
    workflow.add_edge("classifier", "explainer")
    workflow.add_edge("explainer", "path_generator")
    workflow.add_edge("path_generator", END)
    return workflow.compile()

scholar_graph = build_graph()

async def run_scholar_pipeline(query: str) -> dict:
    initial_state = {
        "query": query,
        "papers": [],
        "classified_papers": [],
        "explained_papers": [],
        "learning_path": {},
        "research_gaps": []
    }
    result = await scholar_graph.ainvoke(initial_state)
    return result