import streamlit as st
import pandas as pd
import plotly.express as px
from html import escape
from pathlib import Path
import base64
import unicodedata
from google.oauth2 import service_account
from google.cloud import bigquery

### BIGQUERY CONFIGS
creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
client = bigquery.Client(credentials=creds, project=st.secrets["gcp_service_account"]["project_id"])
project_id = st.secrets["gcp_service_account"]["project_id"]
bigquery_db = st.secrets["bigquery"]["database"]
###


CACHE_DATA_STR = "Cargando datos... Esto puede demorar unos segundos."
BASE_DIR = Path(__file__).resolve().parent
ICONS_DIR = BASE_DIR / "utils" / "icons"
ICONS_MAPPING_FILE = BASE_DIR / "utils" / "issuer_icon_mapping.csv"
LOGO_FILE = BASE_DIR / "utils" / "logo.png"
LOGO_SIZE = 350

# Page Configuration
st.set_page_config(
    page_title="Explorador de descuentos",
    page_icon="💸",
    layout="wide"
)

st.logo(str(LOGO_FILE), size='large')

def load_query(query_file):
    with open(BASE_DIR / "utils" / "queries" / query_file, "r") as f:
        return f.read().replace("{project_id}", project_id)\
            .replace("{bigquery_db}", bigquery_db)

# Data Loading
@st.cache_data(ttl=600, show_spinner=CACHE_DATA_STR)
def load_discount_data():
    try:
        query = load_query("streamlit_data.sql")
        df = client.query(query).to_dataframe(create_bqstorage_client=False)
        return df
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=CACHE_DATA_STR)
def load_issuer_metadata():
    try:
        query = load_query("issuer_metadata.sql")
        return client.query(query).to_dataframe(create_bqstorage_client=False)
    except Exception as e:
        return pd.DataFrame()

def normalize_issuer_key(value):
    if pd.isna(value) or value is None:
        return ""
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return "".join(ch for ch in value if ch.isalnum())


@st.cache_data(ttl=600, show_spinner=False)
def load_issuer_icon_mapping():
    try:
        mapping_df = pd.read_csv(ICONS_MAPPING_FILE)
    except FileNotFoundError:
        return {}

    cleaned = mapping_df.dropna(subset=["issuer_name", "icon_file"]).copy()
    cleaned["issuer_name_key"] = cleaned["issuer_name"].apply(normalize_issuer_key)
    cleaned = cleaned[cleaned["issuer_name_key"] != ""]

    mapping = (
        cleaned
        .drop_duplicates(subset=["issuer_name_key"], keep="last")
        .set_index("issuer_name_key")["icon_file"]
        .to_dict()
    )
    return mapping


@st.cache_data(ttl=600, show_spinner=False)
def get_base64_icon(icon_path_str):
    try:
        with open(icon_path_str, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

# Helper Functions
def truncate_text(text, max_length=150):
    """Truncate text to max_length with ellipsis if needed."""
    if pd.isna(text) or text is None:
        return ""
    text = str(text).strip()
    return text[:max_length] + "..." if len(text) > max_length else text

def map_days(days_str):
    """Map day numbers to Spanish shorthand day names list."""
    if days_str is None or (hasattr(days_str, '__len__') and len(days_str) == 0) or str(days_str).strip() in ('', 'nan', 'None'):
        return []
    day_names = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    try:
        if isinstance(days_str, str):
            days_str = days_str.strip('{}')
            days = [int(d.strip()) for d in days_str.split(',')]
        elif isinstance(days_str, (list, tuple)):
            days = [int(d) for d in days_str]
        else:
            days = [int(d) for d in days_str]
        names = [day_names[d] for d in days if 0 <= d <= 6]
        return names
    except:
        return []

DAY_ORDER = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
DAY_FULL_NAMES = {
    'Lun': 'Lunes',
    'Mar': 'Martes',
    'Mié': 'Miércoles',
    'Jue': 'Jueves',
    'Vie': 'Viernes',
    'Sáb': 'Sábado',
    'Dom': 'Domingo',
}

def format_valid_days(valid_days_list):
    """Build the 'Días válidos' display string: 'Todos' if every day is valid, else full day names."""
    if not valid_days_list:
        return "-"
    if set(valid_days_list) >= set(DAY_ORDER):
        return "Todos"
    return ", ".join(DAY_FULL_NAMES[day] for day in DAY_ORDER if day in valid_days_list)

def get_validity(row):
    """Determine where discount is valid."""
    online = row.get('discount_valid_online', False)
    instore = row.get('discount_valid_instore', False)
    if online and instore:
        return "Online y Presencial"
    elif online:
        return "Solo Online"
    elif instore:
        return "Solo Presencial"
    else:
        return "Ver legales"


def format_discount_fields(row):
    discount_rate_raw = row.get('discount_rate')
    if pd.notna(discount_rate_raw) and float(discount_rate_raw) > 0:
        discount_rate = f"{discount_rate_raw:.0%}"
    else:
        discount_rate = "-"

    installments_raw = row.get('discount_no_interest_installment_qty')
    if pd.notna(installments_raw) and float(installments_raw) > 0:
        installments_value = str(int(installments_raw))
    else:
        installments_value = "-"

    min_purchase_raw = row.get('discount_min_purchase_amount')
    if pd.notna(min_purchase_raw):
        min_purchase_value = "Sin mínimo" if float(min_purchase_raw) == 0 else f"${int(min_purchase_raw)}"
    else:
        min_purchase_value = "N/A"

    max_discount_raw = row.get('discount_max_discount_amount')
    if pd.notna(max_discount_raw):
        max_discount_value = "Sin tope" if float(max_discount_raw) == 0 else f"${int(max_discount_raw)}"
    else:
        max_discount_value = "N/A"

    return discount_rate, installments_value, min_purchase_value, max_discount_value

def format_display_value(value, suffix=""):
    if value == "-":
        return "-"
    return f"{value}{suffix}"


PAYMENT_METHOD_TYPE_LABELS = {
    'credit_card': 'Tarjeta de crédito',
    'debit_card': 'Tarjeta de débito',
    'account_money': 'Dinero en cuenta',
}


def _is_missing_payment_field(value):
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


def format_payment_method_entry(entry):
    """Build a display label for a single payment method struct (type, card_network, card_tier)."""
    raw_type = entry.get('type') if isinstance(entry, dict) else None
    type_label = PAYMENT_METHOD_TYPE_LABELS.get(raw_type, raw_type or '')

    parts = [type_label] if type_label else []
    for field in ('card_network', 'card_tier'):
        value = entry.get(field) if isinstance(entry, dict) else None
        if _is_missing_payment_field(value):
            continue
        label = 'Todas' if value == 'all' else str(value)
        if label not in parts:
            parts.append(label)
    return " ".join(parts)


def format_payment_methods(payment_methods_list):
    """Build the 'Métodos de pago' display string from a discount's payment methods array."""
    if payment_methods_list is None or (hasattr(payment_methods_list, '__len__') and len(payment_methods_list) == 0):
        return "-"
    labels = []
    for entry in payment_methods_list:
        label = format_payment_method_entry(entry)
        if label and label not in labels:
            labels.append(label)
    return ", ".join(labels) if labels else "-"


def extract_payment_method_types(payment_methods_list):
    """Return the distinct payment method type labels (e.g. 'Tarjeta de crédito') present in a discount's payment methods array."""
    if payment_methods_list is None or (hasattr(payment_methods_list, '__len__') and len(payment_methods_list) == 0):
        return []
    types = []
    for entry in payment_methods_list:
        raw_type = entry.get('type') if isinstance(entry, dict) else None
        type_label = PAYMENT_METHOD_TYPE_LABELS.get(raw_type, raw_type or '')
        if type_label and type_label not in types:
            types.append(type_label)
    return types


def format_payment_methods_grouped_html(payment_methods_list):
    """Build an HTML 'Métodos de pago' string, grouped by type with bolded type labels.

    Returns HTML (a bold <strong> type label per group, with card_network/card_tier
    combos for that type in parentheses) — the caller must render it with
    unsafe_allow_html=True and must NOT re-escape the returned string, since the
    dynamic parts are already escaped here and only the surrounding <strong> tags
    (literal, not derived from data) are unescaped markup.
    """
    if payment_methods_list is None or (hasattr(payment_methods_list, '__len__') and len(payment_methods_list) == 0):
        return "-"

    group_order = []
    group_details = {}
    for entry in payment_methods_list:
        if not isinstance(entry, dict):
            continue
        raw_type = entry.get('type')
        type_label = PAYMENT_METHOD_TYPE_LABELS.get(raw_type, raw_type or '')
        if not type_label:
            continue
        if type_label not in group_details:
            group_details[type_label] = []
            group_order.append(type_label)

        details = []
        for field in ('card_network', 'card_tier'):
            value = entry.get(field)
            if _is_missing_payment_field(value):
                continue
            label = 'Todas' if value == 'all' else str(value)
            if label not in details:
                details.append(label)
        detail_str = " ".join(details)
        if detail_str and detail_str not in group_details[type_label]:
            group_details[type_label].append(detail_str)

    if not group_order:
        return "-"

    parts = []
    for type_label in group_order:
        escaped_type = f"<strong>{escape(type_label)}</strong>"
        details = group_details[type_label]
        if details:
            escaped_details = ", ".join(escape(d) for d in details)
            parts.append(f"{escaped_type} ({escaped_details})")
        else:
            parts.append(escaped_type)
    return ", ".join(parts)


# --- PAGE: ISSUER STATUS ---
def page_issuer_status():
    st.image(str(LOGO_FILE), width=LOGO_SIZE)
    st.subheader("Entidades disponibles")

    metadata_df = load_issuer_metadata()
    icon_mapping = load_issuer_icon_mapping()

    metadata_df = metadata_df.copy()
    metadata_df["last_scraped_at"] = pd.to_datetime(metadata_df["last_scraped_at"], errors="coerce")
    metadata_df["discount_count"] = pd.to_numeric(metadata_df["discount_count"], errors="coerce").fillna(0).astype(int)

    summary_cards = [
        ("Entidades Activas", len(metadata_df)),
        ("Total Descuentos", int(metadata_df["discount_count"].sum())),
    ]
    for col, (label, value) in zip(st.columns(2), summary_cards):
        col.markdown(
            f"""
            <div style="background-color:#00A36C; border-radius:10px; padding:16px; text-align:center;">
                <div style="font-size:0.9rem; color:#FFFFFF;">{escape(label)}</div>
                <div style="font-size:2rem; font-weight:700; color:#FFFFFF; line-height:1.1;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    for _, row in metadata_df.iterrows():
        issuer_name = str(row.get("issuer_name", "Emisor"))
        issuer_key = normalize_issuer_key(issuer_name)
        icon_filename = icon_mapping.get(issuer_key)
        icon_path = ICONS_DIR / icon_filename if icon_filename else None
        issuer_last_scrape = row.get("last_scraped_at")
        issuer_last_scrape_label = issuer_last_scrape.strftime("%d/%m/%Y %H:%M") if pd.notna(issuer_last_scrape) else "N/A"

        with st.container(border=True):
            icon_col, info_col, metric_col = st.columns([1.2, 4.8, 2.0])

            with icon_col:
                if icon_path and icon_path.exists():
                    st.image(str(icon_path), width=56)

            with info_col:
                st.markdown(f"**{issuer_name}**")
                st.caption(f"Última actualización: {issuer_last_scrape_label}")

            with metric_col:
                st.metric("Descuentos", int(row.get("discount_count", 0)))


# --- PAGE: GUIDED SEARCH ---
def page_guided_search():
    st.image(str(LOGO_FILE), width=LOGO_SIZE)

    df = load_discount_data()
    icon_mapping = load_issuer_icon_mapping()

    df = df.copy()
    df["valid_days_names"] = df["discount_valid_days_list"].apply(map_days)
    df["formato"] = df.apply(get_validity, axis=1)
    df["payment_method_types"] = df["discount_payment_methods_list"].apply(extract_payment_method_types)

    st.subheader("¿Dónde querés comprar?")
    merchant_col, category_col = st.columns(2)
    with merchant_col:
        merchant_query = st.text_input(
            "Buscar por nombre del comercio",
            placeholder="Ej: Coto, Starbucks, Carrefour...",
            key="guided_merchant_query",
        ).strip()

    with category_col:
        category_options = sorted(df["merchant_category_name"].dropna().unique())
        selected_category = st.selectbox(
            "Buscar por categoría",
            options=category_options,
            index=None,
            placeholder="Todas las categorías",
            key="guided_category_select",
        )

    has_primary_filter = bool(merchant_query) or bool(selected_category)

    if not has_primary_filter:
        return

    st.subheader("¿Qué bancos/membresías tenés?")

    pre_mask = pd.Series(True, index=df.index)
    if merchant_query:
        pre_mask = pre_mask & df["merchant_name"].str.contains(merchant_query, case=False, na=False)
    if selected_category:
        pre_mask = pre_mask & (df["merchant_category_name"] == selected_category)

    prefiltered_df = df[pre_mask].copy()
    issuer_options = sorted(prefiltered_df["issuer_name"].dropna().unique())
    
    selected_issuers = st.multiselect(
        "Emisores a considerar",
        label_visibility="hidden",
        options=issuer_options,
        default=[],
        placeholder="Podés elegir bancos u otras membresías",
        key="guided_issuers",
    )
    if prefiltered_df.empty:
        st.info("No hay descuentos que coincidan con comercio/categoría.")
        return

    if not selected_issuers:
        return

    st.divider()

    _show_inactive = st.session_state.get("guided_show_inactive", False)
    _display_count = len(prefiltered_df) if _show_inactive else int(prefiltered_df["discount_is_active"].sum())
    st.markdown(
        f"<h3 style='margin:0 0 0.25rem 0;'><span style='color:#00A36C; font-weight:800;'>{_display_count}</span> <span style='color:#00A36C; font-weight:800;'>descuentos</span> <span style='color:#1A202C; font-weight:600;'>encontrados</span></h3>",
        unsafe_allow_html=True,
    )

    day_order = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    rf_col1, rf_col2, rf_col3, rf_col4, rf_col5, rf_col6 = st.columns(6)
    with rf_col1:
        selected_result_days = st.multiselect(
            "Filtrar por día de validez",
            options=day_order,
            default=[],
            placeholder="Todos los días",
            key="guided_result_days",
        )

    filtered_df = prefiltered_df[prefiltered_df["issuer_name"].isin(selected_issuers)]

    if selected_result_days:
        filtered_df = filtered_df[
            filtered_df["valid_days_names"].apply(
                lambda days: any(day in days for day in selected_result_days)
            )
        ]

    merchant_options = sorted(filtered_df["merchant_name"].dropna().unique())
    with rf_col2:
        selected_result_merchant = st.multiselect(
            "Filtrar por comercio",
            options=merchant_options,
            default=[],
            placeholder="Todos los comercios",
            key="guided_result_merchant_select",
        )
    formato_options = sorted(filtered_df["formato"].dropna().unique())
    with rf_col3:
        selected_result_formato = st.selectbox(
            "Filtrar por formato",
            options=formato_options,
            index=None,
            placeholder="Todos los formatos",
            key="guided_result_formato_select",
        )
    payment_method_type_options = sorted({
        payment_type
        for types in filtered_df["payment_method_types"]
        for payment_type in types
    })
    with rf_col4:
        selected_payment_method_types = st.multiselect(
            "Filtrar por método de pago",
            options=payment_method_type_options,
            default=[],
            placeholder="Todos los métodos",
            key="guided_result_payment_method_types",
        )
    with rf_col5:
        result_order_by = st.selectbox(
            "Ordenar por",
            options=["Descuento más grande", "Más cuotas sin interés"],
            index=0,
            key="guided_result_order_by",
        )
    with rf_col6:
        show_inactive = st.toggle("Incluir vencidos", value=False, key="guided_show_inactive")

    if selected_result_merchant:
        filtered_df = filtered_df[
            filtered_df["merchant_name"].isin(selected_result_merchant)
        ]

    if selected_result_formato:
        filtered_df = filtered_df[
            filtered_df["formato"] == selected_result_formato
        ]

    if selected_payment_method_types:
        filtered_df = filtered_df[
            filtered_df["payment_method_types"].apply(
                lambda types: any(t in types for t in selected_payment_method_types)
            )
        ]

    order_column = "discount_rate" if result_order_by == "Descuento más grande" else "discount_no_interest_installment_qty"
    filtered_df = filtered_df.sort_values(
        by=[order_column, "merchant_name"],
        ascending=[False, True],
    ).reset_index(drop=True)

    if not show_inactive:
        filtered_df = filtered_df[filtered_df["discount_is_active"] == True]

    filter_signature = (
        merchant_query,
        selected_category,
        tuple(sorted(selected_issuers)),
        tuple(selected_result_days),
        selected_result_merchant,
        selected_result_formato,
        tuple(sorted(selected_payment_method_types)),
        result_order_by,
        show_inactive,
    )
    if st.session_state.get("guided_filter_signature") != filter_signature:
        st.session_state["guided_filter_signature"] = filter_signature
        st.session_state["guided_visible_count"] = 20

    visible_count = st.session_state.get("guided_visible_count", 20)
    shown_count = min(visible_count, len(filtered_df))
    visible_df = filtered_df.head(shown_count)

    st.caption(f"Mostrando {shown_count} de {len(filtered_df)} descuentos")

    if filtered_df.empty:
        st.info("No hay descuentos que coincidan con la búsqueda y emisores seleccionados.")
        return

    column_widths = [0.7, 1.0, 1.1, 1.0, 0.7, 0.9, 1.0, 0.8, 0.8, 1.5, 0.7, 0.7, 0.7]
    column_headers = [
        "Entidad", "Comercio", "Categoría", "Descuento", "Cuotas s/int.",
        "Formato", "Vigencia", "Compra mínima", "Tope",
        "Métodos de pago", "Días válidos", "T&C", "Ir al sitio web",
    ]
    st.markdown(
        """
        <style>
        div[class*="st-key-guided_v2_header"] {
            background-color: #00A36C;
            border-radius: 8px;
            padding: 16px 10px;
            margin-bottom: 6px;
            min-height: 100px;
            display: flex;
            align-items: center;
        }
        div[class*="st-key-guided_v2_header"] p {
            color: #F5F5F5 !important;
            margin: 0;
        }
        div[class*="st-key-guided_v2_top_row"] {
            border-color: #D4AF37 !important;
            background-color: rgba(212,175,55,0.14) !important;
        }
        div[class*="st-key-guided_v2_header"] div[data-testid="stColumn"]:not(:last-child) {
            border-right: 1px solid rgba(245,245,245,0.35);
        }
        div[class*="st-key-guided_v2_top_row"] div[data-testid="stColumn"]:not(:last-child),
        div[class*="st-key-guided_v2_row_"] div[data-testid="stColumn"]:not(:last-child) {
            border-right: 1px solid #E2E8F0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="guided_v2_header"):
        header_cols = st.columns(column_widths)
        for header_col, header in zip(header_cols, column_headers):
            header_col.markdown(f"**{header}**")

    for row_idx, (_, row) in enumerate(visible_df.iterrows()):
        issuer_name = str(row.get("issuer_name", ""))
        issuer_key = normalize_issuer_key(issuer_name)
        icon_filename = icon_mapping.get(issuer_key)
        icon_path = ICONS_DIR / icon_filename if icon_filename else None
        icon_base64 = get_base64_icon(str(icon_path)) if icon_path and icon_path.exists() else None
        icon_html = (
            f"<img src=\"data:image/png;base64,{icon_base64}\" alt=\"{escape(issuer_name)}\" style=\"height:28px; width:auto; max-width:60px; object-fit:contain;\"/>"
            if icon_base64
            else ""
        )

        start_date = pd.to_datetime(row["discount_start_date"]).strftime("%d/%m/%Y") if pd.notna(row["discount_start_date"]) else "N/A"
        end_date = pd.to_datetime(row["discount_end_date"]).strftime("%d/%m/%Y") if pd.notna(row["discount_end_date"]) else "N/A"
        validity = get_validity(row)
        discount_rate, installments_value, min_purchase_value, max_discount_value = format_discount_fields(row)
        payment_methods_html = format_payment_methods_grouped_html(row.get("discount_payment_methods_list"))
        valid_days_list = map_days(row.get("discount_valid_days_list"))
        days_display = format_valid_days(valid_days_list)

        is_active = row.get('discount_is_active', True)
        row_text_color = "#1A202C" if is_active else "#9CA3AF"
        discount_color = "#00A36C" if is_active else "#9CA3AF"

        row_container = (
            st.container(border=True, key="guided_v2_top_row")
            if row_idx == 0
            else st.container(border=True, key=f"guided_v2_row_{row_idx}")
        )
        with row_container:
            row_cols = st.columns(column_widths)
            row_cols[0].markdown(icon_html, unsafe_allow_html=True)
            row_cols[1].markdown(
                f"<span style='color:{row_text_color}; font-weight:700;'>{escape(str(row.get('merchant_name', 'N/A')))}</span>",
                unsafe_allow_html=True,
            )
            row_cols[2].markdown(
                f"<span style='color:{row_text_color};'>{escape(str(row.get('merchant_category_name', 'N/A')))}</span>",
                unsafe_allow_html=True,
            )
            row_cols[3].markdown(
                f"<span style='color:{discount_color}; font-weight:700;'>{escape(format_display_value(discount_rate, ' OFF'))}</span>",
                unsafe_allow_html=True,
            )
            remaining_values = [
                installments_value,
                validity,
                f"{start_date} a {end_date}",
                min_purchase_value,
                max_discount_value,
            ]
            for row_col, value in zip(row_cols[4:9], remaining_values):
                row_col.markdown(
                    f"<span style='color:{row_text_color};'>{escape(str(value))}</span>",
                    unsafe_allow_html=True,
                )
            row_cols[9].markdown(
                f"<span style='color:{row_text_color};'>{payment_methods_html}</span>",
                unsafe_allow_html=True,
            )
            row_cols[10].markdown(
                f"<span style='color:{row_text_color};'>{escape(str(days_display))}</span>",
                unsafe_allow_html=True,
            )

            with row_cols[11]:
                with st.popover("📋"):
                    tc = row.get("discount_terms_and_conditions")
                    if pd.notna(tc) and str(tc).strip() != "":
                        st.text(str(tc))
                    else:
                        st.text("No hay términos y condiciones disponibles.")
            with row_cols[12]:
                st.link_button("🔗", row.get('discount_url'), help="Ir al descuento", width='stretch')

    if shown_count < len(filtered_df):
        if st.button("Cargar más descuentos", key="guided_load_more"):
            st.session_state["guided_visible_count"] = shown_count + 20
            st.rerun()


# --- Navigation ---
pg = st.navigation([
    st.Page(page_guided_search, title="Explorar descuentos", icon=":material/search:"),
    st.Page(page_issuer_status, title="Entidades disponibles", icon=":material/fact_check:"),
])
pg.run()