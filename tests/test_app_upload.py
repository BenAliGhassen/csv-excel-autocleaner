from io import BytesIO
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _xlsx_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()


def test_uploading_xlsx_displays_the_first_worksheet():
    expected = pd.DataFrame({"name": ["Ada"], "score": [36]})
    contents = _xlsx_bytes(
        {
            "People": expected,
            "Other": pd.DataFrame({"other": ["not shown"]}),
        }
    )
    app = AppTest.from_file(str(APP_PATH)).run()

    app.file_uploader[0].set_value(
        (
            "people.xlsx",
            contents,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    ).run()

    assert not app.exception
    assert_frame_equal(app.dataframe[0].value, expected)


def test_uploaded_csv_preserves_columns_and_values():
    expected = pd.DataFrame({"city": ["Paris", "Rome"], "population": [2, 3]})
    app = AppTest.from_file(str(APP_PATH)).run()

    app.file_uploader[0].set_value(
        ("cities.csv", b"city,population\nParis,2\nRome,3\n", "text/csv")
    ).run()

    assert not app.exception
    assert_frame_equal(app.dataframe[0].value, expected)
