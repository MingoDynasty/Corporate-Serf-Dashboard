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

    // Passed on every library call this file makes. `prefersReducedMotion`
    // below asks the same question before anything is scheduled at all, which
    // is what the styles that loop need; this flag is the library's own second
    // line, on the particles themselves.
    const REDUCED_MOTION_GUARD = {disableForReducedMotion: true};

    // Every style takes the resolved library and returns either nothing or a
    // cancel function. A style that schedules anything -- an interval, an
    // animation frame, a timeout -- returns the call that unschedules it and
    // nothing else; start() below owns when that runs. This is the whole
    // reason the looping recipes are not the demo code verbatim:
    // `confetti.reset()` clears the particles already drawn but does not stop
    // a loop, so a style that schedules and returns nothing would keep firing
    // over the style that replaced it.

    // The Realistic Look recipe from the canvas-confetti demos, unchanged:
    // five bursts from one origin, about 200 particles, spent in about three
    // seconds. It schedules nothing, so there is nothing to cancel.
    const confettiStyle = (confetti) => {
        const defaults = {...REDUCED_MOTION_GUARD, origin: {y: 0.7}};
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

    // The Fireworks recipe, cut from the demo's 15 s to 3 s: paired volleys
    // every 250 ms from random points left and right, thinning as the time
    // runs out.
    const fireworksStyle = (confetti) => {
        const duration = 3000;
        const end = Date.now() + duration;
        const defaults = {
            ...REDUCED_MOTION_GUARD,
            startVelocity: 30,
            spread: 360,
            ticks: 60,
        };
        const between = (min, max) => Math.random() * (max - min) + min;
        const interval = window.setInterval(() => {
            const remaining = end - Date.now();
            if (remaining <= 0) {
                window.clearInterval(interval);
                return;
            }
            const particleCount = 50 * (remaining / duration);
            // Started a little above the top edge, since the particles fall.
            confetti({
                ...defaults,
                particleCount,
                origin: {x: between(0.1, 0.3), y: Math.random() - 0.2},
            });
            confetti({
                ...defaults,
                particleCount,
                origin: {x: between(0.7, 0.9), y: Math.random() - 0.2},
            });
        }, 250);

        return () => window.clearInterval(interval);
    };

    // The School Pride recipe, cut from 15 s to 2.5 s and in the app's own
    // colors rather than the demo's team red and white: Mantine's primary
    // blue (blue.6, #228be6, the filled-button color) and white.
    const cannonsStyle = (confetti) => {
        const end = Date.now() + 2500;
        const shot = {
            ...REDUCED_MOTION_GUARD,
            particleCount: 2,
            spread: 55,
            colors: ["#228be6", "#ffffff"],
        };
        let frame = 0;
        const fire = () => {
            confetti({...shot, angle: 60, origin: {x: 0}});
            confetti({...shot, angle: 120, origin: {x: 1}});
            if (Date.now() < end) {
                frame = window.requestAnimationFrame(fire);
            }
        };

        fire();
        return () => window.cancelAnimationFrame(frame);
    };

    // The Stars recipe, unchanged: three volleys of weightless stars 100 ms
    // apart, spent in about a second.
    const starsStyle = (confetti) => {
        const defaults = {
            ...REDUCED_MOTION_GUARD,
            spread: 360,
            ticks: 50,
            gravity: 0,
            decay: 0.94,
            startVelocity: 30,
            colors: ["FFE400", "FFBD00", "E89400", "FFCA6C", "FDFFB8"],
        };
        const shoot = () => {
            confetti({
                ...defaults,
                particleCount: 40,
                scalar: 1.2,
                shapes: ["star"],
            });
            confetti({
                ...defaults,
                particleCount: 10,
                scalar: 0.75,
                shapes: ["circle"],
            });
        };
        const timers = [0, 100, 200].map((d) => window.setTimeout(shoot, d));

        return () => {
            for (const timer of timers) {
                window.clearTimeout(timer);
            }
        };
    };

    // The registry. Its keys and the Settings page's option list agree by
    // convention, which a Python test pins by parsing this block: an option
    // with no entry here falls back to Confetti, so the user picks Stars and
    // gets Confetti, which is a wrong answer rather than a visible failure.
    const styles = {
        confetti: confettiStyle,
        fireworks: fireworksStyle,
        cannons: cannonsStyle,
        stars: starsStyle,
    };

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
    // The cancel handle of the style now playing, or null. Exactly one is ever
    // held, and start() is the only way to begin a celebration, so the whole
    // leak surface of this file is the four closures returned above.
    let activeCancel = null;

    const start = (styleName) => {
        const confetti = library();
        if (!confetti) {
            return;
        }
        if (activeCancel) {
            const cancel = activeCancel;
            activeCancel = null;
            // A handle whose style already finished is a no-op: clearing a
            // spent timer or frame costs nothing, so a style never has to
            // report that it is done.
            cancel();
        }
        // Cancel a burst still in flight, so a fast streak never stacks. This
        // clears the canvas; the handle above is what stops anything more from
        // being scheduled onto it.
        confetti.reset();
        const style = styles[styleName] || styles[DEFAULT_STYLE];
        activeCancel = style(confetti) || null;
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
