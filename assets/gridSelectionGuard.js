// Keeps a text selection made by dragging inside a playlist table from also
// counting as a click on it.
//
// Cell text on both playlist tables can be selected, and one cell in each row
// navigates on a click anywhere in it: the Playlist name and the Scenario
// name. A browser sends a click when a drag ends on the element it began on,
// so selecting that name by dragging, or dragging through the cell's empty
// part, would open the page the name links to. This listener swallows that
// one click.
//
// It listens on the document in the capture phase so it runs before AG Grid's
// own listener, which sits on the grid, and before the anchor's native
// navigation. It leaves alone:
//   - a click the pointer did not move during, which is how a selection made
//     earlier and still on screen never blocks a plain click;
//   - a click with a modifier key, which keeps opening a new tab or window;
//   - a click from the keyboard, which arrives with a detail of 0.
(function () {
  var GRIDS = ".playlist-overview-grid, .playlist-scenarios-grid";
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
      if (
        event.detail === 0 ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }
      var target = event.target;
      if (!target || !target.closest || !target.closest(GRIDS)) {
        return;
      }
      var dragged =
        Math.abs(event.clientX - pressX) > DRAG_PIXELS ||
        Math.abs(event.clientY - pressY) > DRAG_PIXELS;
      if (!dragged) {
        return;
      }
      var selection = window.getSelection();
      if (!selection || selection.isCollapsed || !selection.toString()) {
        return;
      }
      event.stopPropagation();
      event.preventDefault();
    },
    true
  );
})();
