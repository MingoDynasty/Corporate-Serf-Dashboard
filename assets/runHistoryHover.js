// Link only run markers and already-loaded list rows. No Plotly restyle is
// needed: changing marker size through Plotly can change an autoranged axis.
(function () {
  var attached = new WeakSet();
  var graph = null;
  var markers = new Map();
  var marked = [];
  var source = null;
  var listRow = null;

  function emphasize(id) {
    marked.forEach(function (point) {
      point.classList.remove("run-history-point-linked");
    });
    marked = markers.get(id) || [];
    marked.forEach(function (point) {
      point.classList.add("run-history-point-linked");
    });
  }

  function clear() {
    source = null;
    listRow = null;
    emphasize(null);
    if (window.runHistoryList) {
      window.runHistoryList.highlightRun(null);
    }
  }
  window.runHistoryHover = { clear: clear };

  function indexMarkers(gd) {
    markers = new Map();
    // Plotly's SVG scatter binds calcdata to each trace and marker. In
    // plotly.js 4.1.1, calcdata.id is the trace's public ids value. Re-index
    // after every plot: zoom, preferences and new runs can replace the paths.
    // Select traces across layers: zorder gives the summary and runs separate
    // scatterlayer containers with different class names.
    gd.querySelectorAll(".trace.scatter").forEach(function (group) {
      var trace = group.__data__ && group.__data__[0] && group.__data__[0].trace;
      if (!trace || trace.meta !== "run-history-run" || trace.visible !== true) {
        return;
      }
      group.querySelectorAll(".points .point").forEach(function (point) {
        var id = point.__data__ && point.__data__.id;
        if (typeof id === "string") {
          if (!markers.has(id)) {
            markers.set(id, []);
          }
          markers.get(id).push(point);
        }
      });
    });
  }

  var functions = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});
  functions.runHistoryHoverOver = function (params) {
    var target = params.event && params.event.target;
    var row = target && target.closest && target.closest(".ag-row");
    // AG Grid dispatches these events asynchronously. An old row's over/out
    // can arrive after Plotly's new hover, so accept only the live row under
    // the pointer, with its id checked in case the grid recycled it.
    if (!row || !row.matches(":hover") || !params.data ||
        row.getAttribute("row-id") !== params.data.id) {
      return;
    }
    if (params.data.kind !== "run") {
      clear();
      return;
    }
    source = "list";
    listRow = params.data.id;
    emphasize(params.data.id.slice(params.context.runRowIdPrefix.length));
  };
  functions.runHistoryHoverOut = function (params) {
    var target = params.event && params.event.target;
    var current = target && target.closest && target.closest(".ag-row");
    if (current && current.matches(":hover")) {
      return;
    }
    var related = params.event && params.event.relatedTarget;
    var row = related && related.closest && related.closest(".ag-row");
    if (row && params.data && row.getAttribute("row-id") === params.data.id) {
      return;
    }
    if (source === "list" && params.data && listRow === params.data.id) {
      clear();
    }
  };
  functions.runHistoryHoverClear = clear;

  function attach() {
    var gd = document.querySelector("#run-history-graph .js-plotly-plot");
    if (graph && graph !== gd) {
      clear();
      graph = null;
      markers = new Map();
    }
    if (!gd || attached.has(gd) || typeof gd.on !== "function") {
      return;
    }
    graph = gd;
    attached.add(gd);
    indexMarkers(gd);
    gd.on("plotly_hover", function (event) {
      if (!gd.matches(":hover")) {
        return;
      }
      var point = (event.points || []).find(function (item) {
        return item.data.meta === "run-history-run";
      });
      var id = point && point.data.ids && point.data.ids[point.pointNumber];
      clear();
      if (typeof id === "string") {
        source = "chart";
        emphasize(id);
        window.runHistoryList.highlightRun(id);
      }
    });
    gd.on("plotly_unhover", function () {
      if (graph === gd && source === "chart") {
        clear();
      }
    });
    gd.on("plotly_afterplot", function () {
      if (graph !== gd) {
        return;
      }
      clear();
      indexMarkers(gd);
    });
    gd.addEventListener("mouseleave", clear);
  }

  new MutationObserver(attach).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
