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
