// Tool + category catalog — mirrors src/anm/gui/catalog.py.
// `wired: true` => Python bridge `run_tool` knows this tool.

const TOOLS = [
  // Organize
  { id: 'merge',       label: 'Merge',         cat: 'organize', desc: 'Combine multiple PDFs into one', wired: true },
  { id: 'split',       label: 'Split',         cat: 'organize', desc: 'Break a PDF into parts',         wired: true  },
  { id: 'reorder',     label: 'Reorder',       cat: 'organize', desc: 'Rearrange pages',                wired: true  },
  { id: 'delete',      label: 'Delete Pages',  cat: 'organize', desc: 'Remove specific pages',          wired: true  },
  { id: 'rotate',      label: 'Rotate',        cat: 'organize', desc: 'Rotate pages 90/180/270°',       wired: true  },
  { id: 'extract',     label: 'Extract',       cat: 'organize', desc: 'Pull pages into a new PDF',      wired: true  },
  // Edit
  { id: 'annotate',    label: 'Annotate',      cat: 'edit',     desc: 'Add notes, highlights, shapes',  wired: false },
  { id: 'watermark',   label: 'Watermark',     cat: 'edit',     desc: 'Stamp text over pages',          wired: true  },
  { id: 'numbers',     label: 'Page Numbers',  cat: 'edit',     desc: 'Add page numbering',             wired: true  },
  { id: 'metadata',    label: 'Metadata',      cat: 'edit',     desc: 'Edit title, author, keywords',   wired: true  },
  // Convert
  { id: 'to_images',   label: 'PDF → Images',  cat: 'convert',  desc: 'Export pages as PNG or JPG',     wired: true  },
  { id: 'from_images', label: 'Images → PDF',  cat: 'convert',  desc: 'Combine images into a PDF',      wired: true  },
  { id: 'compress',    label: 'Compress',      cat: 'convert',  desc: 'Reduce file size',               wired: true  },
  { id: 'ocr',         label: 'OCR',           cat: 'convert',  desc: 'Recognize text from scans',      wired: false },
  // Secure
  { id: 'protect',     label: 'Protect/Unlock',cat: 'secure',   desc: 'Add or remove a password',       wired: false },
  { id: 'flatten',     label: 'Flatten',       cat: 'secure',   desc: 'Lock form fields & annotations', wired: false },
  { id: 'compare',     label: 'Compare',       cat: 'secure',   desc: 'Diff two PDFs side-by-side',     wired: false },
];

const CATEGORIES = [
  { id: 'organize', label: 'Organize', accent: '#5B6CFF', icon: 'folder' },
  { id: 'edit',     label: 'Edit',     accent: '#E47A2E', icon: 'annotate' },
  { id: 'convert',  label: 'Convert',  accent: '#2BA876', icon: 'images' },
  { id: 'secure',   label: 'Secure',   accent: '#A24EC7', icon: 'protect' },
];

const toolsByCat = (catId) => TOOLS.filter(t => t.cat === catId);
const getTool = (id) => TOOLS.find(t => t.id === id);

window.TOOLS = TOOLS;
window.CATEGORIES = CATEGORIES;
window.toolsByCat = toolsByCat;
window.getTool = getTool;
