from google.oauth2 import service_account

import streamlit as st
import ee
import pandas as pd
import folium

from streamlit_folium import st_folium

from gee_modules import (
    get_boundaries,
    get_region_geometry,
    get_vegetation_data,
    get_rainfall_data,
    get_temperature_data,
    get_deforestation_data
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="GeoClimate AI",
    page_icon="🌍",
    layout="wide"
)


# ============================================================
# SESSION STATE
# Keeps results visible after Streamlit reruns
# ============================================================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "analysis_module" not in st.session_state:
    st.session_state.analysis_module = None

if "analysis_region_level" not in st.session_state:
    st.session_state.analysis_region_level = None

if "analysis_region_name" not in st.session_state:
    st.session_state.analysis_region_name = None

if "analysis_start_year" not in st.session_state:
    st.session_state.analysis_start_year = None

if "analysis_end_year" not in st.session_state:
    st.session_state.analysis_end_year = None

if "analysis_geometry" not in st.session_state:
    st.session_state.analysis_geometry = None


# ============================================================
# EARTH ENGINE INITIALIZATION
# ============================================================

def initialize_earth_engine():

    try:

        credentials = service_account.Credentials.from_service_account_info(
    {
        "type": "service_account",
        "project_id": st.secrets["GEE_PROJECT_ID"],
        "private_key": st.secrets["GEE_PRIVATE_KEY"].replace("\\n", "\n"),
        "client_email": st.secrets["GEE_CLIENT_EMAIL"],
        "token_uri": "https://oauth2.googleapis.com/token",
    },
    scopes=["https://www.googleapis.com/auth/earthengine"],
)

ee.Initialize(
    credentials=credentials,
    project=st.secrets["GEE_PROJECT_ID"]
)
        return True

    except Exception as error:

        st.error("Google Earth Engine could not be initialized.")

        st.error(str(error))

        return False


ee_ready = initialize_earth_engine()

if not ee_ready:
    st.stop()


# ============================================================
# LOAD BOUNDARIES
# ============================================================

india, states, districts = get_boundaries()


# ============================================================
# HEADER
# ============================================================

st.title("🌍 GEOCLIMATE AI")

st.subheader(
    "Environmental Change Analysis Dashboard"
)

st.write(
    "Analyze vegetation, rainfall, temperature and "
    "potential forest loss using Google Earth Engine."
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("🔍 Analysis Controls")


module = st.sidebar.selectbox(
    "Select Module",
    [
        "Vegetation",
        "Rainfall",
        "Temperature",
        "Deforestation",
        "Integrated Analysis"
    ]
)


region_level = st.sidebar.selectbox(
    "Region Level",
    [
        "India",
        "State",
        "District"
    ]
)


# ============================================================
# REGION SELECTION
# ============================================================

if region_level == "India":

    region_name = "India"


elif region_level == "State":

    state_names = (
        states
        .aggregate_array("ADM1_NAME")
        .distinct()
        .sort()
        .getInfo()
    )

    region_name = st.sidebar.selectbox(
        "Select State",
        state_names
    )


else:

    district_names = (
        districts
        .aggregate_array("ADM2_NAME")
        .distinct()
        .sort()
        .getInfo()
    )

    region_name = st.sidebar.selectbox(
        "Select District",
        district_names
    )


# ============================================================
# YEAR SELECTION
# ============================================================

year_list = list(range(2005, 2026))


start_year = st.sidebar.selectbox(
    "Start Year",
    year_list,
    index=0
)


end_year = st.sidebar.selectbox(
    "End Year",
    year_list,
    index=len(year_list) - 1
)


st.sidebar.divider()


analyze_button = st.sidebar.button(
    "🔍 Analyze",
    use_container_width=True
)


# ============================================================
# ANALYSIS
# ============================================================

if analyze_button:

    if start_year >= end_year:

        st.error(
            "End Year must be greater than Start Year."
        )

        st.stop()


    with st.spinner(
        "Processing environmental data..."
    ):

        # Get selected region geometry

        region_geometry = get_region_geometry(
            region_level,
            region_name,
            india,
            states,
            districts
        )


        # ----------------------------------------------------
        # SINGLE MODULE
        # ----------------------------------------------------

        if module == "Vegetation":

            result = get_vegetation_data(
                region_geometry,
                start_year,
                end_year
            )


        elif module == "Rainfall":

            result = get_rainfall_data(
                region_geometry,
                start_year,
                end_year
            )


        elif module == "Temperature":

            result = get_temperature_data(
                region_geometry,
                start_year,
                end_year
            )


        elif module == "Deforestation":

            result = get_deforestation_data(
                region_geometry,
                start_year,
                end_year
            )


        # ----------------------------------------------------
        # INTEGRATED ANALYSIS
        # ----------------------------------------------------

        else:

            vegetation = get_vegetation_data(
                region_geometry,
                start_year,
                end_year
            )

            rainfall = get_rainfall_data(
                region_geometry,
                start_year,
                end_year
            )

            temperature = get_temperature_data(
                region_geometry,
                start_year,
                end_year
            )

            deforestation = get_deforestation_data(
            region_geometry,
            start_year,
            end_year
            )


            result = {

                "vegetation": vegetation,

                "rainfall": rainfall,

                "temperature": temperature,

                "deforestation": deforestation
            }


        # ----------------------------------------------------
        # SAVE RESULTS IN SESSION STATE
        # ----------------------------------------------------

        st.session_state.analysis_result = result

        st.session_state.analysis_module = module

        st.session_state.analysis_region_level = region_level

        st.session_state.analysis_region_name = region_name

        st.session_state.analysis_start_year = start_year

        st.session_state.analysis_end_year = end_year

        st.session_state.analysis_geometry = region_geometry


# ============================================================
# DISPLAY SAVED ANALYSIS
# ============================================================

if st.session_state.analysis_result is not None:

    result = st.session_state.analysis_result

    saved_module = st.session_state.analysis_module

    saved_region = st.session_state.analysis_region_name

    saved_start = st.session_state.analysis_start_year

    saved_end = st.session_state.analysis_end_year

    region_geometry = st.session_state.analysis_geometry


    # ========================================================
    # DISPLAY TITLE
    # ========================================================

    st.header(
        f"{saved_module}"
    )

    st.write(
        f"Region: **{saved_region}**  |  "
        f"Period: **{saved_start} – {saved_end}**"
    )


    # ========================================================
    # INTEGRATED ANALYSIS DISPLAY
    # ========================================================

    if saved_module == "Integrated Analysis":

        vegetation = result["vegetation"]

        rainfall = result["rainfall"]

        temperature = result["temperature"]

        deforestation = result["deforestation"]


        st.success(
            "Integrated environmental analysis completed successfully."
        )


        st.subheader(
            "🌍 Integrated Environmental Summary"
        )


        # ----------------------------------------------------
        # SUMMARY TABLE
        # ----------------------------------------------------

        summary_data = {

            "Indicator": [

                "Vegetation (NDVI)",

                "Rainfall",

                "Temperature",

                "Potential Forest Loss"
            ],

            "Start Value": [

                f"{vegetation['start_value']:.4f}",

                f"{rainfall['start_value']:.2f} mm",

                f"{temperature['start_value']:.2f} °C",

                "-"
            ],

            "End Value": [

                f"{vegetation['end_value']:.4f}",

                f"{rainfall['end_value']:.2f} mm",

                f"{temperature['end_value']:.2f} °C",

                "-"
            ],

            "Change": [

                f"{vegetation['change']:+.4f}",

                f"{rainfall['change']:+.2f} mm",

                f"{temperature['change']:+.2f} °C",

                f"{deforestation['loss_area']:.2f} km²"
            ]
        }


        st.table(
            pd.DataFrame(summary_data)
        )


        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)


        with col1:

            st.metric(
                "NDVI Change",
                f"{vegetation['change']:+.4f}"
            )


        with col2:

            st.metric(
                "Rainfall Change",
                f"{rainfall['change']:+.2f} mm"
            )


        with col3:

            st.metric(
                "Temperature Change",
                f"{temperature['change']:+.2f} °C"
            )


        with col4:

            st.metric(
                "Potential Forest Loss",
                f"{deforestation['loss_area']:.2f} km²"
            )


        # ----------------------------------------------------
        # INTEGRATED INTERPRETATION
        # ----------------------------------------------------

        st.subheader(
            "🧠 Integrated Interpretation"
        )


        rainfall_direction = (
            "increased"
            if rainfall["change"] > 0
            else "decreased"
            if rainfall["change"] < 0
            else "remained stable"
        )


        temperature_direction = (
            "increased"
            if temperature["change"] > 0
            else "decreased"
            if temperature["change"] < 0
            else "remained stable"
        )


        vegetation_direction = (
            "increased"
            if vegetation["change"] > 0
            else "decreased"
            if vegetation["change"] < 0
            else "remained stable"
        )


        loss_text = (

            f"Potential forest loss detected: "
            f"{deforestation['loss_area']:.2f} km²."

            if deforestation["loss_area"] > 0

            else

            "No significant potential forest loss was detected "
            "using the selected threshold."
        )


        interpretation = (

            f"During the selected period, rainfall "
            f"{rainfall_direction}, temperature "
            f"{temperature_direction}, and vegetation "
            f"greenness {vegetation_direction}. "
            f"{loss_text}"
        )


        st.info(
            interpretation
        )


    # ========================================================
    # SINGLE MODULE DISPLAY
    # ========================================================

    else:

        st.success(
            "Analysis completed successfully."
        )


        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        if saved_module != "Deforestation":

            col1, col2, col3 = st.columns(3)


            with col1:

                st.metric(
                    f"{saved_start} Value",
                    f"{result['start_value']:.4f}"
                )


            with col2:

                st.metric(
                    f"{saved_end} Value",
                    f"{result['end_value']:.4f}",
                    f"{result['change']:+.4f}"
                )


            with col3:

                st.metric(
                    "Percentage Change",
                    f"{result['percentage_change']:+.2f}%"
                )


        else:

            col1, col2, col3 = st.columns(3)


            with col1:

                st.metric(
                    f"{saved_start} NDVI",
                    f"{result['start_value']:.4f}"
                )


            with col2:

                st.metric(
                    f"{saved_end} NDVI",
                    f"{result['end_value']:.4f}",
                    f"{result['change']:+.4f}"
                )


            with col3:

                st.metric(
                    "Potential Forest Loss",
                    f"{result['loss_area']:.2f} km²"
                )


            col4, col5 = st.columns(2)


            with col4:

                st.metric(
                    "Potential Loss of Tree Cover",
                    f"{result['loss_percentage']:.2f}%"
                )


            with col5:

                st.metric(
                    "NDVI Change",
                    f"{result['change']:+.4f}"
                )


        # ----------------------------------------------------
        # INTERPRETATION
        # ----------------------------------------------------

        st.subheader(
            "🧠 Interpretation"
        )


        st.info(
            result["interpretation"]
        )


        # ----------------------------------------------------
        # YEAR-WISE TREND
        # ----------------------------------------------------

        st.subheader(
            "📈 Year-wise Trend"
        )


        chart_data = pd.DataFrame(
            result["annual_data"]
        )


        if not chart_data.empty:

            chart_data = chart_data.set_index(
                "year"
            )

            st.line_chart(
                chart_data
            )


