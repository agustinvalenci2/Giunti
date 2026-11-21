import {useEffect, useState} from 'react';
import {Link, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams, useSearchParams} from 'react-router-dom';
import {api} from './api';
import {useAuth} from './auth';

const statuses = {uploaded: 'Sin procesar', processing: 'Procesando', completed: 'Completado', failed: 'Necesita atención'};
const date = value => new Date(value).toLocaleDateString('es-CO');
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
  return <><a className="skip-link" href="#main">Ir al contenido</a><header className="topbar">
    <Link className="brand" to="/"><span className="brand-mark" aria-hidden="true">c.</span>cuaderno<span className="brand-divider">/</span><span className="brand-caption">Cuestionarios</span></Link>
    <nav aria-label="Navegación principal">{user ? <><Link to="/">Mis documentos</Link><span className="user-name">{user.username}</span><button className="text-button" onClick={signOut} disabled={busy}>Salir</button></> : <><Link to="/cuenta/ingresar">Ingresar</Link><Link className="button small secondary" to="/cuenta/registro">Crear cuenta</Link></>}</nav>
  </header><main id="main" className="container"><Notice>{error}</Notice><Outlet /></main><footer className="footer"><span>Cuaderno</span><span>Del documento a las preguntas.</span></footer></>;
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
    if (register && form.get('password') !== form.get('confirm')) { setError('Las contraseñas no coinciden.'); return; }
    const values = {username: form.get('username'), password: form.get('password')};
    if (register) values.email = form.get('email');
    setBusy(true);
    try { await authenticate(mode, values); navigate(location.state?.from || '/', {replace: true}); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <div className="auth-layout"><section className="auth-intro"><span className="eyebrow">UN ESPACIO PARA TUS CUESTIONARIOS</span><h1>Menos transcripción.<br /><em>Más posibilidades.</em></h1><p>Convertí tus documentos en preguntas estructuradas y volvé a tus resultados cuando los necesites.</p><div className="format-row"><span>PDF</span><span>WORD</span><span>EXCEL</span></div></section>
    <section className="panel auth-card"><span className="eyebrow">{register ? 'EMPEZÁ ACÁ' : 'BIENVENIDO DE NUEVO'}</span><h2>{register ? 'Creá tu cuenta' : 'Ingresá a tu cuenta'}</h2><p className="muted">Tus documentos, en un solo lugar.</p><Notice>{error}</Notice><form onSubmit={submit} aria-busy={busy}>
      <div className="field"><label htmlFor="username">Usuario</label><input id="username" name="username" autoComplete="username" required maxLength={150} /></div>
      {register && <div className="field"><label htmlFor="email">Correo electrónico</label><input id="email" name="email" type="email" autoComplete="email" required maxLength={254} /></div>}
      <div className="field"><label htmlFor="password">Contraseña</label><input id="password" name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={register ? 10 : 1} maxLength={256} />{register && <p className="help">Usá al menos 10 caracteres y evitá contraseñas predecibles.</p>}</div>
      {register && <div className="field"><label htmlFor="confirm">Repetir contraseña</label><input id="confirm" name="confirm" type="password" autoComplete="new-password" required maxLength={256} /></div>}
      <button className="button full" disabled={busy}>{busy ? 'Un momento…' : register ? 'Crear cuenta' : 'Ingresar'}</button>
    </form><p className="auth-switch">{register ? '¿Ya tenés cuenta? ' : '¿Primera vez? '}<Link to={register ? '/cuenta/ingresar' : '/cuenta/registro'}>{register ? 'Ingresá' : 'Creá una cuenta'}</Link></p></section></div>;
}

function Library() {
  const [params] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => { const controller = new AbortController(); setData(null); setError(''); api(`/documents?page=${page}`, {signal: controller.signal}).then(setData).catch(e => { if (e.name !== 'AbortError') setError(e.message); }); return () => controller.abort(); }, [page, retry]);
  return <><section className="page-heading"><div><span className="eyebrow">TU ESPACIO DE TRABAJO</span><h1>Mis documentos</h1><p>Subí un cuestionario. Recuperá sus preguntas. Conservá el resultado.</p></div><Link className="button" to="/documentos/subir">Subir documento</Link></section><Notice>{error}</Notice>{error && <button className="button secondary" onClick={() => setRetry(v => v + 1)}>Reintentar</button>}
    {!data && !error && <p role="status">Cargando tu biblioteca…</p>}
    {data && <><section className="stats" aria-label="Resumen de documentos">{[['Documentos guardados', data.stats.total], ['Resultados listos', data.stats.completed], ['Por completar', data.stats.pending]].map(([label, count]) => <div key={label}><span>{label}</span><strong>{count}</strong></div>)}</section>
    <section className="panel library"><div className="section-heading"><h2>Tu biblioteca</h2><span className="muted">Solo visible para vos</span></div>{data.items.length ? <div className="table-wrap"><table><thead><tr><th>Documento</th><th>Guardado</th><th>Estado</th><th><span className="sr-only">Abrir documento</span></th></tr></thead><tbody>{data.items.map(entry => <tr key={entry.id}><td><div className="document-cell"><span className="file-icon">{entry.extension.slice(1).toUpperCase()}</span><div><Link className="document-name" to={`/documentos/${entry.id}`}>{entry.original_name}</Link><span className="metadata">{size(entry.size)}{entry.total_items != null && ` · ${entry.total_items} preguntas`}</span></div></div></td><td className="date-cell">{date(entry.created_at)}</td><td><Badge status={entry.status} /></td><td><Link className="open-link" to={`/documentos/${entry.id}`}>Abrir</Link></td></tr>)}</tbody></table></div> : <div className="empty-state"><div className="empty-art" aria-hidden="true"><span /><span /><span /></div><h3>Tu primer cuestionario empieza acá</h3><p>Adjuntá un PDF, Word o Excel para organizar sus preguntas y alternativas.</p><Link className="button" to="/documentos/subir">Subir mi primer documento</Link></div>}
    {data.pages > 1 && <nav className="pagination" aria-label="Páginas">{page > 1 && <Link to={`/?page=${page - 1}`}>Anterior</Link>}<span>{page} de {data.pages}</span>{page < data.pages && <Link to={`/?page=${page + 1}`}>Siguiente</Link>}</nav>}</section><p className="footnote">Si volvés a subir el mismo archivo, recuperamos el registro que ya guardaste.</p></>}
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
    try { const data = await api('/documents', {method: 'POST', body}); navigate(`/documentos/${data.document.id}`, {state: {notice: data.created ? 'Archivo guardado. Ya podés procesarlo.' : 'Este archivo ya está en tu historial. Recuperamos el registro existente.'}}); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <><Link className="breadcrumb" to="/">Mis documentos / Nuevo documento</Link><section className="page-heading"><div><span className="eyebrow">DE ARCHIVO A CUESTIONARIO</span><h1>Un documento.<br />Todo su contenido.</h1><p>Guardá tu archivo para empezar a extraer las preguntas.</p></div></section><div className="upload-layout"><section className="panel upload-card"><Notice>{error}</Notice><form onSubmit={submit} aria-busy={busy}><div className="upload-zone"><span className="upload-symbol" aria-hidden="true">+</span><label htmlFor="file">Elegí el archivo de tu cuestionario</label><p>PDF, DOCX, XLSX o XLS</p><input id="file" name="file" type="file" accept=".pdf,.docx,.xlsx,.xls" required onChange={e => setFilename(e.target.files[0]?.name || '')} /><p className="selected-file" aria-live="polite">{filename}</p></div><div className="consent"><label><input name="public_content" type="checkbox" value="true" required /><span>Confirmo que es material inventado o de dominio público y no contiene datos personales.</span></label></div><button className="button full" disabled={busy}>{busy ? 'Guardando archivo…' : 'Guardar documento'}</button></form></section><aside className="upload-aside"><span className="eyebrow">CÓMO FUNCIONA</span><h2>Del archivo al resultado.</h2><div><h3>Guardá el original</h3><p>El archivo queda asociado a tu cuenta para consultarlo después.</p></div><div><h3>Extraé las preguntas</h3><p>Cuando inicies el procesamiento, Gemini leerá el documento y organizará sus ítems.</p></div><div><h3>Volvé cuando quieras</h3><p>Revisá las preguntas y descargá el JSON guardado desde tu biblioteca.</p></div><p className="aside-note">El contenido se envía a Google al procesarlo. Usá únicamente material inventado o de dominio público.</p></aside></div></>;
}

export function QuestionResults({result}) {
  return <><section aria-label="Preguntas extraídas" className="questions">{result.items.map(item => <article className="panel question" key={item.numero}><div className="question-top"><span className="eyebrow">PREGUNTA {item.numero}</span><span className="type-label">{item.tipo.replaceAll('_', ' ')}</span></div><h3>{item.enunciado}</h3>{item.alternativas.length ? <ul className="alternatives">{item.alternativas.map(alt => <li key={`${typeof alt.valor}-${alt.valor}`}><span>{alt.valor}</span>{alt.texto}</li>)}</ul> : <p className="muted">Respuesta abierta</p>}{item.respuesta_correcta !== null && <p className="correct-answer">Respuesta indicada en el documento: <strong>{typeof item.respuesta_correcta === 'object' ? JSON.stringify(item.respuesta_correcta) : String(item.respuesta_correcta)}</strong></p>}</article>)}</section><details className="panel json-panel"><summary>Ver JSON completo</summary><pre><code>{JSON.stringify(result, null, 2)}</code></pre></details></>;
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
  return <><Link className="breadcrumb" to="/">Mis documentos / Detalle</Link>{location.state?.notice && <div className="notice" role="status">{location.state.notice}</div>}<Notice>{error}</Notice>{!entry && !error && <p role="status">Cargando documento…</p>}{!entry && error && <button className="button secondary" onClick={refresh}>Reintentar</button>}{entry && <><section className="page-heading detail-heading"><div><span className="eyebrow">{entry.extension.slice(1).toUpperCase()} · {size(entry.size)}</span><h1>{entry.original_name}</h1><p>Guardado el {date(entry.created_at)} <Badge status={entry.status} /></p></div><a className="button secondary" href={`/api/documents/${id}/original`}>Descargar original</a></section><Notice>{entry.error_message}</Notice>
  {entry.status === 'completed' && entry.result ? <><section className="panel result-heading"><div><span className="eyebrow">RESULTADO GUARDADO</span><h2>{entry.result.titulo}</h2><p className="muted">{entry.result.total_items} preguntas · Idioma: {entry.result.idioma.toUpperCase()}</p></div><a className="button" href={`/api/documents/${id}/result`}>Descargar JSON</a></section><QuestionResults result={entry.result} /></> : entry.can_process ? <section className="panel process-card"><span className="eyebrow">EL ORIGINAL YA ESTÁ GUARDADO</span><h2>Listo para extraer las preguntas</h2><p>Identificaremos los enunciados, tipos de pregunta y alternativas. El resultado quedará guardado en tu cuenta.</p><button className="button" disabled={busy} onClick={process}>{busy ? 'Procesando con Gemini…' : entry.status === 'uploaded' ? 'Procesar con Gemini' : 'Reintentar procesamiento'}</button><p className="help">Al continuar, el contenido se enviará a Google. Puede demorar hasta dos minutos.</p>{busy && <p role="status">Estamos leyendo tu documento. Mantené esta página abierta.</p>}</section> : <section className="panel process-card"><h2>Estamos leyendo tu documento</h2><p>Actualizá el estado en unos instantes. Si el proceso se interrumpió, podrás reintentarlo después de cinco minutos.</p><button className="button secondary" onClick={refresh}>Actualizar estado</button></section>}</>}</>;
}

export default function App() {
  const {loading, error, refresh} = useAuth();
  if (loading) return <main className="container"><p role="status">Abriendo tu espacio…</p></main>;
  if (error) return <main className="container"><Notice>{error}</Notice><button className="button" onClick={refresh}>Reintentar conexión</button></main>;
  return <Routes><Route element={<Layout />}><Route path="/cuenta/ingresar" element={<AuthPage key="login" mode="login" />} /><Route path="/cuenta/registro" element={<AuthPage key="register" mode="register" />} /><Route element={<Protected />}><Route index element={<Library />} /><Route path="/documentos/subir" element={<UploadPage />} /><Route path="/documentos/:id" element={<DetailPage />} /></Route><Route path="*" element={<><h1>Página no encontrada</h1><Link to="/">Volver a mis documentos</Link></>} /></Route></Routes>;
}
