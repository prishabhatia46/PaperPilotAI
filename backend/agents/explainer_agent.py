from backend.rag.paper_rag import ingest_papers, generate_explanations_parallel

async def explain_papers(state: dict) -> dict:
    papers = state["classified_papers"]
    if papers:
        ingest_papers(papers)
        papers = await generate_explanations_parallel(papers)
    return {"explained_papers": papers}