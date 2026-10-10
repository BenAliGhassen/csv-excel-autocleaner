from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.mark.parametrize(
    ("action_type", "csv_content", "columns", "strategy", "rename_values", "expected"),
    [
        (
            "Trim whitespace",
            "name\n Ada \n",
            ["name"],
            None,
            None,
            pd.DataFrame({"name": ["Ada"]}),
        ),
        (
            "Normalize casing",
            "name\nada lovelace\n",
            ["name"],
            "upper",
            None,
            pd.DataFrame({"name": ["ADA LOVELACE"]}),
        ),
        (
            "Remove special characters",
            "name\nA_B!\n",
            ["name"],
            None,
            None,
            pd.DataFrame({"name": ["AB"]}),
        ),
        (
            "Remove duplicates",
            "name\nAda\nAda\nGrace\n",
            ["name"],
            None,
            None,
            pd.DataFrame({"name": ["Ada", "Grace"]}, index=[0, 2]),
        ),
        (
            "Remove null",
            'name\nAda\n""\nGrace\n',
            ["name"],
            None,
            None,
            pd.DataFrame({"name": ["Ada", "Grace"]}, index=[0, 2]),
        ),
        (
            "Fill null",
            'score\n1\n""\n3\n',
            ["score"],
            "zero",
            None,
            pd.DataFrame({"score": [1.0, 0.0, 3.0]}),
        ),
        (
            "Retype numeric",
            "amount\n12\n15\n",
            ["amount"],
            None,
            None,
            pd.DataFrame({"amount": [12, 15]}),
        ),
        (
            "Retype date",
            "date\n2024-01-31\n",
            ["date"],
            "31 Jan 2024",
            None,
            pd.DataFrame({"date": ["31 Jan 2024"]}),
        ),
        (
            "Retype as",
            "active\nyes\nno\n",
            ["active"],
            "boolean",
            None,
            pd.DataFrame({"active": [True, False]}),
        ),
        (
            "Drop blank rows",
            'name,age\nAda,36\n"",""\nGrace,85\n',
            [],
            None,
            None,
            pd.DataFrame(
                {"name": ["Ada", "Grace"], "age": [36.0, 85.0]}, index=[0, 2]
            ),
        ),
        (
            "Rename columns",
            "first_name,age\nAda,36\n",
            ["first_name"],
            None,
            {"first_name": "name"},
            pd.DataFrame({"name": ["Ada"], "age": [36]}),
        ),
        (
            "Drop columns",
            "name,age\nAda,36\n",
            ["age"],
            None,
            None,
            pd.DataFrame({"name": ["Ada"]}),
        ),
    ],
    ids=[
        "trim-whitespace",
        "normalize-casing",
        "remove-special-characters",
        "remove-duplicates",
        "remove-null",
        "fill-null",
        "retype-numeric",
        "retype-date",
        "retype-as",
        "drop-blank-rows",
        "rename-columns",
        "drop-columns",
    ],
)
def test_each_cleanup_action_runs_through_the_app(
    action_type: str,
    csv_content: str,
    columns: list[str],
    strategy: str | None,
    rename_values: dict[str, str] | None,
    expected: pd.DataFrame,
):
    app = AppTest.from_file(str(APP_PATH)).run()
    app.file_uploader[0].set_value(
        ("test.csv", csv_content.encode("utf-8"), "text/csv")
    ).run()
    app.button(key="add_action").click().run()
    action_id = app.session_state["actions"][-1]["id"]

    app.selectbox(key=f"type_{action_id}").select(action_type).run()
    if action_type != "Drop blank rows":
        app.multiselect(key=f"columns_{action_id}").set_value(columns).run()
    if rename_values:
        for column, new_name in rename_values.items():
            app.text_input(key=f"rename_{action_id}_{column}").set_value(new_name).run()
    if strategy is not None:
        app.selectbox(key=f"strategy_{action_id}").select(strategy).run()

    app.button(key="run_cleaning").click().run()

    assert not app.exception
    assert not app.error
    assert_frame_equal(app.dataframe[1].value, expected)
