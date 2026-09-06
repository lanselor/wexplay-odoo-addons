# Ejecutar en PowerShell como administrador. Actualiza la base local test2.
$ErrorActionPreference = "Stop"
Stop-Service -Name "odoo-server-18.0"
try {
    & "C:\Program Files\Odoo 18.0.20260220\python\python.exe" `
      "C:\Program Files\Odoo 18.0.20260220\server\odoo-bin" `
      -c "C:\Program Files\Odoo 18.0.20260220\server\odoo.conf" `
      -d test2 `
      -u wexplay_repair,wexplay_portal,wexplay_portal_repair_billing `
      -i wexplay_portal_repair_billing `
      --stop-after-init --no-http --max-cron-threads=0
    if ($LASTEXITCODE -ne 0) { throw "La actualización falló. Revisa el log de Odoo." }
}
finally {
    Start-Service -Name "odoo-server-18.0"
}
