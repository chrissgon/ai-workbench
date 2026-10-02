// The example block. Today it renders the preview only; the code panel is the subject of ADR-0002.
export function example(slot: string): string {
  return `<div class="example"><div class="example-preview">${slot}</div></div>`;
}
