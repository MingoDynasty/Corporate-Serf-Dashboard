// The Run History page's run viewer (source/components/run_viewer_panel.py):
// one run in the chart's place until it is closed. The server decides what
// opens and closes it and draws it. This script asks it for a run, closes the
// run on Esc, and once a change is drawn moves focus and marks the run's row
// in the list (assets/runHistoryList.js). It also gives By Bot's grid its name
// order. The viewer's root names the store a request goes to and the control
// focus returns to, in its data- attributes.
(function () {
  function viewer() {
    return document.querySelector(".run-viewer[data-request-store]");
  }

  function isOpen(root) {
    return Boolean(root && root.closest(".run-viewer-open"));
  }

  function visible(element) {
    return element.getClientRects().length > 0;
  }

  // Asked by a Run row ("list") or a chart point ("chart"). The time makes
  // each press a new value, so the same run asked for again after a close
  // still reaches the server.
  function request(runId, from) {
    var root = viewer();
    if (!root || !window.dash_clientside) {
      return;
    }
    window.dash_clientside.set_props(root.getAttribute("data-request-store"), {
      data: { run_id: runId, from: from, at: Date.now() },
    });
  }

  function isTextField(element) {
    if (!element) {
      return false;
    }
    if (element.isContentEditable) {
      return true;
    }
    var tag = element.tagName;
    if (tag === "TEXTAREA" || tag === "SELECT") {
      return true;
    }
    return (
      tag === "INPUT" &&
      !/^(button|checkbox|color|file|image|radio|range|reset|submit)$/i.test(element.type)
    );
  }

  // A dialog, menu or dropdown on screen: the note dialog, a Select's list,
  // the Columns menu. Mantine draws them in a portal, and closes one on Esc
  // itself; some stay mounted while hidden, so only a drawn one counts. A
  // group row's toggle in the list is expanded too, but has no popup.
  function overlayOpen() {
    if (document.querySelector('[aria-haspopup][aria-expanded="true"]')) {
      return true;
    }
    var overlays = document.querySelectorAll(
      '[role="dialog"], [role="alertdialog"], [role="menu"], [role="listbox"]'
    );
    return Array.prototype.some.call(overlays, visible);
  }

  // In the capture phase on the window, ahead of Mantine's own handlers: an
  // overlay that Esc closes is still open when this runs, so the same press
  // never closes the run too.
  window.addEventListener(
    "keydown",
    function (event) {
      if (
        event.key !== "Escape" ||
        event.isComposing ||
        event.altKey ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey
      ) {
        return;
      }
      var root = viewer();
      if (!isOpen(root) || isTextField(document.activeElement) || overlayOpen()) {
        return;
      }
      var close = root.querySelector(".run-viewer-close");
      if (close) {
        close.click();
      }
    },
    true
  );

  // Focus a control once the change that shows it is drawn. Dash runs this
  // after the server's answer is applied, and a frame later the column's
  // class has taken effect.
  function focusWhenShown(find) {
    var frames = 0;
    function attempt() {
      var target = find();
      if (target && visible(target)) {
        target.focus();
      } else if (frames < 10) {
        frames += 1;
        window.requestAnimationFrame(attempt);
      }
    }
    window.requestAnimationFrame(attempt);
  }

  function chartModeControl(root) {
    var control = document.getElementById(root.getAttribute("data-return-focus"));
    return control && (control.querySelector("input:checked") || control.querySelector("input"));
  }

  // ``shown`` is what the server drew: the open run, or none, what focus
  // does next, and the run the change was about.
  function shown(change) {
    var root = viewer();
    var list = window.runHistoryList;
    if (window.runHistoryHover) {
      window.runHistoryHover.clear();
    }
    if (list) {
      list.markOpen(change.open);
    }
    if (change.open && root) {
      // A run starts from its top, the one switched to included.
      root.scrollTop = 0;
    }
    if (change.focus === "close") {
      focusWhenShown(function () {
        return root && root.querySelector(".run-viewer-close");
      });
    } else if (change.focus === "row" || change.focus === "chart") {
      // The row that opened the run, when it is still in the view on screen
      // and its group is open. Otherwise the chart's mode control.
      if (change.focus === "row" && list && list.focusRun(change.run)) {
        return;
      }
      focusWhenShown(function () {
        return root && chartModeControl(root);
      });
    }
  }

  window.runViewer = { request: request, shown: shown };

  // By Bot's grid sorts its Bot column in the server's name order, which puts
  // "Bot 2" before "Bot 10", so a sort by name and the default order agree.
  var functions = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});
  functions.runViewerBotNameComparator = function (valueA, valueB, nodeA, nodeB) {
    return nodeA.data.bot_order - nodeB.data.bot_order;
  };
})();
