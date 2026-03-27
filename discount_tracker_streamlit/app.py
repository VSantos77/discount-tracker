import streamlit as st
import pandas as pd
import plotly.express as px
from html import escape
from utils.functions import get_db_connection
from utils.functions import get_project_root_path
from utils.configs import DB_SETTINGS

# Page Configuration
st.set_page_config(
    page_title="Explorador de descuentos",
    page_icon="💸",
    layout="wide"
)

# Data Loading
@st.cache_data(ttl=600)
def load_discount_data():
    try:
        with get_db_connection(DB_SETTINGS) as conn:
            with conn.cursor() as cur:
                with open(get_project_root_path() / 'utils' / 'queries' / 'streamlit_data.sql') as f:
                    query = f.read()
                df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(
            f"Error al cargar datos: {e}"
        )
        return pd.DataFrame()  # Return empty DataFrame on error

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

    if df.empty:
        st.warning("No se encontraron datos. ¿Ejecutaste los modelos de dbt?")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Descuentos", len(df))
    col2.metric("Emisores", df['issuer_name'].nunique())
    col3.metric("Categorías", df['merchant_category_name'].nunique())
    col4.metric("Comercios", df['merchant_name'].nunique())

    st.divider()

    # Chart 1: Discounts by issuer
    st.subheader("Descuentos por Emisor")
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
    st.plotly_chart(fig_issuer, use_container_width=True)

    st.divider()

    # Chart 2: Discounts by category
    st.subheader("Descuentos por Categoría")
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
    st.plotly_chart(fig_category, use_container_width=True)

    st.caption("Datos actualizados vía orquestador Scrapy & dbt.")


# --- PAGE: DISCOUNT EXPLORER ---
def page_explorer():
    st.title("Explorador de descuentos")
    st.markdown("Explora los descuentos disponibles. Usá el panel de la izquierda para filtrar resultados")
    day_order = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    df = load_discount_data()

    if df.empty:
        st.warning("No se encontraron datos. ¿Ejecutaste los modelos de dbt?")
        return

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
            discount_rate = f"{row['discount_rate']:.0%}" if pd.notna(row['discount_rate']) else 'N/A'

            installments_val = int(row['discount_no_interest_installment_qty']) if pd.notna(row['discount_no_interest_installment_qty']) else 'N/A'
            installments_metric_value = str(installments_val) if installments_val != 'N/A' else 'N/A'

            min_purchase_val = f"${int(row['discount_min_purchase_amount'])}" if pd.notna(row['discount_min_purchase_amount']) else 'N/A'
            max_purchase_val = f"${int(row['discount_max_discount_amount'])}" if pd.notna(row['discount_max_discount_amount']) else 'N/A'

            valid_days_list = map_days(row['discount_valid_days_list'])
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
                    <div style=\"background-color:rgba(0,163,108,0.12); border-radius:10px 10px 0 0; padding:4px 12px; margin:-0.95rem -0.95rem 0 -0.95rem; color:#00A36C; font-size:0.8rem; font-weight:600; text-transform:uppercase; letter-spacing:0.04em;\">
                        {row['merchant_category_name']}
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
                        <div style=\"font-size:1.8rem; font-weight:700; color:#00A36C; line-height:1.1;\">{discount_rate} OFF</div>
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
                        st.markdown(row['discount_terms_and_conditions'])
                    else:
                        st.text("No hay términos y condiciones disponibles.")

    st.caption("Datos actualizados vía orquestador Scrapy & dbt.")


# --- Navigation ---
pg = st.navigation([
    st.Page(page_dashboard, title="Dashboard", icon=":material/dashboard:"),
    st.Page(page_explorer, title="Explorador de descuentos", icon=":material/search:"),
])
pg.run()