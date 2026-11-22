import ee


# ============================================================
# GEOCLIMATE AI
# Google Earth Engine Backend
# ============================================================

def get_boundaries():
    """Load India, State and District boundaries."""

    india = ee.FeatureCollection(
        'FAO/GAUL/2015/level0'
    ).filter(
        ee.Filter.eq('ADM0_NAME', 'India')
    )

    states = ee.FeatureCollection(
        'FAO/GAUL/2015/level1'
    ).filter(
        ee.Filter.eq('ADM0_NAME', 'India')
    )

    districts = ee.FeatureCollection(
        'FAO/GAUL/2015/level2'
    ).filter(
        ee.Filter.eq('ADM0_NAME', 'India')
    )

    return india, states, districts


def get_region_geometry(
    level,
    region_name,
    india,
    states,
    districts
):
    """Return the geometry selected by the user."""

    if level == "India":

        return india.geometry()

    elif level == "State":

        return states.filter(
            ee.Filter.eq('ADM1_NAME', region_name)
        ).geometry()

    elif level == "District":

        return districts.filter(
            ee.Filter.eq('ADM2_NAME', region_name)
        ).geometry()

    else:

        raise ValueError("Invalid region level.")

    # ============================================================
# 1. VEGETATION / NDVI
# ============================================================

def get_vegetation_data(region_geometry, start_year, end_year):

    collection = ee.ImageCollection(
        'MODIS/061/MOD13Q1'
    ).filterBounds(
        region_geometry
    )

    def prepare_image(image):

        ndvi = image.select('NDVI').multiply(0.0001)

        quality = image.select('SummaryQA')

        return ndvi.updateMask(
            quality.lte(1)
        ).copyProperties(
            image,
            ['system:time_start']
        )

    collection = collection.map(prepare_image)

    def annual_ndvi(year):

        start_date = ee.Date.fromYMD(
            year, 1, 1
        )

        end_date = start_date.advance(
            1, 'year'
        )

        image = collection.filterDate(
            start_date,
            end_date
        ).mean()

        return image.set(
            'year',
            year
        )

    years = ee.List.sequence(
        start_year,
        end_year
    )

    annual_collection = ee.ImageCollection.fromImages(
        years.map(annual_ndvi)
    )

    # Start year NDVI
    start_image = annual_collection.filter(
        ee.Filter.eq('year', start_year)
    ).first().clip(region_geometry)

    # End year NDVI
    end_image = annual_collection.filter(
        ee.Filter.eq('year', end_year)
    ).first().clip(region_geometry)

    # Regional mean
    start_value = start_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region_geometry,
        scale=250,
        maxPixels=1e10,
        bestEffort=True
    ).get('NDVI')

    end_value = end_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region_geometry,
        scale=250,
        maxPixels=1e10,
        bestEffort=True
    ).get('NDVI')

    change = ee.Number(end_value).subtract(
        ee.Number(start_value)
    )

    percentage_change = change.divide(
        ee.Number(start_value)
    ).multiply(100)

    # --------------------------------------------------------
    # Annual graph data
    # --------------------------------------------------------

    def calculate_yearly_value(image):

        value = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region_geometry,
            scale=1000,
            maxPixels=1e10,
            bestEffort=True
        ).get('NDVI')

        return ee.Feature(
            None,
            {
                'year': image.get('year'),
                'NDVI': value
            }
        )

    yearly_features = ee.FeatureCollection(
        annual_collection.map(
            calculate_yearly_value
        )
    )

    yearly_data = yearly_features.getInfo()

    annual_values = []

    for feature in yearly_data['features']:

        properties = feature['properties']

        if properties.get('NDVI') is not None:

            annual_values.append({
                'year': int(properties['year']),
                'value': float(properties['NDVI'])
            })

    # --------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------

    start = start_value.getInfo()
    end = end_value.getInfo()
    change_value = change.getInfo()

    if change_value > 0:
        interpretation = (
            "Vegetation greenness increased overall "
            "during the selected period."
        )

    elif change_value < 0:
        interpretation = (
            "Vegetation greenness decreased overall "
            "during the selected period."
        )

    else:
        interpretation = (
            "Vegetation greenness remained approximately "
            "stable during the selected period."
        )

    return {
        'start_value': start,
        'end_value': end,
        'change': change_value,
        'percentage_change': percentage_change.getInfo(),
        'annual_data': annual_values,
        'interpretation': interpretation,

        # Images used by the Streamlit map
        'start_image': start_image,
        'end_image': end_image,

        'start_vis': {
            'min': 0,
            'max': 1,
            'palette': [
                'brown',
                'yellow',
                'green'
            ]
        },

        'end_vis': {
            'min': 0,
            'max': 1,
            'palette': [
                'brown',
                'yellow',
                'green'
            ]
        }
    }

# ============================================================
# 2. RAINFALL
# ============================================================

def get_rainfall_data(region_geometry, start_year, end_year):

    collection = ee.ImageCollection(
        'UCSB-CHG/CHIRPS/DAILY'
    ).filterBounds(
        region_geometry
    ).select(
        'precipitation'
    )

    def annual_rainfall(year):

        start_date = ee.Date.fromYMD(
            year, 1, 1
        )

        end_date = start_date.advance(
            1, 'year'
        )

        image = collection.filterDate(
            start_date,
            end_date
        ).sum()

        return image.set(
            'year',
            year
        )

    years = ee.List.sequence(
        start_year,
        end_year
    )

    annual_collection = ee.ImageCollection.fromImages(
        years.map(annual_rainfall)
    )
    # Start year NDVI
    start_image = annual_collection.filter(
        ee.Filter.eq('year', start_year)
    ).first().clip(region_geometry)

    # End year NDVI
    end_image = annual_collection.filter(
        ee.Filter.eq('year', end_year)
    ).first().clip(region_geometry)

    # --------------------------------------------------------
    # Regional mean rainfall
    # --------------------------------------------------------

    start_value = start_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region_geometry,
        scale=5566,
        maxPixels=1e10,
        bestEffort=True
    ).get('precipitation')

    end_value = end_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region_geometry,
        scale=5566,
        maxPixels=1e10,
        bestEffort=True
    ).get('precipitation')

    change = ee.Number(end_value).subtract(
        ee.Number(start_value)
    )

    percentage_change = change.divide(
        ee.Number(start_value)
    ).multiply(100)

    # --------------------------------------------------------
    # Annual graph data
    # --------------------------------------------------------

    def calculate_yearly_value(image):

        value = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region_geometry,
            scale=5566,
            maxPixels=1e10,
            bestEffort=True
        ).get('precipitation')

        return ee.Feature(
            None,
            {
                'year': image.get('year'),
                'rainfall': value
            }
        )

    yearly_features = ee.FeatureCollection(
        annual_collection.map(
            calculate_yearly_value
        )
    )

    yearly_data = yearly_features.getInfo()

    annual_values = []

    for feature in yearly_data['features']:

        properties = feature['properties']

        if properties.get('rainfall') is not None:

            annual_values.append({
                'year': int(properties['year']),
                'value': float(properties['rainfall'])
            })

    # --------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------

    start = start_value.getInfo()
    end = end_value.getInfo()
    change_value = change.getInfo()

    if change_value > 0:

        interpretation = (
            "Annual rainfall increased overall "
            "during the selected period."
        )

    elif change_value < 0:

        interpretation = (
            "Annual rainfall decreased overall "
            "during the selected period."
        )

    else:

        interpretation = (
            "Annual rainfall remained approximately "
            "stable during the selected period."
        )

    return {
        'start_value': start,
        'end_value': end,
        'change': change_value,
        'percentage_change': percentage_change.getInfo(),
        'annual_data': annual_values,
        'interpretation': interpretation,

        'start_image': start_image,
        'end_image': end_image,

        'start_vis': {
            'min': 0,
            'max': 2000,
            'palette': [
                'white',
                'lightblue',
                'blue',
                'darkblue'
            ]
        },

        'end_vis': {
            'min': 0,
            'max': 2000,
            'palette': [
                'white',
                'lightblue',
                'blue',
                'darkblue'
            ]
        }
    }

# ============================================================
# 3. TEMPERATURE
# ============================================================

def get_temperature_data(region_geometry, start_year, end_year):

    collection = ee.ImageCollection(
        'ECMWF/ERA5_LAND/MONTHLY_AGGR'
    ).filterBounds(
        region_geometry
    ).select(
        'temperature_2m'
    )

    def prepare_image(image):

        return image.subtract(273.15).copyProperties(
            image,
            ['system:time_start']
        )

    collection = collection.map(prepare_image)

    def annual_temperature(year):

        start_date = ee.Date.fromYMD(
            year, 1, 1
        )

        end_date = start_date.advance(
            1, 'year'
        )

        image = collection.filterDate(
            start_date,
            end_date
        ).mean()

        return image.set(
            'year',
            year
        )

    years = ee.List.sequence(
        start_year,
        end_year
    )

    annual_collection = ee.ImageCollection.fromImages(
        years.map(annual_temperature)
    )

    # --------------------------------------------------------
    # Start year
    # --------------------------------------------------------

    start_image = annual_collection.filter(
        ee.Filter.eq('year', start_year)
    ).first().clip(region_geometry)


    # --------------------------------------------------------
    # End year
    # --------------------------------------------------------
    end_image = annual_collection.filter(
        ee.Filter.eq('year', end_year)
    ).first().clip(region_geometry)

    # --------------------------------------------------------
    # Regional mean temperature
    # --------------------------------------------------------

    start_value = start_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region_geometry,
        scale=11132,
        maxPixels=1e10,
        bestEffort=True
    ).get('temperature_2m')

    end_value = end_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region_geometry,
        scale=11132,
        maxPixels=1e10,
        bestEffort=True
    ).get('temperature_2m')

    change = ee.Number(end_value).subtract(
        ee.Number(start_value)
    )

    percentage_change = change.divide(
        ee.Number(start_value)
    ).multiply(100)

    # --------------------------------------------------------
    # Annual graph data
    # --------------------------------------------------------

    def calculate_yearly_value(image):

        value = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region_geometry,
            scale=11132,
            maxPixels=1e10,
            bestEffort=True
        ).get('temperature_2m')

        return ee.Feature(
            None,
            {
                'year': image.get('year'),
                'temperature': value
            }
        )

    yearly_features = ee.FeatureCollection(
        annual_collection.map(
            calculate_yearly_value
        )
    )

    yearly_data = yearly_features.getInfo()

    annual_values = []

    for feature in yearly_data['features']:

        properties = feature['properties']

        if properties.get('temperature') is not None:

            annual_values.append({
                'year': int(properties['year']),
                'value': float(properties['temperature'])
            })

    # --------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------

    start = start_value.getInfo()
    end = end_value.getInfo()
    change_value = change.getInfo()

    if change_value > 0:

        interpretation = (
            "Average temperature increased overall "
            "during the selected period."
        )

    elif change_value < 0:

        interpretation = (
            "Average temperature decreased overall "
            "during the selected period."
        )

    else:

        interpretation = (
            "Average temperature remained approximately "
            "stable during the selected period."
        )

    return {
        'start_value': start,
        'end_value': end,
        'change': change_value,
        'percentage_change': percentage_change.getInfo(),
        'annual_data': annual_values,
        'interpretation': interpretation,

        'start_image': start_image,
        'end_image': end_image,

        'start_vis': {
            'min': 15,
            'max': 35,
            'palette': [
                'blue',
                'yellow',
                'orange',
                'red'
            ]
        },

        'end_vis': {
            'min': 15,
            'max': 35,
            'palette': [
                'blue',
                'yellow',
                'orange',
                'red'
            ]
        }
    }

# ============================================================
# 4. DEFORESTATION / POTENTIAL FOREST LOSS
# ============================================================

def get_deforestation_data(region_geometry, start_year, end_year):

    # --------------------------------------------------------
    # Landsat collections
    # --------------------------------------------------------

    def mask_landsat(image):

        qa = image.select('QA_PIXEL')

        mask = (
            qa.bitwiseAnd(1 << 3).eq(0)
            .And(qa.bitwiseAnd(1 << 4).eq(0))
            .And(qa.bitwiseAnd(1 << 1).eq(0))
        )

        return image.updateMask(mask)

    landsat5 = ee.ImageCollection(
        'LANDSAT/LT05/C02/T1_L2'
    ).filterBounds(
        region_geometry
    ).filterDate(
        ee.Date.fromYMD(start_year, 1, 1),
        ee.Date.fromYMD(start_year + 1, 1, 1)
    ).map(mask_landsat)

    landsat7 = ee.ImageCollection(
        'LANDSAT/LE07/C02/T1_L2'
    ).filterBounds(
        region_geometry
    ).filterDate(
        ee.Date.fromYMD(start_year, 1, 1),
        ee.Date.fromYMD(start_year + 1, 1, 1)
    ).map(mask_landsat)

    landsat8 = ee.ImageCollection(
        'LANDSAT/LC08/C02/T1_L2'
    ).filterBounds(
        region_geometry
    ).filterDate(
        ee.Date.fromYMD(start_year, 1, 1),
        ee.Date.fromYMD(start_year + 1, 1, 1)
    ).map(mask_landsat)

    landsat9 = ee.ImageCollection(
        'LANDSAT/LC09/C02/T1_L2'
    ).filterBounds(
        region_geometry
    ).filterDate(
        ee.Date.fromYMD(start_year, 1, 1),
        ee.Date.fromYMD(start_year + 1, 1, 1)
    ).map(mask_landsat)

    # --------------------------------------------------------
    # NDVI functions
    # --------------------------------------------------------

    def ndvi_l5_l7(image):

        red = image.select('SR_B3').multiply(0.0000275).add(-0.2)
        nir = image.select('SR_B4').multiply(0.0000275).add(-0.2)

        return nir.subtract(red).divide(
            nir.add(red)
        ).rename('NDVI')

    def ndvi_l8_l9(image):

        red = image.select('SR_B4').multiply(0.0000275).add(-0.2)
        nir = image.select('SR_B5').multiply(0.0000275).add(-0.2)

        return nir.subtract(red).divide(
            nir.add(red)
        ).rename('NDVI')

    # --------------------------------------------------------
    # Function to create NDVI for one year
    # --------------------------------------------------------

    def yearly_ndvi(year):

        start_date = ee.Date.fromYMD(year, 1, 1)
        end_date = start_date.advance(1, 'year')

        l5 = ee.ImageCollection(
            'LANDSAT/LT05/C02/T1_L2'
        ).filterBounds(
            region_geometry
        ).filterDate(
            start_date,
            end_date
        ).map(mask_landsat).map(ndvi_l5_l7)

        l7 = ee.ImageCollection(
            'LANDSAT/LE07/C02/T1_L2'
        ).filterBounds(
            region_geometry
        ).filterDate(
            start_date,
            end_date
        ).map(mask_landsat).map(ndvi_l5_l7)

        l8 = ee.ImageCollection(
            'LANDSAT/LC08/C02/T1_L2'
        ).filterBounds(
            region_geometry
        ).filterDate(
            start_date,
            end_date
        ).map(mask_landsat).map(ndvi_l8_l9)

        l9 = ee.ImageCollection(
            'LANDSAT/LC09/C02/T1_L2'
        ).filterBounds(
            region_geometry
        ).filterDate(
            start_date,
            end_date
        ).map(mask_landsat).map(ndvi_l8_l9)

        return (
            l5.merge(l7)
            .merge(l8)
            .merge(l9)
            .mean()
            .clip(region_geometry)
        )

    # Only calculate the two selected years
    start_image = yearly_ndvi(start_year)
    end_image = yearly_ndvi(end_year)

    # --------------------------------------------------------
    # Regional NDVI
    # --------------------------------------------------------

    start_value = start_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region_geometry,
        scale=5000,
        maxPixels=1e8,
        bestEffort=True
    ).get('NDVI')

    end_value = end_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region_geometry,
        scale=5000,
        maxPixels=1e8,
        bestEffort=True
    ).get('NDVI')

    start = ee.Number(start_value)
    end = ee.Number(end_value)

    change = end.subtract(start)

    percentage_change = change.divide(
        start
    ).multiply(100)

    # --------------------------------------------------------
    # Potential forest loss
    # --------------------------------------------------------

    worldcover = ee.Image(
        'ESA/WorldCover/v100/2020'
    )

    tree_cover = worldcover.eq(10)

    ndvi_change = end_image.subtract(
        start_image
    )

    potential_loss = ndvi_change.lte(
        -0.20
    ).And(
        tree_cover
    ).clip(
        region_geometry
    )

    # --------------------------------------------------------
    # Potential loss area
    # --------------------------------------------------------

    loss_area = ee.Image.pixelArea().updateMask(
        potential_loss
    )

    loss_area_km2 = loss_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region_geometry,
        scale=5000,
        maxPixels=1e8,
        bestEffort=True
    ).get('area')

    loss_area_value = ee.Number(
        ee.Algorithms.If(
            loss_area_km2,
            loss_area_km2,
            0
        )
    ).divide(1e6)

    # --------------------------------------------------------
    # Python values
    # --------------------------------------------------------

    start_value = start.getInfo()
    end_value = end.getInfo()
    change_value = change.getInfo()
    loss_value = loss_area_value.getInfo()
    percentage_value = percentage_change.getInfo()

    if change_value > 0:
        interpretation = (
            "Overall vegetation greenness increased during "
            "the selected period."
        )
    elif change_value < 0:
        interpretation = (
            "Overall vegetation greenness decreased during "
            "the selected period."
        )
    else:
        interpretation = (
            "Overall vegetation greenness remained approximately stable."
        )

    interpretation += (
        f" Potential forest loss detected: {loss_value:.2f} km²."
    )

    return {
        'start_value': start_value,
        'end_value': end_value,
        'change': change_value,
        'loss_area': loss_value,
        'loss_percentage': percentage_value,
        'annual_data': [],
        'interpretation': interpretation,

        'start_image': start_image,
        'end_image': end_image,
        'loss_image': potential_loss.selfMask(),

        'start_vis': {
            'min': 0,
            'max': 1,
            'palette': [
                'brown',
                'yellow',
                'green'
            ]
        },

        'end_vis': {
            'min': 0,
            'max': 1,
            'palette': [
                'brown',
                'yellow',
                'green'
            ]
        },

        'loss_vis': {
            'min': 0,
            'max': 1,
            'palette': [
                'red'
            ]
        }
    }


def ndvi_change_image(start_image, end_image):

    return end_image.subtract(
        start_image
    ).rename(
        'NDVI_Change'
    )