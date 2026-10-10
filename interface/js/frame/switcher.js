// F-2 the project switcher: a cycle button and a listbox of the projects. On the City it chooses the project the tracking bar
// follows; on another screen it opens the same screen in the chosen project (the page decides: `onSelect`). With one project there is
// nothing to cycle to: the main button is a label (C-1). With none the card still opens, with its foot alone (C-20). The foot holds the
// provisional light/dark control (D-2), where it stays until the design round decides its place, and "Forget the token".

import { h } from "../dom.js";
import { currentMode, MODES, setMode } from "../mode.js";
import { arrowNav } from "./arrows.js";
import { icon } from "./icons.js";

let counter = 0;
const MODE_WORDS = Object.freeze({ light: "Light", dark: "Dark", system: "System" });
const defaultMode = { current: () => currentMode(), set: (mode) => setMode(mode) };

/** mode: {current(): "light" | "dark" | "system", set(mode)} - the preference the foot's control shows and sets (js/mode.js by default). */
export function createSwitcher({ onSelect, onForgetToken, onOpen, mode = defaultMode }) {
  counter += 1;
  const listId = `wb-projects-${counter}`;
  const name = h("strong", { class: "wb-switch-name", text: "No project" });
  const pos = h("span", { class: "wb-switch-pos", text: "" });
  const main = h("button", { class: "pui-btn pui-surface pui-outline wb-switch-main", type: "button", title: "Go to the next project" },
    icon("building-2", 16), name, pos);
  const chevron = h("button", {
    class: "pui-btn pui-surface pui-outline wb-switch-chevron", type: "button", "aria-haspopup": "listbox", "aria-expanded": "false",
    "aria-controls": listId, "aria-label": "Choose a project",
  }, icon("chevron-down", 16));
  // with one project (or none) the main button is a label: no cycling, no place "1/1", no title
  const labelName = h("strong", { class: "wb-switch-name", text: "No project" });
  const label = h("span", { class: "pui-btn pui-surface pui-outline wb-switch-main is-label" }, icon("building-2", 16), labelName);
  const group = h("div", { class: "pui-group-row wb-switch-group" }, main, chevron);
  let single = false;
  const heading = h("div", { class: "pui-card-header wb-listbox-head", text: "" });
  const list = h("ul", { class: "pui-list pui-hoverable wb-listbox", id: listId, role: "listbox", tabindex: "-1", "aria-label": "Projects" });
  const empty = h("p", { class: "wb-empty wb-listbox-empty", hidden: true, text: "No project" });
  const forget = h("button", { class: "pui-btn pui-link wb-forget", type: "button", text: "Forget the token" });
  // the provisional colour-mode control: three radio chips in a group (buttons, so the library's blocked radio mark is not needed)
  const chips = MODES.map((word) => h("button", { class: "pui-btn pui-surface pui-outline wb-mode-chip", type: "button", role: "radio", "aria-checked": "false", tabindex: "-1", "data-mode": word, text: MODE_WORDS[word] }));
  const modeGroup = h("div", { class: "wb-mode", role: "radiogroup", "aria-label": "Colour mode" }, h("span", { class: "wb-mode-label", "aria-hidden": "true", text: "Colour mode" }), h("div", { class: "pui-group-row wb-mode-chips" }, chips));
  const card = h("div", { class: "pui-card wb-listbox-card", hidden: true }, heading, list, empty, h("div", { class: "wb-listbox-foot" }, modeGroup, forget));
  const el = h("div", { class: "wb-switcher" }, group, card);

  let projects = [];
  let selected = null;
  let active = 0;
  let open = false;

  const indexOfSelected = () => Math.max(0, projects.findIndex((p) => p.id === selected));

  function setActive(index) {
    active = Math.max(0, Math.min(projects.length - 1, index));
    const options = [...list.children];
    options.forEach((o, i) => o.classList.toggle("is-active", i === active));
    if (options[active]) list.setAttribute("aria-activedescendant", options[active].id);
    else list.removeAttribute("aria-activedescendant");
  }

  /** The control shows the preference as it is now (it can be changed elsewhere), with the checked chip alone in the tab order. */
  function drawMode() {
    const now = mode.current();
    for (const chip of chips) {
      const on = chip.getAttribute("data-mode") === now;
      chip.setAttribute("aria-checked", String(on));
      chip.setAttribute("tabindex", on ? "0" : "-1");
      chip.classList.toggle("is-selected", on);
    }
  }

  function setOpen(next, { focus = true } = {}) {
    open = Boolean(next);
    card.hidden = !open;
    chevron.setAttribute("aria-expanded", String(open));
    chevron.classList.toggle("is-open", open);
    if (open) {
      onOpen();
      setActive(indexOfSelected());
      drawMode();
      (projects.length > 0 ? list : forget).focus();      // with no project the foot is all there is
    } else if (focus && next === false && document.activeElement && el.contains(document.activeElement)) {
      chevron.focus();
    }
  }

  function choose(index) {
    const project = projects[index];
    if (!project) return;
    setOpen(false);
    onSelect(project.id);
  }

  main.addEventListener("click", () => {
    if (projects.length < 2) return;
    const next = projects[(indexOfSelected() + 1) % projects.length];
    setOpen(false, { focus: false });
    onSelect(next.id);
  });
  chevron.addEventListener("click", () => setOpen(!open));
  chevron.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
    }
  });
  list.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") { event.preventDefault(); setActive(active + 1); }
    else if (event.key === "ArrowUp") { event.preventDefault(); setActive(active - 1); }
    else if (event.key === "Home") { event.preventDefault(); setActive(0); }
    else if (event.key === "End") { event.preventDefault(); setActive(projects.length - 1); }
    else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(active); }
  });
  card.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      setOpen(false);
    }
  });
  arrowNav(card, ".wb-forget");
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      mode.set(chip.getAttribute("data-mode"));
      drawMode();
    });
  });
  modeGroup.addEventListener("keydown", (event) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    event.stopPropagation();      // the card's arrow keys move among its own buttons; these move among the three choices
    const at = chips.findIndex((chip) => chip.getAttribute("aria-checked") === "true");
    const next = chips[(Math.max(0, at) + step + chips.length) % chips.length];
    next.click();
    next.focus();
  });
  forget.addEventListener("click", () => onForgetToken());
  const onPointerDown = (event) => {
    if (open && !el.contains(event.target)) setOpen(false, { focus: false });
  };
  document.addEventListener("pointerdown", onPointerDown);

  return {
    el,
    destroy() { document.removeEventListener("pointerdown", onPointerDown); },
    close() { if (open) setOpen(false, { focus: false }); },
    isOpen: () => open,
    /**
     * projects: [{id, name, badge, sub, accepted}]; selectedId; heading: the card's header text.
     */
    update({ projects: next, selectedId, heading: text }) {
      projects = next;
      selected = selectedId;
      heading.textContent = text;
      const index = indexOfSelected();
      const current = projects[index];
      name.textContent = current ? current.name : "No project";
      labelName.textContent = name.textContent;
      pos.textContent = current ? `${index + 1}/${projects.length}` : "";
      main.setAttribute("aria-label", current ? `${current.name}, project ${index + 1} of ${projects.length}, go to the next project` : "No project");
      if (single !== (projects.length < 2)) {      // the button and the label swap only when the count crosses one
        single = projects.length < 2;
        group.replaceChildren(single ? label : main, chevron);
      }
      list.hidden = projects.length === 0;
      empty.hidden = projects.length > 0;
      list.replaceChildren(...projects.map((p, i) => {
        const optionId = `${listId}-o${i}`;
        const row = h("li", { class: `pui-list-item wb-option${p.id === selected ? " is-selected" : ""}`, id: optionId, role: "option", "aria-selected": String(p.id === selected) },
          h("span", { class: `wb-check${p.id === selected ? " is-on" : ""}` }, icon("check", 16)),
          h("span", { class: "wb-option-text" }, h("strong", { class: "wb-option-name", text: p.name }), h("span", { class: "wb-option-sub", text: p.sub || "" })),
          p.accepted === false
            ? h("span", { class: "pui-chip pui-warn pui-soft wb-chip-small", text: "Not accepted" })
            : h("span", { class: "pui-badge pui-warn pui-soft pui-rounded-full", text: String(p.badge ?? 0) }));
        row.addEventListener("click", () => choose(i));
        return row;
      }));
      if (open) setActive(Math.min(active, projects.length - 1));
    },
  };
}
