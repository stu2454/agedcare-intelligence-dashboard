# app.py - Corrected Version (Fixed SyntaxError on line 349)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re # Import regular expressions
import os # Import os module
from scipy.stats import percentileofscore # Import percentile function
import numpy as np # Import numpy for NaN handling etc.
import traceback # For detailed error logging

# --- Page Configuration (Set early) ---
st.set_page_config(
    page_title="Aged Care Sector Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="expanded" # Keep sidebar open initially
)

# --- Constants ---
PRIMARY_COLOR = "#1f77b4"  # Plotly's default blue
# Define Quality Measure columns (Ensure these EXACTLY match your Excel headers)
QM_FIELDS = [
    '[QM] Pressure injuries*',
    '[QM] Restrictive practices',
    '[QM] Unplanned weight loss*',
    '[QM] Falls and major injury - falls*',
    '[QM] Falls and major injury - major injury from a fall*',
    '[QM] Medication management - polypharmacy',
    '[QM] Medication management - antipsychotic'
]
# Define Compliance columns
COMPLIANCE_COLUMNS = [
    'Service Name',
    'Compliance rating', # Assuming numeric
    '[C] Decision type',
    '[C] Date Decision Applied',
    '[C] Date Decision Ends'
]
# Define columns for the flagged services table
FLAGGED_DISPLAY_COLUMNS = [
    'Service Name',
    'Overall Star Rating',
    'Compliance rating',
    "Residents' Experience rating",
    'Staffing rating',
    'Quality Measures rating'
]
# Define the desired order for RE frequencies
RE_FREQUENCY_ORDER = ['Always', 'Most of the time', 'Some of the time', 'Never']
DEFAULT_DATA_FILENAME = "star-ratings-quarterly-data-extract-february-2025.xlsx" # Define default name

# --- Caching Function for Data Loading ---
@st.cache_data(show_spinner="Loading and processing data...") # Add spinner message
def load_data(file_source):
    """Loads data from the uploaded Excel file or a file path."""
    try:
        # st.write(f"Attempting to load data from source: {type(file_source)}") # Debugging line
        sheets = pd.read_excel(file_source, sheet_name=None, engine="openpyxl")
        star_ratings = sheets.get("Star Ratings", pd.DataFrame())
        detailed_data = sheets.get("Detailed data", pd.DataFrame())

        if detailed_data.empty:
             st.error("The file/upload is missing the required 'Detailed data' sheet.")
             return None, None

        # --- Ensure filter columns are strings ---
        for col in ['Size', 'MMM Code', 'State/Territory', 'Provider Name']:
             if col in detailed_data.columns:
                 detailed_data[col] = detailed_data[col].fillna('Unknown').astype(str)

        # --- Essential Data Cleaning & Type Conversion ---
        numeric_cols_detailed = { # Define numeric cols here
             '[S] Registered Nurse Care Minutes - Actual': 'coerce', '[S] Registered Nurse Care Minutes - Target': 'coerce',
             '[S] Total Care Minutes - Actual': 'coerce', '[S] Total Care Minutes - Target': 'coerce',
             'Overall Star Rating': 'coerce', 'Compliance rating': 'coerce', "Residents' Experience rating": 'coerce',
             'Staffing rating': 'coerce', 'Quality Measures rating': 'coerce',
        }
        for col in QM_FIELDS: numeric_cols_detailed[col] = 'coerce'
        re_cols = [col for col in detailed_data.columns if col.startswith('[RE]') and any(freq in col for freq in RE_FREQUENCY_ORDER)]
        for col in re_cols: numeric_cols_detailed[col] = 'coerce'

        for col, errors_strategy in numeric_cols_detailed.items(): # Apply conversion
            if col in detailed_data.columns:
                if detailed_data[col].dtype == 'object': detailed_data.loc[:, col] = detailed_data[col].astype(str).str.replace('%', '', regex=False).str.strip()
                detailed_data.loc[:, col] = pd.to_numeric(detailed_data[col], errors=errors_strategy)

        # Calculate Compliance Percentages
        if '[S] Registered Nurse Care Minutes - Actual' in detailed_data and '[S] Registered Nurse Care Minutes - Target' in detailed_data:
            target_rn = detailed_data['[S] Registered Nurse Care Minutes - Target'].replace(0, pd.NA)
            detailed_data['RN Care Compliance %'] = (detailed_data['[S] Registered Nurse Care Minutes - Actual'] / target_rn).replace([float('inf'), -float('inf')], pd.NA) * 100
        else: detailed_data['RN Care Compliance %'] = pd.NA
        if '[S] Total Care Minutes - Actual' in detailed_data and '[S] Total Care Minutes - Target' in detailed_data:
             target_total = detailed_data['[S] Total Care Minutes - Target'].replace(0, pd.NA)
             detailed_data['Total Care Compliance %'] = (detailed_data['[S] Total Care Minutes - Actual'] / target_total).replace([float('inf'), -float('inf')], pd.NA) * 100
        else: detailed_data['Total Care Compliance %'] = pd.NA

        # --- Basic Validation ---
        required_cols = ['Provider Name', 'Service Name', 'State/Territory']
        missing_cols = [col for col in required_cols if col not in detailed_data.columns]
        if missing_cols:
            st.error(f"Uploaded file ('Detailed data' sheet) is missing essential columns: {', '.join(missing_cols)}")
            return None, None

        return star_ratings, detailed_data

    except FileNotFoundError:
        st.error(f"Error: Default data file not found at ({file_source}). Check Docker mount.")
        return None, None
    except ValueError as ve:
         st.error(f"Error processing file content: {ve}. Check data formats.")
         return None, None
    except Exception as e:
        st.error(f"An unexpected error occurred during data loading/processing: {e}")
        st.error(traceback.format_exc()) # Show full traceback
        return None, None

# --- App Title ---
st.title("Aged Care Sector Intelligence Dashboard")

# --- Sidebar: File Uploader ---
st.sidebar.header("1. Data Input")
uploaded_file = st.sidebar.file_uploader(
    "Upload Star Ratings Excel File (Optional if default file is mounted)",
    type=["xlsx", "xls"],
    help=f"Upload the quarterly data extract file (.xlsx or .xls). If not uploaded, the app will try to load '{DEFAULT_DATA_FILENAME}' if available."
)

#--define benchmarks ---
def compute_sector_benchmarks(df: pd.DataFrame, measures: list[str]):
    benchmarks = {}
    for m in measures:
        s = df[m].dropna()
        benchmarks[m] = {
            'median': s.median(),
            'p75':    s.quantile(0.75),
            'p90':    s.quantile(0.90),
        }
    return pd.DataFrame(benchmarks).T

# --- Initialize DataFrames ---
star_ratings = pd.DataFrame()
detailed_data = pd.DataFrame()
data_loaded_successfully = False # Flag

# --- Main Application Logic: Determine and Load Data Source ---
data_source = None
source_type = "none"
if uploaded_file is not None:
    data_source = uploaded_file
    source_type = "uploaded"
else:
    default_file_path = os.path.join("/app", DEFAULT_DATA_FILENAME)
    if os.path.exists(default_file_path):
        data_source = default_file_path
        source_type = "default_file"

if data_source is not None:
    star_ratings, detailed_data = load_data(data_source)
    if detailed_data is not None and not detailed_data.empty:
        data_loaded_successfully = True
        if source_type == "uploaded": st.sidebar.success("Uploaded data loaded!")
        elif source_type == "default_file": st.sidebar.success("Default data file loaded!")
        st.sidebar.markdown("---")
    else:
         if source_type != "none": st.sidebar.error("Failed to load/process data.")
         detailed_data = pd.DataFrame()

# --- App Body: Display content only if data loaded successfully ---
if data_loaded_successfully:
    # --- Sidebar: Filters ---
    st.sidebar.header("2. Filter Options")
    # -- State Filter --
    selected_state = "All"
    if 'State/Territory' in detailed_data.columns:
        states = sorted(detailed_data['State/Territory'].dropna().unique())
        selected_state = st.sidebar.selectbox("Select State/Territory", options=["All"] + states, index=0)
    else: st.sidebar.caption("State/Territory column not found.")
    # -- Size Filter --
    selected_sizes = []
    if 'Size' in detailed_data.columns:
        sizes = sorted(detailed_data['Size'].dropna().unique())
        if sizes: selected_sizes = st.sidebar.multiselect("Select Service Size(s)", options=sizes, default=sizes)
        else: st.sidebar.caption("No values found in 'Size'.")
    else: st.sidebar.caption("'Size' column not found.")
    # -- MMM Filter --
    selected_mmms = []
    if 'MMM Code' in detailed_data.columns:
        unique_mmms_str = detailed_data['MMM Code'].dropna().unique()
        try: mmms_sorted = sorted(unique_mmms_str, key=int)
        except ValueError: mmms_sorted = sorted(unique_mmms_str)
        if mmms_sorted: selected_mmms = st.sidebar.multiselect("Select MMM Code(s)", options=mmms_sorted, default=mmms_sorted)
        else: st.sidebar.caption("No values found in 'MMM Code'.")
    else: st.sidebar.caption("'MMM Code' column not found.")

    # --- Apply Filters Sequentially ---
    filtered_df = detailed_data.copy()
    if selected_state != "All" and 'State/Territory' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['State/Territory'] == selected_state]
    if selected_sizes and 'Size' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Size'].isin(selected_sizes)]
    if selected_mmms and 'MMM Code' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['MMM Code'].isin(selected_mmms)]

    # -- Provider Filter --
    selected_provider = "All"
    provider_list = []
    if 'Provider Name' in filtered_df.columns:
         provider_list = sorted(filtered_df['Provider Name'].dropna().unique())
         if provider_list: selected_provider = st.sidebar.selectbox("Select Provider (filtered)", options=["All"] + provider_list, index=0)
         else: st.sidebar.caption("No providers match filters.")
    else: st.sidebar.caption("'Provider Name' column not found.")

    # --- Define DataFrames for Tabs ---
    sector_filtered_df = filtered_df.copy()
    provider_filtered_df = filtered_df.copy()
    if selected_provider != "All" and 'Provider Name' in provider_filtered_df.columns:
        provider_filtered_df = provider_filtered_df[provider_filtered_df['Provider Name'] == selected_provider]

    # --- Main layout with tabs ---
    st.sidebar.markdown("---")
    st.sidebar.header("3. Navigate Sections")
    tabs = st.tabs([
        "Introduction",                 # 0
        "Sector Overview",              # 1
        "Provider Profile Drill-Down",  # 2
        "Quality Measures Risk Radar",  # 3
        "Anomaly Detection",            # 4
        "Compare Providers",            # 5
        "Compliance Actions Tracker"    # 6
    ])

    # ===============================================
    # Introduction Tab (Index 0)
    # ===============================================
    with tabs[0]:
        st.header("Welcome to the Aged Care Sector Intelligence Dashboard")
        st.markdown("""
        **Data Source:** This dashboard is designed specifically for analyzing data from the official **Star Ratings quarterly data extract** published by the Australian Government.

        *   **Content:** This extract provides service-level Star Ratings data (Overall and component ratings) for government-funded residential aged care homes at a specific point in time. It typically includes sheets like 'Star Ratings' and 'Detailed data'.
        *   **Origin:** The data is usually found via the GEN Aged Care Data website and hosted on the Department of Health and Aged Care resources section.
        *   **How to Obtain:** You must manually download the desired quarterly extract file (`.xlsx`) from the official government sources. The exact download location changes with each release. Start your search here:
            *   **GEN Aged Care Data:** [https://www.gen-agedcaredata.gov.au/](https://www.gen-agedcaredata.gov.au/) (Look for Star Ratings or quarterly reports)
            *   *Example Path (May Change):* You might navigate through GEN -> Specific Quarter Report -> `health.gov.au` Publication Page -> Final `.xlsx` Link.

        **Using the Dashboard:**
        1.  **Obtain the File:** Download the specific quarterly `.xlsx` data extract you wish to analyze.
        2.  **Upload:** Use the sidebar (**1. Data Input**) to upload the downloaded Excel file.
        3.  *(Alternative)* If running via Docker with a volume mount, the application may load a default file named `{DEFAULT_DATA_FILENAME}` if no file is uploaded.
        4.  **Analyze:** Use the sidebar filters and navigate the tabs above to explore the data.
        """.format(DEFAULT_DATA_FILENAME=DEFAULT_DATA_FILENAME))

        st.warning(f"**Important:** Please ensure you are using the official and complete '{DEFAULT_DATA_FILENAME}' (or similar) Excel file. The accuracy of the analysis depends entirely on the structure and content of the uploaded data matching the expected format.")
        st.markdown("---")

    # ===============================================
    # Sector Overview Tab (Index 1)
    # ===============================================
    with tabs[1]:
        st.subheader("Sector Overview")
        filter_desc_parts = [selected_state]
        if selected_sizes and 'Size' in detailed_data.columns and len(selected_sizes) < len(detailed_data['Size'].dropna().unique()): filter_desc_parts.append(f"Sizes: {', '.join(selected_sizes)}")
        if selected_mmms and 'MMM Code' in detailed_data.columns and len(selected_mmms) < len(detailed_data['MMM Code'].dropna().unique()): filter_desc_parts.append(f"MMMs: {', '.join(selected_mmms)}")
        st.markdown(f"#### Metrics for: **{' / '.join(filter_desc_parts)}**")

        if not sector_filtered_df.empty:
            col1, col2, col3 = st.columns(3)
            with col1: avg_rn_care = sector_filtered_df['RN Care Compliance %'].mean(); st.metric("Avg RN Care Compliance (%)", f"{avg_rn_care:.1f}%" if pd.notna(avg_rn_care) else "N/A")
            with col2: avg_total_care = sector_filtered_df['Total Care Compliance %'].mean(); st.metric("Avg Total Care Compliance (%)", f"{avg_total_care:.1f}%" if pd.notna(avg_total_care) else "N/A")
            with col3: non_compliant_count = sector_filtered_df[sector_filtered_df['Compliance rating'] == 1].shape[0] if 'Compliance rating' in sector_filtered_df and pd.api.types.is_numeric_dtype(sector_filtered_df['Compliance rating']) else 0; st.metric("Services with Non-Compliance Rating (1)", non_compliant_count)
            st.markdown("---")
            st.markdown("#### Distribution Plots")
            col_hist1, col_hist2 = st.columns(2)
            with col_hist1:
                 hist_col = 'RN Care Compliance %'
                 if hist_col in sector_filtered_df and sector_filtered_df[hist_col].notna().any(): fig_rn = px.histogram(sector_filtered_df.dropna(subset=[hist_col]), x=hist_col, nbins=30, title='RN Care Compliance %'); st.plotly_chart(fig_rn, use_container_width=True)
                 else: st.caption(f"{hist_col} N/A.")
            with col_hist2:
                 hist_col = 'Overall Star Rating'
                 if hist_col in sector_filtered_df and sector_filtered_df[hist_col].notna().any(): fig_star = px.histogram(sector_filtered_df.dropna(subset=[hist_col]), x=hist_col, nbins=5, title='Overall Star Ratings'); st.plotly_chart(fig_star, use_container_width=True)
                 else: st.caption(f"{hist_col} N/A.")
        else:
            st.warning(f"No services match the selected filters: {', '.join(filter_desc_parts)}")

    # ===============================================
    # Provider Profile Drill-Down Tab (Index 2)
    # ===============================================
    with tabs[2]:
        st.subheader("Provider Profile Drill-Down")

        if selected_provider == "All":
            st.info("Please select a specific provider from the sidebar filter.")
        elif not provider_filtered_df.empty:
            provider_data = provider_filtered_df

            st.markdown(f"### Profile for: **{selected_provider}**")
            entries=len(provider_data); unique_suburbs = provider_data['Service Suburb'].nunique() if 'Service Suburb' in provider_data else 'N/A'; size_counts = provider_data['Size'].value_counts().to_dict() if 'Size' in provider_data else {}; tooltip_text = f"Services Found (matching filters): {entries} | Unique Suburbs: {unique_suburbs}\n" + f"Size - Small: {size_counts.get('Small', 0)} | Medium: {size_counts.get('Medium', 0)} | Large: {size_counts.get('Large', 0)}"; st.caption(tooltip_text)
            st.markdown("---")

            st.markdown("#### Key Performance Metrics (Provider Average)")
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1: avg_star = provider_data['Overall Star Rating'].mean() if 'Overall Star Rating' in provider_data else None; st.metric("Overall Star Rating", f"{avg_star:.1f}" if pd.notna(avg_star) else "N/A")
            with col_m2: avg_rn_comp = provider_data['RN Care Compliance %'].mean() if 'RN Care Compliance %' in provider_data else None; st.metric("RN Care Compliance (%)", f"{avg_rn_comp:.1f}%" if pd.notna(avg_rn_comp) else "N/A")
            with col_m3: avg_total_comp = provider_data['Total Care Compliance %'].mean() if 'Total Care Compliance %' in provider_data else None; st.metric("Total Care Compliance (%)", f"{avg_total_comp:.1f}%" if pd.notna(avg_total_comp) else "N/A")
            st.markdown("---")

            st.markdown("#### Resident Experience Breakdown (Average %)")
            re_cols_provider = [col for col in provider_data.columns if col.startswith('[RE]') and any(freq in col for freq in RE_FREQUENCY_ORDER)];
            if re_cols_provider:
                re_avg = provider_data[re_cols_provider].mean().reset_index(); re_avg.columns = ['Metric', 'Average Percentage']; re_avg.dropna(subset=['Average Percentage'], inplace=True); parsed_data = re_avg['Metric'].str.extract(r'^\[RE\]\s+(.*?)\s+-\s+(Always|Most of the time|Some of the time|Never)$', expand=True); parsed_data.columns = ['Category', 'Frequency']; re_plot_data = pd.concat([parsed_data, re_avg['Average Percentage']], axis=1); re_plot_data.dropna(subset=['Category', 'Frequency'], inplace=True);
                if not re_plot_data.empty:
                    try: fig_re = px.bar(re_plot_data, x='Category', y='Average Percentage', color='Frequency',title=f"Avg RE Responses", labels={'Average Percentage': 'Avg. Response %', 'Category': 'Category'}, category_orders={'Frequency': RE_FREQUENCY_ORDER}, color_discrete_sequence=px.colors.sequential.Blues_r, text_auto='.1f'); fig_re.update_layout(xaxis_tickangle=-45, yaxis_title="Avg Response (%)", legend_title_text='Frequency'); fig_re.update_traces(textangle=0, textposition="inside", textfont_size=10); st.plotly_chart(fig_re, use_container_width=True)
                    except Exception as e: st.error(f"Error creating RE chart: {e}")
                else: st.info("No valid RE data.")
            else: st.warning("No RE columns found.")
            st.markdown("---")

            st.markdown("#### Average Quality Measures (with Standard Error)")
            valid_qm_fields = [f for f in QM_FIELDS if f in provider_data.columns and pd.api.types.is_numeric_dtype(provider_data[f])];
            if valid_qm_fields:
                qm_summary = provider_data[valid_qm_fields].agg(['mean', 'sem']).T.reset_index(); qm_summary.columns = ['Quality Indicator', 'Mean', 'SEM']; qm_summary.dropna(subset=['Mean'], inplace=True);
                if not qm_summary.empty: fig_bar = px.bar(qm_summary, x='Quality Indicator', y='Mean', error_y='SEM', title=f"Avg Quality Indicators", color_discrete_sequence=[PRIMARY_COLOR], labels={'Mean': 'Avg Value', 'Quality Indicator': 'Indicator'}, hover_data={'SEM': ':.2f'}); fig_bar.update_layout(xaxis_tickangle=-45); st.plotly_chart(fig_bar, use_container_width=True)
                else: st.info("No data for QM bar chart.")
            else: st.warning("No valid QM columns for bar chart.")
            st.markdown("---")

            st.markdown("#### Quality Measures Distribution (Box Plot)")
            if valid_qm_fields and 'Service Name' in provider_data.columns:
                qm_melted_provider = provider_data[['Service Name'] + valid_qm_fields].melt(id_vars="Service Name", var_name="Quality Indicator", value_name="Value"); qm_melted_provider.dropna(subset=['Value'], inplace=True);
                if not qm_melted_provider.empty: fig_box = px.box(qm_melted_provider, x="Quality Indicator", y="Value", points="all", hover_name="Service Name", title=f"QM Distributions"); fig_box.update_traces(marker_color=PRIMARY_COLOR, marker_outliercolor="red", line_color=PRIMARY_COLOR); fig_box.update_layout(xaxis_tickangle=-45); st.plotly_chart(fig_box, use_container_width=True)
                else: st.info("No data points for QM box plot.")
            else: st.warning("Required columns missing for box plot.")
            st.markdown("---")

            st.markdown("#### Compliance History")
            valid_compliance_cols = [c for c in COMPLIANCE_COLUMNS if c in provider_data.columns];
            if '[C] Decision type' in valid_compliance_cols:
                compliance_filtered = provider_data[valid_compliance_cols].dropna(subset=['[C] Decision type'], how='all');
                if not compliance_filtered.empty: st.dataframe(compliance_filtered[['Service Name']+[c for c in valid_compliance_cols if c != 'Service Name']], use_container_width=True, hide_index=True)
                else: st.info(f"No recorded compliance decisions found.")
            else: st.warning("Compliance decision column not found.")
            st.markdown("---")

            # --- REVISED Performance Summary Text ---
            st.markdown("#### Performance Summary & Concerns")
            st.markdown(f"""
            The metrics above show the average performance for **{selected_provider}** across its services (matching current filters).

            **Important:** These averages provide a high-level overview only. For a detailed assessment of specific risks, performance relative to peers, and potential outliers, please consult the:
            *   **'Quality Measures Risk Radar'** tab (comparison to filtered sector peers).
            *   **'Anomaly Detection'** tab (statistical outliers).
            *   **'Serious Concerns' table** displayed below (services meeting absolute risk thresholds).
            """)
            st.markdown("---") # Separator before the concerns table

            # --- Serious Concerns Table (Absolute Thresholds) ---
            concern_flags = pd.Series(False, index=provider_data.index);
            if 'Overall Star Rating' in provider_data: concern_flags |= (provider_data['Overall Star Rating'].fillna(5) <= 2.0)
            if 'Compliance rating' in provider_data: concern_flags |= (provider_data['Compliance rating'].fillna(5) == 1)
            # ***** CORRECTED LINE *****
            if "Residents' Experience rating" in provider_data: concern_flags |= (provider_data["Residents' Experience rating"].fillna(5) <= 2.0)
            # ***** END CORRECTION *****
            if 'Staffing rating' in provider_data: concern_flags |= (provider_data['Staffing rating'].fillna(5) <= 2.0)
            if 'Quality Measures rating' in provider_data: concern_flags |= (provider_data['Quality Measures rating'].fillna(5) <= 2.0)
            flagged_services = provider_data[concern_flags].copy();

            if not flagged_services.empty:
                st.error(f"⚠️ **Serious Concerns Identified (Absolute Thresholds)**")
                st.markdown(f"""<div style='padding: 0.5rem; border: 1px solid #d9534f; border-radius: 5px; background-color: #f2dede; margin-bottom: 1rem; color: #a94442;'>
                <strong>{len(flagged_services)} service(s) meet one or more absolute criteria for potential concern.</strong> Review details below.</div>""", unsafe_allow_html=True)
                valid_flagged_cols = [c for c in FLAGGED_DISPLAY_COLUMNS if c in flagged_services.columns];
                if valid_flagged_cols:
                    def highlight_concerns(row): # Red text styling
                        styles = [''] * len(row); col_map = {col: i for i, col in enumerate(row.index)}; concern_style = 'color: red; font-weight: bold;'
                        if 'Overall Star Rating' in col_map and pd.notna(row['Overall Star Rating']) and row['Overall Star Rating'] <= 2.0: styles[col_map['Overall Star Rating']] = concern_style
                        if 'Compliance rating' in col_map and pd.notna(row['Compliance rating']) and row['Compliance rating'] == 1: styles[col_map['Compliance rating']] = concern_style
                        if "Residents' Experience rating" in col_map and pd.notna(row["Residents' Experience rating"]) and row["Residents' Experience rating"] <= 2.0: styles[col_map["Residents' Experience rating"]] = concern_style
                        if 'Staffing rating' in col_map and pd.notna(row['Staffing rating']) and row['Staffing rating'] <= 2.0: styles[col_map['Staffing rating']] = concern_style
                        if 'Quality Measures rating' in col_map and pd.notna(row['Quality Measures rating']) and row['Quality Measures rating'] <= 2.0: styles[col_map['Quality Measures rating']] = concern_style
                        return styles
                    format_dict = {c: "{:.0f}" for c in valid_flagged_cols if 'rating' in c.lower() or 'star' in c.lower()};
                    styled_flagged = flagged_services[valid_flagged_cols].style.apply(highlight_concerns, axis=1).format(format_dict).set_properties(**{'text-align': 'center'});
                    st.dataframe(styled_flagged, use_container_width=True, hide_index=True)
                else: st.warning("Cannot display flagged services table.")
            else: st.success(f"✅ No services met **absolute** serious concern criteria.")

        elif selected_provider != "All":
             st.warning(f"No data found for provider '{selected_provider}' matching filters.")

    # ===============================================
    # Quality Measures Risk Radar Tab (Index 3)
    # ===============================================
    with tabs[3]:
        st.subheader("Quality Measures Risk Radar")
        st.markdown("""
        This radar chart visualizes the selected provider's performance on key Quality Measures (QMs) relative to its peers within the **currently filtered sector** (State/Size/MMM).

        **How to Interpret the Chart:**

        *   **Axis Values are Percentile Ranks:** Each point represents the provider's **percentile rank** for that QM compared to the filtered sector.
        *   **Lower QM Values are Better:** For most QMs displayed, a lower value indicates better performance.
        *   **Percentile Interpretation:**
            *   **50% = Sector Median:** The <span style='color:red;'>red dashed line</span> represents the median performance (50th percentile) in the filtered sector.
            *   **Below 50% = Better than Median:** Points inside the red line indicate performance better than the sector median. Closer to 0% is significantly better.
            *   **Above 50% = Worse than Median:** Points outside the red line indicate performance worse than the sector median. Closer to 100% suggests potentially higher relative risk.
        """, unsafe_allow_html=True) # Allow HTML for span styling
        st.caption("Note: Percentile calculation requires the 'scipy' library.")

        if selected_provider == "All":
            st.info("Please select a specific provider to generate their Risk Radar.")
        elif provider_filtered_df.empty:
             st.warning(f"No data for provider '{selected_provider}' matching filters.")
        elif sector_filtered_df.empty:
             st.warning("No benchmark data for current filters.")
        elif len(sector_filtered_df) < 3:
             st.warning(f"Insufficient benchmark data (< 3 services).")
        else:
            provider_data = provider_filtered_df
            benchmark_data = sector_filtered_df

            valid_qm_radar = []; qm_has_data = {}
            for qm in QM_FIELDS:
                 if (qm in provider_data.columns and pd.api.types.is_numeric_dtype(provider_data[qm]) and
                     qm in benchmark_data.columns and pd.api.types.is_numeric_dtype(benchmark_data[qm])):
                      valid_qm_radar.append(qm); qm_has_data[qm] = benchmark_data[qm].notna().any()
            valid_qm_radar = [qm for qm in valid_qm_radar if qm_has_data[qm]]

            if not valid_qm_radar:
                st.warning("No valid QM columns with benchmark data found.")
            else:
                qm_percentiles = {}; qm_averages = {}; calculation_possible = False
                for qm in valid_qm_radar:
                    provider_avg = provider_data[qm].mean(); qm_averages[qm] = provider_avg;
                    benchmark_distribution = benchmark_data[qm].dropna();
                    if pd.notna(provider_avg) and not benchmark_distribution.empty:
                        perc = percentileofscore(benchmark_distribution, provider_avg, kind='weak'); qm_percentiles[qm] = perc; calculation_possible = True
                    else: qm_percentiles[qm] = np.nan

                if not calculation_possible:
                     st.warning("Could not calculate percentiles.")
                else:
                    plot_data = {'Percentile': [], 'Provider Avg': []}; plot_labels = []
                    for qm in valid_qm_radar:
                        perc = qm_percentiles.get(qm)
                        if pd.notna(perc):
                             short_label = qm.replace('[QM] ', '').replace('Medication management - ', 'Med Mgmt-').replace('Falls and major injury - ', '').replace(' restrictive practices', ' restraint').replace(' pressure injuries', ' pressure inj.')
                             plot_labels.append(short_label); plot_data['Percentile'].append(perc); plot_data['Provider Avg'].append(qm_averages.get(qm, np.nan))

                    if not plot_labels:
                         st.warning("No valid percentile values to display.")
                    else:
                        fig_radar = go.Figure()
                        # Provider Trace
                        fig_radar.add_trace(go.Scatterpolar(
                            r=plot_data['Percentile'], theta=plot_labels, fill='toself', name=f"{selected_provider} (Percentile Rank)",
                            hovertemplate='<b>%{theta}</b><br>Percentile Rank: %{r:.1f}<br>Provider Avg: %{customdata:.2f}<extra></extra>',
                            customdata=[f'{avg:.2f}' if pd.notna(avg) else 'N/A' for avg in plot_data['Provider Avg']]
                        ))
                        # 50th Percentile Line (Median Benchmark) - ADDED
                        if plot_labels:
                            fig_radar.add_trace(go.Scatterpolar(
                                r=[50] * len(plot_labels), theta=plot_labels, mode='lines',
                                line=dict(color='red', dash='dash', width=1), # Style the line
                                name='Sector Median (50th Percentile)',
                                hoverinfo='skip'
                            ))

                        fig_radar.update_layout(
                            polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix='%', tickfont=dict(color='black')), angularaxis=dict(tickfont=dict(size=10))), # Black tick labels
                            title=f"QM Risk Radar for {selected_provider}<br>(Percentile Rank vs Filtered Sector)",
                            showlegend=True, legend=dict(yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig_radar, use_container_width=True)

                        # --- Dynamic Narrative Based on Radar Results ---
                        st.markdown("---")
                        st.markdown("#### Radar Chart Interpretation Summary:")
                        concern_threshold = 80; strength_threshold = 20 # Define thresholds
                        high_risk_qms = []; low_risk_qms = []
                        for i, qm_label in enumerate(plot_labels):
                            percentile = plot_data['Percentile'][i]; provider_avg = plot_data['Provider Avg'][i];
                            if pd.notna(percentile):
                                if percentile >= concern_threshold: high_risk_qms.append(f"**{qm_label}** (Pctl: {percentile:.0f}%, Avg: {provider_avg:.2f})")
                                elif percentile <= strength_threshold: low_risk_qms.append(f"**{qm_label}** (Pctl: {percentile:.0f}%, Avg: {provider_avg:.2f})")

                        narrative = f"For **{selected_provider}** compared to the filtered sector:\n"
                        if high_risk_qms: narrative += f"\n*   **Potential Areas of Concern (Rank ≥ {concern_threshold}th Pctl):**\n"; narrative += "".join([f"    *   {item}\n" for item in high_risk_qms])
                        else: narrative += f"\n*   No QMs ranked at or above the {concern_threshold}th percentile concern threshold.\n"
                        if low_risk_qms: narrative += f"\n*   **Potential Areas of Strength (Rank ≤ {strength_threshold}th Pctl):**\n"; narrative += "".join([f"    *   {item}\n" for item in low_risk_qms])
                        else: narrative += f"\n*   No QMs ranked at or below the {strength_threshold}th percentile strength threshold.\n"
                        st.markdown(narrative)
                        st.caption("(Based on available QMs with calculable percentiles)")

                        # --- Simple Interpretation Guide - CORRECTED ---
                        st.markdown("---") # Optional separator
                        st.subheader("Quick Interpretation Guide:")
                        # CORRECTED LINE: Use st.markdown, not st.info
                        st.markdown("""
                        *   **Points INSIDE the <span style='color:red;'>red dashed line</span> (Median):** Provider performs better (lower QM value, lower percentile) than the median service in the filtered sector for that measure.
                        *   **Points OUTSIDE the <span style='color:red;'>red dashed line</span> (Median):** Provider performs worse (higher QM value, higher percentile) than the median service in the filtered sector for that measure. Further out indicates potentially higher relative risk.
                        """, unsafe_allow_html=True) # unsafe_allow_html IS valid for st.markdown

    # ===============================================
    # Anomaly Detection Tab (Index 4)
    # ===============================================
    with tabs[4]:
        st.subheader("Anomaly Detection (IQR Outliers)")
        st.markdown("""
        Identifies services with performance outside the typical range (Q1 - 1.5*IQR to Q3 + 1.5*IQR)
        within the **currently filtered sector** (State/Size/MMM).
        """)
        METRICS_TO_CHECK = { # Configuration for outliers
            'Overall Star Rating': {'lower_is_concern': True}, 'RN Care Compliance %': {'lower_is_concern': True},
            'Total Care Compliance %': {'lower_is_concern': True}, '[QM] Pressure injuries*': {'higher_is_concern': True},
            '[QM] Restrictive practices': {'higher_is_concern': True}, '[QM] Falls and major injury - falls*': {'higher_is_concern': True},
            '[QM] Medication management - antipsychotic': {'higher_is_concern': True},
        }
        if sector_filtered_df.empty: st.warning("No benchmark data for current filters.")
        elif len(sector_filtered_df) < 5: st.warning("Insufficient data (< 5 services) for robust outlier detection.")
        else:
            benchmark_data = sector_filtered_df.copy(); outlier_results = []
            # st.write("Calculating IQR boundaries...") # Less verbose
            for metric, config in METRICS_TO_CHECK.items():
                if metric not in benchmark_data.columns or not pd.api.types.is_numeric_dtype(benchmark_data[metric]): continue
                metric_data = benchmark_data[metric].dropna();
                if len(metric_data) < 5: continue
                Q1 = metric_data.quantile(0.25); Q3 = metric_data.quantile(0.75); IQR = Q3 - Q1; lower_bound = Q1 - 1.5 * IQR; upper_bound = Q3 + 1.5 * IQR;
                if config.get('lower_is_concern', False):
                    low_outliers = benchmark_data.loc[benchmark_data[metric] < lower_bound, ['Provider Name', 'Service Name', metric]];
                    for index, row in low_outliers.iterrows(): outlier_results.append({'Provider Name': row['Provider Name'], 'Service Name': row['Service Name'], 'Metric': metric, 'Value': row[metric], 'Reason': f"Low Outlier (< {lower_bound:.2f})", 'IQR Range': f"[{Q1:.2f} - {Q3:.2f}]"})
                if config.get('higher_is_concern', False):
                    high_outliers = benchmark_data.loc[benchmark_data[metric] > upper_bound, ['Provider Name', 'Service Name', metric]];
                    for index, row in high_outliers.iterrows(): outlier_results.append({'Provider Name': row['Provider Name'], 'Service Name': row['Service Name'], 'Metric': metric, 'Value': row[metric], 'Reason': f"High Outlier (> {upper_bound:.2f})", 'IQR Range': f"[{Q1:.2f} - {Q3:.2f}]"})

            if not outlier_results: st.success("No potential outlier concerns identified by IQR method.")
            else:
                st.error(f"**{len(outlier_results)} Potential Outlier Concerns Identified (IQR Method)**")
                outliers_df = pd.DataFrame(outlier_results); outliers_df['Value'] = outliers_df['Value'].map('{:.2f}'.format); outliers_df = outliers_df[['Provider Name', 'Service Name', 'Metric', 'Value', 'Reason', 'IQR Range']];
                st.dataframe(outliers_df, use_container_width=True, hide_index=True)
                st.markdown("---"); st.write("Summary Counts:"); st.dataframe(outliers_df['Metric'].value_counts().reset_index(name='Outlier Count'), hide_index=True); st.dataframe(outliers_df['Provider Name'].value_counts().reset_index(name='Outlier Count'), hide_index=True)


    with tabs[5]:
        # ← exactly four spaces before this line
        st.subheader(f"Benchmark Comparison for {selected_provider}")
        # then all the rest of your block also indented by four spaces:
        sector_df = df[df['Provider Name'] != selected_provider]
        benchmarks = compute_sector_benchmarks(sector_df, QUALITY_MEASURES)

        prov_row = df[df['Provider Name'] == selected_provider].iloc[0]
        prov_vals = {m: prov_row[m] for m in QUALITY_MEASURES}
        prov_df = pd.DataFrame.from_dict(prov_vals,
                                        orient='index',
                                        columns=['Provider Value'])

        comparison = benchmarks.join(prov_df).rename(columns={
            'median':   'Sector Median',
            'p75':      'Sector 75th pct',
            'p90':      'Sector 90th pct',
        })

        def colour_flag(val, row):
            if val >= row['Sector 90th pct']:
                return 'background-color: #C9A66B'
            if val >= row['Sector Median']:
                return 'background-color: #3A7CA5'
            return 'background-color: #FDD'

        styled = comparison.style.apply(
            lambda r: [colour_flag(r['Provider Value'], r)]*len(r),
            axis=1
        ).format("{:.1f}")

        st.write("### Summary Table")
        st.dataframe(styled, use_container_width=True)


        # 6. Legend
        st.markdown(
            "- **Gold**  Top-decile (≥ 90th pct)  \n"
            "- **Blue**  At or above median  \n"
            "- **Red**  Below median (areas to investigate)"
        )
    
        
        # ===============================================
        # Placeholder Tabs (Indices 5, 6)
        # ===============================================
        
    with tabs[6]: st.subheader("Compliance Actions Tracker"); st.info("Future Development: Compliance decision tracking.")

# --- App Body: Display messages if data NOT loaded successfully ---
elif source_type == "uploaded" and not data_loaded_successfully:
     st.warning("Could not process the uploaded file. Check format/content.")
else: # No source identified or loading failed
    st.info(f"📈 **Welcome!** Upload data or ensure '{DEFAULT_DATA_FILENAME}' is available.")
    st.caption(f"(Docker users: Mount data to `/app/{DEFAULT_DATA_FILENAME}`).")

# --- Footer or Disclaimer ---
st.markdown("---")
st.caption("Disclaimer: Demonstrator model for intelligence and policy analysis purposes.")