-- Veterinaria U Proyect
-- Ejecuta este archivo una vez en MySQL Workbench o HeidiSQL.

CREATE DATABASE IF NOT EXISTS veterinaria_u_proyect
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE veterinaria_u_proyect;

-- Tabla principal: cada fila representa una consulta veterinaria.
CREATE TABLE IF NOT EXISTS consultas (
  id_consulta INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre_mascota VARCHAR(120) NOT NULL,
  motivo_consulta VARCHAR(200) NOT NULL,
  valor_consulta DECIMAL(10,2) NOT NULL,
  consulta_pagada BOOLEAN NOT NULL DEFAULT FALSE,
  veterinario_asignado VARCHAR(120) NULL
);

-- Tabla hija: la historia clínica pertenece a una consulta.
-- RESTRICT impide borrar una consulta que tenga historia asociada.
CREATE TABLE IF NOT EXISTS historial_clinico (
  id_historial INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_consulta INT UNSIGNED NOT NULL,
  descripcion VARCHAR(250) NOT NULL,
  fecha DATE NOT NULL,
  CONSTRAINT fk_historial_consulta
    FOREIGN KEY (id_consulta)
    REFERENCES consultas (id_consulta)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
);

-- Datos de ejemplo: dos casos aplican a la regla de abono y dos no.
INSERT INTO consultas
  (id_consulta, nombre_mascota, motivo_consulta, valor_consulta, consulta_pagada, veterinario_asignado)
VALUES
  (101, 'Firulais', 'Vacunación anual', 60000.00, FALSE, 'Dra. Martínez'),
  (102, 'Luna', 'Control general', 45000.00, TRUE, 'Dr. Gómez'),
  (103, 'Rocky', 'Cirugía menor', 180000.00, FALSE, 'Dra. Martínez'),
  (104, 'Pelusa', 'Revisión de rutina', 35000.00, FALSE, NULL)
ON DUPLICATE KEY UPDATE id_consulta = id_consulta;

INSERT INTO historial_clinico (id_historial, id_consulta, descripcion, fecha)
VALUES
  (501, 101, 'Aplicación de vacuna triple y revisión general', '2026-11-18'),
  (502, 102, 'Control de peso y recomendaciones de alimentación', '2026-11-19')
ON DUPLICATE KEY UPDATE id_historial = id_historial;

-- La regla de negocio: alto valor y consulta todavía sin pagar.
SELECT
  id_consulta,
  nombre_mascota,
  motivo_consulta,
  valor_consulta,
  veterinario_asignado
FROM consultas
WHERE consulta_pagada = FALSE
  AND valor_consulta > 50000.00
ORDER BY valor_consulta DESC;

-- Ver las dos tablas y la relación entre una consulta y su historia.
SELECT
  c.id_consulta,
  c.nombre_mascota,
  h.descripcion,
  h.fecha
FROM consultas AS c
LEFT JOIN historial_clinico AS h ON h.id_consulta = c.id_consulta
ORDER BY c.id_consulta, h.fecha;
