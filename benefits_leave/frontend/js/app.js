import { api } from './api.js';
import { navigation, routeFromHash, readEmployeePreference, saveEmployeePreference } from './state.js';
import { icon, escape, loadingView, notice, buttonLink, pageHeader } from './components.js';
import { employeeView } from './views/employee.js';
import { hrView } from './views/hr.js';

const state = { people: [], employeeId: readEmployeePreference(), data: null, menuOpen: false };
let loadVersion = 0;
const app = document.getElementById('app');
const main = () => document.getElementById('main');

function shell(route) {
  const person = state.people.find(item => item.id === state.employeeId);
  const identity = route.role === 'hr' ? 'HR specialist preview' : person?.name || 'Employee preview';
  const initials = route.role === 'hr' ? 'HR' : person?.id.slice(-2) || 'EE';
  const active = route.page === 'cases' ? route.role === 'hr' ? 'queue' : 'overview' : route.page;
  app.innerHTML = `<header class="topbar"><div class="actions"><button id="menu-toggle" class="mobile-menu" aria-label="Open navigation" aria-controls="sidebar" aria-expanded="false">${icon('menu')}</button><a class="brand" href="#/${route.role}/${navigation[route.role][0].id}"><span class="brandmark">${icon('shield')}</span><span>Benefits & Leave<small>Your workplace, simplified</small></span></a></div><div class="toptools"><div class="preview-toggle" role="group" aria-label="Demo workspace preview"><button data-preview="employee" aria-label="Employee preview" aria-pressed="${route.role === 'employee'}"><span class="desktop-label">Employee preview</span><span class="mobile-label" aria-hidden="true">Employee</span></button><button data-preview="hr" aria-label="HR preview" aria-pressed="${route.role === 'hr'}"><span class="desktop-label">HR preview</span><span class="mobile-label" aria-hidden="true">HR</span></button></div><div class="profile"><span class="avatar" aria-hidden="true">${escape(initials)}</span><div><b>${escape(identity)}</b><small>${route.role === 'hr' ? 'Demo review workspace' : escape(person?.id || 'Demo profile')}</small></div></div></div></header><aside class="sidebar" id="sidebar"><div class="nav-label">${route.role === 'hr' ? 'HR case center' : 'Personal workspace'}</div><nav class="nav-list" aria-label="${route.role === 'hr' ? 'HR' : 'Employee'} navigation">${navigation[route.role].map(item => `<a class="nav-link" href="#/${route.role}/${item.id}" ${active === item.id ? 'aria-current="page"' : ''}>${icon(item.icon)}${item.label}</a>`).join('')}</nav><div class="sidebar-bottom"><b>Built around clear next steps.</b><p>Computer checks. AI explains.<br>People make the decisions.</p><a href="/legacy" target="_blank" rel="noopener">Open existing workflow demo ${icon('external')}</a></div></aside><div class="main-wrap"><div class="contextbar"><span class="context-note">${icon('info')}Demo workspace · fictional records · no real sign-in</span>${route.role === 'employee' ? `<div class="context-picker"><label for="employee-picker">Demo profile</label><select id="employee-picker">${state.people.map(person => `<option value="${escape(person.id)}" ${person.id === state.employeeId ? 'selected' : ''}>${escape(person.id)} · ${escape(person.name)}</option>`).join('')}</select></div>` : `<span>Case store resets when the server restarts.</span>`}</div><main class="main" id="main" tabindex="-1" aria-busy="true">${loadingView()}</main></div>`;
  document.querySelectorAll('[data-preview]').forEach(button => button.onclick = () => {
    const role = button.dataset.preview;
    location.hash = `/${role}/${navigation[role][0].id}`;
  });
  document.getElementById('menu-toggle').onclick = () => {
    state.menuOpen = !state.menuOpen;
    document.getElementById('sidebar').classList.toggle('is-open', state.menuOpen);
    document.getElementById('menu-toggle').setAttribute('aria-expanded', String(state.menuOpen));
    document.getElementById('menu-toggle').setAttribute('aria-label', state.menuOpen ? 'Close navigation' : 'Open navigation');
  };
  document.getElementById('employee-picker')?.addEventListener('change', event => {
    state.employeeId = event.target.value;
    saveEmployeePreference(state.employeeId);
    if (route.page === 'cases') location.hash = '/employee/overview';
    else load();
  });
}

function bindView() {
  document.getElementById('leave-preview')?.addEventListener('submit', event => event.preventDefault());
  const rows = [...document.querySelectorAll('[data-case-row]')];
  let filter = 'all';
  const applyFilters = () => {
    const query = document.getElementById('case-search')?.value.trim().toLowerCase() || '';
    let visible = 0;
    rows.forEach(row => {
      const matchesFilter = filter === 'all' || (filter === 'review' ? ['incomplete', 'ready_for_hr_review', 'info_requested'].includes(row.dataset.status) : ['approved', 'vendor_records_ready', 'sent_to_vendors', 'vendor_follow_up', 'vendor_confirmed'].includes(row.dataset.status));
      const matches = matchesFilter && row.dataset.search.includes(query);
      row.hidden = !matches;
      if (matches) visible++;
    });
    const empty = document.getElementById('no-filter-results');
    if (empty) empty.hidden = visible !== 0;
  };
  document.querySelectorAll('[data-filter]').forEach(button => button.onclick = () => {
    filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(value => value.setAttribute('aria-pressed', String(value === button)));
    applyFilters();
  });
  document.getElementById('case-search')?.addEventListener('input', applyFilters);
  document.getElementById('retry-load')?.addEventListener('click', load);
}

async function load() {
  const version = ++loadVersion;
  const route = routeFromHash(location.hash);
  state.data = null;
  state.menuOpen = false;
  shell(route);
  try {
    if (!state.people.length) {
      const result = await api.people();
      if (version !== loadVersion) return;
      state.people = result.people;
      if (!state.people.some(person => person.id === state.employeeId)) state.employeeId = state.people[0]?.id || '';
      shell(route);
    }
    const data = route.role === 'employee' ? await api.overview(state.employeeId) : await api.queue();
    if (version !== loadVersion) return;
    state.data = { ...data, people: state.people };
    main().innerHTML = (route.role === 'employee' ? employeeView(route, state.data) : hrView(route, state.data))
      + `<footer class="footer"><span>Benefits & Leave · Interface foundation</span><span>Read-only views · <a href="/legacy" target="_blank" rel="noopener">Existing workflow demo ${icon('external')}</a></span></footer>`;
    const title = main().querySelector('h1')?.textContent || 'Workspace';
    document.title = `${title} · Benefits & Leave`;
  } catch (error) {
    if (version !== loadVersion) return;
    main().innerHTML = pageHeader('We couldn’t load this workspace', 'Your information has not been changed.') + notice(error.message, 'error') + `<div class="actions spaced"><button class="btn primary" id="retry-load">${icon('refresh')}Try again</button>${buttonLink('Open existing demo', '/legacy')}</div>`;
  } finally {
    if (version === loadVersion) {
      main().setAttribute('aria-busy', 'false');
      if (version > 1) main().focus({ preventScroll: true });
      bindView();
    }
  }
}

document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && state.menuOpen) {
    state.menuOpen = false;
    document.getElementById('sidebar')?.classList.remove('is-open');
    const button = document.getElementById('menu-toggle');
    button?.setAttribute('aria-expanded', 'false');
    button?.setAttribute('aria-label', 'Open navigation');
    button?.focus();
  }
});
document.querySelector('.skip-link').addEventListener('click', event => {
  event.preventDefault();
  main()?.focus();
});
window.addEventListener('hashchange', () => { window.scrollTo(0, 0); load(); });
load();
