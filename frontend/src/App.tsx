import { useState, useEffect, useRef } from 'react';
import { Play, PiggyBank, CreditCard, ShieldAlert, BadgeHelp, CheckCircle2, AlertTriangle, AlertCircle, HelpCircle, Send, ArrowRight, Lock, User, LogOut, History, FileText, MonitorUp, Link2 } from 'lucide-react';
import './App.css';

// --- Types ---
interface TemplateInfo {
  id: string;
  name: string;
  description: string;
  required_inputs: string[];
}

interface TaskResult {
  summary: string;
  steps_taken: number;
  duration_seconds: number;
  outcome_details: Record<string, string>;
  transcript: string[];
  error?: string;
  transcript_path?: string;
}

interface TaskStatusResponse {
  task_id: string;
  status: 'running' | 'success' | 'failed' | 'partial' | 'needs_input';
  result: TaskResult | null;
  pending_question: string | null;
  progress: ProgressEvent[];
  created_at: string;
  updated_at: string;
}

interface ProgressEvent {
  step: number;
  phase: 'starting' | 'complete';
  message?: string;
  thought?: string;
  goal?: string;
  timestamp: string;
}

interface HistoryTask {
  id: string;
  site: string;
  template: string;
  status: string;
  created_at: string;
}

// --- Icons mapping ---
const getTemplateIcon = (id: string) => {
  if (id.includes('fee')) return <CreditCard size={20} />;
  if (id.includes('dispute')) return <ShieldAlert size={20} />;
  if (id.includes('retention')) return <PiggyBank size={20} />;
  return <BadgeHelp size={20} />;
};

function App() {
  // Auth state
  const [token, setToken] = useState<string | null>(localStorage.getItem('pig_token'));
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');

  // Dashboard state
  const [view, setView] = useState<'new_task' | 'history'>('new_task');
  const [sites, setSites] = useState<string[]>([]);
  const [selectedSite, setSelectedSite] = useState<string>('amex');
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateInfo | null>(null);
  const [taskHistory, setTaskHistory] = useState<HistoryTask[]>([]);
  
  // Launch forms
  const [taskOverride, setTaskOverride] = useState('');
  const [browserMode, setBrowserMode] = useState<'launch' | 'attach'>('launch');
  const [cdpUrl, setCdpUrl] = useState('');
  const [browserLaunchStatus, setBrowserLaunchStatus] = useState('');
  const [browserLaunchError, setBrowserLaunchError] = useState('');
  
  // Active Task state
  const [taskId, setTaskId] = useState<string | null>(null);
  const [activeTask, setActiveTask] = useState<TaskStatusResponse | null>(null);
  const [userResponse, setUserResponse] = useState('');
  
  // Polling ref
  const pollInterval = useRef<number | null>(null);

  // --- Auth Handlers ---
  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/signup';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });
      
      const data = await res.json();
      if (!res.ok) {
        setAuthError(data.detail || 'Authentication failed');
        return;
      }
      
      setToken(data.access_token);
      localStorage.setItem('pig_token', data.access_token);
    } catch (e: any) {
      setAuthError(e.message || 'Network error');
    }
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem('pig_token');
    setTaskId(null);
    setActiveTask(null);
  };

  // --- Fetch initial data (Authenticated) ---
  const authHeaders = { 'Authorization': `Bearer ${token}` };

  useEffect(() => {
    if (!token) return;
    fetch('/api/sites', { headers: authHeaders })
      .then(r => r.json())
      .then(d => setSites(d.sites || []))
      .catch(console.error);
  }, [token]);

  useEffect(() => {
    if (!token || !selectedSite) return;
    fetch(`/api/sites/${selectedSite}/templates`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => {
        setTemplates(d.templates || []);
        if (d.templates?.length > 0) setSelectedTemplate(d.templates[0]);
      })
      .catch(console.error);
  }, [token, selectedSite]);

  useEffect(() => {
    if (!token || view !== 'history') return;
    fetch('/api/tasks', { headers: authHeaders })
      .then(r => r.json())
      .then(d => setTaskHistory(d.tasks || []))
      .catch(console.error);
  }, [token, view]);

  // --- Polling logic ---
  useEffect(() => {
    if (!taskId || !token) return;
    
    const fetchStatus = () => {
      fetch(`/api/tasks/${taskId}`, { headers: authHeaders })
        .then(r => {
          if (r.status === 401) { logout(); throw new Error('Unauthorized'); }
          return r.json();
        })
        .then((d: TaskStatusResponse) => {
          setActiveTask(d);
          if (d.status !== 'running' && d.status !== 'needs_input') {
            stopPolling();
          }
        })
        .catch(console.error);
    };

    fetchStatus(); // immediate
    pollInterval.current = window.setInterval(fetchStatus, 2000);
    
    return stopPolling;
  }, [taskId, token]);

  const stopPolling = () => {
    if (pollInterval.current) {
      clearInterval(pollInterval.current);
      pollInterval.current = null;
    }
  };

  // --- Actions ---
  const selectBrowserMode = (mode: 'launch' | 'attach') => {
    setBrowserMode(mode);
    setBrowserLaunchError('');
    setBrowserLaunchStatus('');
    if (mode === 'attach' && !cdpUrl) {
      setCdpUrl('http://127.0.0.1:9222');
    }
  };

  const handleLaunchBrowser = async () => {
    if (!selectedSite || !token) return;

    setBrowserLaunchStatus('Launching visible Chrome...');
    setBrowserLaunchError('');
    try {
      const res = await fetch('/api/browser/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ site: selectedSite })
      });
      const data = await res.json();
      if (!res.ok) {
        setBrowserLaunchError(data.detail || 'Could not launch Chrome');
        setBrowserLaunchStatus('');
        return;
      }
      setCdpUrl(data.cdp_url);
      setBrowserLaunchStatus(data.message || 'Chrome is ready.');
    } catch (e: any) {
      setBrowserLaunchError(e.message || 'Could not launch Chrome');
      setBrowserLaunchStatus('');
    }
  };

  const handleLaunch = async () => {
    if (!selectedSite || !selectedTemplate || !token) return;
    
    const defaultTaskText = `Execute ${selectedTemplate.name} template.`;
    const preparedCdpUrl = browserMode === 'launch' ? cdpUrl : cdpUrl.trim();
    const payload = {
      site: selectedSite,
      task: taskOverride || defaultTaskText,
      template: selectedTemplate.id,
      headless: false,
      cdp_url: preparedCdpUrl || undefined
    };

    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.task_id) {
        setTaskId(data.task_id);
        setActiveTask(null);
        setView('new_task');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleProvideInput = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskId || !userResponse || !token) return;

    try {
      await fetch(`/api/tasks/${taskId}/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ response: userResponse })
      });
      setUserResponse('');
      fetch(`/api/tasks/${taskId}`, { headers: authHeaders })
        .then(r => r.json())
        .then(setActiveTask);
    } catch (e) {
      console.error(e);
    }
  };

  const viewTaskRecord = (id: string) => {
    setTaskId(id);
    setView('new_task');
  };

  // --- Renders ---
  if (!token) {
    return (
      <div className="app-container" style={{justifyContent: 'center', alignItems: 'center', minHeight: '100vh', padding: '20px'}}>
        <div className="glass-panel" style={{padding: '3rem', maxWidth: '400px', width: '100%', textAlign: 'center'}}>
          <PiggyBank size={48} className="text-gradient" style={{margin: '0 auto 1rem'}} />
          <h1 style={{marginBottom: '2rem'}}>Flying Pig AI</h1>
          <form onSubmit={handleAuth} style={{display: 'flex', flexDirection: 'column', gap: '1rem', textAlign: 'left'}}>
            <div className="form-group">
              <label>Username</label>
              <div className="input-with-icon" style={{display: 'flex', alignItems: 'center', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', borderRadius: '8px', padding: '0 10px'}}>
                <User size={16} color="var(--text-secondary)" />
                <input type="text" value={username} onChange={e=>setUsername(e.target.value)} required style={{border: 'none', background: 'transparent', flex: 1}} />
              </div>
            </div>
            <div className="form-group">
              <label>Password</label>
              <div className="input-with-icon" style={{display: 'flex', alignItems: 'center', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', borderRadius: '8px', padding: '0 10px'}}>
                <Lock size={16} color="var(--text-secondary)" />
                <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required style={{border: 'none', background: 'transparent', flex: 1}} />
              </div>
            </div>
            {authError && <p style={{color: 'var(--danger)', fontSize: '0.9rem'}}>{authError}</p>}
            <button className="primary-btn" type="submit" style={{marginTop: '1rem'}}>
              {authMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
            <p style={{textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem', cursor: 'pointer'}} onClick={() => setAuthMode(authMode==='login'?'signup':'login')}>
              {authMode === 'login' ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </p>
          </form>
        </div>
      </div>
    );
  }

  const renderStatus = (status: string, pq: string | null = null) => {
    let icon = <Play size={16} />;
    if (status === 'success') icon = <CheckCircle2 size={16} />;
    if (status === 'partial') icon = <AlertTriangle size={16} />;
    if (status === 'failed') icon = <AlertCircle size={16} />;
    if (status === 'needs_input') icon = <HelpCircle size={16} />;

    return (
      <div className={`task-status ${status}`}>
        {icon}
        <span>{status === 'running' ? 'Running' + (pq ? '' : '...') : status.toUpperCase()}</span>
      </div>
    );
  };

  const progressLines = activeTask?.progress?.filter((event) => event.phase === 'complete') || [];

  return (
    <div className="app-container">
      <header>
        <div className="logo">
          <PiggyBank className="logo-icon text-gradient" />
          <h1><span className="text-gradient">Flying Pig AI</span></h1>
        </div>
        <div className="nav-links" style={{display: 'flex', gap: '1rem'}}>
          <button className={`nav-btn ${view==='new_task' && !taskId ? 'active' : ''}`} onClick={() => {setView('new_task'); setTaskId(null);}}>New Task</button>
          <button className={`nav-btn ${view==='history' ? 'active' : ''}`} onClick={() => setView('history')}><History size={16}/> History</button>
          <button className="nav-btn" onClick={logout}><LogOut size={16}/> Sign Out</button>
        </div>
      </header>

      <main className="main-content">
        {view === 'history' ? (
          <div className="glass-panel" style={{gridColumn: '1 / -1', padding: '2rem'}}>
            <h2 style={{marginBottom: '1.5rem'}}>Audit Trail</h2>
            <div className="history-list" style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
              {taskHistory.length === 0 ? (
                <p style={{color: 'var(--text-secondary)'}}>No tasks recorded yet.</p>
              ) : taskHistory.map(th => (
                <div key={th.id} className="history-item glass-panel" style={{padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer'}} onClick={() => viewTaskRecord(th.id)}>
                  <div>
                    <h3 style={{fontSize: '1rem'}}>{th.site.toUpperCase()} — {th.template || 'Custom'}</h3>
                    <p style={{color: 'var(--text-secondary)', fontSize: '0.85rem'}}>Date: {new Date(th.created_at).toLocaleString()} | ID: {th.id}</p>
                  </div>
                  <div>
                    {renderStatus(th.status)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Left Column: Configuration */}
            <div className="sidebar">
              <div className="glass-panel" style={{padding: '1.5rem'}}>
                <h2 className="section-title">Site Selection</h2>
                <select 
                  value={selectedSite} 
                  onChange={e => setSelectedSite(e.target.value)}
                  style={{width: '100%', marginTop: '0.5rem'}}
                >
                  {sites.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
                </select>
              </div>

              <div className="glass-panel" style={{padding: '1.5rem'}}>
                <h2 className="section-title">Template</h2>
                <div className="templates-grid" style={{marginTop: '1rem'}}>
                  {templates.map(t => (
                    <div 
                      key={t.id} 
                      className={`template-card ${selectedTemplate?.id === t.id ? 'active' : ''}`}
                      onClick={() => setSelectedTemplate(t)}
                    >
                      <h3 style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                        <span style={{color: selectedTemplate?.id === t.id ? 'var(--accent-primary)' : 'var(--text-secondary)'}}>
                          {getTemplateIcon(t.id)}
                        </span>
                        {t.name}
                      </h3>
                      <p>{t.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column: Execution */}
            <div className="execution-area">
              {taskId ? (
                <div className="glass-panel task-dashboard">
                  <div className="task-header">
                    <div>
                      <h2 style={{fontSize: '1.5rem'}}>Task Dashboard</h2>
                      <p style={{color: 'var(--text-secondary)'}}>ID: {taskId}</p>
                    </div>
                    {activeTask && renderStatus(activeTask.status, activeTask.pending_question)}
                  </div>

                  <div className="task-body">
                    {/* Mid-session Input Prompt */}
                    {activeTask?.status === 'needs_input' && activeTask.pending_question && (
                      <div className="user-input-prompt">
                        <h3><HelpCircle size={18} /> Intervention Required</h3>
                        <p>{activeTask.pending_question}</p>
                        <form onSubmit={handleProvideInput} className="user-input-form">
                          <input 
                            type="text" 
                            value={userResponse}
                            onChange={e => setUserResponse(e.target.value)}
                            placeholder="Type your response here..."
                            autoFocus
                          />
                          <button type="submit"><Send size={16} /></button>
                        </form>
                      </div>
                    )}

                    {/* Final Outcome */}
                    {(activeTask?.status === 'success' || activeTask?.status === 'partial') && activeTask.result && (
                      <div className="outcome-card">
                        <h3><CheckCircle2 size={24} /> {activeTask.status.toUpperCase()}</h3>
                        <p style={{marginBottom: '1rem'}}>{activeTask.result.summary}</p>
                        
                        {activeTask.result.outcome_details && Object.keys(activeTask.result.outcome_details).length > 0 && (
                          <div style={{marginTop: '1rem'}}>
                            <h4 style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase'}}>Outcome Details</h4>
                            {Object.entries(activeTask.result.outcome_details).map(([k, v]) => {
                              if (!v || typeof v === 'object') return null;
                              return (
                                <div className="outcome-stat" key={k}>
                                  <span>{k.replace(/_/g, ' ')}</span>
                                  <span>{v}</span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                        
                        {activeTask.result.transcript_path && (
                          <div className="outcome-stat" style={{marginTop: '1rem'}}>
                            <span><FileText size={14}/> Transcript Archive</span>
                            <span style={{color: 'var(--info)'}}>{activeTask.result.transcript_path}</span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Live Transcript (or DB fetched) */}
                    <div style={{marginTop: 'auto'}}>
                      <h4 style={{marginBottom: '0.5rem', color: 'var(--text-secondary)'}}>Agent Activity</h4>
                      <div className="agent-transcript">
                        {activeTask?.status === 'running' && !activeTask.pending_question && (
                          <div className="transcript-line">
                            <span style={{color: 'var(--accent-primary)'}}>[SYSTEM]</span> Agent processing<span className="loading-dots"></span>
                          </div>
                        )}
                        {progressLines.map((event) => (
                          <div className="transcript-line progress-line" key={`${event.step}-${event.timestamp}`}>
                            <span className="progress-step">Step {event.step}</span>
                            <span>{event.message || event.goal || event.thought || 'Completed'}</span>
                          </div>
                        ))}
                        {activeTask?.result?.transcript?.map((l, i) => (
                          <div className="transcript-line" key={i} style={{color: l.includes('[ERROR]') ? 'var(--danger)' : 'var(--text-secondary)'}}>
                            {l}
                          </div>
                        ))}
                      </div>
                    </div>

                    {activeTask?.status !== 'running' && activeTask?.status !== 'needs_input' && (
                      <button className="primary-btn" onClick={() => {setTaskId(null); setView('new_task');}} style={{background: 'rgba(255,255,255,0.1)'}}>
                        Start New Task
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="glass-panel launch-control">
                  <h2 style={{fontSize: '1.5rem', marginBottom: '0.5rem'}}>Launch Task</h2>
                  <p style={{color: 'var(--text-secondary)', marginBottom: '2rem'}}>Configure the agent to handle customer service on your behalf.</p>
                  
                  <div className="launch-form">
                    <div className="form-group">
                      <label>Browser</label>
                      <div className="segmented-control" role="tablist" aria-label="Browser run mode">
                        <button
                          className={browserMode === 'launch' ? 'active' : ''}
                          onClick={() => selectBrowserMode('launch')}
                          type="button"
                        >
                          <MonitorUp size={16} /> Launch
                        </button>
                        <button
                          className={browserMode === 'attach' ? 'active' : ''}
                          onClick={() => selectBrowserMode('attach')}
                          type="button"
                        >
                          <Link2 size={16} /> Attach
                        </button>
                      </div>
                    </div>

                    {browserMode === 'launch' ? (
                      <div className="browser-prep">
                        <div>
                          <h3>Prepare Chrome</h3>
                          <p>Open a FlyingPig Chrome window, sign in if needed, then start the agent.</p>
                        </div>
                        <button className="secondary-btn" onClick={handleLaunchBrowser} type="button">
                          <MonitorUp size={16} /> Open Chrome
                        </button>
                      </div>
                    ) : (
                      <div className="form-group">
                        <label>Remote debugging URL</label>
                        <input
                          type="text"
                          value={cdpUrl}
                          onChange={e => setCdpUrl(e.target.value)}
                          placeholder="http://127.0.0.1:9222"
                        />
                      </div>
                    )}

                    {(browserLaunchStatus || browserLaunchError) && (
                      <div className={`inline-status ${browserLaunchError ? 'error' : 'success'}`}>
                        {browserLaunchError || browserLaunchStatus}
                      </div>
                    )}

                    <div className="form-group">
                      <label>Additional Context (Optional)</label>
                      <textarea 
                        value={taskOverride}
                        onChange={e => setTaskOverride(e.target.value)}
                        placeholder="E.g., I've been a member for 5 years, mention my loyalty."
                        rows={4}
                      />
                    </div>
                    
                    <div style={{background: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid var(--danger)', padding: '1rem', borderRadius: '4px', marginTop: '1rem'}}>
                      <p style={{fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.9)'}}>
                        <strong>Important:</strong> Use the visible Chrome window for login and MFA. Flying Pig attaches after the tab is ready, so account credentials stay out of the app.
                      </p>
                    </div>

                    <div style={{display: 'flex', justifyContent: 'flex-end', marginTop: '1rem'}}>
                      <button className="primary-btn" onClick={handleLaunch} disabled={!selectedTemplate || !cdpUrl.trim()}>
                        Deploy Agent <ArrowRight size={18} />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
