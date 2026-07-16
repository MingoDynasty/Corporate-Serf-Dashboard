// Custom AG Grid cell renderer components. This is a DIFFERENT registry from
// dashAgGridFunctions.js: colDef `"cellRenderer": "Name"` strings resolve
// against window.dashAgGridComponentFunctions and render as React components
// (window.React is provided by Dash). The bare-name rule for
// `{"function": ...}` expression strings (decision log 2026-06-20) applies to
// the other registry, not here.
var dagcomponentfuncs = (window.dashAgGridComponentFunctions =
  window.dashAgGridComponentFunctions || {});

// Benchmark/Playlist pill for the playlist overview's Type column; styled by
// the .type-badge rules in stylesheet.css.
dagcomponentfuncs.TypeBadge = function (props) {
  if (props.value === null || props.value === undefined || props.value === "") {
    return null;
  }
  return React.createElement(
    "span",
    { className: "type-badge type-badge-" + String(props.value).toLowerCase() },
    props.value
  );
};

// Hide/Unhide action for the playlist overview's visibility column. Clicks
// are handled server-side via the grid's cellClicked payload (colId
// "hidden"); this renderer only draws the eye icon (masked SVG, styled by
// the .visibility-action rules in stylesheet.css). Layers-panel convention:
// the eye mirrors the row's current state — open eye = visible (click
// hides), struck-out eye = hidden (click unhides) — while the column's
// tooltip carries the click consequence.
dagcomponentfuncs.VisibilityAction = function (props) {
  var hidden = props.data && props.data.hidden;
  return React.createElement("span", {
    className:
      "visibility-action " +
      (hidden ? "visibility-action-hidden" : "visibility-action-visible"),
    role: "img",
    "aria-label": hidden ? "Unhide" : "Hide",
  });
};

// Delete action for the playlist overview's delete column. Only user
// playlists are deletable (bundled benchmarks offer hide instead), so this
// renders nothing for non-deletable rows. The click is handled server-side
// via the grid's cellClicked payload (colId "deletable"), which opens a
// confirmation modal; this renderer only draws the link-styled label.
dagcomponentfuncs.DeleteAction = function (props) {
  if (!props.data || !props.data.deletable) {
    return null;
  }
  return React.createElement("span", { className: "delete-action" }, "Delete");
};

// Shared ref binder wiring the hybrid click behavior on the navigation anchors
// below. The handler is attached as a NATIVE listener on the anchor itself
// (not a React onClick), and that placement is load-bearing: AG Grid's
// cellClicked fires from a native listener on an ancestor, and a native
// listener on the anchor (the event target) runs first, whereas React's onClick
// is delegated at the app root and runs too late to influence it.
//   - Plain left-click: preventDefault() suppresses the native anchor and lets
//     the click bubble to cellClicked, which does the fast in-app nav.
//   - Modified click (Ctrl/Cmd/Shift/Alt): keep the native anchor default (open
//     a new tab) but stopPropagation() so cellClicked does NOT also navigate
//     the current tab.
// Middle-click arrives as auxclick, not click, so it never reaches this handler
// or cellClicked and stays native with no handling. The listener reads only the
// event's modifier flags, so it never goes stale as row data changes; the
// once-guard keeps a reused anchor node from stacking duplicate listeners.
function bindGridNavAnchor(element) {
  if (!element || element.__gridNavBound) {
    return;
  }
  element.__gridNavBound = true;
  element.addEventListener("click", function (event) {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
      event.stopPropagation();
    } else {
      event.preventDefault();
    }
  });
}

// Real anchor for the playlist overview's Playlist name column. The href is
// built here from the row's share code (the same value getRowId uses), so
// middle-click / Ctrl+click open the scenario table in a new tab and
// right-click offers Copy Link Address.
dagcomponentfuncs.PlaylistNameLink = function (props) {
  var code = props.data && props.data.code;
  var href = code ? "/playlists/" + encodeURIComponent(code) : undefined;
  return React.createElement(
    "a",
    {
      href: href,
      className: "playlist-scenario-link-cell",
      ref: bindGridNavAnchor,
    },
    props.value
  );
};

// Real anchor for the per-playlist Scenario column. The href is prebuilt
// server-side (row "href", via scenario_home_href) so query-string encoding
// stays in Python; this renderer only wires it to an anchor with the same
// hybrid click handling as PlaylistNameLink.
dagcomponentfuncs.ScenarioLink = function (props) {
  var href = (props.data && props.data.href) || undefined;
  return React.createElement(
    "a",
    {
      href: href,
      className: "playlist-scenario-link-cell",
      ref: bindGridNavAnchor,
    },
    props.value
  );
};
