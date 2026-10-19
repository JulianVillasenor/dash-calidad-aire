"""Recolector periódico de calidad del aire de Open-Meteo hacia MySQL."""

import logging
import os
import time
from datetime import datetime, timezone

import mysql.connector
import requests

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
VARIABLES = ["pm2_5", "pm10", "ozone", "nitrogen_dioxide", "carbon_monoxide", "european_aqi"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def configuracion():
    return {
        "latitude": float(os.getenv("LATITUDE", "19.4326")),
        "longitude": float(os.getenv("LONGITUDE", "-99.1332")),
        "location": os.getenv("LOCATION_NAME", "Ciudad de México"),
        "interval": max(60, int(os.getenv("COLLECT_INTERVAL_SECONDS", "900"))),
    }


def descargar(cfg):
    respuesta = requests.get(
        API_URL,
        params={"latitude": cfg["latitude"], "longitude": cfg["longitude"],
                "hourly": ",".join(VARIABLES), "past_days": 2,
                "forecast_days": 1, "timezone": "UTC"},
        timeout=30,
    )
    respuesta.raise_for_status()
    hourly = respuesta.json().get("hourly", {})
    if not hourly.get("time"):
        raise ValueError("La API no devolvió observaciones horarias")
    return hourly


def filas(hourly, cfg):
    for indice, fecha in enumerate(hourly["time"]):
        yield (
            cfg["location"], cfg["latitude"], cfg["longitude"], datetime.fromisoformat(fecha),
            hourly["pm2_5"][indice], hourly["pm10"][indice], hourly["ozone"][indice],
            hourly["nitrogen_dioxide"][indice], hourly["carbon_monoxide"][indice],
            hourly["european_aqi"][indice],
        )


def guardar(registros):
    conexion = mysql.connector.connect(
        host=os.environ["DB_HOST"], port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], connection_timeout=10,
    )
    consulta = """
        INSERT INTO mediciones_aire
        (ubicacion, latitud, longitud, fecha_hora, pm2_5, pm10, ozono,
         dioxido_nitrogeno, monoxido_carbono, indice_aire_europeo)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS nueva
        ON DUPLICATE KEY UPDATE
          latitud=nueva.latitud, longitud=nueva.longitud,
          pm2_5=nueva.pm2_5, pm10=nueva.pm10, ozono=nueva.ozono,
          dioxido_nitrogeno=nueva.dioxido_nitrogeno,
          monoxido_carbono=nueva.monoxido_carbono,
          indice_aire_europeo=nueva.indice_aire_europeo,
          consultado_en=CURRENT_TIMESTAMP
    """
    try:
        with conexion.cursor() as cursor:
            cursor.executemany(consulta, registros)
        conexion.commit()
    finally:
        conexion.close()


def ciclo():
    cfg = configuracion()
    while True:
        inicio = time.monotonic()
        try:
            registros = list(filas(descargar(cfg), cfg))
            guardar(registros)
            logging.info("Consulta exitosa: %d horas guardadas para %s (UTC %s)",
                         len(registros), cfg["location"], datetime.now(timezone.utc).isoformat())
        except (requests.RequestException, mysql.connector.Error, ValueError, KeyError):
            logging.exception("Falló el ciclo de obtención o almacenamiento")
        time.sleep(max(1, cfg["interval"] - (time.monotonic() - inicio)))


if __name__ == "__main__":
    ciclo()
