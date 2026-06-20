

# PaperPilot AI

**Find, understand, and master any research topic — without getting lost in academic jargon.**

🔗 **Live Demo:** [https://paper-pilot-ai-sigma.vercel.app](https://paper-pilot-ai-sigma.vercel.app) *(Best viewed on desktop)*

---

## What is this?

PaperPilot AI is a multi-agent research assistant that takes a topic you care about and does the heavy lifting — fetching real academic papers, explaining them in plain English, and helping you figure out where to start and what's still unsolved.

It's built for students, researchers, and curious people who want to actually understand a field, not just skim abstracts.

---

## Features

### 📚 Smart Paper Search

* Pulls papers from ArXiv, Semantic Scholar, and OpenAlex
* Uses an LLM to score relevance on a scale of 1–10

### 🎯 Difficulty Classification

* Beginner
* Intermediate
* Advanced

Classification is based on:

* Citation count
* Publication age
* Abstract complexity

### 🧠 Multi-Level Explanations

Each paper includes:

* Simple Explanation (ELI5)
* Technical Summary
* Limitations

### 🛣 Learning Path Generation

* Recommends which papers to read first
* Personalized to the user's query

### 🔍 Research Gap Detection

* Identifies unanswered questions
* Highlights future research opportunities

### ⚖️ Paper Comparison

* Methodology comparison
* Contribution analysis
* Overall verdict

### 🔗 URL Analyzer

* Paste any ArXiv URL
* Get an instant breakdown

### 💬 AI Chat

* Ask questions about a specific paper

### 📄 Related Papers

* Discover similar research automatically

### 🔎 Keyword Search

* Fuzzy search across paper content

### 🎤 Voice Search

* Speak instead of typing

### 📥 PDF Export

* Export learning paths and research gaps

### 🌙 Theme Support

* Warm Scholar Dark Theme
* Parchment Light Theme

---

## Tech Stack

| Layer            | Technology                        |
| ---------------- | --------------------------------- |
| Frontend         | React, Custom CSS                 |
| Backend          | FastAPI, Python                   |
| Agents           | LangGraph                         |
| LLM              | Groq (Llama 3.3 70B)              |
| RAG              | ChromaDB + HuggingFace Embeddings |
| Paper Sources    | ArXiv, Semantic Scholar, OpenAlex |
| Deployment       | Railway + Vercel                  |
| Containerization | Docker                            |

---

## System Architecture

```text
User Query
    ↓
paper_fetcher_agent
    ↓
classifier_agent
    ↓
explainer_agent
    ↓
learning_path_agent
    ↓
Response to Frontend
```

### Detailed Flow

```text
User Query
    ↓
paper_fetcher_agent   → ArXiv + Semantic Scholar + OpenAlex
    ↓
classifier_agent      → Beginner / Intermediate / Advanced
    ↓
explainer_agent       → ELI5 + Technical Summary + Limitations
    ↓
learning_path_agent   → Learning Path + Research Gaps
    ↓
Response to Frontend
```

---

## Project Structure

```text
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

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8001
```

### Frontend

```bash
cd frontend/paperpilot-ui
npm install
npm start
```

### Environment Variables

Create a `.env` file inside the `backend` directory:

```env
GROQ_API_KEY=your_key
SEMANTIC_SCHOLAR_API_KEY=your_key
```

---

## Deployment

* Backend deployed on Railway using Docker (Python 3.11)
* Frontend deployed on Vercel
* Automatic deployment on every push to `master`

---

## Built By

**Prisha Bhatia**

GitHub: [https://github.com/prishabhatia46](https://github.com/prishabhatia46)


