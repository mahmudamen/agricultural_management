from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import json


class AgriculturalProject(models.Model):
    _inherit = 'agricultural.project'
    _order = 'start_date desc, priority desc'
    total_profit = fields.Float('total profit', required=False,
                                  digits='Product Unit of Measure', tracking=True)
    harvest_schedule_ids = fields.One2many('agricultural.harvest.schedule', 'project_id',
                                           string='Harvest Schedules')
    harvest_batch_ids = fields.One2many('harvest.batch', 'project_id',
                                        string='Harvest Batches')
    household_harvest_ids = fields.One2many('household.harvest', 'project_id',
                                            string='Household Harvest')
    harvest_sorting_line_ids = fields.One2many('harvest.sorting.line', 'project_id',
                                               string='Sorting Lines')
    total_harvest_schedules = fields.Float('Total Harvest Quantity',store=True)
    total_harvest_batches = fields.Float('Total Harvest Quantity', store=True)
    total_harvest_quantity = fields.Float('Total Harvest Quantity', store=True)
    active_harvest_schedules = fields.Float('Active Harvest Schedule', store=True)
    total_household_harvests = fields.Float('Total Harvest Quantity', store=True)
    total_sorting_lines = fields.Float('Total Harvest Quantity', store=True)
    completed_harvest_schedules = fields.Float('Total Completed', store=True)
    total_sorted_quantity = fields.Float('Total Sorted Quantity', store=True)
    total_waste_quantity = fields.Float('Total Waste Quantity', store=True)
    total_harvest_cost = fields.Monetary('Total Harvest Cost', currency_field='currency_id',
                                         compute='_compute_harvest_totals', store=True)
    total_harvest_revenue = fields.Monetary('Total Harvest Revenue', currency_field='currency_id',
                                            compute='_compute_harvest_totals', store=True)
    harvest_profit = fields.Monetary('Harvest Profit', currency_field='currency_id',
                                     compute='_compute_harvest_totals', store=True)
    harvest_efficiency_rate = fields.Float('Rate', store=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company, required=True)

    def _compute_harvest_totals(self):
        for project in self:
            project.total_harvest_quantity = sum(project.harvest_schedule_ids.mapped('actual_quantity'))
            project.total_harvest_cost = sum(project.harvest_schedule_ids.mapped('total_cost'))
            project.total_harvest_revenue = sum(project.harvest_schedule_ids.mapped('actual_revenue'))
            project.harvest_profit = project.total_harvest_revenue - project.total_harvest_cost

    def _compute_financial_totals(self):
        for project in self:
            project.actual_cost = sum(project.harvest_schedule_ids.mapped('total_cost'))
            project.total_revenue = sum(project.harvest_schedule_ids.mapped('actual_revenue'))
            project.total_profit = project.total_revenue - project.actual_cost

            if project.total_revenue > 0:
                project.profit_margin = (project.total_profit / project.total_revenue) * 100
            else:
                project.profit_margin = 0

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('agricultural.project') or _('New')
        return super(AgriculturalProject, self).create(vals)
class AgriculturalHarvestSchedule(models.Model):
    _inherit = 'agricultural.harvest.schedule'

    labor_cost = fields.Monetary('Cost Workers', currency_field='currency_id', tracking=True)
    equipment_cost = fields.Monetary('Cost Equipment', currency_field='currency_id', tracking=True)
    material_cost = fields.Monetary('Cost Materials', currency_field='currency_id', tracking=True)
    transport_cost = fields.Monetary('Cost Transfer', currency_field='currency_id', tracking=True)
    other_costs = fields.Monetary('Costs Other', currency_field='currency_id', tracking=True)
    total_cost = fields.Monetary('Total Cost', currency_field='currency_id',
                                 compute='_compute_costs', store=True, tracking=True)
    cost_per_unit = fields.Monetary('Cost per unit', currency_field='currency_id',
                                    compute='_compute_costs', store=True)
    grade_a_price = fields.Monetary('Grade Price A', currency_field='currency_id', default=0)
    grade_b_price = fields.Monetary('Grade Price B', currency_field='currency_id', default=0)
    grade_c_price = fields.Monetary('Grade Price C', currency_field='currency_id', default=0)
    estimated_revenue = fields.Monetary('Revenue Expected', currency_field='currency_id',
                                        compute='_compute_revenue', store=True)
    actual_revenue = fields.Monetary('Revenue Actual', currency_field='currency_id',
                                     compute='_compute_revenue', store=True)
    profit_margin = fields.Monetary('Margin Profit', currency_field='currency_id',
                                    compute='_compute_profitability', store=True)
    profit_margin_percent = fields.Float('Percentage Margin Profit (%)',
                                         compute='_compute_profitability', store=True)
    roi = fields.Float('Return on Investment (%)', compute='_compute_profitability', store=True)

    # ========== COMPUTE METHODS ==========
    @api.depends('actual_start_date', 'actual_end_date')
    def _compute_duration(self):
        for record in self:
            if record.actual_start_date and record.actual_end_date:
                delta = record.actual_end_date - record.actual_start_date
                record.duration_hours = delta.total_seconds() / 3600
            else:
                record.duration_hours = 0

    @api.depends('estimated_quantity', 'actual_quantity', 'grade_a_quantity',
                 'grade_b_quantity', 'grade_c_quantity', 'rejected_quantity')
    def _compute_quantities(self):
        for record in self:
            record.total_graded_quantity = (record.grade_a_quantity + record.grade_b_quantity +
                                            record.grade_c_quantity)
            record.quantity_difference = record.actual_quantity - record.estimated_quantity

            if record.estimated_quantity > 0:
                record.yield_efficiency = (record.actual_quantity / record.estimated_quantity) * 100
            else:
                record.yield_efficiency = 0

            if record.actual_quantity > 0:
                record.waste_percentage = (record.rejected_quantity / record.actual_quantity) * 100
            else:
                record.waste_percentage = 0

    @api.depends('labor_cost', 'equipment_cost', 'material_cost', 'transport_cost', 'other_costs', 'actual_quantity')
    def _compute_costs(self):
        for record in self:
            record.total_cost = (record.labor_cost + record.equipment_cost + record.material_cost +
                                 record.transport_cost + record.other_costs)

            if record.actual_quantity > 0:
                record.cost_per_unit = record.total_cost / record.actual_quantity
            else:
                record.cost_per_unit = 0

    @api.depends('grade_a_quantity', 'grade_b_quantity', 'grade_c_quantity',
                 'grade_a_price', 'grade_b_price', 'grade_c_price', 'estimated_quantity')
    def _compute_revenue(self):
        for record in self:
            record.actual_revenue = ((record.grade_a_quantity * record.grade_a_price) +
                                     (record.grade_b_quantity * record.grade_b_price) +
                                     (record.grade_c_quantity * record.grade_c_price))

            # Estimated revenue based on estimated quantity and average price
            avg_price = 0
            if record.grade_a_price or record.grade_b_price or record.grade_c_price:
                prices = [p for p in [record.grade_a_price, record.grade_b_price, record.grade_c_price] if p > 0]
                if prices:
                    avg_price = sum(prices) / len(prices)

            record.estimated_revenue = record.estimated_quantity * avg_price

    @api.depends('actual_revenue', 'total_cost')
    def _compute_profitability(self):
        for record in self:
            record.profit_margin = record.actual_revenue - record.total_cost

            if record.actual_revenue > 0:
                record.profit_margin_percent = (record.profit_margin / record.actual_revenue) * 100
            else:
                record.profit_margin_percent = 0

            if record.total_cost > 0:
                record.roi = (record.profit_margin / record.total_cost) * 100
            else:
                record.roi = 0

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('agricultural.harvest.schedule') or _('New')
        return super(AgriculturalHarvestSchedule, self).create(vals)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_start(self):
        self.write({
            'state': 'in_progress',
            'actual_start_date': fields.Datetime.now()
        })

    def action_complete(self):
        self.write({
            'state': 'completed',
            'actual_end_date': fields.Datetime.now()
        })
class HarvestBatch(models.Model):
    _inherit = 'harvest.batch'


    def _compute_totals(self):
        for batch in self:
            # Use sorting_line_ids which exists on harvest.batch
            batch.total_weight = batch.total_collection_qty or 0.0
            batch.sorted_weight = sum(batch.sorting_line_ids.mapped('final_weight'))
            batch.waste_weight = sum(batch.sorting_line_ids.mapped('waste_weight'))

    @api.depends('sorting_line_ids.total_amount')
    def _compute_financial(self):
        for batch in self:
            batch.batch_revenue = sum(batch.sorting_line_ids.mapped('total_amount'))
            # Cost calculation based on proportion of schedule cost
            if batch.schedule_id.total_cost and batch.schedule_id.actual_quantity > 0:
                cost_per_kg = batch.schedule_id.total_cost / batch.schedule_id.actual_quantity
                batch.batch_cost = batch.total_weight * cost_per_kg
            else:
                batch.batch_cost = 0

            batch.batch_profit = batch.batch_revenue - batch.batch_cost

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('harvest.batch') or _('New')
        return super(HarvestBatch, self).create(vals)

    def action_start_harvesting(self):
        self.state = 'harvesting'

    def action_complete_harvest(self):
        self.state = 'harvested'

    def action_start_sorting(self):
        self.state = 'sorting'

    def action_complete(self):
        self.state = 'completed'
        # Update parent schedule quantities
        self.schedule_id._update_from_batches()
class HouseholdHarvest(models.Model):
    _inherit = 'household.harvest'

    # ========== QUANTITIES ==========
    total_quantity = fields.Float('Quantity (kg)', required=True,
                                  digits='Product Unit of Measure', tracking=True)
    sorted_quantity = fields.Float('Sorted Quantity (kg)', compute='_compute_sorted_totals', store=True)
    waste_quantity = fields.Float('Waste Quantity (kg)', compute='_compute_sorted_totals', store=True)
    yield_rate = fields.Float('Yield Rate (%)', compute='_compute_sorted_totals', store=True)
    # ========== QUALITY ==========
    quality_rating = fields.Selection([
        ('1', 'Poor'), ('2', 'Fair'), ('3', 'Good'), ('4', 'Very Good'), ('5', 'Excellent')
    ], string='Quality Rating', default='3', tracking=True)
    moisture_content = fields.Float('Moisture Content (%)', help="Moisture percentage in harvest")
    temperature = fields.Float('Harvest Temperature (°C)')
    # ========== FINANCIAL ==========
    base_price_per_kg = fields.Monetary('Base Price per KG', currency_field='currency_id',
                                        help="Base price paid to household per kg")
    quality_bonus = fields.Monetary('Quality Bonus', currency_field='currency_id',
                                    compute='_compute_financial', store=True)
    # ========== COMPUTE METHODS ==========
    def _compute_sorted_totals(self):
        for record in self:
            record.sorted_quantity = sum(record.sorting_line_ids.mapped('final_weight'))
            record.waste_quantity = sum(record.sorting_line_ids.mapped('waste_weight'))

            if record.total_quantity > 0:
                record.yield_rate = (record.sorted_quantity / record.total_quantity) * 100
            else:
                record.yield_rate = 0
    @api.depends('total_quantity', 'base_price_per_kg', 'quality_rating')
    def _compute_financial(self):
        for record in self:
            base_amount = record.total_quantity * record.base_price_per_kg

            # Quality bonus calculation
            quality_multiplier = {
                '1': 0.0,  # Poor - no bonus
                '2': 0.05,  # Fair - 5% bonus
                '3': 0.10,  # Good - 10% bonus
                '4': 0.15,  # Very Good - 15% bonus
                '5': 0.20  # Excellent - 20% bonus
            }

            bonus_rate = quality_multiplier.get(record.quality_rating, 0.10)
            record.quality_bonus = base_amount * bonus_rate
    @api.depends('sorting_line_ids')
    def _compute_sorting_count(self):
        for record in self:
            record.sorting_count = len(record.sorting_line_ids)
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('household.harvest') or _('New')
        return super(HouseholdHarvest, self).create(vals)
    def action_weigh(self):
        self.state = 'weighed'
    def action_approve(self):
        self.state = 'approved'
    def action_mark_paid(self):
        pass
class AgriculturalProjectEx(models.Model):
    _inherit = 'agricultural.project'

    def _update_harvest_totals(self):
        """Update project harvest totals when schedules change"""
        for project in self:
            project._compute_harvest_totals()
            project._compute_financial_totals()

    def action_view_harvest_schedules(self):
        return {
            'name': _('Harvest Schedules'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.harvest.schedule',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }

