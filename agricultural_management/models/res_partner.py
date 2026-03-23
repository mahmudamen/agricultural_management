# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    company_type = fields.Selection(selection_add=[('contract', 'Subsidiary Company'),
                                                   ('engineer', 'Engineer / Agronomist'),
                                                   ('worker', 'Worker'),
                                                   ('accountant','Accountant'),
                                                   ('serviceprovider', 'Service Provider')],store=True,search=True ,
                                    ondelete={'contract': 'cascade', 'engineer': 'cascade', 'worker': 'cascade'})
    is_engineer = fields.Boolean(string='Agricultural Engineer', default=False,
                               help="Check if the contact is an agricultural engineer", tracking=True)
    is_accountant = fields.Boolean(string='Accountant', default=False,
                                help="Check if the contact is a accountant", tracking=True)
    is_worker = fields.Boolean(string='Worker', default=False,
                              help="Check if the contact is a Worker", tracking=True)
    is_contract = fields.Boolean(string='Contract Company', default=False,
                                help="Check if the contact is contract Company", tracking=True)
    is_service_provider = fields.Boolean(string='Service Provider', default=False,
                                  help="Check if the contact is Service Provider")













