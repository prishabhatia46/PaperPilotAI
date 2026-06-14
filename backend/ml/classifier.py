import os

def classify_difficulty(abstract: str, citation_count: int, year: str) -> dict:
    current_year = 2026
    paper_age = current_year - int(year)
    abstract_lower = abstract.lower()
    
    if any(word in abstract_lower for word in ["survey", "review", "tutorial", "introduction to", "overview"]):
        level = "beginner"
    elif any(word in abstract_lower for word in ["theorem", "proof", "convergence", "lower bound", "complexity analysis"]):
        level = "advanced"
    elif citation_count > 500 and paper_age > 3:
        level = "beginner"
    elif citation_count < 10 and paper_age < 2:
        level = "advanced"
    else:
        level = "intermediate"
    
    emoji_map = {
        "beginner": "🟢",
        "intermediate": "🟡",
        "advanced": "🔴"
    }
    
    return {
        "level": level,
        "emoji": emoji_map[level],
        "reason": f"Citations: {citation_count}, Age: {paper_age} years"
    }