from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.tools.arxiv_tool import search_arxiv_papers
from backend.ml.classifier import classify_difficulty
from dotenv import load_dotenv

load_dotenv()

app = Server("scholarpath-ai")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_research_papers",
            description="Search and analyze research papers on any topic with difficulty classification",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research topic to search"},
                    "max_results": {"type": "integer", "description": "Number of papers", "default": 5}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_learning_path",
            description="Generate a personalized learning path for a research topic",
            inputSchema={
                "type": "object", 
                "properties": {
                    "query": {"type": "string", "description": "Research topic"}
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "search_research_papers":
        query = arguments["query"]
        max_results = arguments.get("max_results", 5)
        papers = search_arxiv_papers(query, max_results)
        
        for paper in papers:
            diff = classify_difficulty(paper["abstract"], paper["citation_count"], paper["published"])
            paper["difficulty"] = diff
        
        result = f"Found {len(papers)} papers on '{query}':\n\n"
        for i, p in enumerate(papers, 1):
            result += f"{i}. {p['title']} ({p['published']})\n"
            result += f"   Difficulty: {p['difficulty']['emoji']} {p['difficulty']['level']}\n"
            result += f"   Citations: {p['citation_count']}\n"
            result += f"   PDF: {p['pdf_url']}\n\n"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "get_learning_path":
        query = arguments["query"]
        papers = search_arxiv_papers(query, 5)
        
        path = f"Learning Path for '{query}':\n\n"
        beginner = [p for p in papers if classify_difficulty(p["abstract"], p["citation_count"], p["published"])["level"] == "beginner"]
        intermediate = [p for p in papers if classify_difficulty(p["abstract"], p["citation_count"], p["published"])["level"] == "intermediate"]
        advanced = [p for p in papers if classify_difficulty(p["abstract"], p["citation_count"], p["published"])["level"] == "advanced"]
        
        if beginner:
            path += "Step 1 - Start here:\n"
            for p in beginner:
                path += f"  • {p['title']}\n"
        if intermediate:
            path += "\nStep 2 - Build understanding:\n"
            for p in intermediate:
                path += f"  • {p['title']}\n"
        if advanced:
            path += "\nStep 3 - Advanced:\n"
            for p in advanced:
                path += f"  • {p['title']}\n"
        
        return [types.TextContent(type="text", text=path)]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())