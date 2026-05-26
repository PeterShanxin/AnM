// AnM SPA — renders Variant B home + Variant A in-tool chrome.
// State lives in a single ``state`` object.  Re-render on change.

'use strict';

// --------------------------------------------------------------------- //
// State
// --------------------------------------------------------------------- //

const state = {
  view: 'home',          // 'home' | 'tool'
  toolId: null,          // active tool id when view === 'tool'
  activeCat: 'organize', // active category in Variant A rail
  pdf: null,             // { path, name, page_count, size_bytes } — single-PDF tools
  outputDir: null,       // string
  selectedPages: new Set(),   // 0-based page indices
  thumbCache: {},        // { [index]: dataUri }
  options: {},           // per-tool option state (keyed by tool id)
  running: false,
  // Merge-only state — multi-file tool needs its own shape.
  merge: {
    files: [],           // [{ path, name, page_count, size_bytes }]
    annotation: {
      text_template: '{filename}',
      position: 'top-center',
      font_size: 12,
      margin: 24,
      box_opacity: 0.5,
    },
    run: {
      output_filename: 'annotated-merged.pdf',
      save_intermediate: false,
      open_folder: false,
      overwrite: true,
    },
    dragIndex: null,     // index of row currently being dragged
  },
  recents: [             // placeholder until persisted-recents lands
    { name: 'Quarterly-Report.pdf', tool: 'Split',    when: '2h ago' },
    { name: 'Invoice-104.pdf',      tool: 'Annotate', when: 'Yesterday' },
    { name: 'Scan_2026-05.pdf',     tool: 'OCR',      when: 'Yesterday' },
    { name: 'Contract_v3.pdf',      tool: 'Compare',  when: '3 days ago' },
  ],
  dark: false,
};

const POSITIONS = [
  'top-left', 'top-center', 'top-right',
  'bottom-left', 'bottom-center', 'bottom-right',
];

// --------------------------------------------------------------------- //
// pywebview API wrapper — waits for the bridge to be ready
// --------------------------------------------------------------------- //

let _apiReady = null;

function apiReady() {
  if (_apiReady) return _apiReady;
  _apiReady = new Promise((resolve) => {
    if (window.pywebview && window.pywebview.api) return resolve(window.pywebview.api);
    window.addEventListener('pywebviewready', () => resolve(window.pywebview.api), { once: true });
  });
  return _apiReady;
}

async function api(method, ...args) {
  const a = await apiReady();
  const fn = a[method];
  if (typeof fn !== 'function') throw new Error(`No such API method: ${method}`);
  const result = await fn(...args);
  if (!result || result.ok !== true) {
    const msg = (result && result.error) || 'Unknown error';
    throw new Error(msg);
  }
  return result.data;
}

// --------------------------------------------------------------------- //
// Toast (status + errors)
// --------------------------------------------------------------------- //

function toast(message, { error = false, duration = 2800 } = {}) {
  let el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.toggle('error', !!error);
  el.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.classList.remove('show'), duration);
}

// --------------------------------------------------------------------- //
// Render entrypoint
// --------------------------------------------------------------------- //

function render() {
  const root = document.getElementById('root');
  root.innerHTML = `<div class="anm-window ${state.dark ? 'anm-dark' : ''}">
    <div class="view">${state.view === 'home' ? renderHome() : renderTool()}</div>
  </div>`;
  if (state.view === 'home') bindHome();
  else bindTool();
}

// --------------------------------------------------------------------- //
// Home (Variant B)
// --------------------------------------------------------------------- //

function renderHome() {
  return `
    <div style="flex:1;overflow:auto;background:var(--anm-bg)" class="scroll">
      ${renderTopBar()}
      <div style="padding:28px 32px 36px">
        ${renderContinue()}
        ${CATEGORIES.map(renderCategorySection).join('')}
      </div>
    </div>
  `;
}

function renderTopBar() {
  return `
    <div style="height:64px;padding:0 32px;display:flex;align-items:center;gap:16px;border-bottom:1px solid var(--anm-border);background:var(--anm-surface)">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="anm-titlebar-logo" style="width:24px;height:24px;border-radius:5px;font-size:13px;letter-spacing:-0.4px">A</div>
        <div style="font-size:18px;font-weight:600;letter-spacing:-0.2px">AnM</div>
      </div>
      <div id="searchbar" style="flex:1;max-width:460px;height:36px;padding:0 12px;border-radius:8px;border:1px solid var(--anm-border);background:var(--anm-surface-2);display:flex;align-items:center;gap:8px;color:var(--anm-text-subtle);cursor:text">
        ${icon('search', 16)}
        <span style="font-size:13px">Search tools and files…</span>
        <span style="flex:1"></span>
        <span class="anm-kbd">Ctrl K</span>
      </div>
      <button data-act="open" class="anm-btn">${icon('open', 14)} Open</button>
      <button data-act="theme" class="anm-btn anm-btn-ghost" title="Toggle theme">${icon(state.dark ? 'sun' : 'moon', 14)}</button>
      <button data-act="settings" class="anm-btn anm-btn-ghost">${icon('settings', 14)}</button>
    </div>
  `;
}

function renderContinue() {
  return `
    <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:12px">
      <div style="font-size:13px;font-weight:600;color:var(--anm-text-muted);text-transform:uppercase;letter-spacing:0.6px">Continue</div>
      <div style="font-size:12px;color:var(--anm-text-subtle);cursor:pointer">View all recent</div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px">
      ${state.recents.map(r => `
        <div class="anm-card clickable" style="padding:12px;display:flex;gap:10px;align-items:center">
          <div class="anm-page-thumb" style="width:36px;height:48px">
            <div class="lines"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
          </div>
          <div style="min-width:0;flex:1">
            <div style="font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(r.name)}</div>
            <div style="font-size:11px;color:var(--anm-text-subtle);display:flex;align-items:center;gap:4px">
              ${icon((getTool(r.tool.toLowerCase()) || {}).id || 'file', 10)} ${escapeHtml(r.tool)} · ${escapeHtml(r.when)}
            </div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderCategorySection(cat) {
  const tools = toolsByCat(cat.id);
  return `
    <div style="margin-bottom:22px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
        <div style="width:8px;height:8px;border-radius:50%;background:${cat.accent}"></div>
        <div style="font-size:13px;font-weight:600;color:var(--anm-text-muted);text-transform:uppercase;letter-spacing:0.6px">${escapeHtml(cat.label)}</div>
        <div style="flex:1;height:1px;background:var(--anm-border)"></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">
        ${tools.map(t => renderToolCard(t, cat)).join('')}
      </div>
    </div>
  `;
}

function renderToolCard(tool, cat) {
  const wiredAttr = tool.wired ? '' : 'title="Coming soon"';
  const opacity = tool.wired ? '' : 'opacity:0.55;';
  return `
    <div class="anm-card clickable" data-tool="${tool.id}" ${wiredAttr}
         style="padding:14px;display:flex;flex-direction:column;gap:8px;min-height:96px;${opacity}">
      <div style="width:32px;height:32px;border-radius:8px;background:${cat.accent}22;color:${cat.accent};display:flex;align-items:center;justify-content:center">
        ${icon(tool.id, 18)}
      </div>
      <div style="font-size:13px;font-weight:600">${escapeHtml(tool.label)}</div>
      <div style="font-size:11px;color:var(--anm-text-muted);line-height:1.4">${escapeHtml(tool.desc)}</div>
    </div>
  `;
}

function bindHome() {
  document.querySelectorAll('[data-tool]').forEach(el => {
    el.addEventListener('click', () => {
      const id = el.getAttribute('data-tool');
      const tool = getTool(id);
      if (!tool || !tool.wired) {
        toast(`${tool ? tool.label : id} is not wired yet.`);
        return;
      }
      enterTool(id);
    });
  });
  document.querySelector('[data-act="open"]')?.addEventListener('click', openPdfDialog);
  document.querySelector('[data-act="theme"]')?.addEventListener('click', toggleTheme);
  document.querySelector('[data-act="settings"]')?.addEventListener('click', () => toast('Settings — not implemented yet.'));
}

// --------------------------------------------------------------------- //
// Tool view (Variant A)
// --------------------------------------------------------------------- //

function renderTool() {
  const tool = getTool(state.toolId);
  if (!tool) return `<div style="padding:40px">Unknown tool: ${escapeHtml(state.toolId || '')}</div>`;
  return `
    <div style="flex:1;display:flex;min-height:0">
      ${renderRail(tool)}
      ${renderSidebar(tool)}
      ${renderToolMain(tool)}
    </div>
  `;
}

function renderRail(tool) {
  const railItem = (iconName, label, active, dataAct) => `
    <div class="rail-item" data-act="${dataAct}" title="${escapeHtml(label)}" style="
      width:40px;height:40px;border-radius:6px;display:flex;align-items:center;justify-content:center;
      color:${active ? 'var(--anm-accent)' : 'var(--anm-text-muted)'};
      background:${active ? 'var(--anm-surface-3)' : 'transparent'};
      position:relative;cursor:pointer">
      ${icon(iconName, 20)}
      ${active ? '<div style="position:absolute;left:-4px;top:8px;bottom:8px;width:3px;border-radius:2px;background:var(--anm-accent)"></div>' : ''}
    </div>
  `;
  const cats = CATEGORIES.map(c =>
    railItem(c.icon, c.label, state.activeCat === c.id, `cat:${c.id}`)
  ).join('');
  return `
    <div style="width:56px;background:var(--anm-surface-2);border-right:1px solid var(--anm-border);display:flex;flex-direction:column;align-items:center;padding:8px 0;gap:4px;flex-shrink:0">
      ${railItem('home', 'Home', false, 'home')}
      <div style="height:1px;width:28px;background:var(--anm-border);margin:6px 0"></div>
      ${cats}
      <div style="flex:1"></div>
      ${railItem('search', 'Search', false, 'search')}
      ${railItem('settings', 'Settings', false, 'settings')}
    </div>
  `;
}

function renderSidebar(tool) {
  const cat = CATEGORIES.find(c => c.id === state.activeCat) || CATEGORIES[0];
  const sidebarItem = (t, active) => `
    <div class="side-tool" data-tool="${t.id}" style="
      display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:5px;cursor:pointer;
      background:${active ? 'var(--anm-accent-soft)' : 'transparent'};
      color:var(--anm-text);font-weight:${active ? 600 : 400}">
      <span style="color:${active ? 'var(--anm-accent)' : 'var(--anm-text-muted)'}">${icon(t.id, 16)}</span>
      <span style="flex:1;font-size:13px">${escapeHtml(t.label)}</span>
    </div>
  `;
  const pinned = ['merge', 'split', 'annotate'].map(getTool).filter(Boolean);
  return `
    <div style="width:232px;background:var(--anm-surface);border-right:1px solid var(--anm-border);display:flex;flex-direction:column;min-height:0;flex-shrink:0">
      <div style="padding:14px 14px 6px;display:flex;align-items:center;justify-content:space-between">
        <div style="font-size:13px;font-weight:600">${escapeHtml(cat.label)}</div>
        <span style="color:var(--anm-text-subtle)">${icon('search', 14)}</span>
      </div>
      <div class="scroll" style="padding:0 8px;flex:1;overflow:auto">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.6px;color:var(--anm-text-subtle);padding:8px 6px 4px;font-weight:600">Pinned</div>
        ${pinned.map(t => sidebarItem(t, t.id === state.toolId)).join('')}
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.6px;color:var(--anm-text-subtle);padding:12px 6px 4px;font-weight:600">All ${escapeHtml(cat.label.toLowerCase())}</div>
        ${toolsByCat(cat.id).map(t => sidebarItem(t, t.id === state.toolId)).join('')}
      </div>
      <div style="padding:10px;border-top:1px solid var(--anm-border);display:flex;align-items:center;gap:8px;color:var(--anm-text-muted);font-size:12px">
        ${icon('history', 14)} Recent files
      </div>
    </div>
  `;
}

function renderToolMain(tool) {
  return `
    <div style="flex:1;display:flex;flex-direction:column;min-width:0;background:var(--anm-bg)">
      ${renderToolHeader(tool)}
      <div style="flex:1;display:flex;min-height:0">
        ${renderToolBody(tool)}
      </div>
    </div>
  `;
}

function renderToolHeader(tool) {
  const isMerge = tool.id === 'merge';
  const hasInput = isMerge ? state.merge.files.length > 0 : !!state.pdf;
  const runDisabled = state.running || !hasInput;
  const openLabel = isMerge ? 'Add files' : 'Open file';
  const openAct = isMerge ? 'add-files' : 'open';
  return `
    <div style="height:56px;padding:0 24px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--anm-border);background:var(--anm-surface)">
      <div style="width:32px;height:32px;border-radius:7px;background:var(--anm-accent-soft);color:var(--anm-accent);display:flex;align-items:center;justify-content:center">
        ${icon(tool.id, 18)}
      </div>
      <div style="flex:1">
        <div style="font-size:15px;font-weight:600">${escapeHtml(tool.label)}</div>
        <div style="font-size:12px;color:var(--anm-text-muted)">${escapeHtml(tool.desc)}</div>
      </div>
      <button data-act="${openAct}" class="anm-btn">${icon('open', 14)} ${openLabel}</button>
      <button data-act="run" class="anm-btn anm-btn-primary" ${runDisabled ? 'disabled style="opacity:0.55;cursor:not-allowed"' : ''}>
        ${state.running ? '<span class="spinner"></span>' : icon(tool.id, 14)} ${state.running ? 'Running…' : tool.label}
      </button>
    </div>
  `;
}

function renderToolBody(tool) {
  if (tool.id === 'merge') {
    return `
      <div class="scroll" style="flex:1;padding:20px;overflow:auto">
        ${renderMergeFileList()}
      </div>
      <div class="scroll" style="width:280px;background:var(--anm-surface);border-left:1px solid var(--anm-border);padding:18px;display:flex;flex-direction:column;gap:14px;overflow:auto">
        ${mergeInspector()}
      </div>
    `;
  }
  return `
    <div class="scroll" style="flex:1;padding:20px;overflow:auto" id="page-grid-host">
      ${renderPdfHeader()}
      ${renderPageGrid()}
    </div>
    <div class="scroll" style="width:280px;background:var(--anm-surface);border-left:1px solid var(--anm-border);padding:18px;display:flex;flex-direction:column;gap:14px;overflow:auto">
      ${renderInspector(tool)}
    </div>
  `;
}

// ----- Merge body (multi-file list) ----- //

function renderMergeFileList() {
  const files = state.merge.files;
  if (!files.length) {
    return `
      <div style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--anm-text-muted);text-align:center;padding:40px">
        <div style="font-size:48px;color:var(--anm-border-strong);margin-bottom:16px">${icon('merge', 48)}</div>
        <div style="font-size:15px;font-weight:500;margin-bottom:6px;color:var(--anm-text)">No files yet</div>
        <div style="font-size:13px;margin-bottom:20px">Add PDFs to merge. Drag rows to reorder.</div>
        <button data-act="add-files" class="anm-btn anm-btn-primary">${icon('open', 14)} Add files</button>
      </div>
    `;
  }
  const rows = files.map((f, i) => `
    <div class="merge-row" draggable="true" data-mrow="${i}"
         style="display:flex;align-items:center;gap:12px;padding:10px 12px;background:var(--anm-surface);border:1px solid var(--anm-border);border-radius:var(--anm-radius);cursor:grab">
      <div style="color:var(--anm-text-subtle);font-size:12px;width:18px;text-align:right">${i + 1}</div>
      <div class="anm-page-thumb" style="width:28px;height:36px;flex-shrink:0"><div class="lines"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div>
      <div style="flex:1;min-width:0">
        <div style="font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(f.name)}</div>
        <div style="font-size:11px;color:var(--anm-text-subtle)">${f.page_count} pages · ${formatBytes(f.size_bytes)}</div>
      </div>
      <button class="anm-btn anm-btn-ghost" data-mremove="${i}" title="Remove" style="padding:0 8px">${icon('close', 14)}</button>
    </div>
  `).join('');
  const total = files.reduce((sum, f) => sum + (f.page_count || 0), 0);
  const totalBytes = files.reduce((sum, f) => sum + (f.size_bytes || 0), 0);
  return `
    <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--anm-text-muted);margin-bottom:12px">
      ${icon('file', 14)}
      <span style="color:var(--anm-text);font-weight:500">${files.length} file(s)</span>
      <span>· ${total} pages · ${formatBytes(totalBytes)}</span>
      <span style="flex:1"></span>
      <button data-act="add-files" class="anm-btn anm-btn-ghost" style="padding:0 8px">${icon('plus', 14)} Add more</button>
      <button data-act="clear-files" class="anm-btn anm-btn-ghost" style="padding:0 8px">${icon('close', 14)} Clear</button>
    </div>
    <div id="merge-list" style="display:flex;flex-direction:column;gap:6px">${rows}</div>
  `;
}

// ----- Merge inspector (annotation + run options) ----- //

function mergeInspector() {
  const a = state.merge.annotation;
  const r = state.merge.run;
  const posButtons = POSITIONS.map(p => `
    <button class="anm-btn ${a.position === p ? 'anm-btn-primary' : ''}" data-mpos="${p}" style="padding:4px 6px;font-size:11px;height:auto">
      ${escapeHtml(p)}
    </button>
  `).join('');
  return `
    <div class="cap">Annotation</div>
    <label style="font-size:11px;color:var(--anm-text-muted);display:block">Text template</label>
    <input class="anm-input" data-mbind="annotation.text_template" value="${escapeAttr(a.text_template)}" placeholder="{filename}">
    <div style="font-size:10px;color:var(--anm-text-subtle)">Tokens: {filename} {stem} {index} {page_number} {total_pages}</div>

    <label style="font-size:11px;color:var(--anm-text-muted);display:block;margin-top:4px">Position</label>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px">${posButtons}</div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <div>
        <label style="font-size:11px;color:var(--anm-text-muted);display:block">Font size</label>
        <input class="anm-input" type="number" min="6" max="48" data-mbind="annotation.font_size" value="${a.font_size}">
      </div>
      <div>
        <label style="font-size:11px;color:var(--anm-text-muted);display:block">Margin</label>
        <input class="anm-input" type="number" min="0" max="200" data-mbind="annotation.margin" value="${a.margin}">
      </div>
    </div>
    <div>
      <label style="font-size:11px;color:var(--anm-text-muted);display:block">Box opacity (0–1)</label>
      <input class="anm-input" type="number" min="0" max="1" step="0.05" data-mbind="annotation.box_opacity" value="${a.box_opacity}">
    </div>

    <div class="anm-divider"></div>

    <div class="cap">Output</div>
    <label style="font-size:11px;color:var(--anm-text-muted);display:block">Filename</label>
    <input class="anm-input" data-mbind="run.output_filename" value="${escapeAttr(r.output_filename)}">

    <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--anm-text-muted);cursor:pointer">
      <input type="checkbox" data-mbind="run.overwrite" ${r.overwrite ? 'checked' : ''}> Overwrite if exists
    </label>
    <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--anm-text-muted);cursor:pointer">
      <input type="checkbox" data-mbind="run.save_intermediate" ${r.save_intermediate ? 'checked' : ''}> Keep annotated copies
    </label>
    <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--anm-text-muted);cursor:pointer">
      <input type="checkbox" data-mbind="run.open_folder" ${r.open_folder ? 'checked' : ''}> Open folder after
    </label>

    ${outputBlock()}
  `;
}

function renderPdfHeader() {
  if (!state.pdf) {
    return `
      <div style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--anm-text-muted);text-align:center;padding:40px">
        <div style="font-size:48px;color:var(--anm-border-strong);margin-bottom:16px">${icon('file', 48)}</div>
        <div style="font-size:15px;font-weight:500;margin-bottom:6px;color:var(--anm-text)">No PDF loaded</div>
        <div style="font-size:13px;margin-bottom:20px">Open a PDF to get started.</div>
        <button data-act="open" class="anm-btn anm-btn-primary">${icon('open', 14)} Open file</button>
      </div>
    `;
  }
  return `
    <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--anm-text-muted);margin-bottom:12px">
      ${icon('file', 14)}
      <span style="color:var(--anm-text);font-weight:500">${escapeHtml(state.pdf.name)}</span>
      <span>· ${state.pdf.page_count} pages · ${formatBytes(state.pdf.size_bytes)}</span>
    </div>
  `;
}

function renderPageGrid() {
  if (!state.pdf) return '';
  const cells = [];
  for (let i = 0; i < state.pdf.page_count; i++) {
    const selected = state.selectedPages.has(i);
    const thumb = state.thumbCache[i];
    const body = thumb
      ? `<img class="thumb-img" src="${thumb}" alt="Page ${i + 1}" loading="lazy">`
      : `<div class="anm-page-thumb" style="width:100%;height:100%"><div class="lines"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div>`;
    cells.push(`
      <div data-page="${i}" class="thumb-wrap ${selected ? 'selected' : ''}" style="width:80px;height:104px">
        ${body}
        <div class="thumb-label">${i + 1}</div>
      </div>
    `);
  }
  return `<div id="page-grid" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(90px, 1fr));gap:12px">${cells.join('')}</div>`;
}

// ----- Inspector renderers (per tool) ----- //

function renderInspector(tool) {
  switch (tool.id) {
    case 'split':   return splitInspector();
    case 'rotate':  return rotateInspector();
    case 'extract': return extractInspector();
    case 'delete':  return deleteInspector();
    case 'reorder': return reorderInspector();
    default:        return `<div class="cap">No options</div>`;
  }
}

function getOpts(id) {
  if (!state.options[id]) {
    const defaults = {
      split:   { mode: 'each_page', page_spec: '', every_n: 2 },
      rotate:  { angle: 90, page_spec: 'all' },
      extract: { page_spec: '' },
      delete:  { page_spec: '' },
      reorder: { order: '' },
    };
    state.options[id] = defaults[id] || {};
  }
  return state.options[id];
}

function radioCard(label, desc, on, dataValue) {
  return `
    <label class="radio-card ${on ? 'on' : ''}" data-val="${dataValue}">
      <div class="dot"></div>
      <div><div class="lbl">${escapeHtml(label)}</div><div class="desc">${escapeHtml(desc)}</div></div>
    </label>
  `;
}

function splitInspector() {
  const o = getOpts('split');
  return `
    <div class="cap">Split mode</div>
    <div data-radio="mode" style="display:flex;flex-direction:column;gap:8px">
      ${radioCard('Each page', 'One PDF per page', o.mode === 'each_page', 'each_page')}
      ${radioCard('By page ranges', 'e.g. 1-5, 8, 12-24', o.mode === 'ranges', 'ranges')}
      ${radioCard('Every N pages', 'Fixed-size chunks', o.mode === 'every_n', 'every_n')}
    </div>
    ${o.mode === 'ranges' ? `<input class="anm-input" data-bind="page_spec" placeholder="1-5, 8, 12-24" value="${escapeAttr(o.page_spec)}">` : ''}
    ${o.mode === 'every_n' ? `<input class="anm-input" type="number" min="1" data-bind="every_n" value="${o.every_n}">` : ''}
    ${outputBlock()}
  `;
}

function rotateInspector() {
  const o = getOpts('rotate');
  return `
    <div class="cap">Angle</div>
    <div data-radio="angle" style="display:flex;flex-direction:column;gap:8px">
      ${radioCard('90° clockwise',  'Rotate right', o.angle === 90,  '90')}
      ${radioCard('180°',           'Flip',         o.angle === 180, '180')}
      ${radioCard('270° clockwise', 'Rotate left',  o.angle === 270, '270')}
    </div>
    <div class="cap">Pages</div>
    <input class="anm-input" data-bind="page_spec" placeholder="all  |  1-3,5" value="${escapeAttr(o.page_spec)}">
    ${outputBlock()}
  `;
}

function extractInspector() {
  const o = getOpts('extract');
  return `
    <div class="cap">Pages to extract</div>
    <input class="anm-input" data-bind="page_spec" placeholder="1-3, 5, 8-10" value="${escapeAttr(o.page_spec)}">
    ${outputBlock()}
  `;
}

function deleteInspector() {
  const o = getOpts('delete');
  return `
    <div class="cap">Pages to delete</div>
    <input class="anm-input" data-bind="page_spec" placeholder="2, 4-6" value="${escapeAttr(o.page_spec)}">
    ${outputBlock()}
  `;
}

function reorderInspector() {
  const o = getOpts('reorder');
  return `
    <div class="cap">New page order</div>
    <input class="anm-input" data-bind="order" placeholder="3,1,2,4" value="${escapeAttr(o.order)}">
    <div style="font-size:11px;color:var(--anm-text-muted)">Comma-separated list including every page exactly once.</div>
    ${outputBlock()}
  `;
}

function outputBlock() {
  return `
    <div class="anm-divider"></div>
    <div class="cap">Output</div>
    <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--anm-text-muted)">
      ${icon('folder', 14)}
      <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escapeAttr(state.outputDir || '')}">${escapeHtml(state.outputDir || '— pick folder —')}</span>
      <button data-act="pick-out" class="anm-btn anm-btn-ghost" style="height:24px;padding:0 6px">…</button>
    </div>
  `;
}

// ----- Tool-view bindings ----- //

function bindTool() {
  // Rail
  document.querySelectorAll('.rail-item').forEach(el => {
    const act = el.getAttribute('data-act');
    el.addEventListener('click', () => handleRail(act));
  });
  // Sidebar tool list
  document.querySelectorAll('.side-tool').forEach(el => {
    el.addEventListener('click', () => {
      const id = el.getAttribute('data-tool');
      const t = getTool(id);
      if (!t || !t.wired) { toast(`${t ? t.label : id} not wired yet.`); return; }
      enterTool(id);
    });
  });
  // Header buttons
  document.querySelectorAll('[data-act="open"]').forEach(b => b.addEventListener('click', openPdfDialog));
  document.querySelectorAll('[data-act="add-files"]').forEach(b => b.addEventListener('click', addMergeFiles));
  document.querySelectorAll('[data-act="clear-files"]').forEach(b => b.addEventListener('click', clearMergeFiles));
  document.querySelector('[data-act="run"]')?.addEventListener('click', runActiveTool);
  document.querySelector('[data-act="pick-out"]')?.addEventListener('click', pickOutputDir);

  // Merge-specific: file row drag-reorder + remove + position buttons + binds
  bindMergeUI();

  // Radio cards
  document.querySelectorAll('[data-radio]').forEach(group => {
    const key = group.getAttribute('data-radio');
    group.querySelectorAll('[data-val]').forEach(card => {
      card.addEventListener('click', () => {
        const v = card.getAttribute('data-val');
        const o = getOpts(state.toolId);
        o[key] = /^\d+$/.test(v) ? parseInt(v, 10) : v;
        render();
      });
    });
  });
  // Text inputs
  document.querySelectorAll('[data-bind]').forEach(input => {
    const key = input.getAttribute('data-bind');
    input.addEventListener('input', () => {
      const o = getOpts(state.toolId);
      o[key] = input.type === 'number' ? parseInt(input.value || '0', 10) : input.value;
    });
  });
  // Page thumbs
  document.querySelectorAll('[data-page]').forEach(el => {
    el.addEventListener('click', () => {
      const i = parseInt(el.getAttribute('data-page'), 10);
      if (state.selectedPages.has(i)) state.selectedPages.delete(i);
      else state.selectedPages.add(i);
      render();
    });
  });
  // Lazy-load visible thumbs
  loadVisibleThumbs();
}

function handleRail(act) {
  if (act === 'home') { state.view = 'home'; render(); return; }
  if (act.startsWith('cat:')) {
    state.activeCat = act.slice(4);
    render();
    return;
  }
  if (act === 'search')   { toast('Search — not implemented yet.'); return; }
  if (act === 'settings') { toast('Settings — not implemented yet.'); return; }
}

// --------------------------------------------------------------------- //
// Merge UI helpers
// --------------------------------------------------------------------- //

function bindMergeUI() {
  // File rows: drag-reorder + remove
  document.querySelectorAll('.merge-row').forEach(row => {
    const idx = parseInt(row.getAttribute('data-mrow'), 10);
    row.addEventListener('dragstart', (e) => {
      state.merge.dragIndex = idx;
      e.dataTransfer.effectAllowed = 'move';
      row.style.opacity = '0.5';
    });
    row.addEventListener('dragend', () => {
      state.merge.dragIndex = null;
      row.style.opacity = '';
    });
    row.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });
    row.addEventListener('drop', (e) => {
      e.preventDefault();
      const from = state.merge.dragIndex;
      const to = idx;
      if (from == null || from === to) return;
      const files = state.merge.files.slice();
      const [moved] = files.splice(from, 1);
      files.splice(to, 0, moved);
      state.merge.files = files;
      render();
    });
  });
  document.querySelectorAll('[data-mremove]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const i = parseInt(btn.getAttribute('data-mremove'), 10);
      state.merge.files.splice(i, 1);
      render();
    });
  });
  // Position chips
  document.querySelectorAll('[data-mpos]').forEach(btn => {
    btn.addEventListener('click', () => {
      state.merge.annotation.position = btn.getAttribute('data-mpos');
      render();
    });
  });
  // Generic merge.* binds (text/number/checkbox)
  document.querySelectorAll('[data-mbind]').forEach(input => {
    const path = input.getAttribute('data-mbind');  // e.g. "annotation.font_size"
    const apply = () => {
      const [group, key] = path.split('.');
      const dest = state.merge[group];
      if (!dest) return;
      if (input.type === 'checkbox')      dest[key] = input.checked;
      else if (input.type === 'number')   dest[key] = parseFloat(input.value || '0');
      else                                dest[key] = input.value;
    };
    input.addEventListener('input', apply);
    input.addEventListener('change', apply);
  });
}

async function addMergeFiles() {
  try {
    const data = await api('open_pdfs_dialog');
    if (!data || !data.files) return;
    if (!data.files.length) { toast('No PDFs picked.'); return; }
    // Dedupe by path.
    const existing = new Set(state.merge.files.map(f => f.path));
    for (const f of data.files) if (!existing.has(f.path)) state.merge.files.push(f);
    state.outputDir = data.output_dir;
    render();
  } catch (exc) {
    toast(exc.message || String(exc), { error: true });
  }
}

function clearMergeFiles() {
  state.merge.files = [];
  render();
}

async function runMerge() {
  if (state.running) return;
  if (!state.merge.files.length) { toast('Add at least one PDF.', { error: true }); return; }
  state.running = true;
  render();
  try {
    const result = await api(
      'run_merge',
      state.merge.files.map(f => f.path),
      state.merge.annotation,
      state.merge.run,
    );
    toast(result.summary || 'Done.');
  } catch (exc) {
    toast(exc.message || String(exc), { error: true });
  } finally {
    state.running = false;
    render();
  }
}

// --------------------------------------------------------------------- //
// PDF actions
// --------------------------------------------------------------------- //

async function openPdfDialog() {
  try {
    const data = await api('open_pdf_dialog');
    if (!data) return;  // user cancelled
    applyLoadedPdf(data);
  } catch (exc) {
    toast(exc.message || String(exc), { error: true });
  }
}

function applyLoadedPdf(data) {
  state.pdf = data;
  state.outputDir = data.output_dir;
  state.selectedPages = new Set();
  state.thumbCache = {};
  render();
}

async function pickOutputDir() {
  try {
    const data = await api('choose_output_dir');
    if (!data) return;
    state.outputDir = data.output_dir;
    render();
  } catch (exc) {
    toast(exc.message || String(exc), { error: true });
  }
}

async function runActiveTool() {
  if (!state.toolId || state.running) return;

  // Merge is the only multi-file tool — uses its own dispatcher.
  if (state.toolId === 'merge') return runMerge();

  if (!state.pdf) return;
  const opts = { ...getOpts(state.toolId) };

  // For Reorder, parse the order string into a list of ints.
  if (state.toolId === 'reorder') {
    opts.order = (opts.order || '').split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
  }

  state.running = true;
  render();
  try {
    const result = await api('run_tool', state.toolId, opts);
    toast(result.summary || 'Done.');
  } catch (exc) {
    toast(exc.message || String(exc), { error: true });
  } finally {
    state.running = false;
    render();
  }
}

// --------------------------------------------------------------------- //
// Lazy thumbnail loading
// --------------------------------------------------------------------- //

async function loadVisibleThumbs() {
  if (!state.pdf) return;
  const needed = [];
  for (let i = 0; i < state.pdf.page_count; i++) {
    if (!state.thumbCache[i]) needed.push(i);
    if (needed.length >= 20) break;  // batch in chunks of 20
  }
  if (!needed.length) return;
  try {
    const batch = await api('get_page_thumbs', needed);
    Object.assign(state.thumbCache, batch);
    // Apply images without full re-render (avoids losing scroll position).
    for (const idx of Object.keys(batch)) {
      const wrap = document.querySelector(`[data-page="${idx}"]`);
      if (!wrap) continue;
      wrap.innerHTML = `<img class="thumb-img" src="${batch[idx]}" alt="Page ${parseInt(idx, 10) + 1}"><div class="thumb-label">${parseInt(idx, 10) + 1}</div>`;
      // Re-bind click since innerHTML wipes listeners on children.
      wrap.addEventListener('click', () => {
        const i = parseInt(idx, 10);
        if (state.selectedPages.has(i)) state.selectedPages.delete(i);
        else state.selectedPages.add(i);
        render();
      });
    }
    // Recurse to load the next chunk (defer to next frame so UI breathes).
    requestAnimationFrame(loadVisibleThumbs);
  } catch (exc) {
    console.error('Thumb load failed:', exc);
  }
}

// --------------------------------------------------------------------- //
// Navigation
// --------------------------------------------------------------------- //

function enterTool(id) {
  const tool = getTool(id);
  if (!tool) return;
  state.view = 'tool';
  state.toolId = id;
  state.activeCat = tool.cat;
  render();
}

function toggleTheme() {
  state.dark = !state.dark;
  render();
}

// --------------------------------------------------------------------- //
// Helpers
// --------------------------------------------------------------------- //

// Escape every char that can break out of HTML text or attribute context.
// `&` MUST be first so we don't double-escape entities we add below.  Single
// quote covered too because we sometimes interpolate into single-quoted
// attributes via template literals.
const _HTML_ESCAPE = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => _HTML_ESCAPE[c]);
}
// `escapeAttr` must defeat the browser's entity decoder inside attribute
// values — a value like `&quot;` could otherwise become a literal `"` and
// terminate the attribute.  We use the same robust replacer as escapeHtml.
const escapeAttr = escapeHtml;
function formatBytes(n) {
  if (n == null) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

// --------------------------------------------------------------------- //
// Boot
// --------------------------------------------------------------------- //

window.addEventListener('DOMContentLoaded', () => {
  render();
  // Ctrl K placeholder
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      toast('Command palette — not implemented yet.');
    }
  });
});
