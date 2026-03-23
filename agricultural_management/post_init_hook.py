from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Confirm harvest
    for harvest in env['agricultural.harvest.schedule'].search([]):
        if harvest.state != 'completed':
            harvest.action_confirm()
            harvest.action_complete()

    # Allocate costs
    for cost in env['agri.cost.allocation'].search([]):
        cost.action_allocate()

    # Compute profit
    for calc in env['agri.cost.calculation'].search([]):
        calc.compute_profit()