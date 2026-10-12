# CSV/Excel Auto-Cleanup Tool

[![Sonar](https://github.com/BenAliGhassen/csv-excel-autocleaner/actions/workflows/sonar.yml/badge.svg?branch=main)](https://github.com/BenAliGhassen/csv-excel-autocleaner/actions/workflows/sonar.yml)

[![.github/workflows/test.yml](https://github.com/BenAliGhassen/csv-excel-autocleaner/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/BenAliGhassen/csv-excel-autocleaner/actions/workflows/test.yml)

A Streamlit app for uploading CSV or Excel files, applying an ordered chain of cleaning actions, reviewing a per-action log, and downloading the cleaned data as CSV.

## Links

- [Live demo](https://csv-excel-autocleaner.streamlit.app/)
- Video walkthrough: coming soon

<!-- ![App demo](docs/demo.gif) -->

## Features

The app provides 12 cleaning actions, grouped by purpose:

| Purpose | Actions |
|---|---|
| Missing values | Remove null; Fill null (mean, zero, max, min, forward fill, or backward fill) |
| Duplicates | Remove duplicates |
| Text | Trim whitespace; Normalize casing (upper, lower, or title); Remove special characters |
| Types | Retype numeric; Retype date; Retype as text or boolean |
| Structure | Drop blank rows; Rename columns; Drop columns |

Build an ordered pipeline: each action receives the DataFrame returned by the preceding action. Column choices follow the columns remaining after earlier drops and renames. Before processing, the app checks that referenced columns remain available and that renamed columns have non-empty, unique names. Mean, minimum, and maximum filling also checks the selected columns' data types at the point that action runs.

After a successful run, the app shows the cleaned table, a per-action log of rows removed and nulls resolved, and a CSV download. The displayed results are not retained after the next app interaction.

## How to use the app

1. Upload a `.csv` or `.xlsx` file.
2. Add cleaning actions and set their options in the order you want them applied.
3. Select **Run cleaning** and review the table and action log.
4. Download the cleaned data as a CSV file.

## Run locally

```bash
git clone https://github.com/BenAliGhassen/csv-excel-autocleaner.git
cd csv-excel-autocleaner
python -m venv .venv
```

Activate the environment, then install the dependencies and start the app:

```bash
# Windows PowerShell
.venv\Scripts\Activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

The CI workflows use Python 3.13.

## Tests and quality checks

The project has **68 passing tests**. The tests cover the cleanup functions, action handling and validation, file uploads, and Streamlit behavior.

Run the tests and coverage report locally:

```bash
pytest
pytest --cov=app --cov=cleanup --cov-report=term
```

Measured results:

| Module | Coverage |
|---|---:|
| `app.py` | 96% |
| `cleanup.py` | 95% |
| Total | 96% |

The tests workflow runs on pushes and pull requests. The SonarQube Cloud workflow runs on pushes to `main` and pull requests; it runs pytest with XML coverage output before submitting a SonarQube scan. The coverage report is configured in `sonar-project.properties`.

Sonar flags the `pip install -r requirements.txt` line in both workflows because dependencies are installed without hash verification. These findings are accepted: the requirements are pinned with `==`; the test workflow runs tests, while the Sonar workflow runs tests and an analysis scan; neither workflow deploys the app. Adding hashes would create maintenance work disproportionate to this project.

## Project structure

```text
.
├── app.py                         Streamlit interface and run loop
├── cleanup.py                     Pandas cleaning functions
├── tests/
│   ├── test_app_actions.py        Action configuration and validation tests
│   ├── test_app_upload.py         Upload handling tests
│   ├── test_cleaning.py           Cleaning function tests
│   └── test_streamlit.py          Streamlit behavior tests
├── .github/
│   └── workflows/
│       ├── test.yml               Test workflow
│       └── sonar.yml              SonarQube Cloud workflow
├── .gitignore                     Ignored files and folders
├── sample_data.csv                Sample input data to test
├── requirements.txt                Python dependencies
├── pytest.ini                      pytest configuration
├── sonar-project.properties        SonarQube project settings
├── LICENSE                         MIT license
└── README.md                       Project documentation
```

## The idea

Messy data usually needs several fixes in a specific order: trim spaces, fix types, fill missing
values, remove duplicates. This tool lets you chain those fixes and shows what each step did.

Order matters. Filling nulls with the mean before or after removing duplicates gives different
averages, so the app keeps the actions in an ordered list and runs them top to bottom, each one
working on the result of the previous one.

## How the app works

The cleaning logic is separate from the UI. Each function in `cleanup.py` takes a DataFrame and
returns a new one. The functions copy the input before changing it, so the caller's DataFrame is
not modified.

### 1. Streamlit reruns the whole script

Every click or widget change reruns `app.py` from the top. Normal variables are recreated each
time, so the action list is stored in `st.session_state["actions"]`. The uploaded file stays in
the file uploader widget, but the app parses it into a DataFrame again on reruns. The cleaned
table and log are displayed only in the successful run branch; they are not saved in session
state and disappear on the next interaction.

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

- `id` is an identifier created when the action is added.
- `strategy` is used by actions that need an extra option: Fill null, Normalize casing,
  Retype date, and Retype as.
- `mapping` is used only by Rename columns and maps old names to new names.
- For Retype date, the selected `strategy` is a readable example such as `31 Jan 2024`. A
  lookup translates it into a format code such as `%d %b %Y` for the function call.

### 3. Adding an action

Clicking **Add action** appends a new action and calls `st.rerun()`. The rerun is needed because
the widget loop runs before the button check: without it, the new action would not appear until
another interaction. On the next run, the loop draws the new action's widgets and stores their
values in its dictionary.

### 4. Widget keys use the action id

Each widget has a key built from the action id, such as `type_<id>`, `columns_<id>` and
`strategy_<id>`. Streamlit uses the key to remember each widget's state across reruns. Using
the id rather than the list index keeps the widget state attached to its action when other
actions are removed and indexes shift.

### 5. Removing an action

Clicking **Remove** records the action's id during the loop. The list is filtered after the
loop, because changing a list while looping over it can skip items. The app then calls
`st.rerun()` to redraw the screen without the removed action.

### 6. Tracking which columns exist

The UI keeps a running list of column names while it draws the actions. It starts with the
uploaded file's columns. Drop columns removes selected names from the list, and Rename columns
replaces names using the mapping. Each later action is offered the names available after all
earlier actions. If an earlier action changes and a selected column is no longer available, the
later selection is filtered to remove it.

### 7. Validation

Clicking **Run cleaning** calls `validate_action_columns`. It walks the same running column
list and reports an error if an action uses a column that is no longer available, or if a
rename has an empty new name or would create duplicate column names. Fill null with mean,
minimum, or maximum also checks at run time that the target columns are numeric at that point
in the action chain.

### 8. The run loop and the log

If validation passes, the loop runs the actions in order. For each action:

1. `previous_cleaned = cleaned_df` holds the table immediately before the action. It is not a
   copy; the cleanup functions return new DataFrames.
2. The function is looked up in the `cleanup_dispatch` dictionary and called with the
   arguments required by that action: only the DataFrame for Drop blank rows, the mapping for
   Rename columns, three arguments for actions with a strategy, and two otherwise.
3. The log records rows removed (rows before minus rows after) and nulls resolved (nulls before
   minus nulls after, counted only in targeted columns that exist both before and after the
   action). A negative null count means the action created nulls, which can happen when values
   cannot be converted by Retype numeric or Retype date.

The counts use the result immediately before each action, not the original upload. That way,
the log reports changes made at each step in the chain.

### 9. Results and download

After a successful run, the app displays the cleaned table and log and provides a CSV download.
If validation or a run-time numeric check fails, the app displays an error instead. The results
are not persisted in session state, so they disappear on the next interaction.

## Adding a new cleaning function

1. Write a function in `cleanup.py` that takes a DataFrame and returns a new one.
2. Import it in `app.py` and add it to `cleanup_dispatch`.
3. If it needs an extra option, add it to `strategy_options`.
4. If it takes a different set of arguments, add a branch in the run loop and, if needed, in
   the widget loop.
5. Add tests in `tests/`.
Note : You can use the test skills provided with the project to write test cases

## Known limitations

- Only the first sheet of an Excel file is read.
- Dates are parsed by pandas' format guessing, so day-first dates like 03/01/24 can be read as month-first; the format chosen in the UI only controls the output.
- CSV files are expected to be comma-separated.
- Cleaned results are shown only right after a run and disappear on the next interaction.
- Uploading a different file does not clear the actions from the previous file.
- Unreadable or empty files show an error message instead of loading.
- Files are processed in memory, so very large files will be slow.

## Privacy

The live demo runs on Streamlit Community Cloud. Do not upload sensitive data to the demo.

## License

This project is licensed under the [MIT License](LICENSE).
