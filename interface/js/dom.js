// Building the page's elements. Everything that came from the service is put in the document as text, never as markup:
// a string child becomes a text node, setText assigns textContent, and nothing here builds markup from a string.

const FORBIDDEN = /^(on[a-z]+|style)$/i;

/**
 * h(tag, attrs, ...children): an element. attrs: `class`, `text` (a string, assigned with textContent), `hidden`
 * and other plain attributes. An event handler attribute and a style attribute are refused (the page's policy
 * forbids both), and so is an href that is not a hash link of this page.
 */
export function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (FORBIDDEN.test(name)) throw new Error(`the attribute ${name} is not allowed`);
    if (name === "text") {
      node.textContent = String(value);
    } else if (name === "href" && !String(value).startsWith("#")) {
      throw new Error("a link on this page is a hash link");
    } else {
      node.setAttribute(name, value === true ? "" : String(value));
    }
  }
  for (const child of children.flat()) {
    if (child === undefined || child === null || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

/** Replace the text of a node. */
export function setText(node, text) {
  node.textContent = String(text);
  return node;
}

/** Empty a node and put the given children in it. */
export function fill(node, ...children) {
  node.replaceChildren(...children.flat().filter((c) => c !== undefined && c !== null && c !== false).map((c) => (c instanceof Node ? c : document.createTextNode(String(c)))));
  return node;
}
