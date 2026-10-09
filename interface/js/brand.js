// The product's mark (OH-3): the one place that names the mark file. It is an <img> of a same-origin file, sized by its own attributes
// (the policy forbids a style attribute), with the product's name as its alt text; nothing here builds markup from a string.

import { h } from "./dom.js";

const MARK_SRC = "./brand/openhora-mark.svg";

/** The mark as an image `size` pixels square: 20 in the top bar, 48 on the token prompt. */
export function markImage(size) {
  return h("img", { class: "wb-mark", src: MARK_SRC, alt: "openhora", width: size, height: size });
}
