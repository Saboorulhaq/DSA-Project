"""
filters.py - single-column filters and composite filters (AND / OR / NOT).

A condition is a dict:  {"column", "op", "value", "negate", "connector"}
  op for text columns   : equals, contains, starts with, ends with, not contains
  op for number columns : =, !=, >, >=, <, <=
  negate    : True means NOT (this condition)
  connector : "AND" or "OR" - how this condition joins the PREVIOUS one

Evaluation rule (normal logic): AND is stronger than OR.
  A AND B OR C   means   (A AND B) OR C
"""
NUMERIC = ("int", "float")
STRING_OPS = ["contains", "equals", "starts with", "ends with", "not contains"]
NUMBER_OPS = ["=", "!=", ">", ">=", "<", "<="]


def make_condition(column, op, value, negate=False, connector="AND"):
    return {"column": column, "op": op, "value": value, "negate": negate, "connector": connector}


def check_condition(row, cond, column_types):
    kind = column_types[cond["column"]]
    cell = row[cond["column"]]
    op = cond["op"]
    if kind in NUMERIC:
        target = float(cond["value"])
        cell = float(cell)
        result = {"=": cell == target, "!=": cell != target, ">": cell > target,
                  ">=": cell >= target, "<": cell < target, "<=": cell <= target}[op]
    else:
        text = str(cell).lower()
        target = str(cond["value"]).lower()
        result = {"equals": text == target, "contains": target in text,
                  "starts with": text.startswith(target), "ends with": text.endswith(target),
                  "not contains": target not in text}[op]
    return (not result) if cond["negate"] else result


def validate(conditions, column_types):
    """Raise ValueError with a friendly message if a number filter has a non-number value."""
    for cond in conditions:
        if column_types[cond["column"]] in NUMERIC:
            try:
                float(cond["value"])
            except ValueError:
                raise ValueError(f"'{cond['value']}' is not a number (column: {cond['column']}).")


def row_matches(row, conditions, column_types):
    groups = [[]]
    for i, cond in enumerate(conditions):
        if i > 0 and cond["connector"] == "OR":
            groups.append([])
        groups[-1].append(cond)
    return any(all(check_condition(row, c, column_types) for c in group) for group in groups)


def filter_rows(rows, conditions, column_types):
    validate(conditions, column_types)
    return [row for row in rows if row_matches(row, conditions, column_types)]
