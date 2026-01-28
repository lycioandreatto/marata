import streamlit as st
from streamlit_js_eval import streamlit_js_eval

def capturar_coordenadas():
    """
    Captura Latitude e Longitude via navegador.
    Retorna (lat, lon) ou (None, None) se não conseguir.
    """

    js_code = """
    new Promise((resolve) => {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                resolve({
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude
                });
            },
            (err) => {
                resolve(null);
            },
            { 
                enableHighAccuracy: true, 
                timeout: 5000, 
                maximumAge: 0 
            }
        );
    });
    """

    with st.spinner("📡 Buscando sinal de GPS..."):
        loc = streamlit_js_eval(
            js_expressions=js_code,
            key="gps_engine_unique",
            want_output=True
        )

    if isinstance(loc, dict) and "lat" in loc and "lon" in loc:
        return loc["lat"], loc["lon"]

    return None, None
