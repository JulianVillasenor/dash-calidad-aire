# Monitor de calidad del aire con Docker

Prototipo académico que obtiene información horaria de contaminación atmosférica,
la conserva en MySQL y permite explorarla en un dashboard. La fuente externa es la
[API Air Quality de Open-Meteo](https://open-meteo.com/en/docs/air-quality-api), que
no requiere clave para este uso de demostración.

## Problema que atiende

La concentración de partículas y gases cambia durante el día. Consultar los datos
en bruto dificulta identificar tendencias. Este proyecto automatiza la captura y
presenta valores recientes, promedios, máximos y series temporales para una ciudad.

## Arquitectura

```text
Open-Meteo (Internet)
        │ HTTP/JSON
        ▼
┌─────────────────┐       SQL        ┌──────────────────┐
│ api             │ ───────────────► │ database         │
│ Ubuntu + Python │                  │ MySQL 8.4        │
└─────────────────┘                  └────────┬─────────┘
                                             │ SQL
                                             ▼
                                    ┌──────────────────┐
Usuario ◄── http://localhost:8050 ──│ dash             │
                                    │ Dash/Plotly      │
                                    └──────────────────┘
```

- `api`: contenedor Ubuntu 24.04 que consulta Open-Meteo al arrancar y después
  cada 15 minutos (configurable).
- `database`: persiste los datos en el volumen `air_quality_data`.
- `dash`: consulta únicamente MySQL; no depende directamente de la API externa.
- Compose crea una red privada. Solo el puerto 8050 se publica en el host.

## Modelo de datos

La tabla `mediciones_aire` guarda ubicación, coordenadas, fecha/hora UTC, PM2.5,
PM10, ozono, dióxido de nitrógeno, monóxido de carbono e índice europeo de calidad
del aire. La combinación `(ubicacion, fecha_hora)` es única: consultas repetidas
actualizan el registro en lugar de duplicarlo. `consultado_en` permite verificar
cuándo se actualizó desde la API.

## Ejecución

Requisitos: Docker Desktop o Docker Engine con Compose v2 y acceso a Internet.

```powershell
Copy-Item .env.example .env   # omitir si .env ya existe
docker compose up -d --build
docker compose ps
```

Abrir <http://localhost:8050>. La primera captura normalmente aparece pocos
segundos después de que MySQL queda saludable. El dashboard se refresca cada minuto.

La ubicación se cambia en `.env` mediante `LATITUDE`, `LONGITUDE` y
`LOCATION_NAME`. Después se recrean los servicios:

```powershell
docker compose up -d --force-recreate api dash
```

## Demostración del flujo completo

1. Mostrar que los tres contenedores están activos:

   ```powershell
   docker compose ps
   ```

2. Mostrar la respuesta/captura de la API en los logs:

   ```powershell
   docker compose logs --tail 20 api
   ```

3. Comprobar almacenamiento real en MySQL:

   ```powershell
   docker compose exec database mysql -uaire_user -p aire
   ```

   Usar `MYSQL_PASSWORD` de `.env` y ejecutar:

   ```sql
   SELECT COUNT(*) AS registros, MIN(fecha_hora), MAX(fecha_hora)
   FROM mediciones_aire;

   SELECT fecha_hora, pm2_5, pm10, ozono, indice_aire_europeo
   FROM mediciones_aire ORDER BY fecha_hora DESC LIMIT 5;
   ```

4. Abrir el dashboard y cambiar contaminante y periodo. Las tarjetas y la gráfica
   se recalculan con los registros recuperados de MySQL.

## Guion breve para la exposición

- **Necesidad:** transformar datos atmosféricos horarios en información visual
  consultable para detectar cambios y episodios de contaminación.
- **API:** Open-Meteo Air Quality; entrega JSON horario por latitud y longitud, sin
  API key para la demostración.
- **Arquitectura:** recolector, base y visualizador son procesos independientes;
  Docker Compose configura red, variables, orden de inicio y persistencia.
- **Base:** una fila por ubicación y hora; índice temporal para consultas y clave
  única para evitar duplicados.
- **Demostración:** logs del recolector, consulta SQL y filtros del dashboard.

## Operación y solución de problemas

```powershell
docker compose logs -f api
docker compose logs -f dash
docker compose logs -f database
docker compose restart api
docker compose down             # conserva mysql_data
docker compose down -v          # elimina también los datos; acción irreversible
```

- Si el puerto 8050 está ocupado, cambiar en `compose.yaml` el mapeo a
  `127.0.0.1:8051:8050` y abrir el puerto 8051.
- Si se modificó `mysql/01-init.sql` después del primer inicio, MySQL no lo ejecuta
  otra vez porque el volumen ya existe. Para una demo nueva se puede usar
  `docker compose down -v` y volver a levantar, sabiendo que borra la base.
- Ante una caída de Internet, el recolector registra el error y reintenta en el
  siguiente ciclo; los datos existentes siguen visibles.
- `.env` contiene contraseñas locales de demostración y no debe publicarse.

## Archivos principales

- `compose.yaml`: definición y comunicación de los tres servicios.
- `Dockerfile.api`: imagen Ubuntu del recolector externo.
- `collector.py`: consumo de la API y carga idempotente.
- `mysql/01-init.sql`: esquema inicial.
- `app.py`: consulta de MySQL y visualización interactiva.
