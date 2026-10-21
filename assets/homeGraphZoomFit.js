// Plotly autoranges the Run History graph's score axis once, over every run, and an
// x-only zoom never recomputes it, so the runs in a zoomed slice sit squashed
// in a thin band. plotly.js has no option to autorange y over the visible x
// window, so refit the score axis to the points in view whenever x is zoomed.
(() => {
    const attached = new WeakSet();
    // The y range each plot's last refit applied, so resetting x undoes only
    // a y range this asset set and never one the user dragged themselves.
    const lastFit = new WeakMap();

    // Only traces are fitted: the run points; the New PB stars and the latest
    // run's ring, which repeat run points and so never move the fit; and the
    // typical score's line and bands. Those are drawn as lines, a band as its
    // outline, so they count where they cross the window as well as their
    // points inside it: on Score vs Time a value held flat across the whole
    // window has no point in it, and a refit keeps it in view rather than
    // clipping it. Overlay lines are shapes and stay out on purpose: the PB
    // score line sits at or above every run, so fitting it would pin the axis
    // top there and undo most of the refit.
    function visibleScoreRange(gd) {
        // _fullLayout, _fullData, and the axis converters are plotly.js
        // internals, unchanged through plotly.js 4. The in-range test
        // mirrors plotly.js's own tick code: range and data both go to linear
        // coordinates (category index, date ms, or the run number as it
        // is), and d2l_noadd keeps a category axis from appending a category
        // it has not seen.
        const xaxis = gd._fullLayout.xaxis;
        const toLinear = (value) =>
            xaxis.type === "category" ? xaxis.d2l_noadd(value) : xaxis.d2l(value);
        const [start, end] = [xaxis.r2l(xaxis.range[0]), xaxis.r2l(xaxis.range[1])]
            .sort((a, b) => a - b);

        let low = Infinity;
        let high = -Infinity;
        for (const trace of gd._fullData) {
            // A legend-hidden trace is "legendonly", which autorange skips too.
            if (trace.visible !== true || !trace.x || !trace.y) {
                continue;
            }
            const length = Math.min(trace.x.length, trace.y.length);
            const xs = [];
            for (let i = 0; i < length; i++) {
                const x = toLinear(trace.x[i]);
                const y = trace.y[i];
                xs.push(x);
                if (x >= start && x <= end && Number.isFinite(y)) {
                    low = Math.min(low, y);
                    high = Math.max(high, y);
                }
            }
            if (!trace.mode || !trace.mode.includes("lines")) {
                continue;
            }
            // Each segment's part inside the window, its ends interpolated.
            // A gap in the line is a null point, which ends a segment, and an
            // upright segment's ends are points already counted.
            for (let i = 1; i < length; i++) {
                const [x0, x1, y0, y1] = [xs[i - 1], xs[i], trace.y[i - 1], trace.y[i]];
                if (![x0, x1, y0, y1].every(Number.isFinite) || x0 === x1) {
                    continue;
                }
                const left = Math.max(Math.min(x0, x1), start);
                const right = Math.min(Math.max(x0, x1), end);
                for (const x of left <= right ? [left, right] : []) {
                    const y = y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
                    low = Math.min(low, y);
                    high = Math.max(high, y);
                }
            }
        }
        // A window with nothing in it, such as the gap between two
        // categories, leaves y alone.
        if (low > high) {
            return null;
        }
        const pad = (high - low) * 0.05 || Math.abs(low) * 0.05 || 1;
        return [low - pad, high + pad];
    }

    function refit(gd) {
        const range = visibleScoreRange(gd);
        const current = gd._fullLayout.yaxis.range;
        // The refit's own relayout carries an x range and re-enters here; the
        // fit is already applied by then, which is what ends the loop.
        if (!range || (range[0] === current[0] && range[1] === current[1])) {
            return;
        }
        // Re-send the current x range with the fit. dcc.Graph copies every
        // relayout into its figure prop from props that can predate the
        // user's zoom, so a y-only relayout would overwrite that zoom and
        // snap x back to the full range.
        lastFit.set(gd, range);
        window.Plotly.relayout(gd, {
            "xaxis.range": gd._fullLayout.xaxis.range.slice(),
            "yaxis.range": range,
        });
    }

    function onRelayout(gd, event) {
        if (event["xaxis.autorange"]) {
            // A plot-area double-click, Reset axes, and Autoscale restore both
            // axes already. A double-click on the x-axis drag handle
            // autoranges x alone and would leave y clamped to the old fit,
            // so reset y too, with x in the same relayout for the reason the
            // refit re-sends x. The event that relayout sends carries both
            // keys and ends here.
            const fit = lastFit.get(gd);
            const current = gd._fullLayout.yaxis.range;
            const yStillFit = fit && fit[0] === current[0] && fit[1] === current[1];
            if (!event["yaxis.autorange"] && yStillFit) {
                window.Plotly.relayout(gd, {
                    "xaxis.autorange": true,
                    "yaxis.autorange": true,
                });
            }
            return;
        }
        // Only an x range change refits, which skips the autosize events a
        // resize sends and a y-only axis drag.
        if (Object.keys(event).some((key) => key.startsWith("xaxis.range"))) {
            refit(gd);
        }
    }

    function onRestyle(gd, [update]) {
        // Showing or hiding a trace from the legend changes which points are
        // fitted, and an explicit y range does not follow it the way
        // autorange would, so a restored trace would stay clipped. Unzoomed,
        // autorange still owns both axes and needs no help.
        if ("visible" in update && gd._fullLayout.xaxis.autorange === false) {
            refit(gd);
        }
    }

    // Dash mounts and remounts the page contents dynamically, so watch the
    // document for the graph's plot div appearing.
    new MutationObserver(() => {
        for (const gd of document.querySelectorAll(".home-graph .js-plotly-plot")) {
            // plotly.js installs gd.on when it first plots the div; a div
            // seen before that is picked up on a later mutation.
            if (!attached.has(gd) && typeof gd.on === "function") {
                attached.add(gd);
                gd.on("plotly_relayout", (event) => onRelayout(gd, event));
                gd.on("plotly_restyle", (event) => onRestyle(gd, event));
            }
        }
    }).observe(document.documentElement, {childList: true, subtree: true});
})();
