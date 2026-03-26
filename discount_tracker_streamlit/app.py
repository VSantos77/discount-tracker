import streamlit as st
import pandas as pd
from utils.functions import get_db_connection
from utils.configs import DB_SETTINGS

# 1. Page Configuration
st.set_page_config(
    page_title="Explorador de Descuentos AR", 
    page_icon="💸", 
    layout="wide"
)

# 3. Data Loading (Cached to avoid hitting DB on every filter click)
@st.cache_data(ttl=600) # Cache for 10 minutes
def load_discount_data():
    conn = get_db_connection()
    if conn:
        # We use a standard SQL query. 
        # Replace 'fct_discounts' with your actual dbt output table name.
        query = "SELECT * FROM dbt_dev.streamlit_data"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

# 4. Helper Functions
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
        # Handle if it's a string like '0,1,2' or '{0,1,2}'
        if isinstance(days_str, str):
            days_str = days_str.strip('{}')
            days = [int(d.strip()) for d in days_str.split(',')]
        elif isinstance(days_str, (list, tuple)):
            days = [int(d) for d in days_str]
        else:
            # Assume it's array-like
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

# --- APP UI ---

st.title("💸 Descuentos Bancarios Argentina")
st.markdown("Explora y filtra los mejores beneficios de **Galicia**, **BBVA** y más.")

df = load_discount_data()

if df.empty:
    st.warning("No se encontraron datos. ¿Ejecutaste los modelos de dbt?")
else:
    # 4. Sidebar Filters
    st.sidebar.header("Opciones de Filtro")
    
    # Search Bar
    search_query = st.sidebar.text_input("Buscar Comercio", placeholder="ej. Coto, Starbucks...")

    # Bank Filter
    banks = sorted(df['issuer_name'].unique())
    selected_banks = st.sidebar.multiselect("Emisores", banks, default=banks)

    # Category Filter
    categories = sorted(df['merchant_category_name'].unique())
    selected_cats = st.sidebar.multiselect("Categorías", categories, default=categories)

    # Sorting Options
    st.sidebar.divider()
    st.sidebar.header("Opciones de Orden")
    sort_by = st.sidebar.selectbox(
        "Ordenar por",
        options=["Tasa de Descuento", "Nombre del Comercio", "Emisor"],
        index=0
    )
    sort_order = st.sidebar.radio(
        "Orden",
        options=["Mayor a Menor", "Menor a Mayor"],
        index=0
    )

    # 5. Apply Filtering Logic
    mask = (
        df['issuer_name'].isin(selected_banks) & 
        df['merchant_category_name'].isin(selected_cats)
    )
    
    if search_query:
        mask = mask & df['merchant_name'].str.contains(search_query, case=False)

    filtered_df = df[mask]

    # Apply Sorting
    sort_column_map = {
        "Tasa de Descuento": "discount_rate",
        "Nombre del Comercio": "merchant_name",
        "Emisor": "issuer_name"
    }
    sort_ascending = sort_order == "Lowest to Highest"
    filtered_df = filtered_df.sort_values(
        by=sort_column_map[sort_by],
        ascending=sort_ascending
    ).reset_index(drop=True)

    # 6. Display Stats
    col1, col2 = st.columns(2)
    col1.metric("Total de Descuentos", len(filtered_df))

    # 7. The Result Grid (Using Streamlit Cards/Columns)
    st.divider()
    
    if filtered_df.empty:
        st.info("Ningún descuento coincide con tus filtros.")
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(filtered_df.iterrows()):
            with cols[i % 3]:
                # Format dates
                start_date = pd.to_datetime(row['discount_start_date']).strftime('%d/%m/%Y') if pd.notna(row['discount_start_date']) else "N/A"
                end_date = pd.to_datetime(row['discount_end_date']).strftime('%d/%m/%Y') if pd.notna(row['discount_end_date']) else "N/A"
                
                # Build details section
                description = truncate_text(row['discount_description'], 150) or 'N/A'
                validity = get_validity(row)
                
                # Always show fields, with N/A if null
                installments_val = int(row['discount_no_interest_installment_qty']) if pd.notna(row['discount_no_interest_installment_qty']) else 'N/A'
                installments = f"<p style=\"margin:2px 0;\"><strong>Cuotas sin Interés:</strong> {installments_val}</p>"
                
                min_purchase_val = f"${int(row['discount_min_purchase_amount'])}" if pd.notna(row['discount_min_purchase_amount']) else 'N/A'
                min_purchase = f"<p style=\"margin:2px 0;\"><strong>Compra Mínima:</strong> {min_purchase_val}</p>"
                
                max_purchase_val = f"${int(row['discount_max_discount_amount'])}" if pd.notna(row['discount_max_discount_amount']) else 'N/A'
                max_purchase = f"<p style=\"margin:2px 0;\"><strong>Tope:</strong> {max_purchase_val}</p>"
                
                valid_days_list = map_days(row['discount_valid_days_list'])
                valid_days_html = ""
                for day in ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']:
                    color = "#3498db" if day in valid_days_list else "#ddd"
                    valid_days_html += f'<span style="display:inline-block; width:24px; height:24px; border-radius:50%; background-color:{color}; margin:0 2px; text-align:center; line-height:24px; font-size:10px; color:white; font-weight:bold;">{day[0]}</span>'
                
                valid_days = f"<p style=\"margin:2px 0;\"><strong>Días Válidos:</strong></p><div style=\"margin:5px 0;\">{valid_days_html}</div>"
                
                st.markdown(f"""
                <div style="border:2px solid var(--text-color); border-radius:10px; padding:15px; margin:10px 0; background-color: var(--secondary-background-color); height: 450px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); outline: 2px solid #ffffff;">
                <h4 style="margin-top:0; background-color: #34495e; color: white; padding: 8px; border-radius: 5px; text-align: center;">{row['merchant_name']}</h4>
                <p style="font-style:italic; font-size:0.9em; color: var(--text-color); margin:5px 0;">{description}</p>
                <p style="color:#e74c3c; font-size:1.2em; margin:2px 0;"><strong>{row['discount_rate']:.0%} OFF</strong></p>
                <p style="margin:2px 0;"><strong>Emisor:</strong> {row['issuer_name']}</p>
                <p style="margin:2px 0;"><strong>Categoría:</strong> {row['merchant_category_name']}</p>
                <p style="margin:2px 0;"><strong>Válido:</strong> {validity}</p>
                <p style="margin:2px 0;"><strong>Fechas:</strong> {start_date} a {end_date}</p>
                {installments}
                {min_purchase}
                {max_purchase}
                {valid_days}
                <a href="{row['discount_url']}" target="_blank" style="display:inline-block; margin-top:10px; padding:8px 12px; background-color:#3498db; color:white; border-radius:5px; text-decoration:none;">Ver Promo</a>
                </div>
                """, unsafe_allow_html=True)
                
                # Terms and conditions popup
                with st.popover("📋 Términos y Condiciones"):
                    if pd.notna(row['discount_terms_and_conditions']) and row['discount_terms_and_conditions'] != '':
                        st.markdown(row['discount_terms_and_conditions'])
                    else:
                        st.text("No hay términos y condiciones disponibles.")

# --- FOOTER ---
st.caption("Datos actualizados vía orquestador Scrapy & dbt.")