-- La auditoría de accesos es de solo inserción (plan 0001d §2; constitución art. 7.3).
CREATE TRIGGER trg_auditoria_acceso_inmutable
    BEFORE UPDATE OR DELETE ON tenancy_auditoriaacceso
    FOR EACH ROW EXECUTE FUNCTION fn_rechazar_cambio();
