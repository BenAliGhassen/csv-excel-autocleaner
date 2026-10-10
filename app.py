import streamlit as st
import pandas as pd
from uuid import uuid4
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

#Dispatch Table a map of each funtion and it's name will be used to display actions
cleanup_dispatch = {
    "Trim whitespace": trim_whitespace,
    "Normalize casing": normalize_casing,
    "Remove special characters": remove_special_characters,
    "Remove duplicates": remove_duplicates,
    "Remove null": remove_null,
    "Fill null": fill_null,
    "Retype numeric": retype_numeric,
    "Retype date": retype_date,
    "Retype as": retype_as,
    "Drop blank rows": drop_blank_rows,
    "Rename columns": rename_columns,
    "Drop columns": drop_columns,
}

#Dispatch Table a map of each date format
date_format_dispatch = {
    "2024-01-31": "%Y-%m-%d",
    "2024/01/31": "%Y/%m/%d",
    "31 Jan 2024": "%d %b %Y",
    "2024-01-31 14:30:00": "%Y-%m-%d %H:%M:%S",
    "20240131": "%Y%m%d",
}

#Dispatch Table a map of each strategy
strategy_options = {
    "Fill null": ["mean", "zero", "max", "min", "ffill", "bfill"],
    "Normalize casing": ["upper", "lower", "title"],
    "Retype date": list(date_format_dispatch),
    "Retype as": ["text", "boolean"]
}



#Btns styling
st.markdown(
    """
    <style>
    .st-key-add_action button,
    .st-key-download_cleaned_csv button {
        background-color: #1976d2;
        color: white;
        border-color: #1976d2;
    }
    .st-key-run_cleaning button {
        background-color: #2e7d32;
        color: white;
        border-color: #2e7d32;
    }

    [class*="st-key-remove_"] button {
        background-color: #D10000;
        color: white;
        border-color: #D10000;
    }
    </style>
    """,
    unsafe_allow_html=True,
)





#Check if actions are created as streamlit re-run all the code on every interaction we want to avoid erasing our actions when adding a new one
if "actions" not in st.session_state :
    st.session_state["actions"] = []

#Upload file and only accept "csv" or "xlsx"
uploaded_file = st.file_uploader(label="Upload your file",type=["csv","xlsx"])



################################## Functions to be called ##################################

#create a btn and return true when clicked
def add_actions() :
    return st.button("Add action", key="add_action")

def remove_action(i):
    return st.button("Remove", key=f"remove_{i}")

def run(disabled=False):
    return st.button("Run cleaning", key="run_cleaning", disabled=disabled)

def download(df : pd.DataFrame):
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return st.download_button(label="Download cleaned CSV", data=csv_bytes, file_name="cleaned_data.csv", mime="text/csv",type="primary", key="download_cleaned_csv", on_click="ignore")

def show_df(df : pd.DataFrame):
    st.dataframe(df)


def configure_actions(df: pd.DataFrame) -> str | None:
    action_id_to_remove = None
    available_columns = list(df.columns)
    for i, action in enumerate(st.session_state["actions"]):
        #if anything causes the id to not be added we add it here
        if "id" not in action :
            action["id"] = str(uuid4())
        #show fields to user    
        action["type"] = st.selectbox("Action type", options=list(cleanup_dispatch.keys()), key=f"type_{action['id']}")
        columns_key = f"columns_{action['id']}"
        if action["type"] == "Drop blank rows":
            action["columns"] = []
            st.session_state.pop(columns_key, None)
        else:
            selected_columns = st.session_state.get(columns_key, action.get("columns", []))
            selected_columns = [column for column in selected_columns if column in available_columns]
            if columns_key in st.session_state and st.session_state[columns_key] != selected_columns:
                st.session_state[columns_key] = selected_columns
            action["columns"] = st.multiselect("Columns", options=available_columns, key=columns_key)

        if action["type"] == "Rename columns":
            action["mapping"] = {column: st.text_input(f"New name for {column}", value=column, key=f"rename_{action['id']}_{column}") for column in action["columns"]}
        else:
            action.pop("mapping", None)
        #if action type is one that require a strategy then show strategy
        if action["type"] in strategy_options:
            action["strategy"] = st.selectbox("Strategy", options=strategy_options[action["type"]], key=f"strategy_{action['id']}")
        else:
            action.pop("strategy", None)
        if action["type"] == "Drop columns":
            available_columns = [column for column in available_columns if column not in action["columns"]]
        elif action["type"] == "Rename columns":
            available_columns = [action["mapping"].get(column, column) for column in available_columns]
        #if remove is clicked    
        if remove_action(i):
            #action id is assigned to the action_id_to_remove
            action_id_to_remove = action["id"]
    return action_id_to_remove        





def validate_action_columns(actions, columns):
    #a list of the columns that are not removed
    available_columns = list(columns)
    validation_error = None
    for action_index, action in enumerate(actions, start=1):
        #if action is rename columns then as the full code re-run the user will be tasked to write the new name for each column they will be shown here
        if action["type"] == "Rename columns":
            action_columns = list(action["mapping"])
        else:
            action_columns = action["columns"]

        #get deleted columns to make sure they are not used laiter
        missing_columns = [column for column in action_columns if column not in available_columns]

        #if used in any action show a warning
        if missing_columns:
            validation_error = (f"Action {action_index} ({action['type']}) uses columns " f"that are no longer available: {', '.join(missing_columns)}.")
            break

        if action["type"] == "Drop columns":
            available_columns = [column for column in available_columns if column not in action_columns]
        elif action["type"] == "Rename columns":
            mapping = action["mapping"]
            if any(not name.strip() for name in mapping.values()):
                validation_error = f"Action {action_index} (Rename columns) has an empty new column name."
                break
            available_columns = [mapping.get(column, column) for column in available_columns]
            if len(available_columns) != len(set(available_columns)):
                validation_error = f"Action {action_index} (Rename columns) creates duplicate column names."
                break
    return validation_error

###############################################################################################################





if uploaded_file is not None :
    #Read the uploaded file check the type to pick the right opening fn call
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.lower().endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            st.warning("File type not supported")
            st.stop()
    except Exception as exc:
        st.error(f"Unable to read '{uploaded_file.name}': {exc}")
        st.stop()

    #display dataframe content
    show_df(df)

    #this list will have the cleaning overview
    log = []

    #for each id in actions show fileds to be filled
    action_id_to_remove = configure_actions(df)

    #if add action is clicked
    if(add_actions()):
        #create a uuid to track the elements by id not by index (prevent deleting the wrong element)
        st.session_state["actions"].append({"id": str(uuid4())})
        st.rerun()   

    #if action_id_to_remove is not None filter the list to delete the element selected
    if action_id_to_remove is not None:
        st.session_state["actions"] = [action for action in st.session_state["actions"] if action["id"] != action_id_to_remove]
        st.rerun()

    #when run is clicked go through the actions list call the fn using the dispatch table and pass columns and strategys(if there is) get a cleane df
    if(run()):

        #this will validate that some actions are called correctly with the selected columns
        validation_error = validate_action_columns(st.session_state["actions"], df.columns)


        #if warning exist show it else run the functions with the right params
        if validation_error:
            st.error(validation_error)
        else:
            cleaned_df = df.copy()
            error = False
            for action in st.session_state["actions"]:

                previous_cleaned = cleaned_df
                rows_before = len(previous_cleaned)

                func = cleanup_dispatch[action["type"]]
                if action["type"] == "Drop blank rows" :
                    cleaned_df = func(cleaned_df)
                elif action["type"] == "Rename columns":
                    cleaned_df = func(cleaned_df, action["mapping"])
                elif "strategy" in action:
                    strategy = action["strategy"]
                    if action["type"] == "Retype date":
                        strategy = date_format_dispatch[strategy]
                    if action["type"] == "Fill null" and strategy in {"mean", "min", "max"}:
                        incompatible_columns = [column for column in action["columns"] if not pd.api.types.is_numeric_dtype(cleaned_df[column])]
                        if incompatible_columns:
                            st.error("The mean, min, and max strategies require numeric columns: " + ", ".join(incompatible_columns) + ".")
                            error = True
                            break
                    cleaned_df = func(
                        cleaned_df, action["columns"], strategy
                    )
                else:
                    cleaned_df = func(cleaned_df, action["columns"])

                common_columns = [col for col in action["columns"] if col in previous_cleaned.columns and col in cleaned_df.columns]
                
                nulls_before = previous_cleaned[common_columns].isna().sum().sum()
                nulls_after = cleaned_df[common_columns].isna().sum().sum()        
                rows_after = len(cleaned_df)
                
                log.append({"action": action["type"], "columns": action["columns"], "rows removed": rows_before - rows_after, "nulls resolved": nulls_before - nulls_after})


            if(not error):
                show_df(cleaned_df)
                show_df(log)
                #convert the cleaned df to csv ready and downloaded it
                download(cleaned_df)