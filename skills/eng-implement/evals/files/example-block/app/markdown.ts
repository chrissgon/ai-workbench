export type Component = (slot: string) => string;
export type Components = Record<string, Component>;

export interface Page {
  title: string;
  html: string;
}

const OPEN_BUTTON = /<fl-button(?: variant="([a-z]+)")?>/g;

// Turns Fernleaf elements into the HTML the library renders in a browser.
export function expandElements(markup: string): string {
  return markup
    .split("\n")
    .map((line) => line.trim())
    .join("")
    .replace(OPEN_BUTTON, (_match, variant) => `<button class="fl-button fl-button--${variant ?? "primary"}">`)
    .replaceAll("</fl-button>", "</button>");
}

export function renderPage(source: string, components: Components): Page {
  const lines = source.split("\n");
  let title = "";
  let index = 0;
  if (lines[0] === "---") {
    for (index = 1; lines[index] !== "---"; index++) {
      const field = lines[index].match(/^title:\s*(.+)$/);
      if (field) title = field[1];
    }
    index++;
  }
  const html: string[] = [];
  while (index < lines.length) {
    const line = lines[index];
    const block = line.match(/^::([a-z]+)$/);
    if (block) {
      const end = lines.indexOf("::", index + 1);
      if (end === -1) throw new RangeError(`block "${block[1]}" is not closed`);
      const component = components[block[1]];
      if (!component) throw new RangeError(`unknown block "${block[1]}"`);
      html.push(component(expandElements(lines.slice(index + 1, end).join("\n"))));
      index = end;
    } else if (line.startsWith("## ")) {
      html.push(`<h2>${line.slice(3)}</h2>`);
    } else if (line.startsWith("# ")) {
      html.push(`<h1>${line.slice(2)}</h1>`);
    } else if (line.trim() !== "") {
      html.push(`<p>${line}</p>`);
    }
    index++;
  }
  return { title, html: html.join("\n") };
}
