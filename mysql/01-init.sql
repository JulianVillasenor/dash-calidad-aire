USE aire;

CREATE TABLE mediciones_aire (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ubicacion VARCHAR(120) NOT NULL,
    latitud DECIMAL(9,6) NOT NULL,
    longitud DECIMAL(9,6) NOT NULL,
    fecha_hora DATETIME NOT NULL COMMENT 'Fecha y hora UTC',
    pm2_5 DOUBLE NULL COMMENT 'Particulas menores a 2.5 um, ug/m3',
    pm10 DOUBLE NULL COMMENT 'Particulas menores a 10 um, ug/m3',
    ozono DOUBLE NULL COMMENT 'O3, ug/m3',
    dioxido_nitrogeno DOUBLE NULL COMMENT 'NO2, ug/m3',
    monoxido_carbono DOUBLE NULL COMMENT 'CO, ug/m3',
    indice_aire_europeo DOUBLE NULL COMMENT 'European AQI',
    consultado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_ubicacion_fecha (ubicacion, fecha_hora),
    INDEX idx_fecha_hora (fecha_hora)
);
