-- tenancy_actividad es de solo inserción (plan 0001b §2).
CREATE TRIGGER trg_actividad_inmutable
    BEFORE UPDATE OR DELETE ON tenancy_actividad
    FOR EACH ROW EXECUTE FUNCTION fn_rechazar_cambio();
