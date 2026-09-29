import DOMPurify from 'dompurify';
import { marked } from 'marked';

export const apiBase = (import.meta.env.PUBLIC_API_BASE_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000/api/v1' : '')).replace(/\/$/, '');
export const tr = (zh: string, en: string) => document.documentElement.dataset.language === 'en' ? en : zh;
export type Reader = { name: string; email: string; active: boolean; articles: boolean; discussions: boolean; replies: boolean; language: string };
const key = 'articles-reader';
export function identity(): {token: string; subscriber: Reader} | null {
  try { const value = JSON.parse(localStorage.getItem(key) || 'null'); return value?.token && value?.subscriber ? value : null; } catch { return null; }
}
export function remember(value: ReturnType<typeof identity>) {
  if (value) localStorage.setItem(key, JSON.stringify(value)); else localStorage.removeItem(key);
  window.dispatchEvent(new Event('readerchange'));
}
export async function request(path: string, method = 'GET', data?: unknown, authenticated = false) {
  if (!apiBase) throw new Error(tr('服务暂时不可用。', 'Service unavailable.'));
  const headers: Record<string, string> = {Accept: 'application/json'};
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  if (authenticated && identity()) headers.Authorization = `Bearer ${identity()!.token}`;
  const response = await fetch(`${apiBase}${path}`, {method, headers, cache: 'no-store', body: data === undefined ? undefined : JSON.stringify(data)});
  if (!response.ok) {
    if (authenticated && [401, 403].includes(response.status)) {
      remember(null);
      throw new Error(tr('登录已过期。请通过右上角订阅入口重新验证邮箱，或以游客身份重试。', 'Sign-in expired. Verify your email again via Subscribe, or retry as a guest.'));
    }
    if (response.status === 429) throw new Error(tr('操作太频繁，请稍后再试。', 'Too many requests. Please try again later.'));
    if (response.status === 503) throw new Error(tr('邮件服务暂未就绪，请稍后重试。', 'Email service is not ready. Please try again later.'));
    if (response.status === 404) throw new Error(tr('内容不存在或已被隐藏。', 'Content is unavailable or hidden.'));
    throw new Error(tr('未能完成操作，请检查输入或刷新重试。', 'Could not complete the request. Check your input or refresh and retry.'));
  }
  return response.status === 204 ? null : response.json();
}
export function markdown(source: string) {
  return DOMPurify.sanitize(marked.parse(source, {async: false, gfm: true, breaks: true}) as string, {
    USE_PROFILES: {html: true}, FORBID_TAGS: ['style', 'iframe', 'form', 'input', 'button', 'textarea'], FORBID_ATTR: ['style'],
  });
}
export function renderMarkdown(element: HTMLElement, source: string) {
  element.innerHTML = markdown(source);
  element.querySelectorAll<HTMLAnchorElement>('a[href]').forEach(link => {
    const url = new URL(link.href, location.href);
    if (url.origin === location.origin && /^\/blog\/article\/?$/.test(url.pathname)) {
      url.pathname = '/articles/article/'; link.href = url.toString();
    }
    if (url.origin !== location.origin) { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
  });
  element.querySelectorAll('img').forEach(image => { image.loading = 'lazy'; image.referrerPolicy = 'no-referrer'; });
}
export function fillIdentity(form: HTMLFormElement) {
  const input = form.elements.namedItem('author') as HTMLInputElement | null;
  if (!input) return;
  const user = identity();
  input.readOnly = !!user;
  if (user) { input.value = user.subscriber.name; input.dataset.reader = 'true'; }
  else if (input.dataset.reader) { input.value = ''; delete input.dataset.reader; }
}
export function formatDate(value: string) {
  return new Intl.DateTimeFormat(tr('zh-CN', 'en-US'), {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value));
}
export async function readPages(endpoint: string, pages: number) {
  const rows: any[] = [];
  let more = false;
  for (let page = 1; page <= pages; page++) {
    const payload = await request(`${endpoint}${endpoint.includes('?') ? '&' : '?'}page=${page}`);
    rows.push(...payload.results); more = !!payload.next;
    if (!more) break;
  }
  return {rows, more};
}
