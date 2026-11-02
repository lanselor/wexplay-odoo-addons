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
from odoo import api, SUPERUSER_ID
with registry.cursor() as cr:
    env=api.Environment(cr,SUPERUSER_ID,{})
    print('BASELINE', env['wex.portal.repair.event'].search([]).mapped(lambda e: (e.event_type,e.partner_id.name,e.handled_state)), flush=True)
    env['wex.portal.repair.event'].search([]).unlink()
    env['repair.order'].search([]).write({'x_budget_stage':'none'})
    cr.commit()
config['test_enable']=True
module=importlib.import_module('odoo.addons.wexplay_portal_repair_workflow.tests.test_portal_dashboard')
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
