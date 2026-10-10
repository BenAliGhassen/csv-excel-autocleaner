import pandas as pd

############ Text formatting ############
def trim_whitespace(df : pd.DataFrame, columns : list[str]) -> pd.DataFrame:
  #Remove spaces
    dcp = df.copy()
    for col in columns:
        dcp[col] = dcp[col].str.strip()
    return dcp    


def normalize_casing(df : pd.DataFrame, columns : list[str], strategy : str)-> pd.DataFrame:
    #Normalize casing
    dcp = df.copy()
    for col in columns:
        try:
          match strategy:
              case "upper" : dcp[col] = dcp[col].str.upper()
              case "lower" : dcp[col] = dcp[col].str.lower()
              case "title" : dcp[col] = dcp[col].str.title()
        except AttributeError: 
                print("Type error")       
    return dcp


def remove_special_characters(df : pd.DataFrame, columns : list[str])-> pd.DataFrame:
  #Remove special chars  
    dcp = df.copy()
    regx = r"[^a-zA-Z0-9\s]"
    for col in columns:
      try:
        dcp[col] = dcp[col].str.replace(regx, "", regex=True)
      except AttributeError:    
          print("Type Error")
    
    return dcp
#########################################    


################ Duplicates #############

def remove_duplicates(df : pd.DataFrame, columns : list[str]) -> pd.DataFrame:
  #Remove duplicate rows or row duplicate on specefic columns  
    dcp = df.copy()
    if(len(columns) > 0):
      dcp = dcp.drop_duplicates(subset= columns)
    else:
          dcp = dcp.drop_duplicates()
    return dcp

#########################################   


############ Missing values #############
def remove_null(df : pd.DataFrame, columns : list[str]) -> pd.DataFrame:
  #Remove rows where a required column is null (empty)
    dcp = df.copy()
    dcp = dcp.dropna(subset= columns)
    return dcp


def fill_null(df: pd.DataFrame, columns: list[str], strategy : str) -> pd.DataFrame:
  #Fill Null 
    dcp =df.copy()
    for col in columns:
        try:
            match strategy:
                case "mean": dcp[col] = dcp[col].fillna(dcp[col].mean())
                case "zero": dcp[col] = dcp[col].fillna(0)
                case "max": dcp[col] = dcp[col].fillna(dcp[col].max())
                case "min": dcp[col] = dcp[col].fillna(dcp[col].min())
                case "ffill": dcp[col] = dcp[col].ffill()
                case "bfill": dcp[col] = dcp[col].bfill()
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Cannot apply the '{strategy}' strategy to column '{col}'"
            ) from exc

    return dcp
#########################################



############ Type correction ############

def retype_numeric( df :pd.DataFrame, columns : list[str]) -> pd.DataFrame:
  #Retype to numeric  
    dcp = df.copy()
    for col in columns :
        dcp[col] = pd.to_numeric(dcp[col], errors='coerce')

    return dcp


def retype_date( df : pd.DataFrame, columns : list[str], format : str) -> pd.DataFrame :
  #Retype to dates
    dcp = df.copy()

    for col in columns :
        dcp[col] = pd.to_datetime(dcp[col],errors="coerce")
        dcp[col] = dcp[col].dt.strftime(format)
    return dcp


def retype_as(df : pd.DataFrame, columns : list[str], target_type : str)-> pd.DataFrame :
  #Retype as take a target type as param and change the columns type to match it  
    dcp= df.copy()
    boolean_values = {
        "yes": True,
        "no": False,
        "true": True,
        "false": False,
        "1": True,
        "0": False,
    }
    for col in columns :
        match target_type :
            case "text" : dcp[col] = dcp[col].astype(str)
            case "boolean" : dcp[col] = dcp[col].astype("string").str.lower().map(boolean_values)

    return dcp
#########################################

########## Row-level filtering ##########

def drop_blank_rows(df :pd.DataFrame)-> pd.DataFrame :
  #Remove rows that are entirely blank
    dcp = df.copy()
    dcp = dcp.dropna(how="all")
    return dcp

#########################################

######### Column-level cleanup #########

def rename_columns(df : pd.DataFrame, mapping: dict)-> pd.DataFrame :
  #Rename column
    dcp = df.copy()
    dcp = dcp.rename(columns=mapping)
    return dcp 


def drop_columns(df : pd.DataFrame, columns : list[str])-> pd.DataFrame :
  #Remove unwanted columns
    dcp = df.copy()
    dcp = dcp.drop(columns= columns) 
    return dcp

#########################################