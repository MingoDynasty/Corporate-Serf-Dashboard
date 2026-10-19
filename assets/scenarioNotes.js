// The Run History page's scenario note, in the browser: the controller that
// opens and closes its editor and answers its dialog, and the guard that
// keeps a page change from throwing unsaved text away. The card's layout and
// its server callbacks are in source/components/scenario_note_card.py, and
// every string the card shows comes from there.
//
// The guard listens on window in the capture phase, so it runs before React's
// root listener and before Dash Pages hears of a link or a history move.
// While the card says its note has unsaved changes it:
//   - stops the run toast's link, and asks the card about it, unless the link
//     is to the edited scenario itself, which changes nothing;
//   - stops a link to another address in this app, asks, and on Save or
//     Discard clicks it again, so nothing repeats dcc.Link's navigation by
//     hand;
//   - stops the history move of the back and forward buttons from reaching
//     Dash Pages, puts the address back, asks, and on Save or Discard moves
//     again and lets it through. A popstate arrives after the address has
//     changed, so it can't be cancelled, only undone;
//   - sets the browser's own unload prompt, for a reload, a closed tab and
//     another site. It is added only while there is something to lose: a
//     page with an unload listener is kept out of the browser's back-forward
//     cache.
// Another site's link is left to that prompt, and a link that opens a new
// tab leaves nothing behind.

(function () {
  "use strict";

  var NOTE_CARD = "[data-note-held-store]";
  // The history entry's place, written into each entry's state, which is how
  // a popstate says how far it moved and the guard can move back.
  var INDEX_KEY = "scenarioNoteIndex";

  function noteCard() {
    return document.querySelector(NOTE_CARD);
  }

  // Read from the page, not from the controller's memory, so a page that is
  // gone guards nothing.
  function guarded() {
    var card = noteCard();
    return !!card && card.getAttribute("data-unsaved") === "true";
  }

  function dialogOpen(card) {
    return card.getAttribute("data-dialog") === "true";
  }

  function ask(card, request) {
    window.dash_clientside.set_props(card.getAttribute("data-note-held-store"), {
      data: request,
    });
  }

  function stop(event) {
    event.preventDefault();
    event.stopImmediatePropagation();
  }

  function addressOf(location) {
    return location.pathname + location.search;
  }

  // ---- The history entries' places ----

  function stamped(state, index) {
    if (state !== null && typeof state !== "object") {
      return state;
    }
    var copy = Object.assign({}, state);
    copy[INDEX_KEY] = index;
    return copy;
  }

  function indexOf(state) {
    var index = state && state[INDEX_KEY];
    return typeof index === "number" ? index : null;
  }

  var push = window.history.pushState.bind(window.history);
  var replace = window.history.replaceState.bind(window.history);
  var here = indexOf(window.history.state);
  var index = here === null ? 0 : here;
  var address = addressOf(window.location);
  window.history.pushState = function (state, title, url) {
    index += 1;
    var result = push(stamped(state, index), title, url);
    address = addressOf(window.location);
    return result;
  };
  window.history.replaceState = function (state, title, url) {
    var result = replace(stamped(state, index), title, url);
    address = addressOf(window.location);
    return result;
  };
  if (here === null) {
    replace(stamped(window.history.state, index), "");
  }

  // ---- What the guard holds while the dialog asks ----

  var pending = null; // {kind: "link", link} or {kind: "history", delta}
  var passThrough = false;
  var restoring = 0; // popstates owed by the guard's own moves back
  var releasing = false;

  function onClick(event) {
    if (passThrough || event.button !== 0) {
      return;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    var link =
      event.target instanceof Element ? event.target.closest("a[href]") : null;
    if (!link || !guarded()) {
      return;
    }
    if (link.target && link.target !== "_self") {
      return;
    }
    var url = new URL(link.href, window.location.href);
    if (url.origin !== window.location.origin) {
      return;
    }
    var card = noteCard();
    if (link.classList.contains(card.getAttribute("data-note-toast-link-class"))) {
      stop(event);
      var scenario = url.searchParams.get("scenario");
      if (dialogOpen(card) || !scenario || scenario === card.getAttribute("data-scenario")) {
        return;
      }
      ask(card, { kind: "toast", to: scenario });
      return;
    }
    if (addressOf(url) === addressOf(window.location)) {
      return;
    }
    stop(event);
    if (dialogOpen(card)) {
      return;
    }
    pending = { kind: "link", link: link };
    ask(card, { kind: "leave" });
  }

  function onPopState(event) {
    var to = indexOf(event.state);
    if (restoring > 0) {
      restoring -= 1;
      event.stopImmediatePropagation();
      return;
    }
    if (releasing || !guarded() || addressOf(window.location) === address) {
      releasing = false;
      if (to !== null) {
        index = to;
      }
      address = addressOf(window.location);
      return;
    }
    event.stopImmediatePropagation();
    var card = noteCard();
    var held = dialogOpen(card) ? pending : null;
    if (to === null) {
      // An entry no page of this app stamped: how far it moved is unknown.
      // The address goes back on top of it, so it is one step back.
      push(stamped(null, index), "", address);
      held = held || { kind: "history", delta: -1 };
    } else {
      restoring += 1;
      window.history.go(index - to);
      held = held || { kind: "history", delta: to - index };
    }
    if (!dialogOpen(card)) {
      pending = held;
      ask(card, { kind: "leave" });
    }
  }

  function onBeforeUnload(event) {
    if (guarded()) {
      event.preventDefault();
      event.returnValue = "";
    }
  }

  var unloadGuarded = false;

  window.addEventListener("click", onClick, true);
  window.addEventListener("popstate", onPopState, true);

  window.scenarioNotes = {
    // Follow the unsaved state with the unload prompt.
    track: function (unsaved) {
      if (unsaved && !unloadGuarded) {
        window.addEventListener("beforeunload", onBeforeUnload);
        unloadGuarded = true;
      } else if (!unsaved && unloadGuarded) {
        window.removeEventListener("beforeunload", onBeforeUnload);
        unloadGuarded = false;
      }
    },
    // Save or Discard: go where the player asked.
    release: function () {
      var held = pending;
      pending = null;
      if (!held) {
        return;
      }
      if (held.kind === "link") {
        if (!held.link.isConnected) {
          return;
        }
        passThrough = true;
        try {
          held.link.click();
        } finally {
          passThrough = false;
        }
        return;
      }
      releasing = true;
      window.history.go(held.delta);
    },
    // Keep editing: the address was put back when the dialog opened.
    stay: function () {
      pending = null;
    },
  };

  // ---- The controller ----

  var NO_UPDATE = { description: "no update" };

  function noUpdate() {
    return window.dash_clientside.no_update;
  }

  function hasUnsavedChanges(editor, draft) {
    return !!editor && draft !== editor.opened;
  }

  function visible(element) {
    return !!element && element.getClientRects().length > 0;
  }

  // Focus the first of ``ids`` on screen, once the answer that shows it has
  // been drawn. ``atEnd`` puts the cursor at the end of a text box.
  function focusSoon(ids, atEnd) {
    var tries = 0;
    function attempt() {
      for (var i = 0; i < ids.length; i += 1) {
        var element = document.getElementById(ids[i]);
        if (visible(element)) {
          element.focus();
          if (atEnd && typeof element.setSelectionRange === "function") {
            element.setSelectionRange(element.value.length, element.value.length);
          }
          return;
        }
      }
      tries += 1;
      if (tries < 30) {
        window.setTimeout(attempt, 20);
      }
    }
    window.setTimeout(attempt, 0);
  }

  function readOrAdd(ids) {
    return [ids.edit, ids.add];
  }

  // A line from the card's templates: a string part names scenarios, by the
  // keys in ``names``, and any other part is a control's name, drawn bold.
  function filled(parts, names) {
    return parts.map(function (part) {
      if (typeof part === "string") {
        return part.replace(/\{(\w+)\}/g, function (match, key) {
          return Object.prototype.hasOwnProperty.call(names, key) ? names[key] : match;
        });
      }
      return {
        type: "B",
        namespace: "dash_html_components",
        props: { children: part.control },
      };
    });
  }

  function questionFor(config, dialog) {
    var kind = dialog.kind === "filter" || dialog.kind === "leave" ? dialog.kind : "switch";
    return filled(config.questions[kind], { from: dialog.from, to: dialog.to });
  }

  // ``triggered`` holds every input that changed. A page's first call can
  // name every input, or none, so each handler reads a value as well.
  function controller(
    scenario,
    playlist,
    editClicks,
    addClicks,
    cancelClicks,
    draft,
    saveResult,
    held,
    keepClicks,
    discardClicks,
    dialogOpened,
    waiting,
    editor,
    shown,
    dialog,
    filterHistory,
    note,
    config
  ) {
    var ids = config.ids;
    var triggered = (window.dash_clientside.callback_context.triggered || []).map(
      function (trigger) {
        return trigger.prop_id;
      }
    );
    function fired(id, prop) {
      return triggered.indexOf(id + "." + prop) !== -1;
    }
    var firstCall = triggered.length === 0 || triggered.indexOf(".") !== -1;

    var nextEditor = editor || null;
    var nextShown = shown === undefined ? null : shown;
    var nextDialog = dialog || null;
    var opened = NO_UPDATE;
    var text = NO_UPDATE;
    var error = NO_UPDATE;
    var history = filterHistory || { prev: playlist, cur: playlist };
    var request = null;
    var guardCall = null;
    var focus = null;
    var current = draft === null || draft === undefined ? "" : draft;

    function closeEditor() {
      nextEditor = null;
      error = "";
    }

    // The dialog's answer. "stay" is Keep editing, Escape, a click outside
    // it, and a Save that failed. "go" is Discard and a Save that worked.
    function answer(outcome) {
      var asked = nextDialog;
      nextDialog = null;
      opened = false;
      if (!asked) {
        return;
      }
      if (outcome === "stay") {
        if (asked.kind === "pick" || asked.kind === "filter") {
          request = { restore: asked.restore };
        } else if (asked.kind === "leave") {
          guardCall = "stay";
        }
        focus = { ids: [ids.draft], atEnd: false };
        return;
      }
      closeEditor();
      if (asked.kind === "pick" || asked.kind === "filter") {
        // The dropdown already holds where the player asked to go.
        request = { drop: true };
        nextShown = scenario === undefined ? null : scenario;
      } else if (asked.kind === "leave") {
        guardCall = "release";
      } else {
        request = { select: asked.to };
      }
      focus = { ids: readOrAdd(ids), atEnd: false };
    }

    var filterMoved = false;
    if (playlist !== history.cur) {
      history = { prev: history.cur, cur: playlist };
      filterMoved = true;
    }

    if (fired(ids.save_result, "data") && saveResult) {
      if (!nextEditor) {
        // A second press answered after the first closed the editor.
      } else if (saveResult.ok && saveResult.via === "card" && current !== saveResult.text) {
        // Typed into while the save was on its way: what was saved is now
        // the text the editor holds against.
        nextEditor = { scenario: nextEditor.scenario, opened: saveResult.text };
        error = "";
      } else if (saveResult.ok) {
        if (saveResult.via === "dialog") {
          answer("go");
        } else {
          closeEditor();
          if (waiting) {
            request = { release: true };
          }
          focus = {
            ids: note && note.state === "missing" ? [ids.add] : [ids.edit],
            atEnd: false,
          };
        }
      } else {
        error = saveResult.error;
        if (saveResult.via === "dialog") {
          answer("stay");
        }
      }
    }

    if (fired(ids.keep, "n_clicks") && keepClicks && nextDialog) {
      answer("stay");
    }
    if (fired(ids.dialog, "opened") && dialogOpened === false && nextDialog) {
      answer("stay");
    }
    if (fired(ids.discard, "n_clicks") && discardClicks && nextDialog) {
      answer("go");
    }

    if (fired(ids.cancel, "n_clicks") && cancelClicks && nextEditor) {
      closeEditor();
      if (waiting) {
        request = { release: true };
      }
      focus = {
        ids: note && note.state === "missing" ? [ids.add] : [ids.edit],
        atEnd: false,
      };
    }

    var opening =
      (fired(ids.edit, "n_clicks") && editClicks) ||
      (fired(ids.add, "n_clicks") && addClicks);
    if (
      opening &&
      !nextEditor &&
      nextShown &&
      note &&
      note.scenario === nextShown &&
      note.state !== "future" &&
      note.state !== "none"
    ) {
      var openedWith = note.state === "note" ? note.text : "";
      nextEditor = { scenario: nextShown, opened: openedWith };
      text = openedWith;
      current = openedWith;
      error = "";
      focus = { ids: [ids.draft], atEnd: true };
    }

    if (fired(ids.held, "data") && held) {
      if (!hasUnsavedChanges(nextEditor, current)) {
        // Clean again by the time it was asked: nothing to ask about.
        if (held.kind === "leave") {
          guardCall = "release";
        } else {
          request = { select: held.to };
        }
      } else if (!nextDialog) {
        nextDialog = {
          kind: held.kind || "list",
          from: nextEditor.scenario,
          to: held.to || null,
        };
        opened = true;
      }
    }

    if (
      fired(ids.waiting, "data") &&
      waiting &&
      !request &&
      !hasUnsavedChanges(nextEditor, current)
    ) {
      // Held while the text differed, answered once it no longer does.
      request = { release: true };
    }

    if (
      fired(ids.draft, "value") &&
      nextEditor &&
      waiting &&
      !nextDialog &&
      !request &&
      current === nextEditor.opened
    ) {
      // Every change undone while a run waits: nothing is left to protect.
      closeEditor();
      request = { release: true };
      focus = { ids: readOrAdd(ids), atEnd: false };
    }

    var selectionChanged =
      firstCall ||
      fired(ids.scenario_dropdown, "value") ||
      fired(ids.playlist_filter, "value");
    var onScenario = scenario === undefined ? null : scenario;
    if (selectionChanged && onScenario !== nextShown) {
      if (hasUnsavedChanges(nextEditor, current)) {
        if (!nextDialog) {
          var dropped = onScenario === null || onScenario === "";
          nextDialog = {
            kind: dropped ? "filter" : "pick",
            from: nextEditor.scenario,
            to: dropped ? null : onScenario,
            restore: {
              scenario: nextEditor.scenario,
              playlist: dropped || filterMoved ? history.prev : history.cur,
            },
          };
          opened = true;
        }
      } else {
        closeEditor();
        nextShown = onScenario;
      }
    }

    var unsaved = hasUnsavedChanges(nextEditor, current);
    var count = "";
    if (nextEditor && current.length >= config.countFrom) {
      count = config.count.replace("{count}", current.length.toLocaleString("en-US"));
    }

    window.scenarioNotes.track(unsaved);
    if (request) {
      window.dash_clientside.set_props(ids.go, { data: request });
    }
    if (guardCall === "release") {
      window.scenarioNotes.release();
    } else if (guardCall === "stay") {
      window.scenarioNotes.stay();
    }
    if (focus) {
      focusSoon(focus.ids, focus.atEnd);
    }

    function out(value, previous) {
      return value === NO_UPDATE || value === previous ? noUpdate() : value;
    }
    return [
      out(nextEditor, editor || null),
      out(nextShown, shown === undefined ? null : shown),
      out(nextDialog, dialog || null),
      out(opened),
      out(text),
      nextEditor ? "true" : "false",
      unsaved ? "true" : "false",
      nextEditor ? nextEditor.scenario : "",
      nextDialog ? "true" : "false",
      out(error),
      count,
      out(history, filterHistory),
      nextDialog && nextDialog !== (dialog || null)
        ? questionFor(config, nextDialog)
        : noUpdate(),
      fired(ids.waiting, "data") || firstCall
        ? waiting
          ? filled(config.waiting, { scenario: waiting })
          : null
        : noUpdate(),
    ];
  }

  // Fade a note cut off at the card's bottom. Measured once the text is
  // drawn, and again whenever the text's box changes size, since the card's
  // width decides where its lines break.
  function fade(_children, config) {
    var id = config.ids.text;
    function measure() {
      var element = document.getElementById(id);
      if (!element) {
        return;
      }
      if (!element.__scenarioNoteFade && window.ResizeObserver) {
        element.__scenarioNoteFade = new window.ResizeObserver(measure);
        element.__scenarioNoteFade.observe(element);
      }
      var clipped = element.scrollHeight > element.clientHeight + 1;
      element.setAttribute("data-clipped", clipped ? "true" : "false");
    }
    window.requestAnimationFrame(measure);
    return noUpdate();
  }

  window.dash_clientside = window.dash_clientside || {};
  window.dash_clientside.scenario_notes = {
    controller: controller,
    fade: fade,
  };
})();
