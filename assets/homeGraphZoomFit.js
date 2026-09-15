// Plotly autoranges the home graph's score axis once, over every run, and an
// x-only zoom never recomputes it, so the runs in a zoomed slice sit squashed
// in a thin band. plotly.js has no option to autorange y over the visible x
// window, so refit the score axis to the runs in view whenever x is zoomed.
(() => {
    const attached = new WeakSet();
    // The y range each plot's last refit applied, so resetting x undoes only
    // a y range this asset set and never one the user dragged themselves.
    const lastFit = new WeakMap();

    // Only traces (the run points and the Average Score line) are fitted.
    // Overlay lines are shapes and stay out on purpose: the PB Score line
    // sits at or above every run, so fitting it would pin the axis top there
    // and undo most of the refit.
    function visibleScoreRange(gd) {
        // _fullLayout, _fullData, and the axis converters are plotly.js
        // internals, unchanged through plotly.js 4. The in-range test
        // mirrors plotly.js's own tick code: range and data both go to linear
        // coordinates (category index or date ms), and d2l_noadd keeps a
        // category axis from appending a category it has not seen.
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
            for (let i = 0; i < length; i++) {
                const x = toLinear(trace.x[i]);
                const y = trace.y[i];
                if (x >= start && x <= end && Number.isFinite(y)) {
                    low = Math.min(low, y);
                    high = Math.max(high, y);
                }
            }
        }
        // A window with no runs in it, such as the gap between two
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
    // document for the home graph's plot div appearing.
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
