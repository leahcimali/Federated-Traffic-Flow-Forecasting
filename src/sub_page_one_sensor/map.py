from os import path


import streamlit as st
from streamlit_folium import folium_static
import json
import pandas as pd
import folium
from screeninfo import get_monitors
from annotated_text import annotated_text


from metrics import maape
from config import Params
from utils_streamlit_app import create_circle_precision_predict, get_color_fed_vs_local
from utils_streamlit_app import load_numpy


#######################################################################
# Constant(s)
#######################################################################
SEATTLE_ROADS = [
    [47.679470, -122.315626],
    [47.679441, -122.306665],
    [47.683058163418266, -122.30074031156877],
    [47.67941986097163, -122.29031294544225],
    [47.67578888921566, -122.30656814568495],
    [47.67575649888934, -122.29026613694701],
    [47.68307457244817, -122.29054200791231],
    [47.68300028244276, -122.3121427044953],
    [47.670728396123444, -122.31192781883172],
    [47.675825, -122.315658],
    [47.69132417321706, -122.31221442807933],
    [47.68645681961068, -122.30076590191602],
    [47.68304467808857, -122.27975989945097],
    [47.6974488132659, -122.29057907732675]
]

height = []
width = []
for m in get_monitors():
    height.append(m.height)
    width.append(m.width)

HEIGHT = min(height)
WIDTH = min(width)


def plot_map(experiment_path, mapping_sensor_with_nodes, sensor_selected):
    params = Params(f'{experiment_path}/config.json')
    index = load_numpy(f"{experiment_path}/index_0.npy")
    index = pd.to_datetime(index, format='%Y-%m-%dT%H:%M:%S.%f')

    slider = st.slider('Select the step (a step equal 5min)?', 0, len(index) - params.prediction_horizon - params.window_size - 1, 0, key="MAP_and_Graph")
    st.header(f"| {index[slider+params.window_size].strftime(f'Day: %Y-%m-%d | Time prediction: {int(params.prediction_horizon*5/60)}h (%Hh%Mmin')} to {index[slider + params.window_size + params.prediction_horizon].strftime(f'%Hh%Mmin) | Step : {slider} |')}")

    seattle_map_global = folium.Map(location=[47.6776, -122.30064], zoom_start=15, zoomSnap=0.25)
    seattle_map_local = folium.Map(location=[47.67763, -122.30064], zoom_start=15, zoomSnap=0.25)

    sensors_loc = {}
    seattle_roads_crop = [SEATTLE_ROADS[i] for i in range(len(mapping_sensor_with_nodes.keys()))]

    for sensor, locations in zip(mapping_sensor_with_nodes.keys(), seattle_roads_crop):
        sensors_loc[sensor] = locations

    add_sensors_to_map(sensors_loc, params.nodes_to_filter[int(sensor_selected)], seattle_map_global)
    add_sensors_to_map(sensors_loc, params.nodes_to_filter[int(sensor_selected)], seattle_map_local)

    def plot_map_slider(y_true, y_pred, y_pred_fed, i, coords):

        maape_computed_local = 1 - (maape(y_true[i, :].flatten(), y_pred[i, :].flatten())) / 100.0
        maape_computed_fed = 1 - (maape(y_true[i, :].flatten(), y_pred_fed[i, :].flatten())) / 100.0
        color_fed, color_local = get_color_fed_vs_local(maape_computed_fed, maape_computed_local)

        create_circle_precision_predict(coords, maape_computed_local, seattle_map_local, color_local)
        create_circle_precision_predict(coords, maape_computed_fed, seattle_map_global, color_fed)

    for sensor in mapping_sensor_with_nodes.keys():
        y_true = load_numpy(f"{experiment_path}/y_true_local_{mapping_sensor_with_nodes[sensor]}.npy")
        y_pred = load_numpy(f"{experiment_path}/y_pred_local_{mapping_sensor_with_nodes[sensor]}.npy")
        y_pred_fed = load_numpy(f"{experiment_path}/y_pred_fed_{mapping_sensor_with_nodes[sensor]}.npy")
        plot_map_slider(y_true, y_pred, y_pred_fed, slider, sensors_loc[sensor])

    seattle_map_global.fit_bounds(seattle_map_global.get_bounds(), padding=(30, 30))
    seattle_map_local.fit_bounds(seattle_map_local.get_bounds(), padding=(30, 30))

    st.divider()
    annotated_text(
        "A higher percent indicates a better prediction. The ",
        ("green", "", "#75ff5b"), " circle",
        " is better than the ",
        ("red", "", "#fe7597"), " one.")
    st.write("""
            Exemple: for a prediction at one hour (t+12), 98% means that\\
            in average on the 12 points predicted the models have an accuracy\\
            equals to 98%.
            """)
    st.image("data/light_blue_marker.png", width=60)
    st.markdown("""
                The sensor selectioned in \"Choose the sensor\"
                """)
    st.divider()

    col1, col2 = st.columns((0.5, 0.5), gap="small")
    with col1:
        col1.header('Federated model results')
        folium_static(seattle_map_global, width=WIDTH / 2 - 300)  # To fix the overlapping effect (handmade solution)
    with col2:
        col2.header('Local models results')
        folium_static(seattle_map_local, width=WIDTH / 2 - 300)  # To fix the overlapping effect (handmade solution)


def add_sensors_to_map(sensors_loc, sensor_selected, map_folium):
    for sensor in sensors_loc.keys():
        tooltip = f"Road: {sensor}"
        if (sensor_selected == sensor):
            folium.Marker(location=sensors_loc[sensor], tooltip=tooltip, icon=folium.Icon(color="lightblue")).add_to(map_folium)
        else:
            folium.Marker(location=sensors_loc[sensor], tooltip=tooltip, icon=folium.Icon(color="black")).add_to(map_folium)


#######################################################################
# Main
#######################################################################
def map_sensors(experiment_path, sensor_selected):
    st.header("Map")
    st.write("""
                * on this page select one experiment.
                    * On the map, you will find the sensors location and their accuracy.
                """)
    st.divider()

    path_experiment_selected = experiment_path
    if (path_experiment_selected is not None):

        with open(f"{path_experiment_selected}/test.json") as f:
            results = json.load(f)
        with open(f"{path_experiment_selected}/config.json") as f:
            config = json.load(f)

        mapping_sensor_with_nodes = {}
        for node in results.keys():
            mapping_sensor_with_nodes[config["nodes_to_filter"][int(node)]] = node

        if (path.exists(f'{path_experiment_selected}/y_true_local_0.npy') and
            path.exists(f"{path_experiment_selected}/y_pred_fed_0.npy")):
            plot_map(path_experiment_selected, mapping_sensor_with_nodes, sensor_selected)
