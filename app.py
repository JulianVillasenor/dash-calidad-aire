"""Dashboard de las mediciones almacenadas por el contenedor recolector."""

import logging
import os
from datetime import datetime

import mysql.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

app = Dash(__name__)
server = app.server
app.title = "Monitor de calidad del aire"

METRICAS = {
    "pm2_5": ("PM2.5", "µg/m³"),
    "pm10": ("PM10", "µg/m³"),
    "ozono": ("Ozono (O₃)", "µg/m³"),
    "dioxido_nitrogeno": ("Dióxido de nitrógeno (NO₂)", "µg/m³"),
    "monoxido_carbono": ("Monóxido de carbono (CO)", "µg/m³"),
    "indice_aire_europeo": ("Índice europeo de calidad del aire", "AQI"),
}
CARD = {"background": "white", "borderRadius": "14px", "padding": "18px",
        "boxShadow": "0 4px 16px rgba(15, 23, 42, .08)"}

app.layout = html.Div([
    html.Div([
        html.P("PROTOTIPO IoT · API + MYSQL + DASH", style={"color": "#22c55e", "fontWeight": "bold"}),
        html.H1("Calidad del aire urbano", style={"margin": "4px 0"}),
        html.P(f"Datos horarios de Open‑Meteo para {os.getenv('LOCATION_NAME', 'Ciudad de México')}. "
               "Las fechas se muestran en UTC.", style={"color": "#cbd5e1"}),
    ], style={"background": "#0f172a", "color": "white", "padding": "28px", "borderRadius": "18px"}),
    html.Div([
        html.Div([html.Label("Contaminante o índice"), dcc.Dropdown(
            id="metrica", options=[{"label": titulo, "value": clave}
                                   for clave, (titulo, _) in METRICAS.items()],
            value="pm2_5", clearable=False)], style={"flex": "2"}),
        html.Div([html.Label("Periodo"), dcc.Dropdown(
            id="horas", options=[{"label": "Últimas 24 horas", "value": 24},
                                 {"label": "Últimas 48 horas", "value": 48},
                                 {"label": "Todo", "value": 0}],
            value=48, clearable=False)], style={"flex": "1"}),
    ], style={**CARD, "display": "flex", "gap": "18px", "marginTop": "18px"}),
    html.Div(id="resumen", style={"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)",
                                   "gap": "14px", "marginTop": "18px"}),
    html.Div(dcc.Graph(id="grafica", config={"displaylogo": False}), style={**CARD, "marginTop": "18px"}),
    html.P(id="estado", style={"color": "#64748b", "textAlign": "right"}),
    dcc.Interval(id="reloj", interval=60_000, n_intervals=0),
], style={"maxWidth": "1150px", "margin": "32px auto", "padding": "0 20px",
          "fontFamily": "Arial, sans-serif", "color": "#0f172a"})


def leer_datos(horas):
    conexion = mysql.connector.connect(
        host=os.environ["DB_HOST"], port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], connection_timeout=5)
    condicion = "WHERE fecha_hora >= UTC_TIMESTAMP() - INTERVAL %s HOUR" if horas else ""
    parametros = (horas,) if horas else ()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT * FROM mediciones_aire {condicion} ORDER BY fecha_hora", parametros)
            registros = cursor.fetchall()
    finally:
        conexion.close()
    return pd.DataFrame(registros)


def tarjeta(etiqueta, valor):
    return html.Div([html.Div(etiqueta, style={"color": "#64748b", "fontSize": "14px"}),
                     html.Strong(valor, style={"fontSize": "24px"})], style=CARD)


@app.callback(
    Output("grafica", "figure"), Output("resumen", "children"), Output("estado", "children"),
    Input("metrica", "value"), Input("horas", "value"), Input("reloj", "n_intervals"))
def actualizar(metrica, horas, _):
    titulo, unidad = METRICAS[metrica]
    try:
        datos = leer_datos(horas)
    except mysql.connector.Error:
        logging.exception("No se pudo consultar MySQL")
        figura = go.Figure().add_annotation(text="No se pudo consultar la base de datos", showarrow=False)
        return figura, [], "Conexión no disponible; revisa docker compose logs."
    if datos.empty:
        figura = go.Figure().add_annotation(text="Esperando la primera consulta a la API…", showarrow=False)
        return figura, [], "Todavía no hay mediciones almacenadas."

    serie = datos.dropna(subset=[metrica])
    figura = px.line(serie, x="fecha_hora", y=metrica, markers=True, title=f"Evolución de {titulo}")
    figura.update_traces(line_color="#16a34a", hovertemplate=f"%{{x}}<br>%{{y:.1f}} {unidad}<extra></extra>")
    figura.update_layout(template="plotly_white", xaxis_title="Fecha y hora (UTC)", yaxis_title=unidad,
                          hovermode="x unified", margin={"l": 60, "r": 30, "t": 60, "b": 50})
    actual = serie.iloc[-1]
    tarjetas = [tarjeta("Valor más reciente", f"{actual[metrica]:.1f} {unidad}"),
                tarjeta("Promedio del periodo", f"{serie[metrica].mean():.1f} {unidad}"),
                tarjeta("Máximo del periodo", f"{serie[metrica].max():.1f} {unidad}")]
    return figura, tarjetas, (
        f"{len(datos)} registros · Última medición: {actual['fecha_hora']:%Y-%m-%d %H:%M} UTC · "
        f"Dashboard actualizado: {datetime.now():%H:%M:%S}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
