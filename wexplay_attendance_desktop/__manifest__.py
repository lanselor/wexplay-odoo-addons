{
    "name": "Wexplay Attendance Desktop",
    "summary": "Clear attendance controls on the Wexplay apps desktop",
    "version": "18.0.1.0.0",
    "author": "Wexplay",
    "license": "AGPL-3",
    "category": "Human Resources/Attendances",
    "depends": ["web_responsive_app_customizer", "hr_attendance"],
    "assets": {
        "web.assets_backend": [
            "wexplay_attendance_desktop/static/src/attendance_service.js",
            "wexplay_attendance_desktop/static/src/attendance_card.js",
            "wexplay_attendance_desktop/static/src/attendance_sync.js",
            "wexplay_attendance_desktop/static/src/attendance_card.xml",
            "wexplay_attendance_desktop/static/src/attendance_card.scss",
        ],
    },
    "installable": True,
}
