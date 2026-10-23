// The scenario table's Typical Score and Typical Rank cells: the cell
// renderer, both hovers, and the hover opened from the keyboard. Every word
// comes from the row or the column def, which Python builds.
(function () {
  var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});
  var dagcomponentfuncs = (window.dashAgGridComponentFunctions =
    window.dashAgGridComponentFunctions || {});

  var SCORE_COLUMN = "typical_score_sort";
  var RANK_COLUMN = "typical_tier_sort";

  // Only a known value is ever old: Too few runs and N/A carry no value, and
  // a benchmark scenario without a ladder reads N/A in Typical Rank beside
  // an old Typical Score.
  function isOld(params) {
    return Boolean(params.data && params.data.typical_not_recent) && params.value != null;
  }

  dagfuncs.typicalCellClass = function (params, hasHover) {
    var classes = [];
    if (isOld(params)) {
      classes.push("typical-not-recent");
    }
    if (hasHover) {
      classes.push("cell-tooltip-affordance");
    }
    return classes.length ? classes.join(" ") : null;
  };

  // The hover's words as one string, for the cell's accessible description.
  // A readout line ends with no period on screen, where each sits on its own
  // line; read aloud, the period keeps one from running into the next.
  function hoverText(colId, data) {
    if (!data) {
      return null;
    }
    if (colId === RANK_COLUMN) {
      return data.typical_tier_hover
        ? data.typical_tier_hover.split("\n").join(". ")
        : null;
    }
    var hover = data.typical_score_hover;
    if (!hover) {
      return null;
    }
    return [hover.lead]
      .concat(
        hover.lines.map(function (line) {
          return line[0] + line[1] + ".";
        })
      )
      .join(" ");
  }

  var describedCount = 0;

  // The value, and on an old one a clock a screen reader skips and the
  // Not recent words it reads instead. The hover's words become the grid
  // cell's description: AG Grid's hover is the mouse's alone.
  dagcomponentfuncs.TypicalCell = function (props) {
    var e = React.createElement;
    var colId = props.column ? props.column.getColId() : "";
    var text = props.valueFormatted != null ? props.valueFormatted : props.value;
    var description = hoverText(colId, props.data);
    var descriptionId = React.useMemo(function () {
      describedCount += 1;
      return "typical-cell-description-" + describedCount;
    }, []);
    var children = [e("span", { key: "value" }, text)];
    if (isOld(props)) {
      children.push(
        e("span", { key: "mark", className: "typical-old-mark", "aria-hidden": "true" })
      );
      children.push(
        e("span", { key: "status", className: "visually-hidden" }, ", " + props.notRecentText)
      );
    }
    if (description) {
      children.push(e("span", { key: "description", id: descriptionId, hidden: true }, description));
    }
    return e(
      "span",
      {
        className: "typical-cell",
        ref: function (node) {
          var cell = node && node.closest(".ag-cell");
          if (!cell) {
            return;
          }
          if (description) {
            cell.setAttribute("aria-describedby", descriptionId);
          } else {
            cell.removeAttribute("aria-describedby");
          }
        },
      },
      children
    );
  };

  function scoreTooltipChildren(e, hover) {
    var children = [e("p", { key: "lead" }, hover.lead)];
    hover.lines.forEach(function (line, index) {
      children.push(e("div", { key: index }, e("b", null, line[0]), line[1]));
    });
    return children;
  }

  // The Scenario Stats card's hover, drawn from the row. It wears the grid's
  // tooltip class for the app's tooltip styles, and its own width, because
  // the grid's popup otherwise shrinks it to its narrowest.
  dagcomponentfuncs.TypicalScoreTooltip = function (props) {
    var hover = props.data && props.data.typical_score_hover;
    if (!hover) {
      return null;
    }
    var e = React.createElement;
    return e(
      "div",
      { className: "ag-tooltip typical-score-tooltip" },
      scoreTooltipChildren(e, hover)
    );
  };

  // A component, not the grid's plain tooltip, so an old value's second line
  // breaks.
  dagcomponentfuncs.TypicalRankTooltip = function (props) {
    if (!props.value) {
      return null;
    }
    return React.createElement(
      "div",
      { className: "ag-tooltip typical-rank-tooltip" },
      props.value
    );
  };

  // The hover from the keyboard. A popup of this file's own, opened from the
  // grid's cellFocused event only when the last input was a key, so a click
  // that focuses a cell gets the grid's mouse hover alone.
  var lastInputWasKey = false;
  // The open popup, and the row and column of the cell it explains.
  var focusTip = null;

  dagfuncs.hideTypicalFocusTip = function () {
    if (focusTip) {
      focusTip.element.remove();
      focusTip = null;
    }
  };

  // Found by row and column, not by the focused element: the grid can fire
  // its focus event before it moves the browser's focus.
  function cellAt(rowIndex, colId) {
    return document.querySelector(
      '.ag-row[row-index="' + rowIndex + '"] .ag-cell[col-id="' + colId + '"]'
    );
  }

  // Whether the cell's middle is inside the part of the table on screen.
  function inView(cell) {
    var viewport = cell.closest(".ag-body-viewport");
    var columns = cell.closest(".ag-center-cols-viewport");
    var rect = cell.getBoundingClientRect();
    var x = rect.left + rect.width / 2;
    var y = rect.top + rect.height / 2;
    return [viewport, columns].every(function (box) {
      if (!box) {
        return true;
      }
      var bounds = box.getBoundingClientRect();
      return x >= bounds.left && x <= bounds.right && y >= bounds.top && y <= bounds.bottom;
    });
  }

  // Below the cell, or above it where the window has no room below, and
  // never past the window's right edge.
  function place(tip, cell) {
    var rect = cell.getBoundingClientRect();
    var top = rect.bottom + 4;
    if (top + tip.offsetHeight > window.innerHeight && rect.top - 4 - tip.offsetHeight >= 0) {
      top = rect.top - 4 - tip.offsetHeight;
    }
    var left = Math.max(0, Math.min(rect.left, window.innerWidth - tip.offsetWidth));
    tip.style.top = top + "px";
    tip.style.left = left + "px";
  }

  // On every scroll of the table. The grid scrolls a newly focused cell into
  // view after it fires the focus event, so a scroll moves the popup with its
  // cell rather than closing it, or the arrow key that reached an off-screen
  // column would lose its hover at once. A deliberate scroll closes it before
  // it gets here: a wheel or touchpad scroll, and the press that starts a
  // scrollbar drag.
  dagfuncs.placeTypicalFocusTip = function () {
    if (!focusTip) {
      return;
    }
    var cell = cellAt(focusTip.rowIndex, focusTip.colId);
    if (!cell || !inView(cell)) {
      dagfuncs.hideTypicalFocusTip();
      return;
    }
    place(focusTip.element, cell);
  };

  function tipContent(colId, data) {
    var box = document.createElement("div");
    if (colId === SCORE_COLUMN) {
      var hover = data.typical_score_hover;
      if (!hover) {
        return null;
      }
      box.className = "ag-tooltip typical-score-tooltip";
      var lead = document.createElement("p");
      lead.textContent = hover.lead;
      box.appendChild(lead);
      hover.lines.forEach(function (line) {
        var row = document.createElement("div");
        var label = document.createElement("b");
        label.textContent = line[0];
        row.appendChild(label);
        row.appendChild(document.createTextNode(line[1]));
        box.appendChild(row);
      });
      return box;
    }
    if (!data.typical_tier_hover) {
      return null;
    }
    box.className = "ag-tooltip typical-rank-tooltip";
    box.textContent = data.typical_tier_hover;
    return box;
  }

  dagfuncs.showTypicalFocusTip = function (event) {
    dagfuncs.hideTypicalFocusTip();
    if (!lastInputWasKey || event.rowIndex == null || !event.column) {
      return;
    }
    var colId = typeof event.column === "string" ? event.column : event.column.getColId();
    if (colId !== SCORE_COLUMN && colId !== RANK_COLUMN) {
      return;
    }
    var node = event.api.getDisplayedRowAtIndex(event.rowIndex);
    var tip = node && node.data ? tipContent(colId, node.data) : null;
    var cell = cellAt(event.rowIndex, colId);
    if (!tip || !cell) {
      return;
    }
    tip.classList.add("typical-focus-tip");
    tip.setAttribute("role", "tooltip");
    document.body.appendChild(tip);
    focusTip = { element: tip, rowIndex: event.rowIndex, colId: colId };
    place(tip, cell);
  };

  document.addEventListener(
    "keydown",
    function (event) {
      lastInputWasKey = true;
      if (event.key === "Escape") {
        dagfuncs.hideTypicalFocusTip();
      }
    },
    true
  );
  document.addEventListener(
    "pointerdown",
    function () {
      lastInputWasKey = false;
      dagfuncs.hideTypicalFocusTip();
    },
    true
  );
  document.addEventListener("wheel", dagfuncs.hideTypicalFocusTip, {
    capture: true,
    passive: true,
  });
  // Focus anywhere but a typical cell closes it: out of the table, onto a
  // header, or onto another cell.
  document.addEventListener("focusin", function (event) {
    var cell = event.target.closest && event.target.closest(".ag-cell");
    var colId = cell ? cell.getAttribute("col-id") : null;
    if (colId !== SCORE_COLUMN && colId !== RANK_COLUMN) {
      dagfuncs.hideTypicalFocusTip();
    }
  });
})();
