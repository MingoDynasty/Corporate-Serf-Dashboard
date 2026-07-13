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

// Shared onClick for the navigation anchors below. An unmodified left-click is
// suppressed so the grid's cellClicked server callback does the fast in-app
// nav; a modified click (Ctrl/Cmd/Shift/Alt) falls through to the native
// anchor, opening a full Dash page load in a new tab. Middle-click arrives as
// auxclick (not click), so it stays native with no handling here. We never
// call stopPropagation() — cellClicked must keep firing to carry the in-app
// nav.
function suppressPlainLeftClick(event) {
  if (!event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
    event.preventDefault();
  }
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
      onClick: suppressPlainLeftClick,
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
      onClick: suppressPlainLeftClick,
    },
    props.value
  );
};
