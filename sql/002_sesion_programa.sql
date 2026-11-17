-- La sesión autenticada pertenece a una ejecución del programa.
-- Tabla aditiva: conserva las cuentas, cookies y claves existentes.
CREATE TABLE IF NOT EXISTS vc_session_scope (
    token_hash CHAR(64) NOT NULL PRIMARY KEY,
    run_id CHAR(64) NOT NULL,
    KEY vc_scope_run_idx (run_id),
    CONSTRAINT vc_scope_session_fk FOREIGN KEY (token_hash)
        REFERENCES vc_session(token_hash) ON DELETE CASCADE
) ENGINE=InnoDB;
