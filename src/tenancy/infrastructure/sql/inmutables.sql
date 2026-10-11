-- Red de seguridad (plan 0000 §5.1): datos que solo se insertan o no se editan.
CREATE OR REPLACE FUNCTION fn_rechazar_cambio() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% es de solo inserción', TG_TABLE_NAME USING ERRCODE = 'P0001';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_parametro_vigencia_inmutable
    BEFORE UPDATE OR DELETE ON tenancy_parametrovigencia
    FOR EACH ROW EXECUTE FUNCTION fn_rechazar_cambio();

CREATE OR REPLACE FUNCTION fn_ruc_inmutable() RETURNS trigger AS $$
BEGIN
    IF NEW.ruc <> OLD.ruc THEN
        RAISE EXCEPTION 'El RUC no se puede modificar' USING ERRCODE = 'P0001';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_empresa_ruc_inmutable
    BEFORE UPDATE ON tenancy_empresa
    FOR EACH ROW EXECUTE FUNCTION fn_ruc_inmutable();
