PROVIDER_CODE = "wex_redsys"
SIGNATURE_VERSION = "HMAC_SHA256_V1"
API_URLS = {
    "test": "https://sis-t.redsys.es:25443/sis/realizarPago",
    "enabled": "https://sis.redsys.es/sis/realizarPago",
}
NOTIFICATION_URL = "/payment/wex_redsys/notify"
RETURN_URL = "/payment/wex_redsys/return"
