ENVIRONMENT_SELECTION = [
    ("test", "Pruebas"),
    ("production", "Producción"),
]

SERVICE_TYPE_SELECTION = [
    ("national", "Nacional"),
    ("international", "Internacional"),
    ("both", "Nacional e internacional"),
]

SHIPMENT_TYPE_SELECTION = [
    ("national", "Nacional"),
    ("international", "Internacional"),
]

SHIPMENT_STATE_SELECTION = [
    ("draft", "Borrador"),
    ("ready", "Preparado"),
    ("sent", "Enviado"),
    ("label_ready", "Etiqueta lista"),
    ("cancel_pending", "Cancelación pendiente"),
    ("cancelled", "Cancelado"),
    ("error", "Error"),
]

LOG_OPERATION_SELECTION = [
    ("test_connection", "Prueba de conexión"),
    ("inspect_wsdl", "Inspección WSDL"),
    ("run_diagnostic", "Ejecutar diagnóstico"),
    ("test_tracking_connection", "Probar conexión de tracking"),
    ("preview_create_shipment", "Previsualizar creación de envío"),
    ("preview_label", "Previsualizar etiqueta"),
    ("preview_cancel_shipment", "Previsualizar cancelación"),
    ("prepare_shipment", "Preparar envío"),
    ("create_shipment", "Crear envío"),
    ("get_label", "Obtener etiqueta"),
    ("cancel_shipment", "Cancelar envío"),
    ("get_tracking", "Consultar seguimiento"),
]

LOG_STATUS_SELECTION = [
    ("success", "Correcto"),
    ("error", "Error"),
]

CASH_ON_DELIVERY_TYPE_SELECTION = [
    ("D", "Destino"),
    ("O", "Origen"),
]

TIME_SLOT_SELECTION = [
    ("0", "Sin tramo horario"),
    ("1", "Mañana"),
    ("2", "Tarde"),
]
