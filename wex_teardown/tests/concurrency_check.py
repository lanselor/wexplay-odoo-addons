"""Ejecutar run(env) en odoo shell, exclusivamente sobre una BD de pruebas aislada.

Usa conexiones reales, con commits y reintentos: no forma parte de TransactionCase.
Deja fixtures identificadas por un UUID en esa base para inspeccionar el resultado.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from psycopg2 import IntegrityError, OperationalError

from odoo import api, Command
from odoo.exceptions import UserError


def run(env):
    if not env.cr.dbname.startswith("codex_teardown_test_"):
        raise RuntimeError("Use una base aislada cuyo nombre empiece por codex_teardown_test_.")
    suffix = uuid4().hex[:10]
    company = env.company
    destination = env["stock.location"].create({"name": "Race " + suffix, "usage": "internal", "company_id": company.id})
    company.wex_teardown_default_location_id = destination
    brand = env["wex.repair.brand"].create({"name": "Race " + suffix})
    model = env["wex.repair.device_model"].create({"name": "Race " + suffix, "device_type": "mobile", "brand_id": brand.id})
    category = env["product.category"].create({"name": "Race " + suffix})
    component = env["wex.teardown.component.type"].create({
        "name": "Race " + suffix, "device_type": "mobile", "product_category_id": category.id,
    })
    template = env["wex.teardown.template"].create({
        "name": "Race " + suffix, "device_type": "mobile",
        "line_ids": [Command.create({"component_type_id": component.id, "default_quantity": 1})],
    })
    batch_values = {"device_type": "mobile", "model_id": model.id, "template_id": template.id,
                    "company_id": company.id, "physical_identity_confirmed": True}

    def make_line():
        batch = env["wex.teardown.batch"].create(batch_values)
        batch.action_load_template()
        batch.action_mark_review()
        line = batch.line_ids
        line.write({"qc_state": "ok", "part_number": suffix, "name_final": "Race " + suffix,
                    "list_price": 20, "decision": "create_new"})
        batch.action_validate_teardown()
        return line

    first, second = make_line(), make_line()
    env.cr.commit()
    registry = env.registry

    def race(operations):
        barrier = Barrier(2)

        def worker(operation):
            for attempt in range(4):
                with registry.cursor() as cr:
                    other_env = api.Environment(cr, env.uid, {"allowed_company_ids": [company.id]})
                    try:
                        if attempt == 0:
                            cr.execute("SELECT count(*) FROM wex_teardown_line")
                            barrier.wait(timeout=15)
                        operation(other_env)
                        cr.commit()
                        return "ok"
                    except OperationalError:
                        cr.rollback()
                        if attempt == 3:
                            raise
                    except (UserError, IntegrityError):
                        cr.rollback()
                        return "blocked"

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, operations))

    preparation = race([
        lambda e: e["wex.teardown.line"].browse(first.id).action_prepare_product(),
        lambda e: e["wex.teardown.line"].browse(second.id).action_prepare_product(),
    ])
    assert sorted(preparation) == ["blocked", "ok"], preparation
    env.invalidate_all()
    winner = (first | second).filtered("product_tmpl_id")
    assert len(winner) == 1
    product = winner.product_tmpl_id.with_context(active_test=False)
    import base64
    from io import BytesIO
    from PIL import Image
    buffer = BytesIO()
    Image.new("RGB", (80, 80), "blue").save(buffer, "PNG")
    product.image_1920 = base64.b64encode(buffer.getvalue())
    env.cr.commit()
    finalization = race([
        lambda e: e["wex.teardown.line"].browse(winner.id).action_finalize_piece(),
        lambda e: e["wex.teardown.line"].browse(winner.id).action_finalize_piece(),
    ])
    assert finalization == ["ok", "ok"], finalization
    env.invalidate_all()
    assert winner.stock_move_id.state == "done"
    assert product.product_variant_id.with_context(location=destination.id).qty_available == 1
    env.cr.commit()
    identity_values = dict(batch_values, device_identifier_type="serial", device_identifier="RACE-" + suffix)

    def register(e):
        record = e["wex.teardown.batch"].create(identity_values)
        record.flush_recordset()

    identity = race([register, register])
    assert sorted(identity) == ["blocked", "ok"], identity
    print({"preparation": preparation, "finalization": finalization, "identity": identity, "fixture": suffix})
