# PaperPilot AI

**Find, understand, and master any research topic — without getting lost in academic jargon.**

🔗 **Live Demo:** [paper-pilot-ai-sigma.vercel.app](https://paper-pilot-ai-sigma.vercel.app) *(Best viewed on desktop)*

---

## What is this?

PaperPilot AI is a multi-agent research assistant that takes a topic you care about and does the heavy lifting — fetching real academic papers, explaining them in plain English, and helping you figure out where to start and what's still unsolved.

It's built for students, researchers, and curious people who want to actually understand a field, not just skim abstracts.

---

## Features

- **Smart Paper Search** — pulls papers from ArXiv, Semantic Scholar, and OpenAlex, then scores each one for relevance using an LLM (1–10 scoring, not a binary filter)
- **Difficulty Classification** — every paper is tagged as Beginner, Intermediate, or Advanced based on citation count, age, and abstract complexity
- **Simple Explanation / Technical Summary / Limitations** — three tabs per paper, each written for a different audience
- **Learning Path** — tells you which papers to read first and why, specific to your query
- **Research Gaps** — identifies what's still unanswered in the field
- **Paper Comparison** — side-by-side breakdown of methodology, contributions, and verdict
- **URL Analyzer** — paste any ArXiv link and get the full breakdown instantly
- **AI Chat** — ask anything about a specific paper
- **Quiz Mode** — test your understanding with auto-generated MCQs
- **Related Papers** — find similar work with smart query generation
- **Keyword Search** — fuzzy search within any paper's content
- **Voice Search** — speak your query instead of typing
- **PDF Export** — export learning path and research gaps as a PDF
- **Dark / Light Theme** — Warm Scholar dark + Parchment light

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React, CSS (custom themes) |
| Backend | FastAPI, Python |
| Agents | LangGraph (multi-agent pipeline) |
| LLM | Groq (Llama 3.3 70B) |
| RAG | ChromaDB + HuggingFace Embeddings |
| Paper Sources | ArXiv, Semantic Scholar, OpenAlex |
| Deployment | Railway (backend) + Vercel (frontend) |
| Containerization | Docker |

---

## Architecture

```
User Query
    ↓
paper_fetcher_agent   → ArXiv + Semantic Scholar + OpenAlex
    ↓
classifier_agent      → Beginner / Intermediate / Advanced
    ↓
explainer_agent       → ELI5 + Technical Summary + Limitations (parallel)
    ↓
learning_path_agent   → Learning Path + Research Gaps
    ↓
Response to Frontend
```

---

## Project Structure

```
PaperPilotAI/
├── backend/
│   ├── agents/
│   │   ├── paper_fetcher_agent.py
│   │   ├── classifier_agent.py
│   │   ├── explainer_agent.py
│   │   ├── learning_path_agent.py
│   │   └── supervisor.py
│   ├── ml/
│   │   └── classifier.py
│   ├── rag/
│   │   └── paper_rag.py
│   ├── tools/
│   │   └── arxiv_tool.py
│   └── api.py
├── frontend/
│   └── paperpilot-ui/
│       └── src/
│           ├── App.js
│           └── App.css
└── Dockerfile
```

---

## Running Locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8001
```

**Frontend**
```bash
cd frontend/paperpilot-ui
npm install
npm start
```

Add a `.env` file in `/backend` with:
```
GROQ_API_KEY=your_key
SEMANTIC_SCHOLAR_API_KEY=your_key
```

---

## Deployment

- Backend deployed on **Railway** via Docker (Python 3.11)
- Frontend deployed on **Vercel**
- Auto-deploys on every push to `master`

---

Built by [Prisha Bhatia](https://github.com/prishabhatia46)
