# CSV/Excel Auto-Cleanup Tool (v1)

A Streamlit app that cleans messy CSV and Excel files. You upload a file, build an ordered
chain of cleaning actions, run it, and get back the cleaned table, a log of what each action
changed, and a CSV to download.

> This is the first version of the documentation. It explains the idea and how the code works.
> Install instructions, demo, CI badge and known limitations will come in the final version.

## The idea

Messy data usually needs several fixes in a specific order: trim spaces, fix types, fill missing
values, remove duplicates. This tool lets you chain those fixes and shows exactly what each
step did.

Order matters. Filling nulls with the mean before or after removing duplicates gives different
averages, so the app keeps the actions in an ordered list and runs them top to bottom, each one
working on the result of the previous one.

## Project structure

```
app.py          The Streamlit UI and the run loop
cleanup.py      12 pure pandas cleaning functions
tests/          pytest tests
sample_data.csv A small messy file to try the app
```

The cleaning logic is separate from the UI. Each function in `cleanup.py` takes a DataFrame and
returns a new one, so it can be tested without Streamlit. Each function starts with `.copy()`,
so the caller's data is never modified.

## The 12 actions

| Group | Actions | Extra option |
|---|---|---|
| Missing values | Remove null, Fill null | Fill null: mean, zero, max, min, ffill, bfill |
| Duplicates | Remove duplicates | none (no columns selected means all columns) |
| Text | Trim whitespace, Normalize casing, Remove special characters | Casing: upper, lower, title |
| Types | Retype numeric, Retype date, Retype as | Date: output format. Retype as: text or boolean |
| Structure | Drop blank rows, Rename columns, Drop columns | Rename: a new name per column |

## How the app works

### 1. Streamlit reruns the whole script

Every click or widget change reruns `app.py` from the top. Normal variables are recreated each
time, so anything that must survive lives in `st.session_state`. Here that is the list of
actions: `st.session_state["actions"]`.

The uploaded file stays in the file uploader widget, so it is not uploaded again on a rerun,
but the app parses it into a DataFrame again each time. That is fine for small files.

### 2. The action list

Each action is one dictionary, and the list order is the execution order:

```python
[
  {"id": "a1f3", "type": "Trim whitespace", "columns": ["name", "city"]},
  {"id": "b7c2", "type": "Rename columns", "columns": ["name", "age"],
   "mapping": {"name": "full_name", "age": "years"}},
  {"id": "d5e8", "type": "Fill null", "columns": ["years", "salary"], "strategy": "mean"},
  {"id": "e2a6", "type": "Drop blank rows", "columns": []},
]
```

- `id` is a UUID created when the action is added. It never changes.
- `strategy` exists only for types that need a third argument (Fill null, Normalize casing,
  Retype date, Retype as).
- `mapping` exists only for Rename columns (old name to new name).
- For Retype date, `strategy` holds a readable example like `31 Jan 2024`, and a lookup table
  turns it into the format code `%d %b %Y` right before the function is called.

### 3. Adding an action

Clicking **Add action** appends `{"id": <uuid>}` to the list and calls `st.rerun()`. The rerun
is needed because the widget loop runs before the button check: without it, the new action
would not appear until another interaction. On the new run, the loop finds the extra action
and draws its widgets, and writes `type` and `columns` into the dictionary.

### 4. Widget keys use the id

Each widget has a key built from the action id, such as `type_<id>`, `columns_<id>` and
`strategy_<id>`. Streamlit uses the key to remember each widget's state across reruns.
Using the id and not the list index means the state stays attached to the right action when
other actions are removed and the indexes shift.

### 5. Removing an action

Clicking **Remove** stores the action's id in a variable during the loop. The list is filtered
after the loop, because changing a list while looping over it can skip items. Then
`st.rerun()` redraws the screen, since the old action had already been drawn before the
deletion happened.

### 6. Tracking which columns exist

The UI keeps a running list of column names while it draws the actions. It starts with the
file's columns, and after each action it applies two rules:
- Drop columns removes the selected names.
- Rename columns replaces names using the mapping.

The options offered to each action are the names that exist after all earlier actions. If an
earlier action changes and a selected column disappears, it is removed from the later
selection. This only removes columns that are no longer available. It does not translate old
names into new ones.

### 7. Validation

Clicking **Run cleaning** first calls `validate_action_columns`. It walks the same running
column list and returns an error message if:
- an action uses a column that is no longer available (mostly a safety net, since the widgets
  already filter these),
- a rename has an empty new name,
- a rename would create duplicate column names.

Fill null with mean, min or max also checks, at run time, that the target columns are numeric
at that point of the chain.

### 8. The run loop and the log

If validation passes, the loop runs the actions in order. For each one:

1. `previous_cleaned = cleaned_df` keeps the table as it was right before this action. It is
   not a copy: it works because every cleaning function returns a new DataFrame.
2. The function is found with the `cleanup_dispatch` dictionary and called with the right
   arguments: only the DataFrame for Drop blank rows, the mapping for Rename columns, three
   arguments for actions with a strategy, and two otherwise.
3. The log records two numbers:
   - **rows removed:** rows before minus rows after, for the whole table.
   - **nulls resolved:** nulls before minus nulls after, counted only in the columns this
     action targeted that still exist before and after. A negative number means the action
     created nulls, which Retype numeric and Retype date do with values they cannot convert.

Using `previous_cleaned` and not the original upload matters in a chain: otherwise an action
would be credited with nulls or rows that an earlier action had already handled.

### 9. Results and download

The cleaned table, the log and the download button are shown only when the run succeeds. If
validation or the numeric check fails, only the error message appears.

## Adding a new cleaning function

1. Write a function in `cleanup.py` that takes a DataFrame and returns a new one.
2. Import it in `app.py` and add it to `cleanup_dispatch`.
3. If it needs an extra option, add it to `strategy_options`.
4. If it takes a different set of arguments, add a branch in the run loop and, if needed, in
   the widget loop.
5. Add tests in `tests/`.

Note : you can use the ai skills provided to write tests

## Tests

```bash
pytest
```