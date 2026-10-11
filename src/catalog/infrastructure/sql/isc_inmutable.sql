-- Las tarifas de ISC no se editan ni se borran: un cambio es una tarifa nueva (RF-CAT-24).
CREATE TRIGGER trg_isc_tarifa_inmutable
    BEFORE UPDATE OR DELETE ON catalog_isctarifa
    FOR EACH ROW EXECUTE FUNCTION fn_rechazar_cambio();
