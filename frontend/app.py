
from dotenv import load_dotenv
load_dotenv(dotenv_path="C:/Users/Prisha Bhatia/scholarpath-ai/.env")
import streamlit as st
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.supervisor import run_scholar_pipeline

st.set_page_config(
    page_title="ScholarPath AI",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 ScholarPath AI")
st.subheader("Find, Understand, and Master Any Research Topic")

col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("", placeholder="e.g. attention mechanism in transformers")
with col2:
    search_btn = st.button("🔍 Search", use_container_width=True)

if search_btn and query:
    with st.spinner("🤖 Fetching papers... analyzing... generating explanations (1-2 min)"):
        result = asyncio.run(run_scholar_pipeline(query))
    
    papers = result["explained_papers"]
    learning_path = result["learning_path"]
    gaps = result["research_gaps"]
    
    col_papers, col_path = st.columns([2, 1])
    
    with col_papers:
        st.markdown("### 📚 Papers")
        for paper in papers:
            diff = paper["difficulty"]
            with st.expander(f"{diff['emoji']} {paper['title']} ({paper['published']}) — {paper['citation_count']} citations"):
                tab1, tab2, tab3 = st.tabs(["🧒 ELI5", "🔬 Technical", "⚠️ Limitations"])
                with tab1:
                    st.info(paper.get("eli5", ""))
                with tab2:
                    st.write(paper.get("technical_summary", ""))
                with tab3:
                    st.warning(paper.get("limitations", ""))
                st.markdown(f"**Authors:** {', '.join(paper['authors'])}")
                st.markdown(f"[📄 Read Paper]({paper['pdf_url']})")
    
    with col_path:
        st.markdown("### 🗺️ Learning Path")
        st.success(learning_path.get("steps", ""))
        st.markdown("### 🔭 Research Gaps")
        for gap in gaps:
            st.warning(f"💡 {gap}")

st.markdown("---")
st.markdown("*ScholarPath AI — Built with LangGraph + RAG + Gemini*")