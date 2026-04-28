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
