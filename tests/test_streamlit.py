from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _load_app(csv_content: str | None = None) -> AppTest:
    app = AppTest.from_file(str(APP_PATH)).run()
    if csv_content is not None:
        app.file_uploader[0].set_value(
            ("test.csv", csv_content.encode("utf-8"), "text/csv")
        ).run()
    return app


def _add_action(app: AppTest) -> str:
    app.button(key="add_action").click().run()
    return app.session_state["actions"][-1]["id"]


def test_app_starts_with_csv_uploader_and_no_errors():
    app = _load_app()

    assert not app.exception
    assert len(app.file_uploader) == 1
    assert app.file_uploader[0].allowed_type == [".csv", ".xlsx"]
    assert not app.button


def test_uploading_csv_displays_data_and_action_controls():
    app = _load_app("name,score\nAda,1\nGrace,2\n")

    assert not app.exception
    assert app.dataframe[0].value["name"].tolist() == ["Ada", "Grace"]
    assert [button.label for button in app.button] == [
        "Add action",
        "Run cleaning",
    ]


@pytest.mark.parametrize(
    ("action_type", "expected_strategies"),
    [
        ("Fill null", ["mean", "zero", "max", "min", "ffill", "bfill"]),
        ("Normalize casing", ["upper", "lower", "title"]),
        (
            "Retype date",
            [
                "2024-01-31",
                "2024/01/31",
                "31 Jan 2024",
                "2024-01-31 14:30:00",
                "20240131",
            ],
        ),
    ],
)
def test_strategy_widget_shows_options_for_strategy_actions(
    action_type: str, expected_strategies: list[str]
):
    app = _load_app("name,score\nAda,1\n")
    action_id = _add_action(app)

    app.selectbox(key=f"type_{action_id}").select(action_type).run()

    strategy_widget = app.selectbox(key=f"strategy_{action_id}")
    assert strategy_widget.options == expected_strategies


def test_strategy_widget_is_hidden_for_action_without_strategy():
    app = _load_app("name,score\nAda,1\n")
    action_id = _add_action(app)

    assert app.selectbox(key=f"type_{action_id}").value == "Trim whitespace"
    assert f"strategy_{action_id}" not in [widget.key for widget in app.selectbox]


def test_fill_null_checks_dtype_after_retype_numeric_action():
    app = _load_app("score\n12\nunknown\n15\n")
    numeric_action_id = _add_action(app)
    app.selectbox(key=f"type_{numeric_action_id}").select("Retype numeric").run()
    app.multiselect(key=f"columns_{numeric_action_id}").select("score").run()

    fill_action_id = _add_action(app)
    app.selectbox(key=f"type_{fill_action_id}").select("Fill null").run()
    app.multiselect(key=f"columns_{fill_action_id}").select("score").run()
    app.selectbox(key=f"strategy_{fill_action_id}").select("mean").run()
    app.button(key="run_cleaning").click().run()

    assert not app.exception
    assert not app.error
    assert app.dataframe[1].value["score"].tolist() == [12.0, 13.5, 15.0]


def test_fill_null_rejects_non_numeric_dtype_at_execution():
    app = _load_app("score\nAda\nGrace\n")
    action_id = _add_action(app)
    app.selectbox(key=f"type_{action_id}").select("Fill null").run()
    app.multiselect(key=f"columns_{action_id}").select("score").run()
    app.selectbox(key=f"strategy_{action_id}").select("mean").run()

    assert not app.button(key="run_cleaning").proto.disabled
    app.button(key="run_cleaning").click().run()

    assert not app.exception
    assert "require numeric columns" in app.error[0].value
    assert len(app.dataframe) == 1


def test_rename_columns_uses_user_provided_mapping():
    app = _load_app("first_name,age\nAda,36\n")
    action_id = _add_action(app)

    app.selectbox(key=f"type_{action_id}").select("Rename columns").run()
    app.multiselect(key=f"columns_{action_id}").select("first_name").run()
    app.text_input(key=f"rename_{action_id}_first_name").set_value("name").run()
    app.button(key="run_cleaning").click().run()

    assert not app.exception
    expected = pd.DataFrame({"name": ["Ada"], "age": [36]})
    assert_frame_equal(app.dataframe[1].value, expected)


def test_stale_column_selection_is_removed_when_an_earlier_action_drops_it():
    app = _load_app("name,age\nAda,36\n")

    drop_action_id = _add_action(app)
    app.selectbox(key=f"type_{drop_action_id}").select("Trim whitespace").run()
    app.multiselect(key=f"columns_{drop_action_id}").select("age").run()

    later_action_id = _add_action(app)
    app.selectbox(key=f"type_{later_action_id}").select("Trim whitespace").run()
    app.multiselect(key=f"columns_{later_action_id}").select("age").run()

    app.selectbox(key=f"type_{drop_action_id}").select("Drop columns").run()
    app.multiselect(key=f"columns_{drop_action_id}").set_value(["name"]).run()

    assert app.multiselect(key=f"columns_{later_action_id}").options == ["age"]
    assert app.multiselect(key=f"columns_{later_action_id}").value == []

    app.button(key="run_cleaning").click().run()

    assert not app.exception
    assert not app.error
    assert app.dataframe[1].value.columns.tolist() == ["age"]


def test_later_action_can_select_a_column_renamed_by_an_earlier_action():
    app = _load_app("first_name,age\nAda,36\n")

    rename_action_id = _add_action(app)
    app.selectbox(key=f"type_{rename_action_id}").select("Rename columns").run()
    app.multiselect(key=f"columns_{rename_action_id}").select("first_name").run()
    app.text_input(key=f"rename_{rename_action_id}_first_name").set_value("name").run()

    later_action_id = _add_action(app)
    app.selectbox(key=f"type_{later_action_id}").select("Trim whitespace").run()
    assert app.multiselect(key=f"columns_{later_action_id}").options == ["name", "age"]
    app.multiselect(key=f"columns_{later_action_id}").select("name").run()
    app.button(key="run_cleaning").click().run()

    assert not app.exception
    assert not app.error
    assert app.dataframe[1].value.columns.tolist() == ["name", "age"]


def test_drop_blank_rows_does_not_render_a_columns_selector():
    app = _load_app("name,age\nAda,36\n")
    drop_action_id = _add_action(app)
    app.selectbox(key=f"type_{drop_action_id}").select("Drop columns").run()
    app.multiselect(key=f"columns_{drop_action_id}").select("age").run()

    blank_rows_action_id = _add_action(app)
    app.selectbox(key=f"type_{blank_rows_action_id}").select("Drop blank rows").run()

    assert f"columns_{blank_rows_action_id}" not in [
        widget.key for widget in app.multiselect
    ]
    assert app.session_state["actions"][-1]["columns"] == []


def test_rename_widget_keeps_value_attached_to_column_after_selection_changes():
    app = _load_app("a,b,c\nA,B,C\n")
    action_id = _add_action(app)
    app.selectbox(key=f"type_{action_id}").select("Rename columns").run()
    app.multiselect(key=f"columns_{action_id}").set_value(["a", "b", "c"]).run()
    app.text_input(key=f"rename_{action_id}_a").set_value("alpha").run()
    app.text_input(key=f"rename_{action_id}_b").set_value("beta").run()
    app.text_input(key=f"rename_{action_id}_c").set_value("gamma").run()

    app.multiselect(key=f"columns_{action_id}").set_value(["a", "c"]).run()

    assert app.text_input(key=f"rename_{action_id}_c").value == "gamma"
    app.button(key="run_cleaning").click().run()
    assert app.dataframe[1].value.columns.tolist() == ["alpha", "b", "gamma"]


@pytest.mark.parametrize(
    ("first_name", "second_name", "expected_error"),
    [
        ("", "b", "empty new column name"),
        ("same", "same", "duplicate column names"),
    ],
)
def test_rename_rejects_empty_and_duplicate_target_names(
    first_name: str, second_name: str, expected_error: str
):
    app = _load_app("a,b\nA,B\n")
    action_id = _add_action(app)
    app.selectbox(key=f"type_{action_id}").select("Rename columns").run()
    app.multiselect(key=f"columns_{action_id}").set_value(["a", "b"]).run()
    app.text_input(key=f"rename_{action_id}_a").set_value(first_name).run()
    app.text_input(key=f"rename_{action_id}_b").set_value(second_name).run()
    app.button(key="run_cleaning").click().run()

    assert not app.exception
    assert expected_error in app.error[0].value
    assert len(app.dataframe) == 1


def test_remove_button_removes_only_the_selected_action_by_id():
    app = _load_app("name,score\nAda,1\n")
    removed_id = _add_action(app)
    remaining_id = _add_action(app)

    app.button(key="remove_0").click().run()

    actions = app.session_state["actions"]
    assert len(actions) == 1
    assert actions[0]["id"] == remaining_id
    assert all(action["id"] != removed_id for action in actions)


def test_run_applies_actions_in_order_and_shows_result_and_download():
    app = _load_app("name,score\nada,1\nbob,\n")

    fill_action_id = _add_action(app)
    app.selectbox(key=f"type_{fill_action_id}").select("Fill null").run()
    app.multiselect(key=f"columns_{fill_action_id}").select("score").run()
    app.selectbox(key=f"strategy_{fill_action_id}").select("zero").run()

    casing_action_id = _add_action(app)
    app.selectbox(key=f"type_{casing_action_id}").select("Normalize casing").run()
    app.multiselect(key=f"columns_{casing_action_id}").select("name").run()
    app.selectbox(key=f"strategy_{casing_action_id}").select("upper").run()

    app.button(key="run_cleaning").click().run()

    assert not app.exception
    expected = pd.DataFrame({"name": ["ADA", "BOB"], "score": [1.0, 0.0]})
    assert_frame_equal(app.dataframe[1].value, expected)
    download_buttons = app.get("download_button")
    assert len(download_buttons) == 1
    assert download_buttons[0].label == "Download cleaned CSV"

    app.button(key="add_action").click().run()

    assert not app.exception
    assert_frame_equal(app.dataframe[1].value, expected)
    assert len(app.dataframe) >= 3


def test_uploading_a_different_file_resets_actions_and_previous_results():
    app = _load_app("name,score\nada,1\n")
    action_id = _add_action(app)
    app.selectbox(key=f"type_{action_id}").select("Normalize casing").run()
    app.multiselect(key=f"columns_{action_id}").select("name").run()
    app.selectbox(key=f"strategy_{action_id}").select("upper").run()
    app.button(key="run_cleaning").click().run()
    assert len(app.session_state["actions"]) == 1
    assert "cleaned_df" in app.session_state

    app.file_uploader[0].set_value(
        ("different.csv", b"city,count\nParis,2\n", "text/csv")
    ).run()

    assert not app.exception
    assert app.session_state["actions"] == []
    assert "cleaned_df" not in app.session_state
    assert [button.label for button in app.button] == ["Add action", "Run cleaning"]
    assert app.dataframe[0].value.columns.tolist() == ["city", "count"]


def test_empty_csv_displays_read_error_without_uncaught_exception():
    app = _load_app("")

    assert not app.exception
    assert "Unable to read" in app.error[0].value
    assert "No columns to parse" in app.error[0].value


def test_invalid_excel_displays_read_error_without_uncaught_exception():
    app = AppTest.from_file(str(APP_PATH)).run()
    app.file_uploader[0].set_value(
        ("invalid.xlsx", b"not an excel workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    ).run()

    assert not app.exception
    assert "Unable to read" in app.error[0].value


def test_run_translates_date_example_to_expected_output_format():
    app = _load_app("date\n2024-01-31\n")
    action_id = _add_action(app)

    app.selectbox(key=f"type_{action_id}").select("Retype date").run()
    app.multiselect(key=f"columns_{action_id}").select("date").run()
    app.selectbox(key=f"strategy_{action_id}").select("31 Jan 2024").run()
    app.button(key="run_cleaning").click().run()

    assert not app.exception
    expected = pd.DataFrame({"date": ["31 Jan 2024"]})
    assert_frame_equal(app.dataframe[1].value, expected)
