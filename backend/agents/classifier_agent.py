from backend.ml.classifier import classify_difficulty

async def classify_papers(state: dict) -> dict:
    papers = state["papers"]
    for paper in papers:
        difficulty = classify_difficulty(
            paper["abstract"],
            paper["citation_count"],
            paper["published"]
        )
        paper["difficulty"] = difficulty
    
    order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    papers.sort(key=lambda x: order.get(x["difficulty"]["level"], 1))
    return {"classified_papers": papers}