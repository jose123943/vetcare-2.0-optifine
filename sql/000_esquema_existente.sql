-- Esquema existente, sin filas privadas ni DROP. Se conserva la identidad de cada tabla.

SET FOREIGN_KEY_CHECKS=0;

CREATE TABLE IF NOT EXISTS `administrador` (
  `id_administrador` int NOT NULL,
  `telefono` varchar(20) NOT NULL,
  PRIMARY KEY (`id_administrador`),
  CONSTRAINT `administrador_id_administrador_97d40f3e_fk_auth_user_id` FOREIGN KEY (`id_administrador`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopcion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `estado` varchar(12) NOT NULL,
  `activa` tinyint(1) DEFAULT NULL,
  `motivo` varchar(1000) NOT NULL,
  `observaciones` longtext NOT NULL,
  `observaciones_adopcion` longtext NOT NULL,
  `fecha_registro` datetime(6) NOT NULL,
  `fecha_adopcion` datetime(6) DEFAULT NULL,
  `fecha_cierre` datetime(6) DEFAULT NULL,
  `cerrado_por_id` int DEFAULT NULL,
  `cliente_adoptante_id` bigint DEFAULT NULL,
  `cliente_origen_id` bigint NOT NULL,
  `creado_por_id` int DEFAULT NULL,
  `mascota_id` bigint NOT NULL,
  `responsable_id` bigint NOT NULL,
  `evaluacion_aprobada_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `adopcion_una_activa_por_mascota` (`mascota_id`,`activa`),
  KEY `adopcion_evaluacion_aprobada__6901f1e8_fk_evaluacio` (`evaluacion_aprobada_id`),
  KEY `adopcion_cerrado_por_id_4cf811c0_fk_auth_user_id` (`cerrado_por_id`),
  KEY `adopcion_cliente_adoptante_id_26250f03_fk_cliente_id_cliente` (`cliente_adoptante_id`),
  KEY `adopcion_cliente_origen_id_d79ca813_fk_cliente_id_cliente` (`cliente_origen_id`),
  KEY `adopcion_creado_por_id_0f355d1d_fk_auth_user_id` (`creado_por_id`),
  KEY `adopcion_responsable_id_f566b74d_fk_empleado_id_empleado` (`responsable_id`),
  KEY `adopcion_estado_2c67ac58` (`estado`),
  CONSTRAINT `adopcion_cerrado_por_id_4cf811c0_fk_auth_user_id` FOREIGN KEY (`cerrado_por_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `adopcion_cliente_adoptante_id_26250f03_fk_cliente_id_cliente` FOREIGN KEY (`cliente_adoptante_id`) REFERENCES `cliente` (`id_cliente`),
  CONSTRAINT `adopcion_cliente_origen_id_d79ca813_fk_cliente_id_cliente` FOREIGN KEY (`cliente_origen_id`) REFERENCES `cliente` (`id_cliente`),
  CONSTRAINT `adopcion_creado_por_id_0f355d1d_fk_auth_user_id` FOREIGN KEY (`creado_por_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `adopcion_evaluacion_aprobada__6901f1e8_fk_evaluacio` FOREIGN KEY (`evaluacion_aprobada_id`) REFERENCES `evaluacion_adopcion` (`id`),
  CONSTRAINT `adopcion_mascota_id_d7fa14aa_fk_mascota_id_mascota` FOREIGN KEY (`mascota_id`) REFERENCES `mascota` (`id_mascota`),
  CONSTRAINT `adopcion_responsable_id_f566b74d_fk_empleado_id_empleado` FOREIGN KEY (`responsable_id`) REFERENCES `empleado` (`id_empleado`),
  CONSTRAINT `adopcion_clientes_distintos` CHECK (((`cliente_adoptante_id` is null) or (`cliente_origen_id` <> `cliente_adoptante_id`) or (`cliente_adoptante_id` is null))),
  CONSTRAINT `adopcion_destino_coherente` CHECK ((((`cliente_adoptante_id` is not null) and (`estado` = _utf8mb4'adoptada') and (`evaluacion_aprobada_id` is not null) and (`fecha_adopcion` is not null)) or ((`cliente_adoptante_id` is null) and (`estado` in (_utf8mb4'disponible',_utf8mb4'cancelada')) and (`evaluacion_aprobada_id` is null) and (`fecha_adopcion` is null)))),
  CONSTRAINT `adopcion_estado_activa_coherente` CHECK ((((`activa` = 0x01) and (`activa` is not null) and (`estado` = _utf8mb4'disponible') and (`fecha_cierre` is null)) or ((`activa` is null) and (`estado` in (_utf8mb4'adoptada',_utf8mb4'cancelada')) and (`fecha_cierre` is not null))))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_criterio` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `peso` smallint unsigned NOT NULL,
  `recomendacion` longtext NOT NULL,
  `orden` smallint unsigned NOT NULL,
  `cuestionario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `adopciones_criterio_cuestionario_id_bcd4881b_fk_adopcione` (`cuestionario_id`),
  CONSTRAINT `adopciones_criterio_cuestionario_id_bcd4881b_fk_adopcione` FOREIGN KEY (`cuestionario_id`) REFERENCES `adopciones_cuestionario` (`id`),
  CONSTRAINT `adopciones_criterio_chk_1` CHECK ((`peso` >= 0)),
  CONSTRAINT `adopciones_criterio_chk_2` CHECK ((`orden` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_cuestionario` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `activa` tinyint(1) NOT NULL,
  `creada` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_entrega` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `fecha` datetime(6) NOT NULL,
  `notas` longtext NOT NULL,
  `responsable_id` int NOT NULL,
  `mascota_id` bigint NOT NULL,
  `solicitud_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `mascota_id` (`mascota_id`),
  UNIQUE KEY `solicitud_id` (`solicitud_id`),
  KEY `adopciones_entrega_responsable_id_f1cd3f1a_fk_auth_user_id` (`responsable_id`),
  CONSTRAINT `adopciones_entrega_mascota_id_108ba232_fk_adopcione` FOREIGN KEY (`mascota_id`) REFERENCES `adopciones_mascotaadopcion` (`id`),
  CONSTRAINT `adopciones_entrega_responsable_id_f1cd3f1a_fk_auth_user_id` FOREIGN KEY (`responsable_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `adopciones_entrega_solicitud_id_1d349f40_fk_adopcione` FOREIGN KEY (`solicitud_id`) REFERENCES `adopciones_solicitud` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_mascotaadopcion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(80) NOT NULL,
  `especie` varchar(50) NOT NULL,
  `raza` varchar(80) NOT NULL,
  `sexo` varchar(20) NOT NULL,
  `edad_aproximada` varchar(60) NOT NULL,
  `peso` decimal(6,2) NOT NULL,
  `fotografia` varchar(100) NOT NULL,
  `descripcion` longtext NOT NULL,
  `personalidad` longtext NOT NULL,
  `salud` longtext NOT NULL,
  `vacunacion` longtext NOT NULL,
  `esterilizada` tinyint(1) NOT NULL,
  `necesidades` longtext NOT NULL,
  `ingreso` date NOT NULL,
  `estado` varchar(20) NOT NULL,
  `actualizada` datetime(6) NOT NULL,
  `paciente_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `paciente_id` (`paciente_id`),
  KEY `adop_catalogo_idx` (`estado`,`especie`,`id`),
  CONSTRAINT `adopciones_mascotaad_paciente_id_3f6a3350_fk_mascota_i` FOREIGN KEY (`paciente_id`) REFERENCES `mascota` (`id_mascota`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_opcion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `texto` varchar(300) NOT NULL,
  `valor` smallint unsigned NOT NULL,
  `alerta` varchar(200) NOT NULL,
  `orden` smallint unsigned NOT NULL,
  `pregunta_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `adopciones_opcion_pregunta_id_95a4421b_fk_adopciones_pregunta_id` (`pregunta_id`),
  CONSTRAINT `adopciones_opcion_pregunta_id_95a4421b_fk_adopciones_pregunta_id` FOREIGN KEY (`pregunta_id`) REFERENCES `adopciones_pregunta` (`id`),
  CONSTRAINT `adopciones_opcion_chk_1` CHECK ((`valor` >= 0)),
  CONSTRAINT `adopciones_opcion_chk_2` CHECK ((`orden` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=66 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_pregunta` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `texto` varchar(300) NOT NULL,
  `orden` smallint unsigned NOT NULL,
  `criterio_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `adopciones_pregunta_criterio_id_7f3cf4e6_fk_adopcione` (`criterio_id`),
  CONSTRAINT `adopciones_pregunta_criterio_id_7f3cf4e6_fk_adopcione` FOREIGN KEY (`criterio_id`) REFERENCES `adopciones_criterio` (`id`),
  CONSTRAINT `adopciones_pregunta_chk_1` CHECK ((`orden` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_respuesta` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `original` json NOT NULL,
  `opcion_id` bigint NOT NULL,
  `pregunta_id` bigint NOT NULL,
  `solicitud_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `adop_respuesta_unica` (`solicitud_id`,`pregunta_id`),
  KEY `adopciones_respuesta_opcion_id_0e4e750b_fk_adopciones_opcion_id` (`opcion_id`),
  KEY `adopciones_respuesta_pregunta_id_0a35ca63_fk_adopcione` (`pregunta_id`),
  CONSTRAINT `adopciones_respuesta_opcion_id_0e4e750b_fk_adopciones_opcion_id` FOREIGN KEY (`opcion_id`) REFERENCES `adopciones_opcion` (`id`),
  CONSTRAINT `adopciones_respuesta_pregunta_id_0a35ca63_fk_adopcione` FOREIGN KEY (`pregunta_id`) REFERENCES `adopciones_pregunta` (`id`),
  CONSTRAINT `adopciones_respuesta_solicitud_id_c5c4b2d6_fk_adopcione` FOREIGN KEY (`solicitud_id`) REFERENCES `adopciones_solicitud` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_revision` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `accion` varchar(30) NOT NULL,
  `notas` longtext NOT NULL,
  `bienestar_verificado` tinyint(1) NOT NULL,
  `fecha` datetime(6) NOT NULL,
  `responsable_id` int NOT NULL,
  `solicitud_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `adopciones_revision_responsable_id_cbb0c33c_fk_auth_user_id` (`responsable_id`),
  KEY `adopciones_revision_solicitud_id_4c54e153_fk_adopcione` (`solicitud_id`),
  CONSTRAINT `adopciones_revision_responsable_id_cbb0c33c_fk_auth_user_id` FOREIGN KEY (`responsable_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `adopciones_revision_solicitud_id_4c54e153_fk_adopcione` FOREIGN KEY (`solicitud_id`) REFERENCES `adopciones_solicitud` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `adopciones_solicitud` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `codigo` char(32) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `documento` varchar(30) NOT NULL,
  `edad` smallint unsigned NOT NULL,
  `telefono` varchar(30) NOT NULL,
  `email` varchar(254) NOT NULL,
  `direccion` varchar(200) NOT NULL,
  `ocupacion` varchar(100) NOT NULL,
  `ingreso_aproximado` varchar(80) NOT NULL,
  `presupuesto_cop` int unsigned NOT NULL,
  `porcentaje` decimal(10,6) NOT NULL,
  `aprobada` tinyint(1) NOT NULL,
  `evaluacion` json NOT NULL,
  `alertas` json NOT NULL,
  `recomendaciones` json NOT NULL,
  `estado` varchar(20) NOT NULL,
  `clave` varchar(100) NOT NULL,
  `huella` varchar(64) NOT NULL,
  `propietario_sesion` varchar(64) NOT NULL,
  `creada` datetime(6) NOT NULL,
  `cuestionario_id` bigint NOT NULL,
  `mascota_id` bigint NOT NULL,
  `tenencia_vivienda` varchar(50) NOT NULL,
  `tipo_vivienda` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `clave` (`clave`),
  KEY `adop_solicitudes_idx` (`estado`,`aprobada`,`id`),
  KEY `adopciones_solicitud_cuestionario_id_4281d9cf_fk_adopcione` (`cuestionario_id`),
  KEY `adopciones_solicitud_mascota_id_e9224f45_fk_adopcione` (`mascota_id`),
  CONSTRAINT `adopciones_solicitud_cuestionario_id_4281d9cf_fk_adopcione` FOREIGN KEY (`cuestionario_id`) REFERENCES `adopciones_cuestionario` (`id`),
  CONSTRAINT `adopciones_solicitud_mascota_id_e9224f45_fk_adopcione` FOREIGN KEY (`mascota_id`) REFERENCES `adopciones_mascotaadopcion` (`id`),
  CONSTRAINT `adopciones_solicitud_chk_1` CHECK ((`edad` >= 0)),
  CONSTRAINT `adopciones_solicitud_chk_2` CHECK ((`presupuesto_cop` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=117 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `cita` (
  `id_cita` bigint NOT NULL AUTO_INCREMENT,
  `fecha` date NOT NULL,
  `hora` time(6) NOT NULL,
  `motivo` varchar(200) NOT NULL,
  `estado` varchar(50) NOT NULL,
  `mascota_id` bigint NOT NULL,
  `veterinario_id` bigint NOT NULL,
  `cliente_id` bigint DEFAULT NULL,
  `duracion_minutos` smallint unsigned NOT NULL,
  `observaciones` longtext NOT NULL,
  PRIMARY KEY (`id_cita`),
  KEY `cita_mascota_id_ec36f721_fk_mascota_id_mascota` (`mascota_id`),
  KEY `cita_veterinario_id_28245400_fk_veterinario_id_veterinario` (`veterinario_id`),
  KEY `cita_cliente_id_14b07771_fk_cliente_id_cliente` (`cliente_id`),
  KEY `cita_pendientes_idx` (`estado`,`fecha`,`hora`),
  CONSTRAINT `cita_cliente_id_14b07771_fk_cliente_id_cliente` FOREIGN KEY (`cliente_id`) REFERENCES `cliente` (`id_cliente`),
  CONSTRAINT `cita_mascota_id_ec36f721_fk_mascota_id_mascota` FOREIGN KEY (`mascota_id`) REFERENCES `mascota` (`id_mascota`),
  CONSTRAINT `cita_veterinario_id_28245400_fk_veterinario_id_veterinario` FOREIGN KEY (`veterinario_id`) REFERENCES `veterinario` (`id_veterinario`),
  CONSTRAINT `cita_chk_1` CHECK ((`duracion_minutos` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `cliente` (
  `id_cliente` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `apellido` varchar(50) NOT NULL,
  `telefono` varchar(20) NOT NULL,
  `direccion` varchar(150) NOT NULL,
  `email` varchar(100) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `documento` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id_cliente`),
  UNIQUE KEY `documento` (`documento`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=43 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `empleado` (
  `id_empleado` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `apellido` varchar(50) NOT NULL,
  `telefono` varchar(20) NOT NULL,
  `cargo` varchar(100) NOT NULL,
  PRIMARY KEY (`id_empleado`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `evaluacion_adopcion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `respuestas` json NOT NULL,
  `desglose` json NOT NULL,
  `puntaje` smallint unsigned NOT NULL,
  `aprobada` tinyint(1) NOT NULL,
  `version` varchar(30) NOT NULL,
  `fecha` datetime(6) NOT NULL,
  `adopcion_id` bigint NOT NULL,
  `cliente_id` bigint NOT NULL,
  `evaluado_por_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `evaluacion_adopcion_adopcion_id_eb071079_fk_adopcion_id` (`adopcion_id`),
  KEY `evaluacion_adopcion_cliente_id_5c9d6c28_fk_cliente_id_cliente` (`cliente_id`),
  KEY `evaluacion_adopcion_evaluado_por_id_ea0e7f6e_fk_auth_user_id` (`evaluado_por_id`),
  CONSTRAINT `evaluacion_adopcion_adopcion_id_eb071079_fk_adopcion_id` FOREIGN KEY (`adopcion_id`) REFERENCES `adopcion` (`id`),
  CONSTRAINT `evaluacion_adopcion_cliente_id_5c9d6c28_fk_cliente_id_cliente` FOREIGN KEY (`cliente_id`) REFERENCES `cliente` (`id_cliente`),
  CONSTRAINT `evaluacion_adopcion_evaluado_por_id_ea0e7f6e_fk_auth_user_id` FOREIGN KEY (`evaluado_por_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `evaluacion_adopcion_chk_1` CHECK ((`puntaje` >= 0)),
  CONSTRAINT `evaluacion_aprobacion_mayor_70` CHECK ((((`aprobada` = 0x01) and (`puntaje` > 70)) or ((`aprobada` = 0x00) and (`puntaje` <= 70)))),
  CONSTRAINT `evaluacion_rango_0_100` CHECK ((`puntaje` <= 100))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `factura` (
  `id_factura` bigint NOT NULL AUTO_INCREMENT,
  `fecha_emision` date NOT NULL,
  `monto_total` decimal(10,2) NOT NULL,
  `estado_pago` varchar(50) NOT NULL,
  `administrador_id` int NOT NULL,
  `cita_id` bigint NOT NULL,
  `cliente_id` bigint NOT NULL,
  `descuento` decimal(10,2) NOT NULL,
  `impuesto` decimal(10,2) NOT NULL,
  `metodo_pago` varchar(50) NOT NULL,
  PRIMARY KEY (`id_factura`),
  KEY `factura_cita_id_87c57c47_fk_cita_id_cita` (`cita_id`),
  KEY `factura_cliente_id_d6cd70fe_fk_cliente_id_cliente` (`cliente_id`),
  KEY `factura_administrador_id_c1ac2529_fk_auth_user_id` (`administrador_id`),
  CONSTRAINT `factura_administrador_id_c1ac2529_fk_auth_user_id` FOREIGN KEY (`administrador_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `factura_cita_id_87c57c47_fk_cita_id_cita` FOREIGN KEY (`cita_id`) REFERENCES `cita` (`id_cita`),
  CONSTRAINT `factura_cliente_id_d6cd70fe_fk_cliente_id_cliente` FOREIGN KEY (`cliente_id`) REFERENCES `cliente` (`id_cliente`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `factura_detallefactura` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `servicio` varchar(200) NOT NULL,
  `cantidad` int unsigned NOT NULL,
  `precio_unitario` decimal(10,2) NOT NULL,
  `factura_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `factura_detallefactura_factura_id_2b91fc6c_fk_factura_id_factura` (`factura_id`),
  CONSTRAINT `factura_detallefactura_factura_id_2b91fc6c_fk_factura_id_factura` FOREIGN KEY (`factura_id`) REFERENCES `factura` (`id_factura`),
  CONSTRAINT `factura_detallefactura_chk_1` CHECK ((`cantidad` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `historial_de_vacunas` (
  `id_vacuna` bigint NOT NULL AUTO_INCREMENT,
  `nombre_vacuna` varchar(100) NOT NULL,
  `fecha_aplic` date NOT NULL,
  `fecha_venc` date NOT NULL,
  `lote` varchar(50) NOT NULL,
  `mascota_id` bigint NOT NULL,
  PRIMARY KEY (`id_vacuna`),
  KEY `historial_de_Vacunas_mascota_id_fd1e13ff_fk_mascota_id_mascota` (`mascota_id`),
  CONSTRAINT `historial_de_Vacunas_mascota_id_fd1e13ff_fk_mascota_id_mascota` FOREIGN KEY (`mascota_id`) REFERENCES `mascota` (`id_mascota`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `mascota` (
  `id_mascota` bigint NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `especie` varchar(50) NOT NULL,
  `raza` varchar(50) NOT NULL,
  `edad` int NOT NULL,
  `peso` decimal(5,2) NOT NULL,
  `cliente_id` bigint NOT NULL,
  `observaciones` longtext NOT NULL,
  `sexo` varchar(20) NOT NULL,
  PRIMARY KEY (`id_mascota`),
  KEY `mascota_cliente_id_df2e0369_fk_cliente_id_cliente` (`cliente_id`),
  CONSTRAINT `mascota_cliente_id_df2e0369_fk_cliente_id_cliente` FOREIGN KEY (`cliente_id`) REFERENCES `cliente` (`id_cliente`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `pagInicio_notificacion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `revision` varchar(64) NOT NULL,
  `destinatario` varchar(254) NOT NULL,
  `asunto` varchar(200) NOT NULL,
  `contexto` json NOT NULL,
  `estado` varchar(20) NOT NULL,
  `intentos` int unsigned NOT NULL,
  `error` varchar(250) NOT NULL,
  `creada` datetime(6) NOT NULL,
  `enviada` datetime(6) DEFAULT NULL,
  `cita_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `notificacion_cita_revision` (`cita_id`,`revision`),
  KEY `pagInicio_notificacion_estado_45855910` (`estado`),
  CONSTRAINT `pagInicio_notificacion_cita_id_a040f9f2_fk_cita_id_cita` FOREIGN KEY (`cita_id`) REFERENCES `cita` (`id_cita`),
  CONSTRAINT `pagInicio_notificacion_chk_1` CHECK ((`intentos` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `pagInicio_operacion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `clave` varchar(100) NOT NULL,
  `huella` varchar(64) NOT NULL,
  `respuesta` json NOT NULL,
  `codigo` smallint unsigned NOT NULL,
  `creada` datetime(6) NOT NULL,
  `usuario_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `operacion_usuario_clave` (`usuario_id`,`clave`),
  CONSTRAINT `pagInicio_operacion_usuario_id_a3462e43_fk_auth_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `pagInicio_operacion_chk_1` CHECK ((`codigo` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `tratamiento` (
  `id_tratamiento` bigint NOT NULL AUTO_INCREMENT,
  `descripcion` varchar(200) NOT NULL,
  `medicamento` varchar(100) NOT NULL,
  `dosis` varchar(50) NOT NULL,
  `duracion` varchar(50) NOT NULL,
  `fecha_inicio` date NOT NULL,
  `cita_id` bigint NOT NULL,
  PRIMARY KEY (`id_tratamiento`),
  KEY `tratamiento_cita_id_f2c3581f_fk_cita_id_cita` (`cita_id`),
  CONSTRAINT `tratamiento_cita_id_f2c3581f_fk_cita_id_cita` FOREIGN KEY (`cita_id`) REFERENCES `cita` (`id_cita`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `veterinario` (
  `id_veterinario` bigint NOT NULL,
  `especialidad` varchar(100) NOT NULL,
  PRIMARY KEY (`id_veterinario`),
  CONSTRAINT `veterinario_id_veterinario_efb1fbb2_fk_empleado_id_empleado` FOREIGN KEY (`id_veterinario`) REFERENCES `empleado` (`id_empleado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS=1;