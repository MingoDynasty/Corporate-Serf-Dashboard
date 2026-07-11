var dagfuncs = (window.dashAgGridFunctions =
  window.dashAgGridFunctions || {});

dagfuncs.nullsLastComparator = function (
  valueA,
  valueB,
  nodeA,
  nodeB,
  isDescending
) {
  const missingA = valueA === null || valueA === undefined;
  const missingB = valueB === null || valueB === undefined;

  if (missingA && missingB) {
    return 0;
  }
  if (missingA) {
    return isDescending ? -1 : 1;
  }
  if (missingB) {
    return isDescending ? 1 : -1;
  }
  return valueA - valueB;
};

// Shared relative/absolute timestamp formatters. Pure (no DOM access) and used
// from two contexts: AG Grid colDef `{"function": ...}` strings, where dash-ag-grid
// spreads this registry's contents into scope as BARE names -- call
// `relativeTime(...)` directly, NOT `dagfuncs.relativeTime(...)` (there is no
// `dagfuncs` in that scope) -- and the home page clientside callback, which runs
// in real browser global scope and uses the full `window.dashAgGridFunctions` path.
// See docs/decision_log.md (2026-06-20: Reference dash-ag-grid Grid Functions By
// Bare Name).
//
// `seconds` is epoch *seconds* (the grid already carries this; the home Store
// emits it too); both guard null/empty -> the caller-supplied sentinel before
// constructing a Date (new Date(null) -> 1970, which must not render as an age).

// Relative, humanized age: "5 minutes ago". Always a single rounded unit, never
// compound. `nowMs` (millisecond number, default Date.now()) is injectable so the
// helper is deterministically testable.
dagfuncs.relativeTime = function (seconds, sentinel, nowMs) {
  if (seconds === null || seconds === undefined || seconds === "") {
    return sentinel;
  }
  if (nowMs === undefined) {
    nowMs = Date.now();
  }

  const thenMs = seconds * 1000;
  const diffMs = nowMs - thenMs; // just now / minutes / hours / days
  const now = new Date(nowMs); // calendar components for months/years
  const then = new Date(thenMs);

  // "just now" floor: anything under a minute, including zero/negative diffs
  // (a future timestamp from clock quirks) so we never render "in N minutes".
  if (diffMs <= 60 * 1000) {
    return "just now";
  }

  const minutes = Math.floor(diffMs / (60 * 1000));
  if (minutes < 60) {
    return minutes + (minutes === 1 ? " minute ago" : " minutes ago");
  }

  const hours = Math.floor(diffMs / (60 * 60 * 1000));
  if (hours < 24) {
    return hours + (hours === 1 ? " hour ago" : " hours ago");
  }

  // Months/years are calendar-based (not day-division) so the day->month handoff
  // is exact and a large age never reads as a giant number.
  let months =
    (now.getFullYear() - then.getFullYear()) * 12 +
    (now.getMonth() - then.getMonth());
  if (now.getDate() < then.getDate()) {
    months--; // day-of-month not yet reached this month
  }
  months = Math.max(0, months); // never negative (near-now / future)

  if (months < 1) {
    const days = Math.floor(diffMs / (24 * 60 * 60 * 1000));
    return days + (days === 1 ? " day ago" : " days ago");
  }

  if (months < 12) {
    return months + (months === 1 ? " month ago" : " months ago");
  }

  const years = Math.floor(months / 12);
  return years + (years === 1 ? " year ago" : " years ago");
};

// Absolute timestamp for the tooltip, humanized to a GitHub-shaped format like
// "Apr 9, 2026, 7:04 PM" (not toLocaleString, which is locale-dependent and
// date-ambiguous). Renders in browser-local time. This mirrors the no-seconds
// output of `format_absolute_timestamp` in source/utilities/utilities.py --
// keep the two in sync by hand (there is no JS test harness for parity).
const ABSOLUTE_MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
dagfuncs.absoluteTime = function (seconds, sentinel) {
  if (seconds === null || seconds === undefined || seconds === "") {
    return sentinel;
  }

  const date = new Date(seconds * 1000);
  const pad = (value) => String(value).padStart(2, "0");

  let hours = date.getHours();
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  if (hours === 0) {
    hours = 12; // 0 -> 12 for both midnight (12 AM) and noon (12 PM)
  }

  const month = ABSOLUTE_MONTHS[date.getMonth()];
  return (
    month +
    " " +
    date.getDate() +
    ", " +
    date.getFullYear() +
    ", " +
    hours +
    ":" +
    pad(date.getMinutes()) +
    " " +
    ampm
  );
};
