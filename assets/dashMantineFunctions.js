// Function props for dash-mantine-components, looked up by name in
// window.dashMantineFunctions when a prop is given as {"function": "<name>"}.
var dmcfuncs = (window.dashMantineFunctions = window.dashMantineFunctions || {});

// Keep every option visible whatever the input holds.
//
// Mantine's default Autocomplete filter matches its options against the input
// text, so a field that already holds a value offers only options containing
// that value -- in practice just the value itself. For the stats-directory
// field that is backwards: the field is normally prefilled (startup seeds it),
// and the case the suggestions exist for is exactly the one where the seeded
// path is the wrong Steam library and the user needs to see the others.
dmcfuncs.allOptions = function ({ options }) {
  return options;
};
