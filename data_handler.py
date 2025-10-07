"""
Data handling module for mail merge application.
Handles data processing, mapping, formatting, and validation.
"""

import re
import pandas as pd
import locale
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from template_processor import normalize


def to_number(x: Any) -> Optional[Union[int, float]]:
    """
    Try to coerce strings like '1.234,56' or '1234.56' to a float/int.
    
    Args:
        x: Value to convert to number
        
    Returns:
        Converted number or None if not numeric
    """
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    
    # Replace common thousand/decimal variants conservatively
    # First, handle European format like 1.234,56 -> 1234.56
    if re.match(r"^\d{1,3}(\.\d{3})+,\d+$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        # Generic: if there is exactly one comma and no dot, treat comma as decimal separator
        if s.count(",") == 1 and s.count(".") == 0:
            s = s.replace(",", ".")
        # Remove thin spaces or regular spaces used as thousand separators
        s = s.replace("\u202f", "").replace(" ", "")
    
    try:
        v = float(s)
        return int(v) if v.is_integer() else v
    except Exception:
        return None


def try_parse_date(val: Any) -> Optional[pd.Timestamp]:
    """
    Return pandas.Timestamp if val looks like a date, else None.
    
    Args:
        val: Value to parse as date
        
    Returns:
        Parsed timestamp or None
    """
    if isinstance(val, (pd.Timestamp, datetime)):
        return pd.Timestamp(val)
    if isinstance(val, str):
        v = val.strip()
        if not v:
            return None
        # try day-first, then month-first
        for dayfirst in (True, False):
            dt = pd.to_datetime(v, dayfirst=dayfirst, errors='coerce')
            if pd.notna(dt):
                return pd.Timestamp(dt)
    return None


# Date formatting constants
MONTHS_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
MONTHS_NL = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december"
]


def ordinal_en(n: int) -> str:
    """Generate English ordinal suffix (1st, 2nd, 3rd, etc.)."""
    # 11,12,13 are special cases
    if 10 < n % 100 < 14:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_date_long(dt: pd.Timestamp, lang: str) -> str:
    """
    Format date in long form based on language.
    
    Args:
        dt: Timestamp to format
        lang: Language code (NL, US, UK)
        
    Returns:
        Formatted date string
    """
    y, m, d = dt.year, dt.month, dt.day
    if lang == "NL":
        return f"{d} {MONTHS_NL[m-1]} {y}"
    elif lang == "US":
        return f"{MONTHS_EN[m-1]} {ordinal_en(d)}, {y}"
    # Default UK
    return f"{d} {MONTHS_EN[m-1]} {y}"


def reshape_wide_to_rows(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return a single row dict carrying original keys and row.* aliases.
    This matches templates that do {% for row in rows %} and then access row.ronde_2021, etc.
    
    Args:
        record: Dictionary of field values
        
    Returns:
        List containing single row with aliases
    """
    cleaned = {}
    for k, v in record.items():
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip().lower() == 'nan':
            val = ""
        else:
            val = v
        cleaned[str(k)] = val
        cleaned[f"row.{k}"] = val
    return [cleaned]


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names by removing spaces and using underscores.
    
    Args:
        df: DataFrame to normalize
        
    Returns:
        DataFrame with normalized column names
    """
    df.columns = [col.strip().replace(" ", "_") for col in df.columns]
    return df


def create_field_mapping(word_fields: List[str], headers: List[str], df_data: pd.DataFrame) -> List[Tuple[str, str, str]]:
    """
    Create mapping data with suggested matches and example values.
    
    Args:
        word_fields: List of template field names
        headers: List of data column headers
        df_data: DataFrame with data
        
    Returns:
        List of tuples (template_field, suggested_match, example_value)
    """
    normalized_headers = {normalize(h): h for h in headers}
    mapping_data = []
    
    for field in word_fields:
        # strip optional 'row.' prefix from template fields for matching
        field_stripped = re.sub(r'^\s*row\.', '', field.strip())
        norm_field = normalize(field_stripped)
        match = normalized_headers.get(norm_field, "")
        sample = df_data[match].iloc[0] if (match and not df_data.empty) else ""
        mapping_data.append((field, match, sample))
    
    return mapping_data


def format_field_value(raw_value: Any, template_field: str, target_lang: str = "UK") -> str:
    """
    Format a field value based on its type and template field name.
    
    Args:
        raw_value: Raw value from data
        template_field: Name of template field (for context)
        target_lang: Target language for formatting
        
    Returns:
        Formatted value string
    """
    if pd.isna(raw_value):
        return ""
    
    # Date formatting (auto-detect & format long-form)
    dt = try_parse_date(raw_value)
    if dt is not None:
        return format_date_long(dt, target_lang)
    
    # Try numeric coercion
    num = to_number(raw_value)
    fld = template_field.lower()
    if num is not None:
        # 'number' = geen decimalen
        if "number" in fld or "#" in fld or "count" in fld or fld.startswith("aantal"):
            return str(int(num)) if isinstance(num, float) and float(num).is_integer() else str(num)
        # 'amount' of 'bedrag' = € + twee decimalen
        elif "amount" in fld or "bedrag" in fld:
            return f"€{locale.format_string('%.2f', float(num), grouping=True)}"
        else:
            # overige getallen: toon integer zonder decimalen indien mogelijk
            if isinstance(num, float) and float(num).is_integer():
                return str(int(num))
            else:
                return locale.format_string('%.2f', float(num), grouping=True)
    
    return str(raw_value)


def calculate_totals(df_data: pd.DataFrame) -> Dict[str, str]:
    """
    Calculate totals for numeric columns in the dataset.
    
    Args:
        df_data: DataFrame with data
        
    Returns:
        Dictionary with total values for each column
    """
    total_row = {}
    rows_all = df_data.to_dict("records")
    
    for col in df_data.columns:
        col_norm = col.strip().lower()
        if col_norm in ("year", "jaar"):
            total_row[col] = ""
            continue
        
        # Som van numerieke waarden in de kolom
        total = 0.0
        any_numeric = False
        for r in rows_all:
            n = to_number(r.get(col, None))
            if n is not None:
                total += float(n)
                any_numeric = True
        
        if not any_numeric:
            total_row[col] = ""
        elif "amount" in col_norm or "bedrag" in col_norm:
            total_row[col] = f"€{locale.format_string('%.2f', total, grouping=True)}"
        elif "number" in col_norm or "#" in col_norm or "count" in col_norm or col_norm.startswith("aantal"):
            total_row[col] = str(int(total)) if float(total).is_integer() else str(total)
        else:
            total_row[col] = ""
    
    # Label de totalerij indien gewenst
    if df_data.columns.size > 0:
        total_row[next(iter(df_data.columns))] = "Totaal"
    
    return total_row


def create_context_from_row(row: pd.Series, field_mapping: Dict[str, str], 
                           square_fields: List[Dict], target_lang: str = "UK") -> Dict[str, Any]:
    """
    Create template context from a data row.
    
    Args:
        row: Data row (pandas Series)
        field_mapping: Mapping from template fields to data columns
        square_fields: List of square bracket fields to include
        target_lang: Target language for formatting
        
    Returns:
        Context dictionary for template rendering
    """
    context = {}
    
    # Normalized view of the current data row for robust lookup
    norm_row = {normalize(str(k)): row[k] for k in row.index}
    
    # Fill context with values from chosen columns
    for template_field, data_col in field_mapping.items():
        if data_col and data_col in row:
            raw = row[data_col]
            value = format_field_value(raw, template_field, target_lang)
            context[template_field] = value if pd.notna(raw) else ""
        else:
            context[template_field] = ""
    
    # Add row.* aliases for all context keys
    for key, value in list(context.items()):
        context[f"row.{key}"] = value  # alias for templates using row.*
    
    # Add square fields if requested
    for rowdata in square_fields:
        if rowdata.get("Opnemen als veld?") is True:
            veldnaam = rowdata["Veldnaam"]
            fld_norm = normalize(str(veldnaam))
            raw = norm_row.get(fld_norm, "")
            formatted = format_field_value(raw, veldnaam, target_lang)
            context[veldnaam] = formatted
    
    # Add reshaped rows list for single-row loops
    context["rows_one"] = reshape_wide_to_rows(norm_row)
    
    return context
