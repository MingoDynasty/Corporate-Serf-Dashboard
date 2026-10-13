// The Run History page's run list: one flat AG Grid made to read as a list of
// sessions with each session's runs under it. The rows are built on the
// server (source/components/run_history_list.py) and reach this script as
// data. Every string it shows comes with the rows or with the grid's
// `context`, so no copy lives here.
//
// AG Grid's tree and grouping features are paid, so the grouping is built
// from free parts, each of which an AG Grid upgrade can break:
//   1. A session row is a full-width row with its own renderer. A full-width
//      row has no cells, so its `gridcell` role is added here by hand.
//   2. Opening and closing is an external filter over a Set of open session
//      row ids. Every row of every loaded session is always in the grid, and
//      what is open never leaves the browser.
//   3. The current session is a pinned top row. The pinned row and the body
//      rows have to change together, so rows go in through the grid's API and
//      not through the `rowData` prop: two props would be two renders, with
//      the current session shown over another session's runs between them.
//   4. `embedFullWidthRows` and `ensureDomOrder`, set with the grid, put the
//      two kinds of row in one container in reading order.
//   5. Enter, Space, Left, and Right on a session row are handled here.
//   6. Tab into a session row's button needs a listener that runs before the
//      grid's own, which skips from a full-width row to the next cell.
//   7. Sorting is off on every column, set with the grid.
//   8. The column widths are fixed and leave room for the scrollbar, set
//      with the grid.
//   9. After new rows are applied, focus goes back to the cell of the same
//      row id. The grid holds focus by position, so a run that lands would
//      otherwise leave a keyboard user on a different run.
(function () {
  var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});
  var dagcomponentfuncs = (window.dashAgGridComponentFunctions =
    window.dashAgGridComponentFunctions || {});
  var h = function () {
    return window.React.createElement.apply(null, arguments);
  };

  var SESSION = "session";
  var RUN = "run";
  var MORE = "more";
  var ROW_HEIGHTS = { session: 32, run: 26, divider: 22, date: 24, note: 26, more: 44 };

  var state = (window.runHistoryList = {
    // The grid the state below belongs to. The page is drawn again on every
    // visit, with a new grid, and which rows are open is not remembered.
    api: null,
    open: new Set(),
    // The newest run whose forced-open rows were applied.
    appliedRun: undefined,
    sessionIds: [],
    sessionLimit: 0,
    expandLabel: undefined,
    // One per mounted session row, so each redraws when a row opens or closes.
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

  function allOpen() {
    return (
      state.sessionIds.length > 0 &&
      state.sessionIds.every(function (id) {
        return state.open.has(id);
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
    ids.forEach(function (id) {
      if (open) {
        state.open.add(id);
      } else {
        state.open.delete(id);
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
    window.dash_clientside.set_props(context.limitStoreId, {
      data: state.sessionLimit + context.sessionsPerLoad,
    });
  }

  // ---- Grid option functions, named bare in {"function": ...} ----
  dagfuncs.runListIsFullWidth = function (params) {
    return params.rowNode.data.kind !== RUN;
  };
  dagfuncs.runListFilterPass = function (node) {
    var data = node.data;
    return data.kind === SESSION || data.kind === MORE || state.open.has(data.sid);
  };
  dagfuncs.runListRowHeight = function (params) {
    return ROW_HEIGHTS[params.data.kind] || ROW_HEIGHTS.run;
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
    if (data.kind !== SESSION) {
      return;
    }
    var open = state.open.has(data.id);
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
      data.new_pb
        ? h(
            "span",
            {
              className: "run-list-star",
              role: "img",
              "aria-label": labels.newPb,
              title: labels.newPb,
            },
            "★"
          )
        : null
    );
  };

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

  dagcomponentfuncs.RunListWideRow = function (props) {
    var data = props.data;
    var api = props.api;
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
    if (data.kind !== SESSION) {
      return wideCell(props, "run-list-" + data.kind, null, [
        h("span", { className: "run-list-wide-text" }, data.text),
      ]);
    }

    var open = state.open.has(data.id);
    function toggle(event) {
      event.stopPropagation();
      setOpen(api, [data.id], !open);
    }
    return wideCell(props, "run-list-session", { onClick: toggle }, [
      h(
        "button",
        {
          type: "button",
          className: "run-list-toggle mantine-focus-auto",
          // Not the session's name: the row already reads it out, and a
          // button named for the row would say the name twice.
          "aria-label": labels.session,
          "aria-expanded": open,
          tabIndex: -1,
          onClick: toggle,
        },
        open ? "▾" : "▸"
      ),
      h("span", { className: "run-list-session-name" }, data.name),
      data.in_progress
        ? h("span", { className: "run-list-in-progress" }, labels.inProgress)
        : null,
      h(
        "span",
        { className: "run-list-session-facts" },
        data.length ? h("span", { title: labels.lengthHelp }, data.length) : null,
        data.length ? " · " : null,
        data.counts
      ),
    ]);
  };

  // ---- Keeping focus on the same row ----
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
    return {
      id: node.data.id,
      kind: node.data.kind,
      column: cell.column,
      inButton: !!active.closest("button"),
    };
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
    if (focus.inButton) {
      var rows = gridElement.querySelectorAll(".ag-row");
      for (var index = 0; index < rows.length; index += 1) {
        if (rows[index].getAttribute("row-id") === node.id) {
          var button = rows[index].querySelector("button");
          if (button) {
            button.focus();
          }
          break;
        }
      }
    }
  }

  // ---- Applying a model from the server ----
  state.apply = function (api, model, follow) {
    var context = contextOf(api);
    var labels = context.labels || {};
    if (state.api !== api) {
      state.api = api;
      state.open = new Set();
      state.appliedRun = undefined;
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
    // A model with nothing to list names no run, and must not make the next
    // one look like an arrival.
    var landed = false;
    if (model.newest_run != null && model.newest_run !== state.appliedRun) {
      landed = state.appliedRun != null;
      (model.forced_open || []).forEach(function (id) {
        state.open.add(id);
      });
      state.appliedRun = model.newest_run;
    }
    state.sessionLimit = model.session_limit;
    state.sessionIds = rows
      .filter(function (row) {
        return row.kind === SESSION;
      })
      .map(function (row) {
        return row.id;
      });

    var focus = focusedRow(api, gridElement);
    api.updateGridOptions({ pinnedTopRowData: rows.slice(0, 1), rowData: rows.slice(1) });
    notify();
    api.onFilterChanged();
    restoreFocus(api, gridElement, focus);
    if (landed && follow && api.getDisplayedRowCount() > 0) {
      api.ensureIndexVisible(0, "top");
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

  // Expand all opens every loaded session, and closes them all once every
  // one is open.
  state.toggleAll = function (api) {
    setOpen(api, state.sessionIds, !allOpen());
  };
})();
