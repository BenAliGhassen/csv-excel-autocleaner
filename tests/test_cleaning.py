import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from cleanup import (
    drop_blank_rows,
    drop_columns,
    fill_null,
    normalize_casing,
    remove_duplicates,
    remove_null,
    remove_special_characters,
    rename_columns,
    retype_as,
    retype_date,
    retype_numeric,
    trim_whitespace,
)


def test_trim_whitespace_changes_only_selected_columns_and_preserves_input():
    source = pd.DataFrame(
        {
            "name": ["  Ada Lovelace ", None],
            "email": [" ada@example.com ", "grace@example.com"],
            "note": ["  keep spaces  ", " unchanged "],
        }
    )

    result = trim_whitespace(source, ["name", "email"])

    assert result["name"].tolist()[0] == "Ada Lovelace"
    assert pd.isna(result.loc[1, "name"])
    assert result["email"].tolist() == ["ada@example.com", "grace@example.com"]
    assert result["note"].tolist() == ["  keep spaces  ", " unchanged "]
    assert source.loc[0, "name"] == "  Ada Lovelace "
    assert result is not source


@pytest.mark.parametrize(
    ("strategy", "expected"),
    [
        ("upper", ["ADA LOVELACE", "GRACE HOPPER"]),
        ("lower", ["ada lovelace", "grace hopper"]),
        ("title", ["Ada Lovelace", "Grace Hopper"]),
    ],
)
def test_normalize_casing_applies_requested_strategy(strategy, expected):
    source = pd.DataFrame(
        {"name": ["Ada Lovelace", "GRACE HOPPER"], "note": ["Keep", "As Is"]}
    )

    result = normalize_casing(source, ["name"], strategy)

    assert result["name"].tolist() == expected
    assert result["note"].tolist() == ["Keep", "As Is"]
    assert source["name"].tolist() == ["Ada Lovelace", "GRACE HOPPER"]


def test_normalize_casing_preserves_missing_values():
    result = normalize_casing(
        pd.DataFrame({"name": [" Ada ", None]}), ["name"], "upper"
    )

    assert result.loc[0, "name"] == " ADA "
    assert pd.isna(result.loc[1, "name"])


def test_normalize_casing_leaves_values_unchanged_for_unknown_strategy():
    source = pd.DataFrame({"name": ["Ada Lovelace"]})

    result = normalize_casing(source, ["name"], "capitalize")

    assert_frame_equal(result, source)


def test_remove_special_characters_preserves_alphanumerics_and_whitespace():
    source = pd.DataFrame(
        {"name": ["A_B! 9", "café@example.com"], "note": ["x-y", " keep! "]}
    )

    result = remove_special_characters(source, ["name"])

    assert result["name"].tolist() == ["AB 9", "cafexamplecom"]
    assert result["note"].tolist() == ["x-y", " keep! "]
    assert source.loc[0, "name"] == "A_B! 9"


def test_remove_special_characters_preserves_missing_values():
    result = remove_special_characters(
        pd.DataFrame({"name": ["A! B?", None]}), ["name"]
    )

    assert result.loc[0, "name"] == "A B"
    assert pd.isna(result.loc[1, "name"])


def test_remove_duplicates_uses_selected_columns_and_keeps_first_row():
    source = pd.DataFrame(
        {
            "email": ["ada@example.com", "ada@example.com", "grace@example.com"],
            "name": ["Ada", "Ada Byron", "Grace"],
        },
        index=[10, 20, 30],
    )

    result = remove_duplicates(source, ["email"])

    expected = source.loc[[10, 30]]
    assert_frame_equal(result, expected)
    assert len(source) == 3


def test_remove_duplicates_without_columns_removes_only_identical_rows():
    source = pd.DataFrame(
        {"name": ["Ada", "Ada", "Ada"], "age": [36, 36, 37]},
        index=[1, 2, 3],
    )

    result = remove_duplicates(source, [])

    assert_frame_equal(result, source.loc[[1, 3]])


def test_remove_duplicates_with_empty_frame_returns_empty_frame():
    source = pd.DataFrame(columns=["name"])

    result = remove_duplicates(source, ["name"])

    assert_frame_equal(result, source)


def test_remove_null_drops_rows_missing_required_values_only():
    source = pd.DataFrame(
        {
            "name": ["Ada", None, "Grace"],
            "age": [36, 85, None],
            "note": [None, "present", "also present"],
        }
    )

    result = remove_null(source, ["name", "age"])

    expected = source.loc[[0]]
    assert_frame_equal(result, expected)
    assert len(source) == 3


def test_remove_null_does_not_treat_empty_string_as_missing():
    source = pd.DataFrame({"name": ["", "Ada"]})

    result = remove_null(source, ["name"])

    assert result["name"].tolist() == ["", "Ada"]


@pytest.mark.parametrize(
    ("strategy", "expected_missing_value"),
    [
        ("mean", 2.0),
        ("zero", 0.0),
        ("max", 3.0),
        ("min", 1.0),
        ("ffill", 1.0),
        ("bfill", 3.0),
    ],
)
def test_fill_null_supports_each_numeric_strategy(strategy, expected_missing_value):
    source = pd.DataFrame({"score": [1.0, None, 3.0], "label": ["a", None, "c"]})

    result = fill_null(source, ["score"], strategy)

    assert result["score"].tolist() == [1.0, expected_missing_value, 3.0]
    assert pd.isna(result.loc[1, "label"])
    assert pd.isna(source.loc[1, "score"])


def test_fill_null_leaves_all_missing_values_when_strategy_has_no_value():
    source = pd.DataFrame({"score": [None, None]})

    result = fill_null(source, ["score"], "mean")

    assert result["score"].isna().all()


def test_fill_null_raises_clear_error_when_mean_strategy_is_used_on_text():
    source = pd.DataFrame({"label": ["Ada", None]})

    with pytest.raises(
        ValueError,
        match="Cannot apply the 'mean' strategy to column 'label'",
    ):
        fill_null(source, ["label"], "mean")

    assert pd.isna(source.loc[1, "label"])


def test_fill_null_leaves_column_unchanged_for_unknown_strategy():
    source = pd.DataFrame({"score": [1.0, None]})

    result = fill_null(source, ["score"], "median")

    assert_frame_equal(result, source)


def test_retype_numeric_converts_numbers_and_coerces_invalid_values():
    source = pd.DataFrame(
        {"amount": ["12.5", "not-a-number", None], "label": ["a", "b", "c"]}
    )

    result = retype_numeric(source, ["amount"])

    assert result.loc[0, "amount"] == 12.5
    assert pd.isna(result.loc[1, "amount"])
    assert pd.isna(result.loc[2, "amount"])
    assert result["amount"].dtype.kind == "f"
    assert source.loc[0, "amount"] == "12.5"
    assert result["label"].tolist() == ["a", "b", "c"]


def test_retype_date_formats_valid_values_and_coerces_invalid_values():
    source = pd.DataFrame({"date": ["2024-02-29", "not-a-date", None]})

    result = retype_date(source, ["date"], "%d/%m/%Y")

    assert result.loc[0, "date"] == "29/02/2024"
    assert pd.isna(result.loc[1, "date"])
    assert pd.isna(result.loc[2, "date"])
    assert source.loc[0, "date"] == "2024-02-29"


def test_retype_as_text_converts_selected_column_to_strings():
    source = pd.DataFrame({"value": [1, 2.5], "other": [True, False]})

    result = retype_as(source, ["value"], "text")

    assert result["value"].tolist() == ["1.0", "2.5"]
    assert pd.api.types.is_string_dtype(result["value"].dtype)
    assert result["other"].tolist() == [True, False]
    assert source["value"].tolist() == [1, 2.5]


def test_retype_as_text_uses_string_representation_for_missing_values():
    source = pd.DataFrame({"value": [None]})

    result = retype_as(source, ["value"], "text")

    assert pd.isna(result.loc[0, "value"])


def test_retype_as_boolean_maps_supported_values_case_insensitively():
    source = pd.DataFrame(
        {"value": ["yes", "NO", "True", "false", "1", "0", "unknown", None]}
    )

    result = retype_as(source, ["value"], "boolean")

    assert result["value"].iloc[:6].tolist() == [
        True,
        False,
        True,
        False,
        True,
        False,
    ]
    assert pd.isna(result.loc[6, "value"])
    assert pd.isna(result.loc[7, "value"])
    assert source.loc[0, "value"] == "yes"


def test_retype_as_leaves_column_unchanged_for_unknown_target_type():
    source = pd.DataFrame({"value": ["1", "2"]})

    result = retype_as(source, ["value"], "integer")

    assert_frame_equal(result, source)


def test_drop_blank_rows_removes_only_rows_that_are_all_null():
    source = pd.DataFrame(
        {"name": [None, "", "Ada"], "age": [None, None, 36]},
        index=[1, 2, 3],
    )

    result = drop_blank_rows(source)

    assert_frame_equal(result, source.loc[[2, 3]])
    assert len(source) == 3


def test_drop_blank_rows_handles_empty_frame():
    source = pd.DataFrame(columns=["name", "age"])

    result = drop_blank_rows(source)

    assert_frame_equal(result, source)


def test_rename_columns_renames_requested_columns_without_mutating_input():
    source = pd.DataFrame({"first_name": ["Ada"], "age": [36]})

    result = rename_columns(source, {"first_name": "name"})

    assert result.columns.tolist() == ["name", "age"]
    assert result.loc[0, "name"] == "Ada"
    assert source.columns.tolist() == ["first_name", "age"]


def test_rename_columns_ignores_mapping_keys_not_in_frame():
    source = pd.DataFrame({"name": ["Ada"]})

    result = rename_columns(source, {"missing": "renamed"})

    assert_frame_equal(result, source)


def test_drop_columns_removes_requested_columns_without_mutating_input():
    source = pd.DataFrame({"name": ["Ada"], "age": [36], "internal_id": [7]})

    result = drop_columns(source, ["internal_id"])

    assert result.columns.tolist() == ["name", "age"]
    assert source.columns.tolist() == ["name", "age", "internal_id"]


def test_drop_columns_raises_for_unknown_column():
    source = pd.DataFrame({"name": ["Ada"]})

    with pytest.raises(KeyError):
        drop_columns(source, ["missing"])
