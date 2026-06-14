import React, { useState, useEffect } from 'react';
import axios from 'axios';
import 'regenerator-runtime/runtime';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import './App.css';

const API = 'http://localhost:8000';

export default function App() {
  const [query, setQuery] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [offset, setOffset] = useState(0);
  const [readPapers, setReadPapers] = useState(() => JSON.parse(localStorage.getItem('readPapers') || '[]'));
  const [chatPaper, setChatPaper] = useState(null);
  const [chatMsg, setChatMsg] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [comparePapers, setComparePapers] = useState([]);
  const [compareResult, setCompareResult] = useState(null);
  const [quizPaper, setQuizPaper] = useState(null);
  const [quizData, setQuizData] = useState(null);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [relatedMap, setRelatedMap] = useState({});
  const [explainLevel, setExplainLevel] = useState({});
  const [explainText, setExplainText] = useState({});
  const [activeTab, setActiveTab] = useState('search');
  const [speaking, setSpeaking] = useState(false);
  const [keywordSearch, setKeywordSearch] = useState({});
  const [sortBy, setSortBy] = useState('relevant');
  const { transcript, listening, resetTranscript, browserSupportsSpeechRecognition } = useSpeechRecognition();
  useEffect(() => { if (transcript) setQuery(transcript); }, [transcript]);
  useEffect(() => { localStorage.setItem('readPapers', JSON.stringify(readPapers)); }, [readPapers]);

  const search = async (q) => {
    const sq = q || query;
    if (!sq.trim()) return;
    setLoading(true); setError(''); setResults(null); setOffset(0);
    try {
      const res = await axios.post(`${API}/search`, { query: sq, offset: 0 });
      setResults(res.data);
      setOffset(5);
    } catch { setError('Search failed. Make sure backend is running.'); }
    setLoading(false);
  };

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const res = await axios.post(`${API}/search`, { query, offset });
      setResults(prev => ({ ...prev, papers: [...prev.papers, ...res.data.papers] }));
      setOffset(o => o + 5);
    } catch { setError('Could not load more papers.'); }
    setLoadingMore(false);
  };

  const analyzeUrl = async () => {
    if (!urlInput.trim()) return;
    setLoading(true); setError(''); setResults(null);
    try {
      const res = await axios.post(`${API}/analyze-url`, { url: urlInput });
      if (res.data.error) { setError(res.data.error); }
      else {
        setResults({
          papers: [res.data.paper],
          learning_path: { steps: res.data.learning_path },
          research_gaps: res.data.research_gaps,
          related_from_url: res.data.related
        });
      }
    } catch { setError('Could not analyze URL.'); }
    setLoading(false);
  };

  const speak = (text) => {
    if (speaking) { window.speechSynthesis.cancel(); setSpeaking(false); return; }
    const u = new SpeechSynthesisUtterance(text);
    u.onend = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  };

  const toggleRead = (id) => setReadPapers(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);

  const toggleCompare = (paper) => {
    setComparePapers(prev => {
      if (prev.find(p => p.id === paper.id)) return prev.filter(p => p.id !== paper.id);
      if (prev.length >= 2) return [prev[1], paper];
      return [...prev, paper];
    });
  };

  const runCompare = async () => {
    if (comparePapers.length < 2) return;
    setCompareResult('loading');
    try {
      const res = await axios.post(`${API}/compare`, {
        paper1_title: comparePapers[0].title,
        paper1_abstract: comparePapers[0].abstract,
        paper2_title: comparePapers[1].title,
        paper2_abstract: comparePapers[1].abstract
      });
      setCompareResult(res.data.comparison);
    } catch { setCompareResult('Failed to compare.'); }
  };

  const fetchQuiz = async (paper) => {
    setQuizPaper(paper); setQuizData(null); setQuizAnswers({}); setQuizSubmitted(false);
    try {
      const res = await axios.post(`${API}/quiz`, { paper_title: paper.title, paper_abstract: paper.abstract });
      setQuizData(res.data.quiz);
    } catch { setQuizData('Failed to load quiz.'); }
  };

  const  fetchRelated = async (paper) => {
    setRelatedMap(prev => ({ ...prev, [paper.id]: 'loading' }));
    try {
      const res = await axios.post(`${API}/related`, { paper_title: paper.title, paper_abstract: paper.abstract });
      setRelatedMap(prev => ({ ...prev, [paper.id]: res.data.related }));
    } catch {}
  };

  const fetchExplain = async (paper, level) => {
    setExplainLevel(prev => ({ ...prev, [paper.id]: level }));
    try {
      const res = await axios.post(`${API}/explain`, { paper_title: paper.title, paper_abstract: paper.abstract, level });
      setExplainText(prev => ({ ...prev, [`${paper.id}_${level}`]: res.data.explanation }));
    } catch {}
  };

  const parseQuiz = (raw) => {
    if (!raw) return [];
    return raw.split('---').filter(Boolean).map((block, i) => {
      const lines = block.trim().split('\n').filter(Boolean);
      const q = lines.find(l => l.startsWith('Q:'))?.replace('Q:', '').trim();
      const options = lines.filter(l => /^[A-D]\)/.test(l));
      const answer = lines.find(l => l.startsWith('ANSWER:'))?.replace('ANSWER:', '').trim();
      const explanation = lines.find(l => l.startsWith('EXPLANATION:'))?.replace('EXPLANATION:', '').trim();
      return { id: i, q, options, answer, explanation };
    }).filter(q => q.q);
  };

  const readCount = results?.papers?.filter(p => readPapers.includes(p.id))?.length || 0;
  const totalPapers = results?.papers?.length || 0;
  const sortedPapers = results?.papers ? [...results.papers].sort((a, b) => {
  if (sortBy === 'newest') return parseInt(b.published) - parseInt(a.published);
  if (sortBy === 'oldest') return parseInt(a.published) - parseInt(b.published);
  return 0;
}) : [];
  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <div className="logo-icon">P</div>
            <div>
              <h1>PaperPilot AI</h1>
              <p>Find, Understand, and Master Any Research Topic</p>
            </div>
          </div>
          <nav className="nav">
            <button className={activeTab === 'search' ? 'nav-btn active' : 'nav-btn'} onClick={() => setActiveTab('search')}>Search</button>
            <button className={activeTab === 'url' ? 'nav-btn active' : 'nav-btn'} onClick={() => setActiveTab('url')}>Analyze Paper URL</button>
            {comparePapers.length > 0 && (
              <button className="nav-btn compare-badge" onClick={() => setActiveTab('compare')}>
                Compare ({comparePapers.length}/2)
              </button>
            )}
          </nav>
        </div>
      </header>

      <main className="main">
        {activeTab === 'search' && (
          <div className="search-section">
            <div className="search-box">
              <input
                className="search-input"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && search()}
                placeholder="Search any research topic..."
              />
              {browserSupportsSpeechRecognition && (
                <button className={`icon-btn ${listening ? 'active' : ''}`}
                  onClick={() => listening ? SpeechRecognition.stopListening() : (resetTranscript(), SpeechRecognition.startListening())}
                  title="Voice search">
                  {listening ? 'Stop' : 'Voice'}
                </button>
              )}
              <button className="search-btn" onClick={() => search()} disabled={loading}>
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
            {listening && <p className="hint">Listening... speak your topic</p>}
            {error && <p className="error">{error}</p>}
          </div>
        )}

        {activeTab === 'url' && (
          <div className="search-section">
            <div className="search-box">
              <input
                className="search-input"
                value={urlInput}
                onChange={e => setUrlInput(e.target.value)}
                placeholder="Paste ArXiv paper URL... e.g. https://arxiv.org/abs/2301.00000"
              />
              <button className="search-btn" onClick={analyzeUrl} disabled={loading}>
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
            {error && <p className="error">{error}</p>}
          </div>
        )}

        {activeTab === 'compare' && (
          <div className="compare-section">
            <h2>Paper Comparison</h2>
            {comparePapers.length < 2 && <p className="hint">Select 2 papers from search results to compare.</p>}
            {comparePapers.length === 2 && (
              <>
                <div className="compare-papers">
                  <div className="compare-paper-card"><strong>{comparePapers[0].title}</strong></div>
                  <div className="vs">VS</div>
                  <div className="compare-paper-card"><strong>{comparePapers[1].title}</strong></div>
                </div>
                <button className="search-btn" onClick={runCompare}>Compare Now</button>
                {compareResult === 'loading' && <p className="hint">Comparing papers...</p>}
                {compareResult && compareResult !== 'loading' && (
                  <div className="compare-result">
                    {compareResult.split('\n').filter(Boolean).map((line, i) => (
                      <p key={i} className={line.includes(':') && line.split(':')[0].length < 20 ? 'compare-heading' : ''}>{line}</p>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {loading && (
          <div className="loading">
            <div className="spinner" />
            <p>Agents working — fetching papers, analyzing, generating explanations...</p>
            <p className="hint">This takes 1-2 minutes</p>
          </div>
        )}

        {results && (
          <div className="results">
            {totalPapers > 0 && (
              <div className="progress-wrap">
                <span className="progress-label">Reading Progress: {readCount}/{totalPapers} papers</span>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${(readCount / totalPapers) * 100}%` }} />
                </div>
              </div>
            )}

            <div className="two-col">
              <div className="papers-col">
                <h2>Papers</h2>
                <div style={{display:'flex', gap:'0.5rem', marginBottom:'1rem', alignItems:'center'}}>
  <span style={{fontSize:'0.8rem', color:'#6b7280'}}>Sort by:</span>
  {['relevant', 'newest', 'oldest'].map(s => (
    <button key={s}
      className={`level-btn ${sortBy === s ? 'active' : ''}`}
      onClick={() => setSortBy(s)}>
      {s === 'relevant' ? 'Relevant' : s === 'newest' ? 'Newest' : 'Oldest'}
    </button>
  ))}
</div>
                {sortedPapers.map((paper, i) => (
                  <div key={i} className={`paper-card ${readPapers.includes(paper.id) ? 'read' : ''} ${comparePapers.find(p => p.id === paper.id) ? 'selected-compare' : ''}`}>
                    <div className="paper-meta">
                      <span className={`diff-badge ${paper.difficulty?.level}`}>{paper.difficulty?.level}</span>
                      <span className="meta-item">{paper.citation_count} citations</span>
                      <span className="meta-item">{paper.published}</span>
                    </div>
                    <h3 className="paper-title">{paper.title}</h3>
                    <p className="paper-authors">{paper.authors?.join(', ')}</p>
                    <div className="keyword-search-wrap">
  <input
    className="keyword-search-input"
    placeholder="Search keyword in this paper..."
    value={keywordSearch[paper.id] || ''}
    onChange={e => setKeywordSearch(prev => ({...prev, [paper.id]: e.target.value}))}
  />
  {keywordSearch[paper.id] && (
    <span className={`keyword-result ${
      paper.abstract?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase()) ||
       paper.title?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase()) ||
       paper.eli5?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase()) ||
       paper.technical_summary?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase()) ||
       paper.limitations?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase())
        ? '✓ Found in this paper' : '✗ Not found in this paper'}
    }`}>
      {paper.abstract?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase()) ||
       paper.title?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase()) ||
       paper.eli5?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase()) ||
       paper.technical_summary?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase()) ||
       paper.limitations?.toLowerCase().includes(keywordSearch[paper.id].toLowerCase())
        ? '✓ Found in this paper' : '✗ Not found in this paper'}
    </span>
  )}
</div>


                    <div className="tabs">
  {paper.eli5 && <details><summary>Simple Explanation</summary><p>{paper.eli5}</p><button className="text-btn" onClick={() => speak(paper.eli5)}>{speaking ? 'Stop Reading' : 'Read Aloud'}</button></details>}
  {paper.technical_summary && <details><summary>Technical Summary</summary><p>{paper.technical_summary}</p></details>}
  {paper.limitations && <details><summary>Limitations</summary><p>{paper.limitations}</p></details>}
</div>

                    <div className="paper-actions">
                      <a href={paper.pdf_url} target="_blank" rel="noreferrer" className="btn btn-primary">
  {paper.pdf_url?.includes('arxiv') ? 'Read Paper (Free)' : paper.pdf_url?.includes('doi.org') ? 'View on DOI' : paper.pdf_url?.includes('acm') ? 'View on ACM' : 'View Paper'}
</a>
                      <button className={`btn ${readPapers.includes(paper.id) ? 'btn-success' : 'btn-secondary'}`} onClick={() => toggleRead(paper.id)}>
                        {readPapers.includes(paper.id) ? 'Read' : 'Mark Read'}
                      </button>
                      <button className="btn btn-purple" onClick={() => { setChatPaper(paper); setChatHistory([]); }}>Ask AI</button>
                      
                      <button className={`btn ${comparePapers.find(p => p.id === paper.id) ? 'btn-warning' : 'btn-secondary'}`}
                        onClick={() => toggleCompare(paper)}>
                        {comparePapers.find(p => p.id === paper.id) ? 'Remove' : 'Compare'}
                      </button>
                      <button className="btn btn-secondary" onClick={() => { fetchRelated(paper); }}>Related</button>
                    </div>

                    {relatedMap[paper.id] && relatedMap[paper.id] !== 'loading' && (
  <div className="related-section">
    <p className="section-label">Related Papers</p>
    {relatedMap[paper.id].map((rp, j) => (
      <div key={j} className="related-item">
        <span className={`diff-badge ${rp.difficulty?.level}`}>{rp.difficulty?.level}</span>
        <a href={rp.pdf_url} target="_blank" rel="noreferrer">{rp.title}</a>
        <span className="meta-item">{rp.published}</span>
        <button
          className={`btn ${comparePapers.find(p => p.id === rp.id) ? 'btn-warning' : 'btn-secondary'}`}
          style={{fontSize: '0.7rem', padding: '0.2rem 0.5rem'}}
          onClick={() => toggleCompare({...rp, abstract: rp.abstract || paper.abstract})}>
          {comparePapers.find(p => p.id === rp.id) ? 'Remove' : 'Compare'}
        </button>
      </div>
    ))}
  </div>
)}
{relatedMap[paper.id] === 'loading' && (
  <p className="hint" style={{marginTop: '0.5rem'}}>Loading related papers...</p>
)}
                  </div>
                ))}

                {results.papers?.length >= 5 && (
                  <button className="load-more-btn" onClick={loadMore} disabled={loadingMore}>
                    {loadingMore ? 'Loading...' : 'Load More Papers'}
                  </button>
                )}
              </div>

              <div className="side-col">
                <div className="card">
                  <h2>Learning Path</h2>
                  <div className="learning-path">
                    {results.learning_path?.steps?.split('\n').filter(Boolean).map((step, i) => (
                      <div key={i} className="step-card">
                        <div className="step-number">{i + 1}</div>
                        <p>{step.replace(/^Step \d+:/, '').trim()}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <h2>Research Gaps</h2>
                  {results.research_gaps?.length > 0
                    ? results.research_gaps.map((gap, i) => <div key={i} className="gap-item">{gap}</div>)
                    : <p className="hint">No gaps identified.</p>}
                </div>

                {results.related_from_url && (
                  <div className="card">
                    <h2>Related Papers</h2>
                    {results.related_from_url.map((rp, i) => (
                      <div key={i} className="related-item">
                        <span className={`diff-badge ${rp.difficulty?.level}`}>{rp.difficulty?.level}</span>
                        <a href={rp.pdf_url} target="_blank" rel="noreferrer">{rp.title}</a>
                      </div>
                    ))}
                  </div>
                )}

                <button className="export-btn" onClick={() => window.print()}>Export as PDF</button>
              </div>
            </div>
          </div>
        )}
      </main>

      {chatPaper && (
        <div className="modal-overlay" onClick={() => setChatPaper(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Ask about: {chatPaper.title?.slice(0, 60)}...</h3>
              <button className="close-btn" onClick={() => setChatPaper(null)}>x</button>
            </div>
            <div className="modal-body">
              {chatHistory.length === 0 && <p className="hint">Ask anything about this paper.</p>}
              {chatHistory.map((m, i) => <div key={i} className={`msg ${m.role}`}>{m.text}</div>)}
            </div>
            <div className="modal-footer">
              <input value={chatMsg} onChange={e => setChatMsg(e.target.value)}
                onKeyDown={async e => {
                  if (e.key === 'Enter' && chatMsg.trim()) {
                    const q = chatMsg; setChatMsg('');
                    setChatHistory(h => [...h, { role: 'user', text: q }]);
                    try {
                      const res = await axios.post(`${API}/chat`, { question: q, paper_title: chatPaper.title, paper_abstract: chatPaper.abstract });
                      setChatHistory(h => [...h, { role: 'ai', text: res.data.answer }]);
                    } catch { setChatHistory(h => [...h, { role: 'ai', text: 'Error. Try again.' }]); }
                  }
                }}
                placeholder="Ask a question..." />
              <button onClick={async () => {
                if (!chatMsg.trim()) return;
                const q = chatMsg; setChatMsg('');
                setChatHistory(h => [...h, { role: 'user', text: q }]);
                try {
                  const res = await axios.post(`${API}/chat`, { question: q, paper_title: chatPaper.title, paper_abstract: chatPaper.abstract });
                  setChatHistory(h => [...h, { role: 'ai', text: res.data.answer }]);
                } catch { setChatHistory(h => [...h, { role: 'ai', text: 'Error. Try again.' }]); }
              }}>Send</button>
            </div>
          </div>
        </div>
      )}

      {quizPaper && (
        <div className="modal-overlay" onClick={() => setQuizPaper(null)}>
          <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Quiz: {quizPaper.title?.slice(0, 60)}...</h3>
              <button className="close-btn" onClick={() => setQuizPaper(null)}>x</button>
            </div>
            <div className="modal-body">
              {!quizData && <p className="hint">Generating quiz...</p>}
              {quizData && parseQuiz(quizData).map((q, i) => (
                <div key={i} className="quiz-question">
                  <p className="q-text">{i + 1}. {q.q}</p>
                  {q.options.map((opt, j) => (
                    <button key={j}
                      className={`quiz-option ${quizAnswers[i] === opt[0] ? 'selected' : ''} ${quizSubmitted ? (opt[0] === q.answer ? 'correct' : quizAnswers[i] === opt[0] ? 'wrong' : '') : ''}`}
                      onClick={() => !quizSubmitted && setQuizAnswers(prev => ({ ...prev, [i]: opt[0] }))}>
                      {opt}
                    </button>
                  ))}
                  {quizSubmitted && <p className="q-explanation">{q.explanation}</p>}
                </div>
              ))}
            </div>
            <div className="modal-footer">
              {!quizSubmitted
                ? <button className="search-btn" onClick={() => setQuizSubmitted(true)}>Submit Answers</button>
                : <p className="hint">Score: {parseQuiz(quizData).filter(q => quizAnswers[q.id] === q.answer).length}/{parseQuiz(quizData).length}</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}