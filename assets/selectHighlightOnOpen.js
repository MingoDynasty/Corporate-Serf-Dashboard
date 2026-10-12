// A searchable select whose input carries the ``select-highlight-on-open``
// class highlights its selected name when its list opens, where dmc's
// ``clearSearchOnFocus`` would empty the field. Either way the first
// keystroke starts a fresh search; highlighted, the name can also be copied.
//
// Mantine opens the list on focus, on a press, on an arrow key, and on an
// edit, and tells the page about none of them, so each is caught at the
// document.
(() => {
    const FIELDS = "input.select-highlight-on-open";
    // Mantine sets this on the input only while its list is open. Without it
    // every field reads as closed, and each keystroke replaces the one before.
    const OPEN = "data-expanded";
    // The closed field a primary press landed on, or whose label it landed
    // on, until the button comes up.
    let press = null;

    const fieldFor = (target) => {
        const element = target.closest ? target.closest("input, label") : null;
        // A press on the label focuses the field and opens the list too.
        const field = element instanceof HTMLLabelElement ? element.control : element;
        return field && field.matches(FIELDS) ? field : null;
    };

    const closedFieldFor = (target) => {
        const field = target.matches && target.matches(FIELDS) ? target : null;
        return field && !field.hasAttribute(OPEN) ? field : null;
    };

    const highlight = (field) => {
        if (document.activeElement === field) {
            field.select();
        }
    };

    // The press itself opens the list, so whether it was closed has to be
    // read here; by the time the button comes up it is always open.
    document.addEventListener(
        "mousedown",
        (event) => {
            const field = event.button === 0 ? fieldFor(event.target) : null;
            press =
                field && !field.hasAttribute(OPEN)
                    ? {field, onField: event.target === field}
                    : null;
        },
        true,
    );

    document.addEventListener(
        "mouseup",
        () => {
            const released = press;
            press = null;
            if (!released) {
                return;
            }
            // Chromium collapses a click on highlighted text only after the
            // click event, which would undo a highlight made before it.
            setTimeout(() => {
                const {field, onField} = released;
                // Only a press on the field itself can drag out a range, and
                // that range is the user's. A range found after a press on
                // the label is one the browser brought back.
                if (!onField || field.selectionStart === field.selectionEnd) {
                    highlight(field);
                }
            }, 0);
        },
        true,
    );

    // An unfocused input keeps its last selection, and Chromium brings it
    // back when focus returns by any route but a press on the field: its
    // label, a right-click, the window coming back to the front. A partial
    // one would take the next keystroke and leave the rest of the name in
    // the search. A press on the field is left to the handler that can tell
    // a drag from a click.
    document.addEventListener(
        "focusin",
        (event) => {
            const field = fieldFor(event.target);
            if (!field || (press && press.onField && press.field === field)) {
                return;
            }
            // The browser restores the old selection after this event.
            setTimeout(() => highlight(field), 0);
        },
        true,
    );

    // Picking an option or pressing Escape closes the list with focus still
    // in the field and the cursor after the name, where the next edit would
    // append to the name and match nothing.
    document.addEventListener(
        "beforeinput",
        (event) => {
            const field = closedFieldFor(event.target);
            if (field) {
                field.select();
            }
        },
        true,
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
                return;
            }
            const field = closedFieldFor(event.target);
            if (field) {
                field.select();
            }
        },
        true,
    );

    // In that same state a right-click opens no list, and the browser's menu
    // would offer no Copy for a cursor. A range showing there is the user's.
    document.addEventListener(
        "contextmenu",
        (event) => {
            const field = closedFieldFor(event.target);
            if (field && field.selectionStart === field.selectionEnd) {
                field.select();
            }
        },
        true,
    );
})();
