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
    "aria-label": hidden ? "Show" : "Hide",
  });
};

// Delete action for the playlist overview's delete column. Only user
// playlists are deletable (bundled benchmarks offer hide instead), so this
// renders nothing for non-deletable rows. The click is handled server-side
// via the grid's cellClicked payload (colId "deletable"), which opens a
// confirmation modal; this renderer only draws the trash icon (masked SVG,
// styled by the .delete-action rules in stylesheet.css). The icon has no
// text label, so the column's tooltip carries the click consequence.
dagcomponentfuncs.DeleteAction = function (props) {
  if (!props.data || !props.data.deletable) {
    return null;
  }
  return React.createElement("span", {
    className: "delete-action",
    role: "img",
    "aria-label": "Delete",
  });
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

// The names of a row's groups, for the Scenario cell's second line. Empty
// unless the table is ungrouped: grouped, the group cells carry the labels.
// Only the levels whose columns are shown are named, read from the grid as the
// cell draws, so hiding a group column through the Columns menu drops its name
// here too. `groupLevels` comes from the column's cellRendererParams and is
// absent on a table without groups.
function scenarioGroupLine(props) {
  if (
    !props.groupLevels ||
    !props.api ||
    !props.context ||
    props.context.grouped !== false
  ) {
    return "";
  }
  var data = props.data || {};
  var names = [];
  props.groupLevels.forEach(function (level) {
    var column = props.api.getColumn(level.columnId);
    if (column && column.isVisible() && data[level.nameField]) {
      names.push(data[level.nameField]);
    }
  });
  return names.join(" \u00b7 ");
}

// Real anchor for the per-playlist Scenario column. The href is prebuilt
// server-side (row "href", via scenario_home_href) so query-string encoding
// stays in Python; this renderer only wires it to an anchor with the same
// hybrid click handling as PlaylistNameLink. While the table is ungrouped the
// anchor also holds the row's group names on a second line, so a click there
// navigates as a click on the name does, and the link's accessible name
// carries the group while the group cells show no label.
dagcomponentfuncs.ScenarioLink = function (props) {
  var href = (props.data && props.data.href) || undefined;
  var groupLine = scenarioGroupLine(props);
  if (!groupLine) {
    return React.createElement(
      "a",
      {
        href: href,
        className: "playlist-scenario-link-cell",
        ref: bindGridNavAnchor,
      },
      props.value
    );
  }
  return React.createElement(
    "a",
    {
      href: href,
      className: "playlist-scenario-link-cell playlist-scenario-link-two-line",
      ref: bindGridNavAnchor,
    },
    React.createElement(
      "span",
      { className: "playlist-scenario-link-name" },
      props.value
    ),
    React.createElement(
      "span",
      { className: "playlist-scenario-link-group" },
      groupLine
    )
  );
};

// A group's label in one of the per-playlist table's two group columns:
// vertical, styled by the .playlist-scenario-group-label rules in
// stylesheet.css. Drawn only while the table is grouped, when each group is
// one merged cell tall enough for it. Ungrouped, most groups are a single
// row, so the cell keeps its color alone and the Scenario cell names the
// group. `nameField` comes from the column's cellRendererParams.
dagcomponentfuncs.ScenarioGroupLabel = function (props) {
  var name = props.data && props.data[props.nameField];
  if (!name || !props.context || props.context.grouped === false) {
    return null;
  }
  return React.createElement(
    "span",
    { className: "playlist-scenario-group-label" },
    name
  );
};
