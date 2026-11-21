import {useEffect, useState} from 'react';
import {Link, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams, useSearchParams} from 'react-router-dom';
import {api} from './api';
import {useAuth} from './auth';

const statuses = {uploaded: 'Not processed', processing: 'Processing', completed: 'Completed', failed: 'Needs attention'};
const questionTypes = {escala_likert: 'Likert scale', seleccion_multiple: 'Multiple choice', verdadero_falso: 'True/false', desarrollo: 'Open-ended', emparejamiento: 'Matching'};
const questionCount = count => `${count} ${count === 1 ? 'question' : 'questions'}`;
const date = value => new Date(value).toLocaleDateString('en-US');
const size = value => `${(value / 1024).toFixed(1)} KB`;

export function Notice({children}) { return children ? <div className="notice error" role="alert">{children}</div> : null; }
function Badge({status}) { return <span className={`badge ${status}`}>{statuses[status] || status}</span>; }

function Layout() {
  const {user, logout} = useAuth();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const location = useLocation();
  useEffect(() => { setError(''); window.scrollTo(0, 0); }, [location.pathname]);
  async function signOut() { setBusy(true); try { await logout(); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  return <><a className="skip-link" href="#main">Skip to content</a><header className="topbar">
    <Link className="brand" to="/"><span className="brand-mark" aria-hidden="true">c.</span>cuaderno<span className="brand-divider">/</span><span className="brand-caption">Questionnaires</span></Link>
    <nav aria-label="Main navigation">{user ? <><Link to="/">My documents</Link><span className="user-name">{user.username}</span><button className="text-button" onClick={signOut} disabled={busy}>Sign out</button></> : <><Link to="/cuenta/ingresar">Sign in</Link><Link className="button small secondary" to="/cuenta/registro">Create account</Link></>}</nav>
  </header><main id="main" className="container"><Notice>{error}</Notice><Outlet /></main><footer className="footer"><span>Cuaderno</span><span>From documents to questions.</span></footer></>;
}

function Protected() {
  const {user} = useAuth();
  const location = useLocation();
  return user ? <Outlet /> : <Navigate to="/cuenta/ingresar" replace state={{from: location.pathname}} />;
}

export function AuthPage({mode}) {
  const {user, authenticate} = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const register = mode === 'register';
  if (user) return <Navigate to="/" replace />;
  async function submit(event) {
    event.preventDefault(); setError('');
    const form = new FormData(event.currentTarget);
    if (register && form.get('password') !== form.get('confirm')) { setError('Passwords do not match.'); return; }
    const values = {username: form.get('username'), password: form.get('password')};
    if (register) values.email = form.get('email');
    setBusy(true);
    try { await authenticate(mode, values); navigate(location.state?.from || '/', {replace: true}); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <div className="auth-layout"><section className="auth-intro"><span className="eyebrow">A HOME FOR YOUR QUESTIONNAIRES</span><h1>Less typing.<br /><em>More possibilities.</em></h1><p>Turn your documents into structured questions and access your results whenever you need them.</p><div className="format-row"><span>PDF</span><span>WORD</span><span>EXCEL</span></div></section>
    <section className="panel auth-card"><span className="eyebrow">{register ? 'GET STARTED' : 'WELCOME BACK'}</span><h2>{register ? 'Create your account' : 'Sign in to your account'}</h2><p className="muted">All your documents in one place.</p><Notice>{error}</Notice><form onSubmit={submit} aria-busy={busy}>
      <div className="field"><label htmlFor="username">Username</label><input id="username" name="username" autoComplete="username" required maxLength={150} /></div>
      {register && <div className="field"><label htmlFor="email">Email address</label><input id="email" name="email" type="email" autoComplete="email" required maxLength={254} /></div>}
      <div className="field"><label htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={register ? 10 : 1} maxLength={256} />{register && <p className="help">Use at least 10 characters and avoid predictable passwords.</p>}</div>
      {register && <div className="field"><label htmlFor="confirm">Confirm password</label><input id="confirm" name="confirm" type="password" autoComplete="new-password" required maxLength={256} /></div>}
      <button className="button full" disabled={busy}>{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}</button>
    </form><p className="auth-switch">{register ? 'Already have an account? ' : 'New here? '}<Link to={register ? '/cuenta/ingresar' : '/cuenta/registro'}>{register ? 'Sign in' : 'Create an account'}</Link></p></section></div>;
}

function Library() {
  const [params] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => { const controller = new AbortController(); setData(null); setError(''); api(`/documents?page=${page}`, {signal: controller.signal}).then(setData).catch(e => { if (e.name !== 'AbortError') setError(e.message); }); return () => controller.abort(); }, [page, retry]);
  return <><section className="page-heading"><div><span className="eyebrow">YOUR WORKSPACE</span><h1>My documents</h1><p>Upload a questionnaire. Extract its questions. Save the results.</p></div><Link className="button" to="/documentos/subir">Upload document</Link></section><Notice>{error}</Notice>{error && <button className="button secondary" onClick={() => setRetry(v => v + 1)}>Try again</button>}
    {!data && !error && <p role="status">Loading your library…</p>}
    {data && <><section className="stats" aria-label="Document summary">{[['Saved documents', data.stats.total], ['Results ready', data.stats.completed], ['Pending', data.stats.pending]].map(([label, count]) => <div key={label}><span>{label}</span><strong>{count}</strong></div>)}</section>
    <section className="panel library"><div className="section-heading"><h2>Your library</h2><span className="muted">Only visible to you</span></div>{data.items.length ? <div className="table-wrap"><table><thead><tr><th>Document</th><th>Saved</th><th>Status</th><th><span className="sr-only">Open document</span></th></tr></thead><tbody>{data.items.map(entry => <tr key={entry.id}><td><div className="document-cell"><span className="file-icon">{entry.extension.slice(1).toUpperCase()}</span><div><Link className="document-name" to={`/documentos/${entry.id}`}>{entry.original_name}</Link><span className="metadata">{size(entry.size)}{entry.total_items != null && ` · ${questionCount(entry.total_items)}`}</span></div></div></td><td className="date-cell">{date(entry.created_at)}</td><td><Badge status={entry.status} /></td><td><Link className="open-link" to={`/documentos/${entry.id}`}>Open</Link></td></tr>)}</tbody></table></div> : <div className="empty-state"><div className="empty-art" aria-hidden="true"><span /><span /><span /></div><h3>Your first questionnaire starts here</h3><p>Upload a PDF, Word, or Excel file to organize its questions and answer choices.</p><Link className="button" to="/documentos/subir">Upload my first document</Link></div>}
    {data.pages > 1 && <nav className="pagination" aria-label="Pages">{page > 1 && <Link to={`/?page=${page - 1}`}>Previous</Link>}<span>{page} of {data.pages}</span>{page < data.pages && <Link to={`/?page=${page + 1}`}>Next</Link>}</nav>}</section><p className="footnote">If you upload the same file again, we will retrieve your saved document.</p></>}
  </>;
}

export function UploadPage() {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [filename, setFilename] = useState('');
  const navigate = useNavigate();
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const body = new FormData(event.currentTarget);
    try { const data = await api('/documents', {method: 'POST', body}); navigate(`/documentos/${data.document.id}`, {state: {notice: data.created ? 'File saved. You can process it now.' : 'This file is already in your library. We retrieved the existing document.'}}); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <><Link className="breadcrumb" to="/">My documents / New document</Link><section className="page-heading"><div><span className="eyebrow">FROM FILE TO QUESTIONNAIRE</span><h1>One document.<br />All its content.</h1><p>Save your file to start extracting its questions.</p></div></section><div className="upload-layout"><section className="panel upload-card"><Notice>{error}</Notice><form onSubmit={submit} aria-busy={busy}><div className="upload-zone"><span className="upload-symbol" aria-hidden="true">+</span><label htmlFor="file">Choose your questionnaire file</label><p>PDF, DOCX, XLSX, or XLS</p><input id="file" name="file" type="file" accept=".pdf,.docx,.xlsx,.xls" required onChange={e => setFilename(e.target.files[0]?.name || '')} /><p className="selected-file" aria-live="polite">{filename}</p></div><div className="consent"><label><input name="public_content" type="checkbox" value="true" required /><span>I confirm that this material is fictional or in the public domain and contains no personal information.</span></label></div><button className="button full" disabled={busy}>{busy ? 'Saving file…' : 'Save document'}</button></form></section><aside className="upload-aside"><span className="eyebrow">HOW IT WORKS</span><h2>From file to results.</h2><div><h3>Save the original</h3><p>The file is saved to your account so you can access it later.</p></div><div><h3>Extract the questions</h3><p>When you start processing, Gemini will read the document and organize its questions.</p></div><div><h3>Come back anytime</h3><p>Review the questions and download the saved JSON from your library.</p></div><p className="aside-note">Content is sent to Google for processing. Only use fictional or public-domain material.</p></aside></div></>;
}

export function QuestionResults({result}) {
  return <><section aria-label="Extracted questions" className="questions">{result.items.map(item => <article className="panel question" key={item.numero}><div className="question-top"><span className="eyebrow">QUESTION {item.numero}</span><span className="type-label">{questionTypes[item.tipo] || 'Question'}</span></div><h3>{item.enunciado}</h3>{item.alternativas.length ? <ul className="alternatives">{item.alternativas.map(alt => <li key={`${typeof alt.valor}-${alt.valor}`}><span>{alt.valor}</span>{alt.texto}</li>)}</ul> : <p className="muted">Open-ended response</p>}{item.respuesta_correcta !== null && <p className="correct-answer">Answer provided in the document: <strong>{typeof item.respuesta_correcta === 'object' ? JSON.stringify(item.respuesta_correcta) : String(item.respuesta_correcta)}</strong></p>}</article>)}</section><details className="panel json-panel"><summary>View full JSON</summary><pre><code>{JSON.stringify(result, null, 2)}</code></pre></details></>;
}

export function DetailPage() {
  const {id} = useParams();
  const location = useLocation();
  const [entry, setEntry] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { const controller = new AbortController(); setEntry(null); setError(''); api(`/documents/${id}`, {signal: controller.signal}).then(setEntry).catch(e => { if (e.name !== 'AbortError') setError(e.message); }); return () => controller.abort(); }, [id]);
  async function refresh() { setError(''); try { setEntry(await api(`/documents/${id}`)); } catch (e) { setError(e.message); } }
  async function process() { setBusy(true); setError(''); try { setEntry(await api(`/documents/${id}/process`, {method: 'POST'})); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  return <><Link className="breadcrumb" to="/">My documents / Details</Link>{location.state?.notice && <div className="notice" role="status">{location.state.notice}</div>}<Notice>{error}</Notice>{!entry && !error && <p role="status">Loading document…</p>}{!entry && error && <button className="button secondary" onClick={refresh}>Try again</button>}{entry && <><section className="page-heading detail-heading"><div><span className="eyebrow">{entry.extension.slice(1).toUpperCase()} · {size(entry.size)}</span><h1>{entry.original_name}</h1><p>Saved on {date(entry.created_at)} <Badge status={entry.status} /></p></div><a className="button secondary" href={`/api/documents/${id}/original`}>Download original</a></section><Notice>{entry.error_message}</Notice>
  {entry.status === 'completed' && entry.result ? <><section className="panel result-heading"><div><span className="eyebrow">SAVED RESULTS</span><h2>{entry.result.titulo}</h2><p className="muted">{questionCount(entry.result.total_items)} · Language: {entry.result.idioma.toUpperCase()}</p></div><a className="button" href={`/api/documents/${id}/result`}>Download JSON</a></section><QuestionResults result={entry.result} /></> : entry.can_process ? <section className="panel process-card"><span className="eyebrow">YOUR ORIGINAL FILE IS SAVED</span><h2>Ready to extract questions</h2><p>We will identify the questions, question types, and answer choices. The results will be saved to your account.</p><button className="button" disabled={busy} onClick={process}>{busy ? 'Processing with Gemini…' : entry.status === 'uploaded' ? 'Process with Gemini' : 'Retry processing'}</button><p className="help">Continuing will send the content to Google. Processing may take up to two minutes.</p>{busy && <p role="status">We are reading your document. Keep this page open.</p>}</section> : <section className="panel process-card"><h2>We are reading your document</h2><p>Refresh the status in a moment. If processing was interrupted, you can try again after five minutes.</p><button className="button secondary" onClick={refresh}>Refresh status</button></section>}</>}</>;
}

export default function App() {
  const {loading, error, refresh} = useAuth();
  if (loading) return <main className="container"><p role="status">Loading your workspace…</p></main>;
  if (error) return <main className="container"><Notice>{error}</Notice><button className="button" onClick={refresh}>Retry connection</button></main>;
  return <Routes><Route element={<Layout />}><Route path="/cuenta/ingresar" element={<AuthPage key="login" mode="login" />} /><Route path="/cuenta/registro" element={<AuthPage key="register" mode="register" />} /><Route element={<Protected />}><Route index element={<Library />} /><Route path="/documentos/subir" element={<UploadPage />} /><Route path="/documentos/:id" element={<DetailPage />} /></Route><Route path="*" element={<><h1>Page not found</h1><Link to="/">Back to my documents</Link></>} /></Route></Routes>;
}
