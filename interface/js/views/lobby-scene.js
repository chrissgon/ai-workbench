// The Lobby's room: the scene engine of the page showing the scene kind `room` (the Floor's scene with the planning agent and a
// door). The room's builder belongs to the Floor package and is registered in `BUILDERS` of scene/engine.js; this file only mounts
// the engine, hands it the plain model of lobby-model.js `roomModel` and frees it. Where the engine cannot draw (no WebGL, or no
// builder registered for `room`) the panel has everything and the frame shows its one line.

import { createEngine, NoWebGL } from "../scene/engine.js";

/** Mount the room in the frame's scene host, fitted to the free rectangle the panel leaves. Returns {update(model, label), dispose()}. */
export function mountLobbyScene(frame, panelEl, { onDoor, onSelect } = {}) {
  let engine = null;
  try {
    engine = createEngine(frame.sceneHost, {
      label: "Lobby, loading",
      getInsets: () => frame.insets(panelEl),
      onOpen: (id) => {
        if (id === "lobby-door") {
          if (onDoor) onDoor();
        } else if (onSelect) {
          onSelect(id);      // the tray, the cabinet, a sheet, the desk, the board, the figure: the tabs' equivalents
        }
      },
      onUnavailable: () => frame.sceneUnavailable(true),
    });
    frame.sceneUnavailable(false);
  } catch (e) {
    if (!(e instanceof NoWebGL)) throw e;
    frame.sceneUnavailable(true);
  }
  const observer = new ResizeObserver(() => { if (engine) engine.refit(); });
  observer.observe(frame.track.el);
  observer.observe(frame.noticeBox);
  observer.observe(panelEl);
  return {
    update(model, label) {
      if (engine) engine.show("room", model, label);
    },
    dispose() {
      observer.disconnect();
      if (engine) engine.dispose();
      engine = null;
      frame.sceneUnavailable(false);
    },
    stats() {
      return engine ? engine.stats() : null;
    },
  };
}
