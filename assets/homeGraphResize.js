// Plotly only redraws a responsive graph on window `resize` events. The home
// graph's height is flex-driven by the controls above it, which can change
// height without a window resize (e.g. the Scenario Stats block wrapping to
// an extra line), so observe the graph container and resize the plot to
// match whenever its box changes.
(() => {
    const observed = new WeakSet();

    const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
            if (!entry.contentRect.width || !entry.contentRect.height) {
                continue;
            }
            const plot = entry.target.querySelector(".js-plotly-plot");
            // window.Plotly is set by dcc's lazily injected plotly.min.js
            // once the first graph renders; before that there is no plot to
            // resize yet and the guard is a safe no-op.
            if (plot && window.Plotly) {
                window.Plotly.Plots.resize(plot);
            }
        }
    });

    // Dash mounts and remounts the page contents dynamically, so watch the
    // document for graph containers appearing.
    new MutationObserver(() => {
        for (const graph of document.querySelectorAll(".home-graph")) {
            if (!observed.has(graph)) {
                observed.add(graph);
                resizeObserver.observe(graph);
            }
        }
    }).observe(document.documentElement, {childList: true, subtree: true});
})();
