let csrfToken = '';

export function setCsrfToken(value) { csrfToken = value || ''; }

export async function api(path, options = {}) {
  const {body, ...rest} = options;
  const headers = new Headers(rest.headers);
  const method = (rest.method || 'GET').toUpperCase();
  if (body !== undefined && !(body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (!['GET', 'HEAD'].includes(method) && csrfToken) headers.set('X-CSRF-Token', csrfToken);
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...rest, method, headers, credentials: 'same-origin',
      body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    if (cause.name === 'AbortError') throw cause;
    throw new Error('Unable to connect to the server. Check your connection and try again.');
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail) ? detail.map(e => `${e.loc.at(-1)}: ${e.msg}`).join(' · ') : detail;
    const error = new Error(message || 'Unable to complete the request.');
    error.status = response.status;
    if (response.status === 401 && !['/auth/login', '/auth/register', '/auth/me'].includes(path)) {
      window.dispatchEvent(new Event('session-expired'));
    }
    throw error;
  }
  return data;
}
