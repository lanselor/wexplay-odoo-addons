from pathlib import Path
import sys, configparser, uuid, unittest, importlib
server=Path('C:/Program Files/Odoo 18.0.20260220/server')
sys.path.insert(0,str(server))
import odoo
from odoo.tools import config
work=Path('C:/odoo18/addons-wexplay/_workspace/portal_rejection')
name='wex_test_portal_rejection_02c5a6ed'
config.parse_config(['-c',str(server/'odoo.conf'),'-d',name,'--no-http','--max-cron-threads=0','--without-demo=all','--data-dir',str(work/'runtime'),'--logfile',str(work/'odoo.log')])
config['db_name']=name
config['test_enable']=False
config['init']={}
print('Isolated database:',name,flush=True)
from odoo.service.db import _create_empty_database
# database already installed
from odoo.modules.registry import Registry
registry=Registry.new(name,update_module=False)
config['test_enable']=True
module=importlib.import_module('odoo.addons.wexplay_portal_repair_workflow.tests.test_portal_budget_workflow')
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    sys.exit(1)
from odoo import api, SUPERUSER_ID
from unittest.mock import patch
from odoo.exceptions import UserError
from psycopg2.errors import SerializationFailure
from concurrent.futures import ThreadPoolExecutor
import threading

def fixture():
    with registry.cursor() as cr:
        env=api.Environment(cr,SUPERUSER_ID,{})
        partner=env['res.partner'].create({'name':'Fictional rejection company'})
        user=env['res.users'].with_context(no_reset_password=True).create({
            'name':'Fictional portal customer','login':uuid.uuid4().hex+'@example.invalid',
            'partner_id':partner.id,'groups_id':[(6,0,[env.ref('base.group_portal').id])],
        })
        product=env['product.product'].create({'name':'Fictional service','type':'service'})
        order=env['sale.order'].create({'partner_id':partner.id,'order_line':[(0,0,{
            'product_id':product.id,'name':'Fictional service','product_uom_qty':1,
            'product_uom':product.uom_id.id,'price_unit':25,
        })]})
        repair=env['repair.order'].create({'partner_id':partner.id,'product_id':product.id,
            'product_uom':product.uom_id.id,'product_qty':1,'sale_order_id':order.id,
            'x_budget_stage':'waiting_customer'})
        ids=(repair.id,order.id,user.id)
        cr.commit()
        return ids

def reject(ids, barrier=None):
    with registry.cursor() as cr:
        env=api.Environment(cr,ids[2],{})
        if barrier:
            barrier.wait(timeout=10)
        try:
            env['repair.order'].browse(ids[0]).action_portal_reject_budget(rejection_reason='Precio de prueba')
            return 'success'
        except (UserError,SerializationFailure):
            cr.rollback()
            return 'blocked'

def verify(ids, rejected):
    with registry.cursor() as cr:
        env=api.Environment(cr,SUPERUSER_ID,{})
        repair=env['repair.order'].browse(ids[0])
        assert repair.x_budget_stage==('rejected' if rejected else 'waiting_customer')
        assert env['sale.order'].browse(ids[1]).state==('cancel' if rejected else 'draft')
        notes=env['mail.message'].search([('model','=','repair.order'),('res_id','=',ids[0]),
            ('body','ilike','Presupuesto rechazado desde el portal')])
        assert len(notes)==int(rejected)
        events=env['wex.portal.repair.event'].search([('repair_id','=',ids[0]),('event_type','=','budget_rejected')])
        assert len(events)==int(rejected)

ids=fixture()
barrier=threading.Barrier(2)
with ThreadPoolExecutor(max_workers=2) as pool:
    outcomes=list(pool.map(lambda _: reject(ids,barrier),range(2)))
assert sorted(outcomes)==['blocked','success'], outcomes
verify(ids,True)
print('PASS actual isolated cursor and concurrent rejection: one note/event',flush=True)
ids=fixture()
with registry.cursor() as cr:
    env=api.Environment(cr,SUPERUSER_ID,{})
    repair_type=type(env['repair.order'])
with patch.object(repair_type,'_post_portal_budget_rejection',side_effect=UserError('Fictional failure')):
    assert reject(ids)=='blocked'
verify(ids,False)
print('PASS actual isolated cursor rollback on note failure',flush=True)


