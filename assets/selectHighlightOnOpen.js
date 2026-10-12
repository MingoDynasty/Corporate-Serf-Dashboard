// A searchable select whose input carries the ``select-highlight-on-open``
// class highlights its selected name when its list opens, where dmc's
// ``clearSearchOnFocus`` would empty the field. Either way the first
// keystroke starts a fresh search; highlighted, the name can also be copied.
//
// Mantine opens the list on a press, on an arrow key, on an edit, and on
// focus, and tells the page about none of them, so each is caught at the
// document. Focus needs no handler: a browser highlights a field it tabs into.
(() => {
    const FIELDS = "input.select-highlight-on-open";
    // Mantine sets this on the input only while its list is open. Without it
    // every field reads as closed, and each keystroke replaces the one before.
    const OPEN = "data-expanded";
    let pressedWhileClosed = null;

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

    // The press itself opens the list, so whether it was closed has to be
    // read here; by the click it is always open.
    document.addEventListener(
        "mousedown",
        (event) => {
            const field = event.button === 0 ? fieldFor(event.target) : null;
            pressedWhileClosed = field && !field.hasAttribute(OPEN) ? field : null;
        },
        true,
    );

    document.addEventListener("click", () => {
        const field = pressedWhileClosed;
        pressedWhileClosed = null;
        if (!field) {
            return;
        }
        // Chromium collapses a click on highlighted text only after the click
        // event, which would undo a highlight made inside it. A drag leaves a
        // range behind instead of a cursor, and that range is the user's.
        setTimeout(() => {
            if (
                document.activeElement === field &&
                field.selectionStart === field.selectionEnd
            ) {
                field.select();
            }
        }, 0);
    });

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
})();
