{
    "name": "Wex Device Test",
    "version": "18.0.1.0.0",
    "summary": "Android device connection test endpoint for Wexplay",
    "category": "Wexplay",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "base_setup",
        "web_responsive_app_customizer",
        "wexplay_repair",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "reports/wex_device_test_phase1_qr_report.xml",
        "views/wex_device_test_session_views.xml",
        "views/wex_device_test_run_views.xml",
        "views/wex_device_test_result_views.xml",
        "views/wex_device_test_log_views.xml",
        "views/repair_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/wex_device_test/static/src/js/device_test_footer.esm.js",
            "/wex_device_test/static/src/scss/device_test_footer.scss",
            "/wex_device_test/static/src/xml/device_test_footer.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
