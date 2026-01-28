import streamlit as st
from streamlit_js_eval import streamlit_js_eval

def capturar_coordenadas():
    """
    Função modular para capturar Latitude e Longitude via Navegador.
    Retorna uma tupla (lat, lon) ou (None, None) em caso de erro.
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
    
    with st.spinner("Buscando sinal de GPS..."):
        loc = streamlit_js_eval(js_expressions=js_code, key="gps_engine", want_output=True)
    
    if loc:
        return loc.get('lat'), loc.get('lon')
    else:
        return None, None
