-- fn_siguiente_correlativo (plan 0000 §5.1): atómica; la fila queda bloqueada hasta el commit.
CREATE OR REPLACE FUNCTION fn_siguiente_correlativo(p_empresa bigint, p_documento text, p_serie text)
RETURNS integer AS $$
    INSERT INTO shared_secuencia (empresa_id, documento, serie, ultimo_numero)
    VALUES (p_empresa, p_documento, p_serie, 1)
    ON CONFLICT (empresa_id, documento, serie)
    DO UPDATE SET ultimo_numero = shared_secuencia.ultimo_numero + 1
    RETURNING ultimo_numero;
$$ LANGUAGE sql;
