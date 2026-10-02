export function escapeHtml(text: string): string {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

// Escapes markup and wraps every tag name in <span class="hl-tag">.
export function highlight(code: string): string {
  return escapeHtml(code).replace(/(&lt;\/?)([a-z][a-z0-9-]*)/g, '$1<span class="hl-tag">$2</span>');
}
