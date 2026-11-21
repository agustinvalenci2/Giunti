import {describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {AuthPage, DetailPage, QuestionResults, UploadPage} from './App';
import {api} from './api';

vi.mock('./api', () => ({api: vi.fn()}));
const authenticate = vi.fn();
vi.mock('./auth', () => ({useAuth: () => ({user: null, authenticate})}));

function wrapper(component, route = '/') {
  return render(<MemoryRouter initialEntries={[route]} future={{v7_startTransition: true, v7_relativeSplatPath: true}}>{component}</MemoryRouter>);
}

describe('questionnaires', () => {
  it('escapes document text and displays zero-valued correct answers', () => {
    const result = {titulo: 'Prueba', idioma: 'es', total_items: 1, items: [{numero: 1, tipo: 'escala_likert', enunciado: '<script>alert(1)</script>', alternativas: [{valor: 0, texto: 'Nunca'}], respuesta_correcta: 0}]};
    const {container} = render(<QuestionResults result={result} />);
    expect(screen.getByRole('heading', {name: '<script>alert(1)</script>'})).toBeInTheDocument();
    expect(container.querySelector('script')).toBeNull();
    expect(screen.getByText('Likert scale')).toBeInTheDocument();
    expect(screen.getByText('Nunca')).toBeInTheDocument();
    expect(screen.getByText('Answer provided in the document:')).toHaveTextContent('0');
  });

  it('shows authentication failure and enables a retry', async () => {
    authenticate.mockRejectedValueOnce(new Error('The username or password is incorrect.'));
    wrapper(<AuthPage mode="login" />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Username'), 'ana');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getByRole('button', {name: 'Sign in'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('is incorrect');
    expect(screen.getByRole('button', {name: 'Sign in'})).toBeEnabled();
  });

  it('rejects mismatching registration passwords before calling the API', async () => {
    authenticate.mockClear();
    wrapper(<AuthPage mode="register" />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Username'), 'ana');
    await user.type(screen.getByLabelText('Email address'), 'a@example.com');
    await user.type(screen.getByLabelText('Password', {exact: true}), 'Example-734!');
    await user.type(screen.getByLabelText('Confirm password'), 'Mismatch-321!');
    await user.click(screen.getByRole('button', {name: 'Create account'}));
    expect(screen.getByRole('alert')).toHaveTextContent('do not match');
    expect(authenticate).not.toHaveBeenCalled();
  });

  it('uploads as multipart and shows server validation errors', async () => {
    api.mockRejectedValueOnce(new Error('The file contents are not a valid PDF.'));
    wrapper(<UploadPage />);
    const user = userEvent.setup();
    await user.upload(screen.getByLabelText('Choose your questionnaire file'), new File(['broken'], 'test.pdf', {type: 'application/pdf'}));
    await user.click(screen.getByRole('checkbox'));
    // JSDOM marks uploaded file inputs valueMissing even when user-event sets files.
    expect(screen.getByLabelText(/Choose your questionnaire file/).files).toHaveLength(1);
    fireEvent.submit(screen.getByRole('button', {name: 'Save document'}).closest('form'));
    expect(await screen.findByRole('alert')).toHaveTextContent('not a valid PDF');
    expect(api.mock.calls.at(-1)[1].body).toBeInstanceOf(FormData);
  });

  it('shows progress, prevents duplicate clicks and renders the saved result', async () => {
    let complete;
    const entry = {id: 'abc', original_name: 'prueba.pdf', extension: '.pdf', size: 1024, status: 'uploaded', can_process: true, created_at: '2026-01-01T00:00:00Z'};
    api.mockResolvedValueOnce(entry).mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }));
    wrapper(<Routes><Route path="/documentos/:id" element={<DetailPage />} /></Routes>, '/documentos/abc');
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', {name: 'Process with Gemini'}));
    expect(screen.getByRole('button', {name: 'Processing with Gemini…'})).toBeDisabled();
    complete({...entry, status: 'completed', can_process: false, result: {titulo: 'Resultado', idioma: 'es', total_items: 1, items: [{numero: 1, tipo: 'desarrollo', enunciado: 'Describa una actividad.', alternativas: [], respuesta_correcta: null}]}});
    expect(await screen.findByRole('link', {name: 'Download JSON'})).toHaveAttribute('href', '/api/documents/abc/result');
    expect(screen.getByText('Open-ended')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('button', {name: 'Process with Gemini'})).not.toBeInTheDocument());
  });
});
