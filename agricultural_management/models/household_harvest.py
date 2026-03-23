from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class HouseholdHarvest(models.Model):
    _name = 'household.harvest'
    _description = 'Household Harvest Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'harvest_date desc, household_code'

    name = fields.Char('Harvest Reference', required=True, copy=False, readonly=True,translate=True, tracking=True,
                       default=lambda self: _('New'))
    household_code = fields.Char('Household Code', required=False, tracking=True)
    household_name = fields.Char('Household Name', translate=True, tracking=True,required=False)
    schedule_id = fields.Many2one(
        'agricultural.harvest.schedule', 'Harvest Schedule',
        required=False, tracking=True, ondelete='cascade'
    )
    harvest_batch_id = fields.Many2one('harvest.batch','Batch')
    farm_id = fields.Many2one(
        'agricultural.farm',
        'Farm',
        related='harvest_batch_id.farm_id',
        store=True,
        readonly=True
    )
    sorting_line_ids = fields.One2many('harvest.sorting.line', 'household_harvest_id', 'Sorting Lines')
    project_id = fields.Many2one('agricultural.project', 'Project')
    crop_id = fields.Many2one('product.product', 'Crop Type', required=False)
    harvest_date = fields.Date('Harvest Date', required=True, default=fields.Date.today)
    expected_total_kg = fields.Float('Expected Total Harvest (kg)', required=True)
    harvested_to_date_kg = fields.Float('Harvested to Date (kg)', compute='_compute_harvest_totals', store=True)
    harvest_completion_percent = fields.Float('Harvest Completion %', compute='_compute_harvest_totals', store=True)
    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='planned', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    total_revenue = fields.Monetary('Total Revenue', currency_field='currency_id',
                                    compute='_compute_financial_totals', store=True)
    total_cost = fields.Monetary('Total Cost', currency_field='currency_id',
                                 compute='_compute_financial_totals', store=True)
    total_profit = fields.Monetary('Total Profit', currency_field='currency_id',
                                   compute='_compute_financial_totals', store=True)
    # Harvest data
    product_id = fields.Many2one(
        'product.product', 'Crop', required=True
    )
    # Business methods
    def action_start_sorting(self):
        """Initiate sorting process for this contribution"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only recorded contributions can be sorted."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sort Contribution'),
            'res_model': 'harvest.sorting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_household_harvest_id': self.id,
                'default_product_id': self.product_id.id,
                'default_quantity': self.total_quantity,
                'default_harvest_batch_id': self.harvest_batch_id.id
            }
        }
    def action_view_sorting_results(self):
        """View sorting results for this contribution"""
        self.ensure_one()
        return {
            'name': _('Sorting Results'),
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.sorting.line',
            'view_mode': 'list,form',
            'domain': [('household_harvest_id', '=', self.id)],
            'context': {'create': False}
        }
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('household.harvest') or _('New')
        return super(HouseholdHarvest, self).create(vals)
    def _compute_harvest_totals(self):
        for record in self:
            total_harvested = sum(record.harvest_batch_ids.mapped('net_weight_kg'))
            record.harvested_to_date_kg = total_harvested
            if record.expected_total_kg > 0:
                record.harvest_completion_percent = (total_harvested / record.expected_total_kg) * 100
            else:
                record.harvest_completion_percent = 0
    def _compute_financial_totals(self):
        for record in self:
            record.total_revenue = sum(record.sorting_line_ids.mapped('revenue'))
            record.total_cost = sum(record.sorting_line_ids.mapped('cost'))
            record.total_profit = sum(record.sorting_line_ids.mapped('profit'))
class HouseholdHarvestExtended(models.Model):
    _inherit = 'household.harvest'

    farmer_analytic_account_id = fields.Many2one('account.analytic.account',
                                                 'Farmer Analytic Account',
                                                 help="Analytic account for tracking farmer costs")
    def action_confirm(self):
        pass
    def action_cancel(self):
        pass
    def action_reset_to_draft(self):
        pass
    def action_view_sorting_lines(self):
        pass
    def action_view_batch(self):
        pass

    @api.onchange('household_id')
    def _onchange_household_id(self):
        """Set analytic account from farmer/household"""
        if self.household_id and self.household_id.property_analytic_account_id:
            self.farmer_analytic_account_id = self.household_id.property_analytic_account_id






