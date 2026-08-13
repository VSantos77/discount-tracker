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

# Page Configuration
st.set_page_config(
    page_title="Explorador de descuentos",
    page_icon="💸",
    layout="wide"
)

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

def get_validity(row):
    """Determine where discount is valid."""
    online = row.get('discount_valid_online', False)
    instore = row.get('discount_valid_instore', False)
    if online and instore:
        return "Online y en Tienda"
    elif online:
        return "Solo Online"
    elif instore:
        return "Solo en Tienda"
    else:
        return "Desconocido"


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


# --- PAGE: ISSUER STATUS ---
def page_issuer_status():
    st.title("Entidades disponibles")

    metadata_df = load_issuer_metadata()
    icon_mapping = load_issuer_icon_mapping()

    metadata_df = metadata_df.copy()
    metadata_df["last_scraped_at"] = pd.to_datetime(metadata_df["last_scraped_at"], errors="coerce")
    metadata_df["discount_count"] = pd.to_numeric(metadata_df["discount_count"], errors="coerce").fillna(0).astype(int)

    latest_scrape = metadata_df["last_scraped_at"].max()
    latest_scrape_label = latest_scrape.strftime("%d/%m/%Y %H:%M") if pd.notna(latest_scrape) else "N/A"

    col1, col2, col3 = st.columns(3)
    col1.metric("Entidades Activas", len(metadata_df))
    col2.metric("Total Descuentos", int(metadata_df["discount_count"].sum()))
    col3.metric("Última Actualización", latest_scrape_label)

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


# --- PAGE: DISCOUNT DASHBOARD ---
def page_dashboard():
    st.title("Dashboard")
    st.markdown("Resumen general de los descuentos disponibles.")

    chart_font_color = "#1A202C"
    chart_background = "#FFFFFF"
    chart_grid = "#DDEBE4"
    issuer_palette = ["#00A36C", "#34B885", "#67CDA2", "#9AE1BF", "#CDEFD9"]
    category_scale = ["#DDF1E8", "#A7DEC5", "#67CDA2", "#34B885", "#00A36C"]

    df = load_discount_data()

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Descuentos", len(df))
    col2.metric("Emisores", df['issuer_name'].nunique())
    col3.metric("Categorías", df['merchant_category_name'].nunique())
    col4.metric("Comercios", df['merchant_name'].nunique())

    st.divider()

    col_left, col_right = st.columns(2)

    # Chart 1: Discounts by issuer
    by_issuer = (
        df['issuer_name']
        .value_counts()
        .reset_index()
        .rename(columns={'issuer_name': 'Emisor', 'count': 'Cantidad'})
    )
    fig_issuer = px.bar(
        by_issuer,
        x='Emisor',
        y='Cantidad',
        color='Emisor',
        color_discrete_sequence=issuer_palette,
        labels={'Cantidad': 'Número de descuentos'},
    )
    fig_issuer.update_layout(
        showlegend=False,
        paper_bgcolor=chart_background,
        plot_bgcolor=chart_background,
        font=dict(color=chart_font_color),
        xaxis=dict(title=None, gridcolor=chart_grid),
        yaxis=dict(gridcolor=chart_grid),
    )
    with col_left:
        st.subheader("Descuentos por Emisor")
        st.plotly_chart(fig_issuer, use_container_width=True)

    # Chart 2: Discounts by category
    by_category = (
        df['merchant_category_name']
        .value_counts()
        .reset_index()
        .rename(columns={'merchant_category_name': 'Categoría', 'count': 'Cantidad'})
        .sort_values('Cantidad')
    )
    fig_category = px.bar(
        by_category,
        x='Cantidad',
        y='Categoría',
        orientation='h',
        color='Cantidad',
        color_continuous_scale=category_scale,
        labels={'Cantidad': 'Número de descuentos'},
    )
    fig_category.update_layout(
        height=max(400, len(by_category) * 28),
        coloraxis_showscale=False,
        paper_bgcolor=chart_background,
        plot_bgcolor=chart_background,
        font=dict(color=chart_font_color),
        xaxis=dict(gridcolor=chart_grid),
        yaxis=dict(title=None, gridcolor=chart_grid),
    )
    with col_right:
        st.subheader("Descuentos por Categoría")
        st.plotly_chart(fig_category, use_container_width=True)


# --- PAGE: GUIDED SEARCH ---
def page_guided_search():
    st.title("Explorar descuentos")

    df = load_discount_data()
    icon_mapping = load_issuer_icon_mapping()

    df = df.copy()
    df["valid_days_names"] = df["discount_valid_days_list"].apply(map_days)

    st.subheader("¿Dónde querés comprar?")
    merchant_col, category_col = st.columns(2)
    with merchant_col:
        merchant_query = st.text_input(
            "Nombre del comercio",
            placeholder="Ej: Coto, Starbucks, Carrefour...",
            key="guided_merchant_query",
        ).strip()
    with category_col:
        category_options = sorted(df["merchant_category_name"].dropna().unique())
        selected_category = st.selectbox(
            "Categoría",
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

    day_order = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    rf_col1, rf_col2, rf_col3, rf_col4 = st.columns(4)
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
        selected_result_merchant = st.selectbox(
            "Filtrar por comercio",
            options=merchant_options,
            index=None,
            placeholder="Todos los comercios",
            key="guided_result_merchant_select",
        )
    with rf_col3:
        result_order_by = st.selectbox(
            "Ordenar por",
            options=["Descuento más grande", "Más cuotas sin interés"],
            index=0,
            key="guided_result_order_by",
        )
    with rf_col4:
        show_inactive = st.toggle("Incluir vencidos", value=False, key="guided_show_inactive")

    if selected_result_merchant:
        filtered_df = filtered_df[
            filtered_df["merchant_name"] == selected_result_merchant
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

    visible_rows = list(visible_df.iterrows())
    for start_idx in range(0, len(visible_rows), 3):
        row_cols = st.columns(3)
        for col_idx, (_, row) in enumerate(visible_rows[start_idx:start_idx + 3]):
            with row_cols[col_idx]:
                issuer_name = str(row.get("issuer_name", ""))
                issuer_key = normalize_issuer_key(issuer_name)
                icon_filename = icon_mapping.get(issuer_key)
                icon_path = ICONS_DIR / icon_filename if icon_filename else None
                icon_base64 = get_base64_icon(str(icon_path)) if icon_path and icon_path.exists() else None
                icon_html = (
                    f"<img src=\"data:image/png;base64,{icon_base64}\" alt=\"{escape(issuer_name)}\" style=\"height:22px; width:auto; max-width:88px; object-fit:contain;\"/>"
                    if icon_base64
                    else ""
                )

                start_date = pd.to_datetime(row["discount_start_date"]).strftime("%d/%m/%Y") if pd.notna(row["discount_start_date"]) else "N/A"
                end_date = pd.to_datetime(row["discount_end_date"]).strftime("%d/%m/%Y") if pd.notna(row["discount_end_date"]) else "N/A"
                validity = get_validity(row)
                discount_rate, installments_value, min_purchase_value, max_discount_value = format_discount_fields(row)
                valid_days_list = map_days(row.get("discount_valid_days_list"))
                day_badges = [
                    ("Lun", "L"),
                    ("Mar", "M"),
                    ("Mié", "M"),
                    ("Jue", "J"),
                    ("Vie", "V"),
                    ("Sáb", "S"),
                    ("Dom", "D"),
                ]

                is_active = row.get('discount_is_active', True)
                if is_active:
                    c_primary     = '#00A36C'
                    c_bg          = 'rgba(0,163,108,0.12)'
                    c_content     = '#F0F7F4'
                    c_border      = 'rgba(0,163,108,0.25)'
                    c_text        = '#1A202C'
                    c_day_on      = '#00A36C'
                    c_day_off     = '#DDEBE4'
                    c_day_on_txt  = '#FFFFFF'
                    c_day_off_txt = '#607081'
                else:
                    c_primary     = '#9CA3AF'
                    c_bg          = 'rgba(156,163,175,0.12)'
                    c_content     = '#F3F4F6'
                    c_border      = 'rgba(156,163,175,0.25)'
                    c_text        = '#6B7280'
                    c_day_on      = '#9CA3AF'
                    c_day_off     = '#E5E7EB'
                    c_day_on_txt  = '#FFFFFF'
                    c_day_off_txt = '#9CA3AF'

                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="background-color:{c_bg}; border-radius:10px 10px 0 0; padding:4px 12px; margin:-0.95rem -0.95rem 0 -0.95rem; color:{c_primary}; font-size:0.8rem; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; display:flex; align-items:center; justify-content:space-between; gap:8px; min-height:34px;">
                            <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{escape(str(row.get('merchant_category_name', 'N/A')))}</span>
                            <span style="display:inline-flex; align-items:center; justify-content:flex-end; min-width:24px;">{icon_html}</span>
                        </div>
                        <div style="background-color:{c_content}; padding:10px 12px; margin:0 -0.95rem 0.75rem -0.95rem; height:5.5rem; display:flex; align-items:center;">
                            <h3 style="margin:0; color:{c_text}; line-height:1.25; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">{escape(str(row.get('merchant_name', 'N/A')))}</h3>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    h1, h2 = st.columns(2)
                    h1.markdown(
                        f"""
                            <div style="background-color:{c_content}; border:1px solid {c_border}; border-radius:10px; padding:8px 10px; text-align:center;">
                            <div style=\"font-size:0.85rem; color:{c_text};\">Descuento</div>
                            <div style=\"font-size:1.8rem; font-weight:700; color:{c_primary}; line-height:1.1;\">{format_display_value(discount_rate, ' OFF')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    h2.markdown(
                        f"""
                            <div style="background-color:{c_content}; border:1px solid {c_border}; border-radius:10px; padding:8px 10px; text-align:center;">
                            <div style=\"font-size:0.85rem; color:{c_text};\">Cuotas sin interes</div>
                            <div style=\"font-size:1.8rem; font-weight:700; color:{c_primary}; line-height:1.1;\">{installments_value}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.text('') # buffer
                    detail_rows = [
                        ("Emisor", row['issuer_name']),
                        ("Formato", validity),
                        ("Validez", f"{start_date} a {end_date}"),
                        ("Compra Mínima", min_purchase_value),
                        ("Tope", max_discount_value),
                    ]
                    detail_rows_html = "".join(
                        f"""
                        <div style=\"display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin:0.25rem 0;\">
                            <span style=\"font-weight:600; color:{c_text};\">{escape(str(label))}:</span>
                            <span style=\"text-align:right; color:{c_text};\">{escape(str(value))}</span>
                        </div>
                        """
                        for label, value in detail_rows
                    )
                    st.markdown(detail_rows_html, unsafe_allow_html=True)

                    day_circles_html = "".join(
                        f"""
                        <span title=\"{escape(day_name)}\" style=\"width:24px; height:24px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:600; background:{c_day_on if day_name in valid_days_list else c_day_off}; color:{c_day_on_txt if day_name in valid_days_list else c_day_off_txt};\">{day_short}</span>
                        """
                        for day_name, day_short in day_badges
                    )
                    st.markdown(
                        f"""
                        <div style=\"display:flex; justify-content:space-between; align-items:center; gap:12px; margin:0.35rem 0 0.15rem 0;\">
                            <span style=\"font-weight:600; color:{c_text};\">Días Válidos:</span>
                            <div style=\"display:flex; gap:6px;\">{day_circles_html}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    bottom_col1, bottom_col2 = st.columns([0.6,0.4])

                    with bottom_col1:
                        with st.popover("📋 Términos y Condiciones"):
                            if pd.notna(row.get("discount_terms_and_conditions")) and str(row.get("discount_terms_and_conditions")).strip() != "":
                                st.text(str(row.get("discount_terms_and_conditions")))
                            else:
                                st.text("No hay términos y condiciones disponibles.")
                    with bottom_col2:
                        st.link_button('Ir al descuento', row.get('discount_url'), width='stretch')

    if shown_count < len(filtered_df):
        if st.button("Cargar más descuentos", key="guided_load_more"):
            st.session_state["guided_visible_count"] = shown_count + 20
            st.rerun()


# --- PAGE: DISCOUNT EXPLORER ---
def page_explorer():
    st.title("Explorador de descuentos")
    st.markdown("Explora los descuentos disponibles. Usá el panel de la izquierda para filtrar resultados")
    day_order = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    df = load_discount_data()
    icon_mapping = load_issuer_icon_mapping()

    df = df.copy()
    df["valid_days_names"] = df["discount_valid_days_list"].apply(map_days)

    # Sidebar Filters
    st.sidebar.header("Filtros")

    search_query = st.sidebar.text_input("Por nombre de comercio", placeholder="ej. Coto, Starbucks...")

    banks = sorted(df['issuer_name'].unique())
    selected_banks = st.sidebar.multiselect("Por emisor del descuento", banks, default=banks)

    categories = sorted(df['merchant_category_name'].unique())
    selected_cats = st.sidebar.multiselect("Por categoría", categories, default=categories)

    selected_days = st.sidebar.multiselect(
        "Por día de validez",
        options=day_order,
        default=[],
        placeholder="Seleccionar días..."
    )

    st.sidebar.divider()
    st.sidebar.header("Ordenar resultados")
    sort_by = st.sidebar.selectbox(
        "Ordenar por",
        options=["% Descuento", "Nombre del Comercio", "Emisor"],
        index=0
    )
    sort_order = st.sidebar.radio(
        "Orden",
        options=["Mayor a Menor", "Menor a Mayor"],
        index=0
    )

    # Filtering
    mask = (
        df['issuer_name'].isin(selected_banks) &
        df['merchant_category_name'].isin(selected_cats)
    )
    if search_query:
        mask = mask & df['merchant_name'].str.contains(search_query, case=False)
    if selected_days:
        mask = mask & df['valid_days_names'].apply(lambda days: any(day in days for day in selected_days))

    filtered_df = df[mask]

    sort_column_map = {
        "% Descuento": "discount_rate",
        "Nombre del Comercio": "merchant_name",
        "Emisor": "issuer_name"
    }
    sort_ascending = sort_order == "Menor a Mayor"
    filtered_df = filtered_df.sort_values(
        by=sort_column_map[sort_by],
        ascending=sort_ascending
    ).reset_index(drop=True)

    col1, col2 = st.columns(2)
    col1.metric("Total de Descuentos", len(filtered_df))

    st.divider()

    if filtered_df.empty:
        st.info("Ningún descuento coincide con tus filtros.")
        return

    items_per_page = 20
    total_items = len(filtered_df)
    total_pages = (total_items + items_per_page - 1) // items_per_page

    if "explorer_page" not in st.session_state:
        st.session_state["explorer_page"] = 1
    st.session_state["explorer_page"] = max(1, min(st.session_state["explorer_page"], total_pages))
    current_page = st.session_state["explorer_page"]

    def get_visible_pages(page, total):
        if total <= 7:
            return list(range(1, total + 1))
        if page <= 4:
            return [1, 2, 3, 4, 5, "...", total]
        if page >= total - 3:
            return [1, "...", total - 4, total - 3, total - 2, total - 1, total]
        return [1, "...", page - 1, page, page + 1, "...", total]

    target_page = current_page
    visible_pages = get_visible_pages(current_page, total_pages)

    _, pager_col, _ = st.columns([2.0, 4.0, 2.0])
    with pager_col:
        pager_widths = [2.0] + [0.55 if item == "..." else 2 for item in visible_pages] + [2.0]
        pager_cols = st.columns(pager_widths, gap="small")

        with pager_cols[0]:
            if st.button("◀", key="explorer_page_prev", use_container_width=True, disabled=current_page == 1):
                target_page = current_page - 1

        for idx, item in enumerate(visible_pages, start=1):
            with pager_cols[idx]:
                if item == "...":
                    st.markdown("<div style='text-align:center; padding-top:0.35rem;'>...</div>", unsafe_allow_html=True)
                else:
                    if st.button(
                        str(item),
                        key=f"explorer_page_{item}",
                        width='stretch',
                        type="primary" if item == current_page else "secondary",
                    ):
                        target_page = item

        with pager_cols[-1]:
            if st.button("▶", key="explorer_page_next", use_container_width=True, disabled=current_page == total_pages):
                target_page = current_page + 1

    target_page = max(1, min(target_page, total_pages))
    if target_page != st.session_state["explorer_page"]:
        st.session_state["explorer_page"] = target_page
        st.rerun()

    current_page = st.session_state["explorer_page"]

    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_df = filtered_df.iloc[start_idx:end_idx]

    st.caption(f"Mostrando {start_idx + 1}-{min(end_idx, total_items)} de {total_items} descuentos")

    cols = st.columns(3)
    for i, (_, row) in enumerate(page_df.iterrows()):
        with cols[i % 3]:
            start_date = pd.to_datetime(row['discount_start_date']).strftime('%d/%m/%Y') if pd.notna(row['discount_start_date']) else "N/A"
            end_date = pd.to_datetime(row['discount_end_date']).strftime('%d/%m/%Y') if pd.notna(row['discount_end_date']) else "N/A"

            validity = get_validity(row)
            discount_rate_raw = row.get('discount_rate')
            if pd.notna(discount_rate_raw) and float(discount_rate_raw) > 0:
                discount_rate = f"{discount_rate_raw:.0%}"
            else:
                discount_rate = "-"

            installments_raw = row.get('discount_no_interest_installment_qty')
            if pd.notna(installments_raw) and float(installments_raw) > 0:
                installments_metric_value = str(int(installments_raw))
            else:
                installments_metric_value = "-"

            min_purchase_raw = row.get('discount_min_purchase_amount')
            if pd.notna(min_purchase_raw):
                min_purchase_val = "Sin mínimo" if float(min_purchase_raw) == 0 else f"${int(min_purchase_raw)}"
            else:
                min_purchase_val = 'N/A'

            max_discount_raw = row.get('discount_max_discount_amount')
            if pd.notna(max_discount_raw):
                max_purchase_val = "Sin tope" if float(max_discount_raw) == 0 else f"${int(max_discount_raw)}"
            else:
                max_purchase_val = 'N/A'

            valid_days_list = map_days(row['discount_valid_days_list'])
            issuer_name = str(row.get('issuer_name', ''))
            issuer_key = normalize_issuer_key(issuer_name)
            icon_filename = icon_mapping.get(issuer_key)
            icon_path = ICONS_DIR / icon_filename if icon_filename else None
            icon_base64 = get_base64_icon(str(icon_path)) if icon_path and icon_path.exists() else None
            icon_html = (
                f"<img src=\"data:image/png;base64,{icon_base64}\" alt=\"{escape(issuer_name)}\" style=\"height:22px; width:auto; max-width:88px; object-fit:contain;\"/>"
                if icon_base64
                else ""
            )
            day_badges = [
                ("Lun", "L"),
                ("Mar", "M"),
                ("Mié", "M"),
                ("Jue", "J"),
                ("Vie", "V"),
                ("Sáb", "S"),
                ("Dom", "D"),
            ]

            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style=\"background-color:rgba(0,163,108,0.12); border-radius:10px 10px 0 0; padding:4px 12px; margin:-0.95rem -0.95rem 0 -0.95rem; color:#00A36C; font-size:0.8rem; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; display:flex; align-items:center; justify-content:space-between; gap:8px; min-height:34px;\">
                        <span style=\"overflow:hidden; text-overflow:ellipsis; white-space:nowrap;\">{row['merchant_category_name']}</span>
                        <span style=\"display:inline-flex; align-items:center; justify-content:flex-end; min-width:24px;\">{icon_html}</span>
                    </div>
                    <div style=\"background-color:#F0F7F4; padding:10px 12px; margin:0 -0.95rem 0.75rem -0.95rem; height:5.5rem; display:flex; align-items:center;\">
                        <h3 style=\"margin:0; color:#1A202C; line-height:1.25; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;\">{row['merchant_name']}</h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                h1, h2 = st.columns(2)
                h1.markdown(
                    f"""
                        <div style="background-color:#F0F7F4; border:1px solid rgba(0,163,108,0.25); border-radius:10px; padding:8px 10px; text-align:center;">
                        <div style=\"font-size:0.85rem; color:#1A202C;\">Descuento</div>
                        <div style=\"font-size:1.8rem; font-weight:700; color:#00A36C; line-height:1.1;\">{format_display_value(discount_rate, ' OFF')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                h2.markdown(
                    f"""
                        <div style="background-color:#F0F7F4; border:1px solid rgba(0,163,108,0.25); border-radius:10px; padding:8px 10px; text-align:center;">
                        <div style=\"font-size:0.85rem; color:#1A202C;\">Cuotas sin interes</div>
                        <div style=\"font-size:1.8rem; font-weight:700; color:#00A36C; line-height:1.1;\">{installments_metric_value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.text('') # buffer
                detail_rows = [
                    ("Emisor", row['issuer_name']),
                    ("Formato", validity),
                    ("Validez", f"{start_date} a {end_date}"),
                    ("Compra Mínima", min_purchase_val),
                    ("Tope", max_purchase_val),
                ]
                detail_rows_html = "".join(
                    f"""
                    <div style=\"display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin:0.25rem 0;\">
                        <span style=\"font-weight:600; color:#1A202C;\">{escape(str(label))}:</span>
                        <span style=\"text-align:right; color:#1A202C;\">{escape(str(value))}</span>
                    </div>
                    """
                    for label, value in detail_rows
                )
                st.markdown(detail_rows_html, unsafe_allow_html=True)

                day_circles_html = "".join(
                    f"""
                    <span title=\"{escape(day_name)}\" style=\"width:24px; height:24px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:600; background:{'#00A36C' if day_name in valid_days_list else '#DDEBE4'}; color:{'#FFFFFF' if day_name in valid_days_list else '#607081'};\">{day_short}</span>
                    """
                    for day_name, day_short in day_badges
                )
                st.markdown(
                    f"""
                    <div style=\"display:flex; justify-content:space-between; align-items:center; gap:12px; margin:0.35rem 0 0.15rem 0;\">
                        <span style=\"font-weight:600; color:#1A202C;\">Días Válidos:</span>
                        <div style=\"display:flex; gap:6px;\">{day_circles_html}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with st.popover("📋 Términos y Condiciones"):
                    if pd.notna(row['discount_terms_and_conditions']) and row['discount_terms_and_conditions'] != '':
                        st.text(row['discount_terms_and_conditions'])
                    else:
                        st.text("No hay términos y condiciones disponibles.")


# --- Navigation ---
pg = st.navigation([
    st.Page(page_guided_search, title="Explorar descuentos", icon=":material/tune:"),
    st.Page(page_issuer_status, title="Entidades disponibles", icon=":material/fact_check:"),
])
pg.run()