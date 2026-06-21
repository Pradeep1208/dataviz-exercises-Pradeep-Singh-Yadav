import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from pathlib import Path

st.set_page_config(page_title="CO2 Dashboard", page_icon="🌱", layout="wide")


# ── Data ──────────────────────────────────────────────────────────────────────
# @st.cache_data: Streamlit reruns the entire script on every widget interaction.
# Without caching, the CSV is read from disk on every interaction — slow and wasteful.
# cache_data stores the result after the first run and reuses it until the file changes.
@st.cache_data
def load_data():
    path = Path(__file__).parent.parent / 'data' / 'co2_emissions.csv'
    #     path = 'co2_emissions.csv'
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-01-01')
    return df


df = load_data()

st.title("🌱 CO2 Emissions Explorer")
st.caption("Source: Our World in Data — ourworldindata.org/co2-emissions")

# ── TASK 1: Sidebar with 5 widgets ────────────────────────────────────────────
#   a) st.selectbox for Region (with 'All')
#   b) st.multiselect for Countries (updates based on region — chained)
#   c) st.date_input for date range (two-handle; convert years to Jan-1 dates)
#   d) st.radio for Metric: "Total CO2 (Mt)" vs "CO2 per capita"
#   e) st.checkbox labelled "Show only top emitter highlighted"
#
# Guards:
#   - empty countries → st.warning + st.stop()
#   - incomplete date_input → st.warning + st.stop()
# Convert date_input result to pd.Timestamp before filtering.
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    # YOUR CODE HERE
    # a) selectbox for Region (with 'All')
    regions = ['All'] + sorted(df['Region'].unique())
    selected_region = st.selectbox("Region", regions)

    # b) multiselect for Countries — chained on Region
    if selected_region == 'All':
        country_options = sorted(df['Country'].unique())
    else:
        country_options = sorted(
            df[df['Region'] == selected_region]['Country'].unique()
        )

    selected_countries = st.multiselect(
        "Countries",
        options=country_options,
        default=country_options[:4]
    )

    # c) date_input for date range — two-handle; years converted to Jan-1 dates
    date_range = st.date_input(
        "Date range",
        value=(datetime.date(2000, 1, 1), datetime.date(2022, 1, 1)),
        min_value=datetime.date(int(df['Year'].min()), 1, 1),
        max_value=datetime.date(int(df['Year'].max()), 1, 1),
        format="YYYY-MM-DD"
    )

    st.divider()

    # d) radio for Metric
    metric = st.radio("Metric", ["Total CO2 (Mt)", "CO2 per capita"])

    # e) checkbox for top-emitter highlight
    highlight_top = st.checkbox("Show only top emitter highlighted")

# ── Guards ────────────────────────────────────────────────────────────────────
if not selected_countries:
    st.warning("👆 Select at least one country in the sidebar.")
    st.stop()

if len(date_range) != 2:
    st.warning("👆 Select both a start date and an end date.")
    st.stop()

# Convert date_input result to pd.Timestamp before filtering
start_ts = pd.Timestamp(date_range[0])
end_ts = pd.Timestamp(date_range[1])

# filtered = ...  # apply all filters and store here
filtered = df[
    df['Country'].isin(selected_countries) &
    (df['Date'] >= start_ts) &
    (df['Date'] <= end_ts)
    ]

if filtered.empty:
    st.warning("No data matches the current filters.")
    st.stop()

# Map metric label → column name
y_col = 'CO2_Mt' if metric == "Total CO2 (Mt)" else 'CO2_per_capita'
y_label = 'CO2 (Mt)' if y_col == 'CO2_Mt' else 'CO2 per Capita'

# ── TASK 2: Filter summary caption ────────────────────────────────────────────
# Show: "X countries | Region | Date range | Metric"
# BBD rule: always show users how many records match current filters
# ─────────────────────────────────────────────────────────────────────────────
# YOUR CODE HERE
date_str = f"{date_range[0].strftime('%Y')}–{date_range[1].strftime('%Y')}"
st.caption(
    f"**{len(selected_countries)} countries** | "
    f"{selected_region} | "
    f"{date_str} | "
    f"{metric}"
)

# ── EXTENSION: KPI row above the charts ───────────────────────────────────────
last_year = filtered['Year'].max()
first_year = filtered['Year'].min()
last_data = filtered[filtered['Year'] == last_year]
first_data = filtered[filtered['Year'] == first_year]

total_last = last_data[y_col].sum()
total_first = first_data[y_col].sum()
pct_change = ((total_last - total_first) / total_first * 100) if total_first else 0
top_country = last_data.loc[last_data[y_col].idxmax(), 'Country']

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(
    f"Total {y_label} ({last_year})",
    f"{total_last:,.1f}"
)
kpi2.metric(
    f"Change {first_year} → {last_year}",
    f"{pct_change:+.1f}%"
)
kpi3.metric(
    f"Top emitter ({last_year})",
    top_country
)

st.divider()

# ── TASK 3: Two charts reacting to ALL filters ────────────────────────────────
#   Left: line chart — selected metric over time, one line per country
#         If "Show only top emitter highlighted" checkbox is on:
#           - grey all lines except the highest emitter in the date range
#           - label that country at the end of its line (SWD grey-and-highlight)
#   Right: bar chart — ranking for the last year in selected date range
#
# BBD colour requirement: name the colour type in a comment next to each chart
# SWD requirements: white background, insight title, use_container_width=True
# ─────────────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    # Line chart — one line per country
    # Colour type: categorical (one hue per country; grey-and-highlight when checkbox on)

    if highlight_top:
        # SWD grey-and-highlight: identify top emitter over the full date range
        top_emitter = (
            filtered.groupby('Country')[y_col].sum().idxmax()
        )

        fig_line = go.Figure()

        for country in selected_countries:
            country_df = filtered[filtered['Country'] == country]
            if country == top_emitter:
                # Highlighted line — bold blue
                fig_line.add_trace(go.Scatter(
                    x=country_df['Date'], y=country_df[y_col],
                    mode='lines+text',
                    name=country,
                    line=dict(color='#2E75B6', width=3),
                    text=[country if i == len(country_df) - 1 else ''
                          for i in range(len(country_df))],
                    textposition='middle right',
                    textfont=dict(color='#2E75B6', size=11)
                ))
            else:
                # Greyed-out lines (SWD de-emphasis)
                fig_line.add_trace(go.Scatter(
                    x=country_df['Date'], y=country_df[y_col],
                    mode='lines',
                    name=country,
                    line=dict(color='#CCCCCC', width=1),
                    showlegend=True
                ))

        fig_line.update_layout(
            title=f"<b>Highest cumulative emitter: {top_emitter}</b>",
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Arial'),
            xaxis=dict(showgrid=False),
            yaxis=dict(title=y_label, gridcolor='#F0F0F0'),
            legend=dict(orientation='h', yanchor='bottom', y=-0.25)
        )

    else:
        # Standard multi-colour line chart (categorical colour)
        fig_line = px.line(
            filtered, x='Date', y=y_col, color='Country',
            labels={y_col: y_label, 'Date': ''},
            title=f"<b>{metric} over time</b>"
        )
        fig_line.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Arial'),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#F0F0F0'),
            legend=dict(orientation='h', yanchor='bottom', y=-0.25)
        )

    st.plotly_chart(fig_line, use_container_width=True)

with col_right:
    # Bar chart — ranking for the last year in selected date range
    # Colour type: single-hue highlight (#2E75B6) — BBD emphasis colour

    ranking = (
        last_data[['Country', y_col]]
        .sort_values(y_col, ascending=True)
    )

    fig_bar = px.bar(
        ranking, x=y_col, y='Country', orientation='h',
        color_discrete_sequence=['#2E75B6'],  # BBD: highlight colour (single-hue)
        labels={y_col: y_label, 'Country': ''},
        title=f"<b>Ranking — {last_year}</b>"
    )
    fig_bar.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Arial'),
        xaxis=dict(gridcolor='#F0F0F0', range=[0, ranking[y_col].max() * 1.15]),
        yaxis=dict(showgrid=False)
    )
    fig_bar.update_traces(marker_line_width=0)

    st.plotly_chart(fig_bar, use_container_width=True)

# ── EXTENSION: KPI row above the charts ───────────────────────────────────────
#   - Total CO2 in last year of selected range (sum across selected countries)
#   - % change from first to last year
#   - Country with highest emissions in last year
# ─────────────────────────────────────────────────────────────────────────────
# YOUR CODE HERE (optional)