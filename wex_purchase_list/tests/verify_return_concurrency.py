"""Ejecutar explícitamente con `odoo-bin shell` en una base desechable codex_purchase_*.

Crea y confirma datos de prueba para comprobar dos transacciones independientes.
No se importa desde tests/__init__.py y no debe ejecutarse sobre datos operativos.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from odoo import api, Command, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.service.model import retrying


def verify_return_concurrency(env):
    if not env.cr.dbname.startswith("codex_purchase_"):
        raise RuntimeError("Esta prueba solo admite una base desechable codex_purchase_*.")
    registry = env.registry
    company = env.company
    warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
    warehouse.int_type_id.active = True
    company._ensure_wex_return_location()
    results = {}

    for scenario in ("shared_receipt", "same_request", "dispatch_shared_trace", "dispatch_same_request"):
        is_dispatch = scenario.startswith("dispatch_")
        shared_capacity = scenario in ("shared_receipt", "dispatch_shared_trace")
        vendor = env["res.partner"].create({"name": "Concurrency verification vendor", "supplier_rank": 1})
        product = env["product.product"].create({
            "name": "Concurrency verification " + scenario, "type": "consu", "is_storable": True,
        })
        order = env["purchase.order"].create({
            "partner_id": vendor.id,
            "order_line": [Command.create({
                "name": product.name, "product_id": product.id, "product_qty": 2,
                "product_uom": product.uom_id.id, "price_unit": 10,
            })],
        })
        order.button_confirm()
        receipt = order.picking_ids.move_ids
        receipt.quantity = 2
        receipt.picked = True
        receipt.picking_id.button_validate()
        line = env["wex_purchase_list.line"].create({
            "product_id": product.id, "vendor_id": vendor.id, "quantity": 2,
            "state": "received", "purchase_order_id": order.id,
            "purchase_order_line_id": order.order_line.id,
        })
        quantity = 2 if shared_capacity else 1
        wizard = env["wex.return.prepare"].create({
            "purchase_list_line_id": line.id, "receipt_move_id": receipt.id, "quantity": quantity,
            "receipt_picking_id": receipt.picking_id.id,
            "return_reason": "unused",
        })
        ids = [wizard.id, wizard.id]
        source_ids = [line.id]
        if scenario == "shared_receipt":
            other = line.copy({"purchase_order_id": order.id, "purchase_order_line_id": order.order_line.id})
            source_ids.append(other.id)
            ids[1] = env["wex.return.prepare"].create({
                "purchase_list_line_id": other.id, "receipt_move_id": receipt.id, "quantity": quantity,
                "receipt_picking_id": receipt.picking_id.id,
                "return_reason": "unused",
            }).id
        model_name = "wex.return.prepare"
        method_name = "action_stage"
        if is_dispatch:
            wizard.action_stage()
            record = wizard.return_id
            first_action = record.action_open_dispatch()
            ids = [first_action["res_id"], first_action["res_id"]]
            if shared_capacity:
                ids[1] = record.action_open_dispatch()["res_id"]
            model_name = "wex.return.dispatch"
            method_name = "action_create_returns"
        receipt_id = receipt.id
        company_id = company.id
        env.cr.commit()
        barrier = Barrier(2)

        def worker(wizard_id):
            with registry.cursor() as cr:
                worker_env = api.Environment(cr, SUPERUSER_ID, {"allowed_company_ids": [company_id]})
                # Ambas solicitudes empiezan con una instantánea anterior al primer traslado.
                cr.execute("SELECT id FROM stock_move WHERE id = %s", [receipt_id])
                barrier.wait(timeout=20)
                try:
                    action = retrying(lambda: getattr(worker_env[model_name].browse(wizard_id), method_name)(), worker_env)
                    return ("ok", action["res_id"])
                except UserError as error:
                    cr.rollback()
                    return ("rejected", str(error))

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(worker, ids))
        env.invalidate_all()
        traces = env["wex.purchase.return"].search([("purchase_list_line_id", "in", source_ids)])
        assert len(traces) == 1, outcomes
        assert traces.internal_picking_id.state == "done", outcomes
        assert traces.quantity == quantity, outcomes
        if is_dispatch:
            assert len(traces.return_picking_ids) == 1, outcomes
            assert traces.state == "return_prepared", outcomes
        if shared_capacity:
            assert sorted(item[0] for item in outcomes) == ["ok", "rejected"], outcomes
        else:
            assert outcomes[0][0] == outcomes[1][0] == "ok", outcomes
            assert outcomes[0][1] == outcomes[1][1], outcomes
        results[scenario] = outcomes
    print("CONCURRENCY_VERIFIED " + json.dumps(results, ensure_ascii=True))


verify_return_concurrency(env)
