// The personal best celebration's animation: a name-keyed style registry and
// the two entries the app drives it through, on window.pbCelebration.
//
// `celebrate(batch, style)` is the clientside callback's entry: it gates on the
// drain's decision, then plays. `play(style)` fires one celebration directly,
// which is what the Settings page's Preview button does. There is no
// JavaScript harness in this repo, so this file stays small and every guard is
// one the manual pass can reach.
(() => {
    "use strict";

    // The setting's off value. Every other value is a style name.
    const OFF = "off";
    // An unknown name plays this rather than nothing, so a style dropped in a
    // later version never silently turns celebrations off.
    const DEFAULT_STYLE = "confetti";

    // The Realistic Look recipe from the canvas-confetti demos, unchanged:
    // five bursts from one origin, about 200 particles, spent in about three
    // seconds. `disableForReducedMotion` is the library's own guard, passed on
    // every call this file makes; `prefersReducedMotion` below asks the same
    // question before anything is scheduled at all, which is what an
    // app-owned loop would need (version one has none).
    const confettiStyle = (confetti) => {
        const defaults = {origin: {y: 0.7}, disableForReducedMotion: true};
        const fire = (particleRatio, options) => {
            confetti({
                ...defaults,
                ...options,
                particleCount: Math.floor(200 * particleRatio),
            });
        };

        fire(0.25, {spread: 26, startVelocity: 55});
        fire(0.2, {spread: 60});
        fire(0.35, {spread: 100, decay: 0.91, scalar: 0.8});
        fire(0.1, {spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2});
        fire(0.1, {spread: 120, startVelocity: 45});
    };

    // Version one registers Confetti alone; the Python side's option list
    // mirrors these names by convention.
    const styles = {confetti: confettiStyle};

    // The vendored library is resolved at call time, never captured while this
    // file runs: Dash serves assets/*.js as classic scripts in its own order,
    // so window.confetti may not exist yet. By the time a drain or a Preview
    // click reaches play(), every asset has loaded.
    const library = () => window.confetti;

    const prefersReducedMotion = () =>
        typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // At most one celebration is ever held, and a newer one replaces it: what
    // matters on the next alt-tab is the latest personal best, not a queue of
    // them.
    let pending = null;
    // The animation sequence of the last decision played. The drain advances
    // it only when it celebrates, so this is what lets two identical personal
    // bests back to back both fire while one payload never plays twice.
    let playedSequence = null;

    const start = (styleName) => {
        const confetti = library();
        if (!confetti) {
            return;
        }
        // Cancel a burst still in flight, so a fast streak never stacks.
        confetti.reset();
        (styles[styleName] || styles[DEFAULT_STYLE])(confetti);
    };

    const play = (styleName) => {
        if (!styleName || styleName === OFF || prefersReducedMotion()) {
            return;
        }
        if (document.hidden) {
            // A fully occluded window counts as hidden under Chromium's
            // occlusion tracking, and the player is in KovaaK's fullscreen
            // when a personal best lands. A hidden tab throttles animation
            // frames, so playing now would stall the burst and dump its
            // remains on the next alt-tab. It is held instead.
            pending = styleName;
            return;
        }
        start(styleName);
    };

    document.addEventListener("visibilitychange", () => {
        if (document.hidden || pending === null) {
            return;
        }
        const styleName = pending;
        pending = null;
        // Back through play() rather than straight to start(): reduced motion
        // can have been turned on while the tab was hidden, and a held
        // celebration obeys it like any other.
        play(styleName);
    });

    const celebrate = (batch, styleName) => {
        // No decision plays nothing, and moves nothing: the sequence stays the
        // record of what was actually played.
        if (!batch || !batch.celebrated_run_id) {
            return;
        }
        if (batch.animation_sequence === playedSequence) {
            return;
        }
        playedSequence = batch.animation_sequence;
        play(styleName);
    };

    window.pbCelebration = {play, celebrate};
})();
