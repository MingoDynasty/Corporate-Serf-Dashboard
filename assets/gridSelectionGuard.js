// Keeps a text selection made by dragging inside a playlist table from also
// counting as a click on it, and a modified click beside a name from opening
// the name in the current tab.
//
// Cell text on both playlist tables can be selected, and one cell in each row
// navigates on a click anywhere in it: the Playlist name and the Scenario
// name. A browser sends a click when a drag ends on the element it began on,
// so selecting that name by dragging, or dragging through the cell's empty
// part, would open the page the name links to. This listener swallows that
// one click.
//
// The name's link is only as wide as its text. A modified click on the link
// is the link's own: it opens a new tab or window and never reaches the grid.
// The same click in the rest of the cell misses the link and would reach the
// grid, whose route cannot see a modifier key and navigates the current tab.
// This listener swallows that click too, and with Ctrl or Meta it opens the
// link's address in a new tab. Shift or Alt alone opens nothing there.
//
// It listens on the document in the capture phase so it runs before AG Grid's
// own listener, which sits on the grid, and before the anchor's native
// navigation. It leaves alone:
//   - a click the pointer did not move during, which is how a selection made
//     earlier and still on screen never blocks a plain click;
//   - a modified click on a name's link, which keeps opening a new tab or
//     window, and one in a cell that does not navigate;
//   - a click from the keyboard, which arrives with a detail of 0.
(function () {
  var GRIDS = ".playlist-overview-grid, .playlist-scenarios-grid";
  // The class each table's name column gives its cells.
  var NAME_CELL = ".cell-navigates";
  // Farther than a hand moves during a plain click, and less than one
  // character of cell text.
  var DRAG_PIXELS = 3;
  var pressX = 0;
  var pressY = 0;

  document.addEventListener(
    "mousedown",
    function (event) {
      pressX = event.clientX;
      pressY = event.clientY;
    },
    true
  );

  document.addEventListener(
    "click",
    function (event) {
      if (event.detail === 0) {
        return;
      }
      var target = event.target;
      if (!target || !target.closest || !target.closest(GRIDS)) {
        return;
      }
      var modified =
        event.ctrlKey || event.metaKey || event.shiftKey || event.altKey;
      var nameCell = target.closest(NAME_CELL);
      if (modified && (!nameCell || target.closest("a"))) {
        return;
      }
      var dragged =
        Math.abs(event.clientX - pressX) > DRAG_PIXELS ||
        Math.abs(event.clientY - pressY) > DRAG_PIXELS;
      var selection = window.getSelection();
      var selecting =
        dragged && selection && !selection.isCollapsed && selection.toString();
      if (!modified && !selecting) {
        return;
      }
      event.stopPropagation();
      event.preventDefault();
      // A modified drag selects text as a plain one does, so the click that
      // ends it opens nothing either.
      if (!modified || selecting || !(event.ctrlKey || event.metaKey)) {
        return;
      }
      var link = nameCell.querySelector("a[href]");
      if (link) {
        // As the tab a link opens, this one holds no reference to the page
        // it came from.
        window.open(link.href, "_blank", "noopener");
      }
    },
    true
  );
})();
