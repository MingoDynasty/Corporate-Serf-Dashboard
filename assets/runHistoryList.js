// The Run History page's run list: one flat AG Grid made to read as a list of
// sessions with rows under each. Under This scenario a session's runs of the
// scenario are under it. Under All scenarios a session's scenarios are, one
// row per visit, and each one's runs are under that. The rows are built on
// the server (source/components/run_history_list.py) and reach this script as
// data. Every string it shows comes with the rows or with the grid's
// `context`, so no copy lives here.
//
// AG Grid's tree and grouping features are paid, so the grouping is built
// from free parts, each of which an AG Grid upgrade can break:
//   1. A session row and a scenario row are full-width rows with their own
//      renderer. A full-width row has no cells, so its `gridcell` role is
//      added here by hand, and the grid does not work its row class rules
//      out again when its data changes, so a scenario row's band is drawn
//      here too.
//   2. Opening and closing is an external filter over a Set of open row ids,
//      one Set for each view. A row under a scenario row shows while its
//      session row and its scenario row are both open. Every row of every
//      loaded session is always in the grid, and what is open never leaves
//      the browser.
//   3. The current session is a pinned top row. The pinned row and the body
//      rows have to change together, so rows go in through the grid's API and
//      not through the `rowData` prop: two props would be two renders, with
//      the current session shown over another session's runs between them.
//   4. `embedFullWidthRows` and `ensureDomOrder`, set with the grid, put the
//      two kinds of row in one container in reading order.
//   5. Enter, Space, Left, and Right on a session row or a scenario row are
//      handled here.
//   6. Tab into a full-width row's buttons needs a listener that runs before
//      the grid's own, which skips from a full-width row to the next cell.
//   7. Sorting is off on every column, set with the grid.
//   8. The column widths are fixed and leave room for the scrollbar, set
//      with the grid.
//   9. After new rows are applied, focus goes back to the same row id, and to
//      the same button in it. The grid holds focus by position, so a run that
//      lands would otherwise leave a keyboard user on a different run, and a
//      press on a scenario's name, which rebuilds the rows, on the row's
//      first button.
//  10. A row's height follows the Median and best checkbox. The grid
//      measures the body's rows again when asked, and the pinned row only
//      when its rows are handed in again.
(function () {
  var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});
  var dagcomponentfuncs = (window.dashAgGridComponentFunctions =
    window.dashAgGridComponentFunctions || {});
  var h = function () {
    return window.React.createElement.apply(null, arguments);
  };

  var SESSION = "session";
  var SCENARIO = "scenario";
  var RUN = "run";
  var MORE = "more";
  var ROW_HEIGHTS = {
    session: 32,
    scenario: 28,
    run: 26,
    divider: 22,
    date: 24,
    note: 26,
    more: 44,
  };
  // What a row's second line adds, while Median and best is on.
  var SECOND_LINE_HEIGHT = 16;

  var state = (window.runHistoryList = {
    // The grid the state below belongs to. The page is drawn again on every
    // visit, with a new grid, and which rows are open is not remembered.
    api: null,
    // One per view: its open rows, its mark, and whether its rows have
    // arrived yet in this visit. The mark is the newest run whose rows the
    // view has opened. Each view keeps its own because a batch can hold runs
    // on two scenarios, and runs land while the other view is on screen: the
    // view opens the rows of every run newer than its own mark when its rows
    // next arrive, and a row the player closed, whose run is at or below the
    // mark, is not opened again.
    views: {},
    // The view whose rows the grid holds.
    view: undefined,
    // The run the visit's first model named, where every view's mark starts.
    started: false,
    firstRun: undefined,
    // The newest run any model named, which tells a run that just landed.
    newestRun: undefined,
    sessionIds: [],
    // Each session row's scenario rows, under All scenarios.
    children: {},
    sessionLimit: 0,
    // Whether Median and best is on. Not the grid's: the checkbox is set as
    // the page mounts, and it lasts across a new grid.
    figures: false,
    // A session asked for from its count, opened when the tree arrives.
    jump: null,
    expandLabel: undefined,
    // One per mounted full-width row, so each redraws when a row opens or
    // closes.
    listeners: new Set(),
  });

  function contextOf(api) {
    return api.getGridOption("context") || {};
  }

  function notify() {
    state.listeners.forEach(function (listener) {
      listener();
    });
  }

  function viewState(name) {
    if (!state.views[name]) {
      state.views[name] = { open: new Set(), mark: state.firstRun, arrived: false };
    }
    return state.views[name];
  }

  function openRows() {
    return viewState(state.view).open;
  }

  function isTree(context) {
    return state.view === context.treeView;
  }

  function allOpen() {
    var open = openRows();
    return (
      state.sessionIds.length > 0 &&
      state.sessionIds.every(function (id) {
        return open.has(id);
      })
    );
  }

  // The button reads what a press would do, so its label follows every way a
  // row can open or close, and not only its own presses.
  function updateExpandLabel(context) {
    var labels = context.labels || {};
    var label = allOpen() ? labels.collapseAll : labels.expandAll;
    if (label !== state.expandLabel) {
      state.expandLabel = label;
      window.dash_clientside.set_props(context.expandAllId, { children: label });
    }
  }

  function setOpen(api, ids, open) {
    var rows = openRows();
    ids.forEach(function (id) {
      if (open) {
        rows.add(id);
      } else {
        rows.delete(id);
      }
    });
    notify();
    api.onFilterChanged();
    updateExpandLabel(contextOf(api));
  }

  // Said through a live region because the open state sits on the button
  // inside the row, and a key pressed on the row itself changes it with focus
  // still on the row, where a screen reader hears nothing change. Emptied
  // first: the same word twice in a row is no change, and would go unsaid.
  // Emptied again once said, so the word is not left in the page for a
  // reader to come across later.
  var announcement = 0;
  function announce(context, text) {
    var region = document.getElementById(context.announcerId);
    if (!region || !text) {
      return;
    }
    announcement += 1;
    var mine = announcement;
    region.textContent = "";
    window.setTimeout(function () {
      if (mine === announcement) {
        region.textContent = text;
      }
    }, 50);
    window.setTimeout(function () {
      if (mine === announcement) {
        region.textContent = "";
      }
    }, 2000);
  }

  function showOlderSessions(context) {
    window.dash_clientside.set_props((context.limitStoreIds || {})[state.view], {
      data: state.sessionLimit + context.sessionsPerLoad,
    });
  }

  // ---- Grid option functions, named bare in {"function": ...} ----
  dagfuncs.runListIsFullWidth = function (params) {
    return params.rowNode.data.kind !== RUN;
  };
  dagfuncs.runListFilterPass = function (node) {
    var data = node.data;
    if (data.kind === SESSION || data.kind === MORE) {
      return true;
    }
    var open = openRows();
    return open.has(data.sid) && (data.vid == null || open.has(data.vid));
  };
  // The figures are on a row whether it is open or closed, so a row's height
  // follows the checkbox and never a click.
  dagfuncs.runListRowHeight = function (params) {
    var data = params.data;
    var height = ROW_HEIGHTS[data.kind] || ROW_HEIGHTS.run;
    return state.figures && data.figures ? height + SECOND_LINE_HEIGHT : height;
  };
  dagfuncs.runListRowClass = function (params) {
    return "run-list-row-" + params.data.kind;
  };
  // A key pressed on the row itself. A key pressed on a button inside the row
  // is the button's own.
  dagfuncs.runListKeyDown = function (params) {
    var event = params.event;
    var data = params.node && params.node.data;
    if (!event || !data || event.target.closest("button")) {
      return;
    }
    var key = event.key;
    var context = contextOf(params.api);
    if (data.kind === MORE) {
      if (key === "Enter" || key === " ") {
        event.preventDefault();
        showOlderSessions(context);
      }
      return;
    }
    if (data.kind !== SESSION && data.kind !== SCENARIO) {
      return;
    }
    var open = openRows().has(data.id);
    if (
      key === "Enter" ||
      key === " " ||
      (key === "ArrowRight" && !open) ||
      (key === "ArrowLeft" && open)
    ) {
      event.preventDefault();
      setOpen(params.api, [data.id], !open);
      var labels = context.labels || {};
      announce(context, open ? labels.collapsed : labels.expanded);
    }
  };

  // Runs in the capture phase, ahead of the grid: Tab from a full-width row
  // goes to the button inside it, and Tab from that button to the row below,
  // which the grid would not do from inside a row.
  function onTab(event) {
    if (event.key !== "Tab" || !state.api) {
      return;
    }
    var row = event.target.closest(".ag-full-width-row");
    if (!row) {
      return;
    }
    var stops = Array.prototype.slice.call(row.querySelectorAll("button"));
    var at = stops.indexOf(event.target);
    var next;
    if (event.shiftKey) {
      next = at > 0 ? stops[at - 1] : at === 0 ? row : null;
    } else {
      next = stops[at + 1];
    }
    if (next) {
      event.preventDefault();
      event.stopPropagation();
      next.focus();
      return;
    }
    if (!event.shiftKey && at >= 0) {
      var api = state.api;
      var pinned = !!row.closest(".ag-floating-top");
      var index = pinned ? 0 : Number(row.getAttribute("row-index")) + 1;
      var columns = api.getAllDisplayedColumns();
      if (index < api.getDisplayedRowCount() && columns.length) {
        event.preventDefault();
        event.stopPropagation();
        api.setFocusedCell(index, columns[0]);
      }
    }
  }

  // ---- Renderers ----
  // The check and the star. A cell with no check is blank to the eye, and
  // says why on hover and to a screen reader.
  dagcomponentfuncs.RunListMarks = function (props) {
    var data = props.data;
    if (!data) {
      return null;
    }
    var labels = (props.context && props.context.labels) || {};
    return h(
      "span",
      { className: "run-list-marks", title: data.passed ? undefined : data.check_text },
      data.passed
        ? h(
            "span",
            {
              className: "run-list-check",
              role: "img",
              "aria-label": data.check_text,
              title: data.check_text,
            },
            "✓"
          )
        : h("span", { className: "visually-hidden" }, data.check_text),
      data.new_pb ? star(labels) : null
    );
  };

  function star(labels) {
    return h(
      "span",
      {
        className: "run-list-star",
        role: "img",
        "aria-label": labels.newPb,
        title: labels.newPb,
      },
      "★"
    );
  }

  function wideCell(props, className, extra, children) {
    var attributes = {
      className: "run-list-wide " + className,
      role: "gridcell",
      "aria-colspan": props.api.getAllDisplayedColumns().length,
    };
    Object.keys(extra || {}).forEach(function (key) {
      attributes[key] = extra[key];
    });
    return h.apply(null, ["div", attributes].concat(children));
  }

  // A session row's parts are flex items with no text between them, and
  // Chrome and Edge hand a screen reader their text joined up: "2:22 AMIn
  // progress" (NVDA, 2026-10-13). A space between the items does nothing,
  // because a flex container drops it. This one sits inside a part, at its
  // end, where the stylesheet keeps it and gives it no size.
  function partEnd() {
    return h("span", { className: "run-list-part-end" }, " ");
  }

  // A group row: its first line, and under it the row's figures while Median
  // and best is on. The figures line is told from the first by its own
  // part end, for the reason partEnd gives.
  function groupRow(props, className, toggle, line, figures) {
    var shown = state.figures && figures;
    return wideCell(props, "run-list-group " + className, { onClick: toggle }, [
      h.apply(null, ["div", { className: "run-list-line" }].concat(line, shown ? [partEnd()] : [])),
      shown ? h("div", { className: "run-list-figures" }, figures) : null,
    ]);
  }

  function toggleButton(label, open, toggle) {
    return h(
      "button",
      {
        type: "button",
        className: "run-list-toggle mantine-focus-auto",
        // Not the row's name: the row already reads it out, and a button
        // named for the row would say the name twice.
        "aria-label": label,
        "aria-expanded": open,
        "data-part": "toggle",
        tabIndex: -1,
        onClick: toggle,
      },
      open ? "▾" : "▸"
    );
  }

  // A button drawn as the app draws a link: it changes what the page shows
  // and goes nowhere.
  function linkButton(className, part, extra, onClick, text) {
    var attributes = {
      type: "button",
      className: "run-list-link mantine-focus-auto " + className,
      "data-part": part,
      tabIndex: -1,
      onClick: function (event) {
        event.stopPropagation();
        onClick();
      },
    };
    Object.keys(extra || {}).forEach(function (key) {
      attributes[key] = extra[key];
    });
    return h("button", attributes, text);
  }

  function scenarioRow(props, context, labels) {
    var data = props.data;
    var api = props.api;
    var open = openRows().has(data.id);
    function toggle(event) {
      event.stopPropagation();
      setOpen(api, [data.id], !open);
    }
    // The page's one callback that writes the scenario dropdown reads which
    // of its inputs called, so the store is written whatever it held before.
    function select() {
      window.dash_clientside.set_props(context.askStoreId, { data: data.name });
      announce(context, data.selected_text);
    }
    return groupRow(
      props,
      // The band is drawn here and not by the grid's row class rule, which
      // the grid works out again when a row's data changes but not for a
      // full-width row (AG Grid 35.3): the rule's band stayed on the
      // scenario selected before. React redraws this class in place.
      data.sel ? "run-list-scenario run-list-scenario-selected" : "run-list-scenario",
      toggle,
      [
        toggleButton(labels.scenario, open, toggle),
        h(
          "span",
          // The hover gives the whole name, which the row may cut short. On
          // the part, not the button: a button whose hover differs from its
          // name is read with both.
          { className: "run-list-scenario-title", title: data.name },
          h("span", { className: "run-list-scenario-number" }, data.number + ".", partEnd()),
          linkButton(
            "run-list-scenario-name",
            "name",
            {
              "aria-label": data.name_label,
              "aria-current": data.sel ? "true" : undefined,
            },
            select,
            data.name
          )
        ),
        h(
          "span",
          { className: "run-list-group-facts" },
          data.counts,
          data.new_pb ? " " : null,
          data.new_pb ? star(labels) : null
        ),
      ],
      data.figures
    );
  }

  function sessionRow(props, context, labels) {
    var data = props.data;
    var api = props.api;
    var open = openRows().has(data.id);
    function toggle(event) {
      event.stopPropagation();
      setOpen(api, [data.id], !open);
    }
    // The tree arrives through the server, which also moves the switch: see
    // register_run_list. What to open and where to scroll stay here.
    function jump() {
      state.jump = { session: data.id };
      window.dash_clientside.set_props(context.jumpStoreId, { data: { place: data.place } });
    }
    var counts =
      data.place != null
        ? linkButton("run-list-count", "count", { title: labels.wholeSession }, jump, data.counts)
        : data.counts;
    var line = [
      toggleButton(labels.session, open, toggle),
      h("span", { className: "run-list-session-name" }, data.name, partEnd()),
      data.in_progress
        ? h("span", { className: "run-list-in-progress" }, labels.inProgress, partEnd())
        : null,
      h(
        "span",
        { className: "run-list-group-facts" },
        data.length
          ? h("span", { title: data.length_help ? labels.lengthHelp : undefined }, data.length)
          : null,
        data.length ? " · " : null,
        counts
      ),
    ];
    var kids = state.children[data.id] || [];
    if (isTree(context) && open && kids.length) {
      var rows = openRows();
      var allKidsOpen = kids.every(function (id) {
        return rows.has(id);
      });
      line.push(
        linkButton(
          "run-list-show-all",
          "all",
          null,
          function () {
            setOpen(api, kids, !allKidsOpen);
            announce(context, allKidsOpen ? labels.collapsed : labels.expanded);
          },
          allKidsOpen ? labels.hideAllRuns : labels.showAllRuns
        )
      );
    }
    return groupRow(props, "run-list-session", toggle, line, data.figures);
  }

  dagcomponentfuncs.RunListWideRow = function (props) {
    var data = props.data;
    var context = props.context || {};
    var labels = context.labels || {};
    var redraw = window.React.useReducer(function (count) {
      return count + 1;
    }, 0)[1];
    window.React.useEffect(function () {
      state.listeners.add(redraw);
      return function () {
        state.listeners.delete(redraw);
      };
    }, []);

    if (data.kind === MORE) {
      return wideCell(props, "run-list-more", null, [
        h(
          "button",
          {
            type: "button",
            className: "run-list-more-button mantine-focus-auto",
            tabIndex: -1,
            onClick: function () {
              showOlderSessions(context);
            },
          },
          data.text
        ),
      ]);
    }
    if (data.kind === SESSION) {
      return sessionRow(props, context, labels);
    }
    if (data.kind === SCENARIO) {
      return scenarioRow(props, context, labels);
    }
    return wideCell(props, "run-list-" + data.kind, null, [
      h("span", { className: "run-list-wide-text" }, data.text),
    ]);
  };

  // ---- Keeping focus on the same row, and the same button in it ----
  function focusedRow(api, gridElement) {
    var active = document.activeElement;
    if (!gridElement || !active || !gridElement.contains(active) || !active.closest(".ag-row")) {
      return null;
    }
    var cell = api.getFocusedCell();
    if (!cell) {
      return null;
    }
    var node =
      cell.rowPinned === "top"
        ? api.getPinnedTopRow(cell.rowIndex)
        : api.getDisplayedRowAtIndex(cell.rowIndex);
    if (!node || !node.data) {
      return null;
    }
    var button = active.closest("button");
    return {
      id: node.data.id,
      kind: node.data.kind,
      column: cell.column,
      part: button ? button.getAttribute("data-part") || "" : null,
    };
  }

  function rowElement(gridElement, id) {
    var rows = gridElement.querySelectorAll(".ag-row");
    for (var index = 0; index < rows.length; index += 1) {
      if (rows[index].getAttribute("row-id") === id) {
        return rows[index];
      }
    }
    return null;
  }

  function restoreFocus(api, gridElement, focus) {
    // After Show older sessions the row at the button's old place is the
    // first of the sessions it loaded, which is where a reader wants to be.
    if (!focus || focus.kind === MORE) {
      return;
    }
    var pinned = api.getPinnedTopRow(0);
    var node = pinned && pinned.data && pinned.data.id === focus.id ? pinned : api.getRowNode(focus.id);
    if (!node || node.rowIndex == null || (!node.rowPinned && !node.displayed)) {
      return;
    }
    // A row outside the rows the grid has drawn cannot take focus.
    if (!node.rowPinned && api.getRenderedNodes().indexOf(node) < 0) {
      api.ensureIndexVisible(node.rowIndex);
    }
    api.setFocusedCell(node.rowIndex, focus.column, node.rowPinned || undefined);
    if (focus.part != null) {
      var row = rowElement(gridElement, node.id);
      var button =
        row &&
        ((focus.part && row.querySelector('button[data-part="' + focus.part + '"]')) ||
          row.querySelector("button"));
      if (button) {
        button.focus();
      }
    }
  }

  // ---- Which rows a model opens ----
  // Under This scenario, the first row, as built. Under All scenarios, the
  // session row and the scenario row of each run newer than the view's mark,
  // found by walking the run rows from the top, which are newest first, down
  // to the mark. The first time the view's rows arrive, unless they arrive
  // for a jump, the rows of the run at the mark open too. Where the walk
  // cannot find the mark, as when the store had no run when the page was
  // drawn, the newest run's rows open alone.
  function rowsToOpen(context, model, rows, mark, arriving) {
    if (model.view !== context.treeView) {
      return model.forced_open || [];
    }
    var markRow = mark == null ? null : context.runRowIdPrefix + mark;
    var ids = [];
    for (var index = 0; index < rows.length; index += 1) {
      var row = rows[index];
      if (row.kind !== RUN) {
        continue;
      }
      if (row.id === markRow) {
        if (arriving) {
          ids.push(row.sid, row.vid);
        }
        return ids;
      }
      ids.push(row.sid, row.vid);
    }
    return model.forced_open || [];
  }

  // ---- A jump from a session's count ----
  // The session's row goes to the top of the list, just under the first row,
  // and takes keyboard focus: the count that was pressed is not in the tree,
  // and focus would otherwise fall to the page. A tree that does not hold the
  // session shows from its top, with focus on its first row.
  function placeJump(api, jump) {
    var pinned = api.getPinnedTopRow(0);
    var node = api.getRowNode(jump.session);
    var target = pinned;
    if (node && node.displayed && node.rowIndex != null) {
      api.ensureNodeVisible(node, "top");
      target = node;
    } else if (api.getDisplayedRowCount() > 0) {
      api.ensureIndexVisible(0, "top");
    }
    var columns = api.getAllDisplayedColumns();
    if (target && target.rowIndex != null && columns.length) {
      api.setFocusedCell(target.rowIndex, columns[0], target.rowPinned || undefined);
    }
  }

  // ---- Applying a model from the server ----
  state.apply = function (api, model, follow) {
    var context = contextOf(api);
    var labels = context.labels || {};
    if (state.api !== api) {
      state.api = api;
      state.views = {};
      state.view = undefined;
      state.started = false;
      state.newestRun = undefined;
      state.jump = null;
      state.expandLabel = labels.expandAll;
      // A full-width row spans the columns shown, and the grid does not
      // draw it again when the Columns menu hides one.
      api.addEventListener("displayedColumnsChanged", notify);
    }
    var gridElement = document.getElementById(context.gridId);
    if (gridElement && !gridElement.__runListTab) {
      gridElement.__runListTab = true;
      gridElement.addEventListener("keydown", onTab, true);
    }

    var rows = model.rows || [];
    // Every view's mark starts at the run the visit's first model names,
    // whichever view it is for and whether or not it lists anything.
    if (!state.started) {
      state.started = true;
      state.firstRun = model.newest_run;
    }
    var landed =
      model.newest_run != null && state.newestRun != null && model.newest_run !== state.newestRun;
    if (model.newest_run != null) {
      state.newestRun = model.newest_run;
    }
    var changedView = model.view !== state.view;
    state.view = model.view;
    var view = viewState(model.view);
    // A model with nothing to list is not the view's rows arriving.
    if (rows.length && model.newest_run != null) {
      // Rows that first arrive for a jump open what the jump opens, and the
      // rows of runs newer than the mark, and not the mark's own: those would
      // open another scenario's visit under a session followed from a count
      // such as `0 of 47 runs`, which opens nothing under it.
      var arriving = !view.arrived && !(state.jump && model.view === context.treeView);
      if (!view.arrived || model.newest_run !== view.mark) {
        rowsToOpen(context, model, rows, view.mark, arriving).forEach(function (id) {
          view.open.add(id);
        });
        view.mark = model.newest_run;
      }
      view.arrived = true;
    }
    var jump = null;
    if (state.jump && model.view === context.treeView && rows.length) {
      jump = state.jump;
      state.jump = null;
      rows.forEach(function (row) {
        if (row.id === jump.session || (row.kind === SCENARIO && row.sid === jump.session && row.sel)) {
          view.open.add(row.id);
        }
      });
    }
    state.sessionLimit = model.session_limit;
    state.sessionIds = [];
    state.children = {};
    rows.forEach(function (row) {
      if (row.kind === SESSION) {
        state.sessionIds.push(row.id);
      } else if (row.kind === SCENARIO) {
        (state.children[row.sid] = state.children[row.sid] || []).push(row.id);
      }
    });

    // A view that was not on screen shows from its top, with focus left on
    // the switch that changed it.
    var focus = changedView ? null : focusedRow(api, gridElement);
    api.updateGridOptions({ pinnedTopRowData: rows.slice(0, 1), rowData: rows.slice(1) });
    notify();
    api.onFilterChanged();
    if (jump) {
      placeJump(api, jump);
    } else if (changedView) {
      if (api.getDisplayedRowCount() > 0) {
        api.ensureIndexVisible(0, "top");
      }
    } else {
      restoreFocus(api, gridElement, focus);
      if (landed && follow && api.getDisplayedRowCount() > 0) {
        api.ensureIndexVisible(0, "top");
      }
    }

    var grid = gridElement && gridElement.querySelector('[role="grid"], [role="treegrid"]');
    if (grid) {
      if (model.grid_name) {
        grid.setAttribute("aria-label", model.grid_name);
      } else {
        grid.removeAttribute("aria-label");
      }
    }
    updateExpandLabel(context);
  };

  // Expand all opens every loaded session of the view on screen, down to its
  // scenario rows under All scenarios, and closes them all once every one is
  // open. It leaves the scenario rows' own state alone. It says so through
  // the live region: the press changes the button's own name, which Chrome
  // and Edge do not report to a screen reader, so there the press would be
  // silent.
  state.toggleAll = function (api) {
    var opening = !allOpen();
    setOpen(api, state.sessionIds, opening);
    var context = contextOf(api);
    var labels = context.labels || {};
    announce(context, opening ? labels.expanded : labels.collapsed);
  };

  // Median and best turned on or off. The figures are always in the rows, so
  // this makes no request: the rows are drawn again, and the grid measures
  // their heights again.
  state.setFigures = function (api, on) {
    if (state.figures === on) {
      return;
    }
    state.figures = on;
    notify();
    api.resetRowHeights();
    // That call measures the body's rows and leaves the pinned row alone,
    // which is in a row model of its own. Handed in again, it is measured
    // too (AG Grid 35.3, 2026-10-14).
    var pinned = api.getPinnedTopRow(0);
    if (pinned && pinned.data) {
      api.updateGridOptions({ pinnedTopRowData: [pinned.data] });
    }
  };
})();
