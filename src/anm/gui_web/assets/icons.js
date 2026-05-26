// Stroke-only SVG icon set — viewBox 20×20, stroke=currentColor.
// Mirrors `Icon` from common.jsx so the markup stays pixel-identical
// to the design reference.

const ICON_PATHS = {
  merge: '<path d="M5 4v6m0 0l-2-2m2 2l2-2"/><path d="M14 4v6m0 0l-2-2m2 2l2-2"/><path d="M3 14h14"/><path d="M9.5 14v4"/>',
  split: '<path d="M10 3v4"/><path d="M10 7L6 11v6"/><path d="M10 7l4 4v6"/>',
  reorder: '<path d="M4 5h10"/><path d="M4 10h6"/><path d="M4 15h12"/><path d="M16 7l2-2-2-2"/><path d="M14 13l-2 2 2 2"/>',
  delete: '<path d="M4 6h12"/><path d="M7 6V4h6v2"/><path d="M6 6l1 11h6l1-11"/>',
  rotate: '<path d="M15 6a6 6 0 10-2 8"/><path d="M15 3v3h-3"/>',
  extract: '<path d="M5 3h7l3 3v11H5z"/><path d="M12 3v3h3"/><path d="M8 11l2 2 2-2"/><path d="M10 8v5"/>',
  annotate: '<path d="M4 14l8-8 3 3-8 8H4z"/><path d="M11 6l3 3"/>',
  watermark: '<path d="M4 4h12v12H4z"/><path d="M7 9l3 3 6-6" opacity=".5"/><text x="10" y="13" text-anchor="middle" font-size="6" fill="currentColor" stroke="none" opacity=".7">©</text>',
  numbers: '<path d="M4 4h12v12H4z"/><path d="M7 13h1m2 0h1m2 0h1"/>',
  metadata: '<path d="M4 4h12v12H4z"/><path d="M7 8h6M7 11h6M7 14h3"/>',
  images: '<path d="M3 5h11v9H3z"/><circle cx="6.5" cy="8.5" r="1"/><path d="M3 13l3-3 3 3 2-2 3 3"/><path d="M16 7v9H6"/>',
  compress: '<path d="M4 4l3 3M16 4l-3 3M4 16l3-3M16 16l-3-3"/><rect x="7" y="7" width="6" height="6" rx="1"/>',
  ocr: '<path d="M3 6V4h2M17 6V4h-2M3 14v2h2M17 14v2h-2"/><path d="M6 8h8v4H6z"/><path d="M7 10h1m2 0h1m2 0h1"/>',
  protect: '<path d="M6 9V7a4 4 0 018 0v2"/><rect x="4" y="9" width="12" height="8" rx="1.5"/>',
  flatten: '<path d="M3 14h14"/><path d="M5 11h10"/><path d="M7 8h6"/><path d="M9 5h2"/>',
  compare: '<path d="M10 3v14"/><path d="M4 6h4M4 10h4M4 14h4"/><path d="M12 6h4M12 10h4M12 14h4"/>',
  home: '<path d="M3 9l7-6 7 6v8H3z"/><path d="M8 17v-5h4v5"/>',
  search: '<circle cx="9" cy="9" r="5"/><path d="M13 13l4 4"/>',
  settings: '<circle cx="10" cy="10" r="2.5"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.5 4.5l1.5 1.5M14 14l1.5 1.5M4.5 15.5L6 14M14 6l1.5-1.5"/>',
  star: '<path d="M10 3l2.2 4.5 5 .7-3.6 3.5.9 5L10 14.4 5.5 16.7l.9-5L2.8 8.2l5-.7z"/>',
  pin: '<path d="M9 3h4l-1 4 3 3-4 1-1 5-1-5-4-1 3-3z"/>',
  open: '<path d="M3 6h6l1 2h7v8H3z"/>',
  chevron: '<path d="M7 5l5 5-5 5"/>',
  chevronD: '<path d="M5 8l5 5 5-5"/>',
  plus: '<path d="M10 4v12M4 10h12"/>',
  close: '<path d="M5 5l10 10M15 5L5 15"/>',
  grid: '<rect x="3" y="3" width="6" height="6"/><rect x="11" y="3" width="6" height="6"/><rect x="3" y="11" width="6" height="6"/><rect x="11" y="11" width="6" height="6"/>',
  list: '<path d="M3 5h14M3 10h14M3 15h14"/>',
  history: '<path d="M3 10a7 7 0 1 0 2-5"/><path d="M3 3v4h4"/><path d="M10 6v4l3 2"/>',
  file: '<path d="M5 3h7l3 3v11H5z"/><path d="M12 3v3h3"/>',
  folder: '<path d="M3 6h5l2 2h7v8H3z"/>',
  sun: '<circle cx="10" cy="10" r="3.5"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.2 4.2l1.4 1.4M14.4 14.4l1.4 1.4M4.2 15.8l1.4-1.4M14.4 5.6l1.4-1.4"/>',
  moon: '<path d="M15 12.5A6.5 6.5 0 017.5 5a6.5 6.5 0 108.5 7.5"/>',
};

function icon(name, size = 18, stroke = 1.6) {
  const inner = ICON_PATHS[name] || ICON_PATHS.file;
  return `<svg viewBox="0 0 20 20" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle">${inner}</svg>`;
}

window.icon = icon;
window.ICON_PATHS = ICON_PATHS;
