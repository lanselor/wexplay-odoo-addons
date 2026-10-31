"""Ejecutar con odoo-bin shell solo en una base desechable codex_purchase_*.

Confirma fixtures y usa transacciones independientes con el reintento nativo.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from odoo import api, Command, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.service.model import retrying


def verify_resolution_concurrency(env):
    if not env.cr.dbname.startswith("codex_purchase_"):
        raise RuntimeError("Esta prueba requiere una base desechable codex_purchase_*.")
    company = env.company
    warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
    company._ensure_wex_return_location()
    results = {}
    for scenario in ("same_recovery_request", "two_recovery_requests", "recovery_vs_dispatch", "scrap_vs_dispatch", "recovery_vs_scrap", "same_reorder_request"):
        vendor = env["res.partner"].create({"name": "Resolution concurrency supplier", "supplier_rank": 1})
        product = env["product.product"].create({"name": scenario, "type": "consu", "is_storable": True})
        order = env["purchase.order"].create({
            "partner_id": vendor.id,
            "order_line": [Command.create({"product_id": product.id, "product_qty": 1,
                                           "name": product.name, "product_uom": product.uom_id.id, "price_unit": 10})],
        })
        order.button_confirm()
        receipt = order.picking_ids
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()
        source = env["wex_purchase_list.line"].create({
            "product_id": product.id, "vendor_id": vendor.id, "quantity": 1, "state": "received",
            "purchase_order_id": order.id, "purchase_order_line_id": order.order_line.id,
        })
        stage_values = {"purchase_list_line_id": source.id, "receipt_picking_id": receipt.id,
                        "receipt_move_id": receipt.move_ids.id, "quantity": 1, "return_reason": "unused"}
        if scenario == "same_reorder_request":
            repair = env["repair.order"].create({"product_id": product.id})
            part = env["stock.move"].create({"repair_id": repair.id, "repair_line_type": "add",
                                            "product_id": product.id, "product_uom": product.uom_id.id,
                                            "product_uom_qty": 1, "purchase_list_line_id": source.id})
            source.write({"repair_id": repair.id, "repair_part_move_id": part.id})
            stage_values.update({"repair_move_id": part.id, "confirm_origin_change": True,
                                 "request_replacement": True, "replacement_quantity": 1})
        stage = env["wex.return.prepare"].create(stage_values)
        if scenario == "same_reorder_request":
            operations = [(stage._name, stage.id, "action_stage")] * 2
        else:
            stage.action_stage()
            trace = stage.return_id

            def prepare_recovery():
                wizard = env["wex.return.resolve"].create({
                    "return_id": trace.id, "quantity": 1, "disposition": "recover",
                    "explanation": scenario, "destination_location_id": warehouse.lot_stock_id.id,
                })
                return (wizard._name, wizard.id, "action_resolve")

            def prepare_scrap():
                wizard = env["wex.return.resolve"].create({"return_id": trace.id, "quantity": 1,
                                                          "disposition": "scrap", "explanation": scenario})
                wizard.action_resolve()
                scrap = wizard.resolution_id.scrap_ids
                return (scrap._name, scrap.id, "do_scrap")

            if scenario == "scrap_vs_dispatch":
                operations = [prepare_scrap()]
            else:
                operations = [prepare_recovery()]
            if scenario == "same_recovery_request":
                operations *= 2
            elif scenario == "two_recovery_requests":
                operations.append(prepare_recovery())
            elif scenario == "recovery_vs_scrap":
                operations.append(prepare_scrap())
            else:
                action = trace.action_open_dispatch()
                operations.append(("wex.return.dispatch", action["res_id"], "action_create_returns"))
        source_id = source.id
        receipt_id = receipt.move_ids.id
        company_id = company.id
        env.cr.commit()
        barrier = Barrier(2)

        def worker(operation):
            model, record_id, method = operation
            with env.registry.cursor() as cr:
                worker_env = api.Environment(cr, SUPERUSER_ID, {"allowed_company_ids": [company_id]})
                cr.execute("SELECT id FROM stock_move WHERE id = %s", [receipt_id])
                barrier.wait(timeout=20)
                try:
                    action = retrying(lambda: getattr(worker_env[model].browse(record_id), method)(), worker_env)
                    return ("ok", action.get("res_id") if isinstance(action, dict) else record_id)
                except UserError as error:
                    cr.rollback()
                    return ("rejected", str(error))

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(worker, operations))
        env.invalidate_all()
        trace = env["wex.purchase.return"].search([("purchase_list_line_id", "=", source_id)])
        assert len(trace) == 1, outcomes
        if scenario in ("same_recovery_request", "same_reorder_request"):
            assert outcomes[0][0] == outcomes[1][0] == "ok", outcomes
            assert outcomes[0][1] == outcomes[1][1], outcomes
            if scenario == "same_reorder_request":
                assert len(trace.replacement_move_id) == 1, outcomes
                assert trace.replacement_purchase_line_id.quantity == 1, outcomes
            else:
                assert len(trace.resolution_ids) == 1 and trace.recovered_quantity == 1, outcomes
        else:
            assert sorted(item[0] for item in outcomes) == ["ok", "rejected"], outcomes
        assert trace.recovered_quantity + trace.scrapped_quantity + trace.returned_quantity + trace.prepared_quantity <= trace.quantity, outcomes
        results[scenario] = outcomes
    print("RESOLUTION_CONCURRENCY_VERIFIED " + json.dumps(results, ensure_ascii=True))


verify_resolution_concurrency(env)
