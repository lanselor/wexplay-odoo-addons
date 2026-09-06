def migrate(cr, version):
    # Conserva exclusivamente la selecciÃ³n administrativa existente antes del cÃ¡lculo.
    cr.execute("ALTER TABLE repair_order ADD COLUMN IF NOT EXISTS wex_portal_billing_tracked boolean")
    cr.execute("""
        UPDATE repair_order
           SET wex_portal_billing_tracked = COALESCE(wex_portal_billing_pending, false)
         WHERE wex_portal_billing_tracked IS NULL
    """)
    cr.execute("ALTER TABLE repair_order ADD COLUMN IF NOT EXISTS wex_billing_cancelled_order boolean")
    cr.execute("""
        UPDATE repair_order r SET wex_billing_cancelled_order = true
          FROM sale_order s
         WHERE r.sale_order_id = s.id AND s.state = 'cancel'
           AND r.wex_portal_billing_tracked = true
    """)
