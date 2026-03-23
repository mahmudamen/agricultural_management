from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging

_logger = logging.getLogger(__name__)

class AgriculturalProject(models.Model):
    _name = 'agricultural.project'
    _description = 'Agricultural Project Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, priority desc'

    name = fields.Char('Project Name', required=True, translate=True, tracking=True, copy=False)
    code = fields.Char('Project Code', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner')
    description = fields.Text('Description', copy=False, translate=True)
    project_type = fields.Selection([
        ('crop_production', 'Crop Production'),
        ('livestock', 'Livestock'),
        ('greenhouse', 'Greenhouses'),
        ('irrigation', 'Irrigation Systems'),
        ('processing', 'Product Processing'),
        ('infrastructure', 'Infrastructure'),
        ('research', 'Research & Development'),
        ('mixed', 'Mixed Project')
    ], string='Project Type', required=True, default='crop_production', tracking=True)

    start_date = fields.Date('Start Date', required=True, tracking=True,
                             default=fields.Date.today, copy=False)
    end_date = fields.Date('Expected End Date', required=True, tracking=True,
                           default=lambda self: fields.Date.today() + relativedelta(months=6))
    actual_start_date = fields.Date('Actual Start Date', tracking=True, copy=False)
    actual_end_date = fields.Date('Actual End Date', tracking=True, copy=False)
    active = fields.Boolean(string="active", default=True)
    duration_months = fields.Integer('Duration (Months)', compute='_compute_duration', store=True)
    remaining_days = fields.Integer('Remaining Days', compute='_compute_remaining_days')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived')
    ], default='draft', tracking=True, copy=False, string='Status')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
        ('4', 'Critical')
    ], string="Priority", default='1', tracking=True)
    progress = fields.Float('Progress (%)', compute='_compute_progress', store=True)
    health_status = fields.Selection([
        ('green', 'Good'),
        ('yellow', 'Warning'),
        ('red', 'Critical Issues')
    ], string='Project Health', compute='_compute_health_status', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.company.currency_id, required=True)
    purchase_order_ids = fields.One2many('purchase.order','agricultural_project_id')
    total_budget = fields.Monetary('Total Budget', currency_field='currency_id',
                                   required=True, tracking=True)
    approved_budget = fields.Monetary('Approved Budget', currency_field='currency_id',
                                      tracking=True)
    allocated_budget = fields.Monetary('Allocated Budget', currency_field='currency_id',
                                       compute='_compute_financial_data', store=True)
    actual_cost = fields.Monetary('Actual Cost', currency_field='currency_id',
                                  compute='_compute_financial_data', store=True)
    committed_cost = fields.Monetary('Committed Cost', currency_field='currency_id',
                                     compute='_compute_financial_data', store=True)
    pending_cost = fields.Monetary('Cost On Hold', currency_field='currency_id',
                                   compute='_compute_financial_data', store=True)
    remaining_budget = fields.Monetary('Budget Remaining', currency_field='currency_id',
                                       compute='_compute_financial_data', store=True)
    budget_variance = fields.Monetary('Deviation Budget', currency_field='currency_id',
                                      compute='_compute_financial_data', store=True)
    budget_utilization = fields.Float('Usage Budget (%)',
                                      compute='_compute_financial_data', store=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company, required=True)
    farm_id = fields.Many2one('agricultural.farm', 'Farm', tracking=True)
    location_ids = fields.Many2many('agricultural.farm', string='Locations')
    manager_id = fields.Many2one('hr.employee', 'Manager Project', required=True, tracking=True)
    customer_id = fields.Many2one('res.partner', 'Customer')
    current_approver_id = fields.Many2one('hr.employee', string='Current Approver')
    approval_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', compute='_compute_approval_status', store=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Account Analytic',
                                          copy=False, tracking=True)
    analytic_line_ids = fields.One2many('account.analytic.account','project_id', 'Account Analytic',
                                          copy=False, tracking=True)
    team_member_ids = fields.Many2many(
        'hr.employee',
        string='Team Members',  # Only employees from the same company
    )
    agricultural_engineer_id = fields.Many2one('hr.employee', string='Agricultural Engineer')
    financial_controller_id = fields.Many2one('hr.employee', string='Financial Controller')
    total_production_requests = fields.Integer('Total Production Requests', default=0)
    pending_production_requests = fields.Integer('Pending Production Requests', default=0)
    completed_production_requests = fields.Integer('Completed Production Requests', default=0)
    planned_budget = fields.Monetary('Planned Budget', currency_field='currency_id')
    planned_profit = fields.Monetary('Planned Profit', currency_field='currency_id')
    actual_profit = fields.Monetary('Actual Profit', currency_field='currency_id')
    total_revenue = fields.Monetary('Total Revenue', currency_field='currency_id')
    material_cost = fields.Monetary('Material Cost', currency_field='currency_id')
    labor_cost = fields.Monetary('Labor Cost', currency_field='currency_id')
    equipment_cost = fields.Monetary('Equipment Cost', currency_field='currency_id')
    overhead_cost = fields.Monetary('Overhead Cost', currency_field='currency_id')
    expected_revenue = fields.Monetary('Expected Revenue', currency_field='currency_id')
    actual_revenue = fields.Monetary('Actual Revenue', currency_field='currency_id')
    expected_profit = fields.Monetary('Expected Profit', currency_field='currency_id',
                                      compute='_compute_expected_profit', store=True)
    profit_margin = fields.Float('Profit Margin (%)', compute='_compute_profit_margin', store=True)
    roi = fields.Float('ROI (%)', compute='_compute_roi', store=True)
    total_operations = fields.Integer('Total Operations', default=0)
    pending_operations = fields.Integer('Pending Operations', default=0)
    in_progress_operations = fields.Integer('In Progress Operations', default=0)
    completed_operations = fields.Integer('Completed Operations', default=0)
    cancelled_operations = fields.Integer('Cancelled Operations', default=0)
    # Yield tracking (ADD THESE)
    expected_yield = fields.Float('Expected Yield', help='Expected production yield for this project')
    actual_yield = fields.Float('Actual Yield', help='Actual production yield achieved')
    total_yield = fields.Float('Total Yield', compute='_compute_total_yield', store=True, help='Computed total yield')
    yield_unit = fields.Selection([
        ('kg', 'Kilograms'),
        ('tons', 'Tons'),
        ('liters', 'Liters'),
        ('pieces', 'Pieces'),
        ('boxes', 'Boxes'),
        ('bags', 'Bags'),
    ], string='Yield Unit', default='kg')
    yield_variance = fields.Float('Yield Variance', compute='_compute_yield_variance', store=True)
    yield_achievement_rate = fields.Float('Yield Achievement Rate (%)', compute='_compute_yield_achievement_rate',
                                          store=True)
    production_request_ids = fields.One2many('agricultural.production.request', 'project_id',
                                             string='Production Requests')
    total_purchase_orders = fields.Integer('Total Purchase Orders', compute='_compute_purchase_orders', store=True)
    pending_purchase_orders = fields.Integer('Pending Purchase Orders', compute='_compute_purchase_orders', store=True)
    confirmed_purchase_orders = fields.Integer('Confirmed Purchase Orders', compute='_compute_purchase_orders',
                                               store=True)
    received_purchase_orders = fields.Integer('Received Purchase Orders', compute='_compute_purchase_orders',
                                              store=True)
    approved_production_requests = fields.Integer('Approved Production Requests', default=0)  # ADD THIS
    rejected_production_requests = fields.Integer('Rejected Production Requests', default=0)  # Additional field
    preferred_vendor_id = fields.Many2one('res.partner', string='Preferred Vendor',
                                          domain="[('is_company', '=', True), ('supplier_rank', '>', 0)]")
    vendor_ids = fields.Many2many('res.partner', 'agricultural_project_vendor_rel', 'project_id', 'vendor_id',
                                  string='Approved Vendors',
                                  domain="[('is_company', '=', True), ('supplier_rank', '>', 0)]")
    # Purchase and Procurement
    total_purchase_amount = fields.Monetary('Total Purchase Amount', currency_field='currency_id',
                                            compute='_compute_purchase_amounts', store=True)
    pending_purchase_amount = fields.Monetary('Pending Purchase Amount', currency_field='currency_id',
                                              compute='_compute_purchase_amounts', store=True)
    confirmed_purchase_amount = fields.Monetary('Confirmed Purchase Amount', currency_field='currency_id',
                                                compute='_compute_purchase_amounts', store=True)
    received_purchase_amount = fields.Monetary('Received Purchase Amount', currency_field='currency_id',
                                               compute='_compute_purchase_amounts', store=True)
    total_rfqs = fields.Integer('Total RFQs', compute='_compute_rfqs', store=True)
    # Vendor performance tracking
    vendor_performance_rating = fields.Float('Vendor Performance Rating', compute='_compute_vendor_performance',
                                             store=True)
    total_vendors = fields.Integer('Total Vendors', compute='_compute_vendor_stats', store=True)
    # Inventory and Stock
    total_stock_moves = fields.Integer('Total Stock Moves', compute='_compute_stock_moves', store=True)
    pending_stock_moves = fields.Integer('Pending Stock Moves', compute='_compute_stock_moves', store=True)
    consumed_materials = fields.Monetary('Consumed Materials', currency_field='currency_id',
                                         compute='_compute_consumed_materials', store=True)
    remaining_materials = fields.Monetary('Remaining Materials', currency_field='currency_id',
                                          compute='_compute_remaining_materials', store=True)
    # Analytics and Performance
    cost_efficiency = fields.Float('Cost Efficiency (%)', compute='_compute_cost_efficiency', store=True)
    time_efficiency = fields.Float('Time Efficiency (%)', compute='_compute_time_efficiency', store=True)
    quality_score = fields.Float('Quality Score', compute='_compute_quality_score', store=True)
    overall_efficiency = fields.Float('Overall Efficiency (%)', compute='_compute_overall_efficiency', store=True)
    milestone_completion_rate = fields.Float('Milestone Completion Rate (%)',
                                             compute='_compute_milestone_completion_rate', store=True)
    compliance_rate = fields.Float('Compliance Rate (%)', default=100.0)
    yield_efficiency = fields.Float('Yield Efficiency (%)', compute='_compute_yield_efficiency', store=True)
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='low', string='Risk Level')
    next_milestone_id = fields.Many2one('project.milestone', string='Next Milestone')
    last_report_date = fields.Date('Last Report Date')
    dashboard_data = fields.Text('Dashboard Data')  # JSON data for charts
    # Analytic Accounting
    cost_center_ids = fields.Many2many('account.analytic.account', 'project_cost_center_rel', 'project_id',
                                       'account_id', string='Cost Centers')
    requires_approval = fields.Boolean('Requires Approval', compute='_compute_requires_approval', store=True)
    approval_comments = fields.Text('Approval Comments')
    attachment_ids = fields.Many2many('ir.attachment', 'agricultural_project_attachment_rel', 'project_id',
                                      'attachment_id', string='Attachments')
    approval_deadline = fields.Date('Approval Deadline')
    last_approval_reminder = fields.Datetime('Last Approval Reminder')
    auto_reminder_enabled = fields.Boolean('Auto Reminder Enabled', default=True)
    reminder_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], default='weekly', string='Reminder Frequency')
    approval_duration_days = fields.Integer('Approval Duration (Days)', compute='_compute_approval_duration',
                                            store=True)
    total_approvers = fields.Integer('Total Approvers', compute='_compute_approval_stats', store=True)
    approved_count = fields.Integer('Approved Count', compute='_compute_approval_stats', store=True)
    rejected_count = fields.Integer('Rejected Count', compute='_compute_approval_stats', store=True)
    # One2many Relations
    stock_move_ids = fields.One2many('stock.move', 'agricultural_project_id', string='Stock Moves')
    stock_picking_ids = fields.One2many('stock.picking', 'agricultural_project_id', string='Stock Pickings')
    household_harvest_id = fields.Many2one('household.harvest', 'Household Harvest')

    def action_request_revision(self):
        pass
    def action_reject_project(self):
        pass
    def action_approve_project(self):
        pass
    def action_submit_for_approval(self):
        pass

    def action_view_analytic_lines(self):
        pass
    def _compute_rfqs(self):
        pass
    def _compute_stock_moves(self):
        pass
    def _compute_approval_duration(self):
        pass
    def _compute_approval_stats(self):
        pass
    def _compute_consumed_materials(self):
        pass
    def _compute_remaining_materials(self):
        pass
    def _compute_requires_approval(self):
        pass
    def _compute_cost_efficiency(self):
        pass
    def _compute_time_efficiency(self):
        pass
    def _compute_quality_score(self):
        pass
    def _compute_overall_efficiency(self):
        pass
    def _compute_milestone_completion_rate(self):
        pass
    def _compute_yield_efficiency(self):
        pass

    # Action methods to manage vendors
    def action_add_vendor(self):
        return {
            'name': 'Add Vendor',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_is_company': True,
                'default_supplier_rank': 1,
            }
        }
    def action_view_purchase_orders(self):
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('agricultural_project_id', '=', self.id)],
            'context': {
                'default_agricultural_project_id': self.id,
            }
        }
    # Computed methods for purchase orders
    @api.depends('purchase_order_ids', 'purchase_order_ids.state')
    def _compute_purchase_orders(self):
        for record in self:
            orders = record.purchase_order_ids
            record.total_purchase_orders = len(orders)
            record.pending_purchase_orders = len(orders.filtered(lambda o: o.state in ['draft', 'sent']))
            record.confirmed_purchase_orders = len(orders.filtered(lambda o: o.state == 'purchase'))
            record.received_purchase_orders = len(orders.filtered(lambda o: o.state == 'done'))
    # Computed methods for purchase amounts
    @api.depends('purchase_order_ids', 'purchase_order_ids.amount_total', 'purchase_order_ids.state')
    def _compute_purchase_amounts(self):
        for record in self:
            orders = record.purchase_order_ids
            record.total_purchase_amount = sum(orders.mapped('amount_total'))
            record.pending_purchase_amount = sum(
                orders.filtered(lambda o: o.state in ['draft', 'sent']).mapped('amount_total'))
            record.confirmed_purchase_amount = sum(
                orders.filtered(lambda o: o.state == 'purchase').mapped('amount_total'))
            record.received_purchase_amount = sum(orders.filtered(lambda o: o.state == 'done').mapped('amount_total'))
    # Vendor statistics
    @api.depends('vendor_ids')
    def _compute_vendor_stats(self):
        for record in self:
            record.total_vendors = len(record.vendor_ids)
    # Vendor performance (you can customize this logic)
    @api.depends('purchase_order_ids', 'purchase_order_ids.state')
    def _compute_vendor_performance(self):
        for record in self:
            orders = record.purchase_order_ids
            if orders:
                completed_orders = orders.filtered(lambda o: o.state == 'done')
                if len(orders) > 0:
                    record.vendor_performance_rating = (len(completed_orders) / len(orders)) * 100
                else:
                    record.vendor_performance_rating = 0.0
            else:
                record.vendor_performance_rating = 0.0
    @api.depends('purchase_order_ids', 'purchase_order_ids.state')
    def _compute_purchase_orders(self):
        for record in self:
            orders = record.purchase_order_ids
            record.total_purchase_orders = len(orders)
            record.pending_purchase_orders = len(orders.filtered(lambda o: o.state in ['draft', 'sent']))
            record.confirmed_purchase_orders = len(orders.filtered(lambda o: o.state == 'purchase'))
            record.received_purchase_orders = len(orders.filtered(lambda o: o.state == 'done'))
    @api.depends('actual_yield')
    def _compute_total_yield(self):
        for record in self:
            # You can customize this logic based on your requirements
            # For now, total_yield is the same as actual_yield
            record.total_yield = record.actual_yield
    @api.depends('expected_yield', 'actual_yield')
    def _compute_yield_variance(self):
        for record in self:
            record.yield_variance = (record.actual_yield or 0) - (record.expected_yield or 0)
    @api.depends('expected_yield', 'actual_yield')
    def _compute_yield_achievement_rate(self):
        for record in self:
            if record.expected_yield > 0:
                record.yield_achievement_rate = (record.actual_yield / record.expected_yield) * 100
            else:
                record.yield_achievement_rate = 0.0
    @api.depends('production_request_ids', 'production_request_ids.state')
    def _compute_production_requests(self):
        for record in self:
            requests = record.production_request_ids
            record.total_production_requests = len(requests)
            record.pending_production_requests = len(requests.filtered(lambda r: r.state == 'pending'))
            record.in_progress_production_requests = len(requests.filtered(lambda r: r.state == 'in_progress'))
            record.completed_production_requests = len(requests.filtered(lambda r: r.state == 'completed'))
    @api.depends('expected_revenue', 'planned_budget')
    def _compute_planned_profit(self):
        for record in self:
            record.planned_profit = (record.expected_revenue or 0) - (record.planned_budget or 0)
    @api.depends('actual_revenue', 'actual_cost')
    def _compute_actual_profit(self):
        for record in self:
            record.actual_profit = (record.actual_revenue or 0) - (record.actual_cost or 0)
    @api.depends('expected_revenue', 'actual_cost')
    def _compute_expected_profit(self):
        for record in self:
            record.expected_profit = (record.expected_revenue or 0) - (record.actual_cost or 0)
    @api.depends('actual_profit', 'actual_revenue')
    def _compute_profit_margin(self):
        for record in self:
            if record.actual_revenue:
                record.profit_margin = (record.actual_profit / record.actual_revenue) * 100
            else:
                record.profit_margin = 0.0
    @api.depends('actual_profit', 'actual_cost')
    def _compute_roi(self):
        for record in self:
            if record.actual_cost:
                record.roi = (record.actual_profit / record.actual_cost) * 100
            else:
                record.roi = 0.0
    @api.depends('planned_material_cost', 'planned_labor_cost', 'planned_equipment_cost', 'planned_overhead_cost')
    def _compute_total_planned_cost(self):
        for record in self:
            record.total_planned_cost = (
                    (record.planned_material_cost or 0) +
                    (record.planned_labor_cost or 0) +
                    (record.planned_equipment_cost or 0) +
                    (record.planned_overhead_cost or 0)
            )
    @api.depends('actual_cost', 'pending_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = (record.actual_cost or 0) + (record.pending_cost or 0)
    @api.depends('planned_material_cost', 'material_cost', 'planned_labor_cost', 'labor_cost',
                 'planned_equipment_cost', 'equipment_cost', 'planned_overhead_cost', 'overhead_cost')
    def _compute_cost_variances(self):
        for record in self:
            record.material_variance = (record.material_cost or 0) - (record.planned_material_cost or 0)
            record.labor_variance = (record.labor_cost or 0) - (record.planned_labor_cost or 0)
            record.equipment_variance = (record.equipment_cost or 0) - (record.planned_equipment_cost or 0)
            record.overhead_variance = (record.overhead_cost or 0) - (record.planned_overhead_cost or 0)
    @api.depends('material_cost', 'labor_cost', 'equipment_cost', 'overhead_cost', 'pending_cost')
    def _compute_actual_cost(self):
        for record in self:
            record.actual_cost = (
                    (record.material_cost or 0) +
                    (record.labor_cost or 0) +
                    (record.equipment_cost or 0) +
                    (record.overhead_cost or 0) +
                    (record.pending_cost or 0)
            )
    @api.depends('state')
    def _compute_approval_status(self):
        for record in self:
            if record.state in ['draft', 'under_review']:
                record.approval_status = 'pending'
            elif record.state in ['approved', 'active', 'completed']:
                record.approval_status = 'approved'
            else:
                record.approval_status = 'rejected'
    def action_submit_for_review(self):
        """Submit project for review"""
        for record in self:
            record.state = 'under_review'
        return True
    def action_approve(self):
        """Approve the project"""
        for record in self:
            record.state = 'approved'
        return True
    def action_cancel(self):
        """Approve the project"""
        for record in self:
            record.state = 'cancelled'
        return True
    def action_start_project(self):
        """Start the project"""
        for record in self:
            record.state = 'active'
        return True
    def action_complete_project(self):
        """Complete the project"""
        for record in self:
            record.state = 'completed'
        return True
    @api.depends('rfq_ids.state')
    def _compute_rfq_statistics(self):
        """Calculate RFQ statistics"""
        for project in self:
            try:
                if hasattr(project, 'rfq_ids'):
                    rfqs = project.rfq_ids
                    project.total_rfqs = len(rfqs)
                    project.active_rfqs = len(rfqs.filtered(lambda r: r.state in ['draft', 'in_progress', 'open']))
                else:
                    project.total_rfqs = 0
                    project.active_rfqs = 0
            except Exception as e:
                _logger.error(f"Error computing RFQ statistics for project {project.id}: {e}")
                project.total_rfqs = 0
                project.active_rfqs = 0
    @api.depends('stock_move_ids.state', 'stock_picking_ids.state')
    def _compute_stock_statistics(self):
        """Calculate stock movement statistics"""
        for project in self:
            try:
                if hasattr(project, 'stock_move_ids'):
                    stock_moves = project.stock_move_ids
                    project.total_stock_moves = len(stock_moves)
                    project.pending_stock_moves = len(
                        stock_moves.filtered(lambda sm: sm.state not in ['done', 'cancel'])
                    )
                else:
                    project.total_stock_moves = 0
                    project.pending_stock_moves = 0

                if hasattr(project, 'stock_picking_ids'):
                    pickings = project.stock_picking_ids
                    project.total_pickings = len(pickings)
                else:
                    project.total_pickings = 0
            except Exception as e:
                _logger.error(f"Error computing stock statistics for project {project.id}: {e}")
                project.total_stock_moves = 0
                project.pending_stock_moves = 0
                project.total_pickings = 0
    @api.depends('stock_move_ids.state', 'stock_move_ids.value')
    def _compute_material_consumption(self):
        """Calculate material consumption"""
        for project in self:
            try:
                project.consumed_materials = 0.0
                project.remaining_materials = 0.0

                if hasattr(project, 'stock_move_ids'):
                    # Calculate consumed materials
                    consumed_moves = project.stock_move_ids.filtered(
                        lambda sm: sm.state == 'done' and
                                   sm.location_dest_id.usage in ['production', 'consume']
                    )
                    project.consumed_materials = sum(consumed_moves.mapped('value'))

                    # Calculate remaining materials in inventory
                    remaining_moves = project.stock_move_ids.filtered(
                        lambda sm: sm.state == 'done' and
                                   sm.location_dest_id.usage == 'internal'
                    )
                    incoming_materials = sum(remaining_moves.mapped('value'))
                    project.remaining_materials = max(0, incoming_materials - project.consumed_materials)

            except Exception as e:
                _logger.error(f"Error computing material consumption for project {project.id}: {e}")
                project.consumed_materials = 0.0
                project.remaining_materials = 0.0
    @api.depends('harvest_record_ids.quantity')
    def _compute_harvest_data(self):
        """Calculate harvest data"""
        for project in self:
            try:
                if hasattr(project, 'harvest_record_ids'):
                    project.total_yield = sum(project.harvest_record_ids.mapped('quantity'))

                    # Calculate yield efficiency if expected yield is set
                    if hasattr(project, 'expected_yield') and project.expected_yield > 0:
                        project.yield_efficiency = (project.total_yield / project.expected_yield) * 100
                    else:
                        project.yield_efficiency = 0.0
                else:
                    project.total_yield = 0.0
                    project.yield_efficiency = 0.0
            except Exception as e:
                _logger.error(f"Error computing harvest data for project {project.id}: {e}")
                project.total_yield = 0.0
                project.yield_efficiency = 0.0
    @api.depends('state', 'total_budget')
    def _compute_approval_requirements(self):
        """Check if approval is required"""
        for project in self:
            try:
                # Get approval limit from company settings
                approval_limit = getattr(self.env.company, 'project_approval_limit', 50000)

                # Define approval requirements based on budget and state
                project.requires_approval = (
                        project.state in ['submitted', 'under_review'] or
                        project.total_budget > approval_limit
                )
            except Exception as e:
                _logger.error(f"Error computing approval requirements for project {project.id}: {e}")
                project.requires_approval = False
    @api.depends('approval_ids', 'state', 'requires_approval')
    def _compute_current_approver(self):
        """Get current approver based on workflow"""
        for project in self:
            try:
                if project.requires_approval and project.state == 'under_review':
                    project.current_approver_id = project._get_next_approver()
                else:
                    project.current_approver_id = False
            except Exception as e:
                _logger.error(f"Error computing current approver for project {project.id}: {e}")
                project.current_approver_id = False
    def _get_next_approver(self):
        """Get next approver in the workflow"""
        try:
            # Multi-level approval workflow based on budget
            if self.total_budget > 500000:
                # High-value projects need CEO approval
                ceo_group = self.env.ref('agricultural_management.group_project_ceo', raise_if_not_found=False)
                if ceo_group and ceo_group.users:
                    return ceo_group.users[0].employee_id
            elif self.total_budget > 100000:
                # Medium-value projects need senior manager approval
                senior_manager_group = self.env.ref('agricultural_management.group_project_senior_manager',
                                                    raise_if_not_found=False)
                if senior_manager_group and senior_manager_group.users:
                    return senior_manager_group.users[0].employee_id

            # Default to project manager
            return self.manager_id
        except Exception as e:
            _logger.error(f"Error getting next approver for project {self.id}: {e}")
            return self.manager_id
    @api.depends('risk_ids.impact', 'risk_ids.probability', 'risk_ids.state')
    def _compute_risk_level(self):
        """Calculate overall project risk level"""
        for project in self:
            try:
                if hasattr(project, 'risk_ids') and project.risk_ids:
                    active_risks = project.risk_ids.filtered(lambda r: r.state == 'active')

                    if not active_risks:
                        project.risk_level = 'low'
                        continue

                    # Calculate risk scores (impact × probability)
                    risk_scores = []
                    for risk in active_risks:
                        impact = getattr(risk, 'impact', 1)  # 1-5 scale
                        probability = getattr(risk, 'probability', 1)  # 1-5 scale
                        risk_scores.append(impact * probability)

                    max_risk = max(risk_scores)
                    avg_risk = sum(risk_scores) / len(risk_scores)

                    # Determine overall risk level
                    if max_risk >= 20 or avg_risk >= 15:
                        project.risk_level = 'critical'
                    elif max_risk >= 15 or avg_risk >= 12:
                        project.risk_level = 'high'
                    elif max_risk >= 10 or avg_risk >= 8:
                        project.risk_level = 'medium'
                    else:
                        project.risk_level = 'low'
                else:
                    project.risk_level = 'low'
            except Exception as e:
                _logger.error(f"Error computing risk level for project {project.id}: {e}")
                project.risk_level = 'low'
    @api.depends('milestone_ids.state', 'milestone_ids.completion_date')
    def _compute_milestone_progress(self):
        """Calculate milestone progress"""
        for project in self:
            try:
                if hasattr(project, 'milestone_ids') and project.milestone_ids:
                    total_milestones = len(project.milestone_ids)
                    completed_milestones = len(project.milestone_ids.filtered(lambda m: m.state == 'completed'))

                    project.milestone_completion_rate = (
                                completed_milestones / total_milestones * 100) if total_milestones > 0 else 0.0

                    # Find next milestone
                    upcoming_milestones = project.milestone_ids.filtered(
                        lambda m: m.state in ['draft', 'in_progress'] and m.planned_date
                    ).sorted('planned_date')
                    project.next_milestone_id = upcoming_milestones[0].id if upcoming_milestones else False
                else:
                    project.milestone_completion_rate = 0.0
                    project.next_milestone_id = False
            except Exception as e:
                _logger.error(f"Error computing milestone progress for project {project.id}: {e}")
                project.milestone_completion_rate = 0.0
                project.next_milestone_id = False
    @api.depends('actual_profit', 'total_budget', 'progress', 'duration_months', 'actual_cost')
    def _compute_performance_kpis(self):
        """Calculate performance KPIs"""
        for project in self:
            try:
                # ROI calculation (Return on Investment)
                if project.total_budget > 0:
                    project.roi = (project.actual_profit / project.total_budget) * 100
                else:
                    project.roi = 0.0

                # Cost efficiency (Budget vs Actual Cost)
                if project.total_budget > 0:
                    project.cost_efficiency = ((
                                                           project.total_budget - project.actual_cost) / project.total_budget) * 100
                else:
                    project.cost_efficiency = 0.0

                # Time efficiency (Progress vs Time Elapsed)
                time_progress = project._calculate_time_based_progress()
                if time_progress > 0:
                    project.time_efficiency = min(100.0, (project.progress / time_progress) * 100)
                else:
                    project.time_efficiency = 100.0

                # Overall efficiency score
                project.overall_efficiency = (project.cost_efficiency + project.time_efficiency + max(0,
                                                                                                      project.roi)) / 3

            except Exception as e:
                _logger.error(f"Error computing performance KPIs for project {project.id}: {e}")
                project.roi = 0.0
                project.cost_efficiency = 0.0
                project.time_efficiency = 100.0
                project.overall_efficiency = 0.0
    @api.depends('report_ids.create_date')
    def _compute_report_data(self):
        """Calculate report data"""
        for project in self:
            try:
                if hasattr(project, 'report_ids') and project.report_ids:
                    latest_report = project.report_ids.sorted('create_date', reverse=True)[:1]
                    project.last_report_date = latest_report.create_date.date() if latest_report else False
                else:
                    project.last_report_date = False
            except Exception as e:
                _logger.error(f"Error computing report data for project {project.id}: {e}")
                project.last_report_date = False
    @api.depends(
        'progress', 'health_status', 'budget_utilization', 'roi',
        'cost_efficiency', 'time_efficiency', 'remaining_days',
        'total_operations', 'completed_operations', 'quality_score',
        'milestone_completion_rate', 'risk_level'
    )
    def _compute_dashboard_data(self):
        """Prepare comprehensive dashboard data as JSON"""
        for project in self:
            try:
                dashboard_info = {
                    # Basic metrics
                    'progress': round(project.progress, 2),
                    'health_status': project.health_status,
                    'budget_utilization': round(project.budget_utilization, 2),
                    'remaining_days': project.remaining_days,
                    'state': project.state,

                    # Financial metrics
                    'roi': round(project.roi, 2),
                    'cost_efficiency': round(project.cost_efficiency, 2),
                    'actual_cost': float(project.actual_cost),
                    'total_budget': float(project.total_budget),
                    'remaining_budget': float(project.remaining_budget),
                    'profit_margin': round(project.profit_margin, 2),

                    # Performance metrics
                    'time_efficiency': round(project.time_efficiency, 2),
                    'overall_efficiency': round(getattr(project, 'overall_efficiency', 0), 2),
                    'quality_score': round(project.quality_score, 2),

                    # Activity metrics
                    'total_operations': project.total_operations,
                    'completed_operations': project.completed_operations,
                    'operations_completion_rate': round(
                        (
                                    project.completed_operations / project.total_operations * 100) if project.total_operations > 0 else 0,
                        2
                    ),

                    # Milestone metrics
                    'milestone_completion_rate': round(getattr(project, 'milestone_completion_rate', 0), 2),

                    # Risk and alerts
                    'risk_level': getattr(project, 'risk_level', 'low'),
                    'alerts': project._generate_dashboard_alerts(),

                    # Dates
                    'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
                    'end_date': project.end_date.strftime('%Y-%m-%d') if project.end_date else None,
                    'duration_months': project.duration_months,
                }

                project.dashboard_data = json.dumps(dashboard_info, ensure_ascii=False)

            except Exception as e:
                _logger.error(f"Error computing dashboard data for project {project.id}: {e}")
                project.dashboard_data = json.dumps({
                    'progress': 0,
                    'health_status': 'green',
                    'budget_utilization': 0,
                    'remaining_days': 0,
                    'error': 'Dashboard data computation failed'
                })
    def _generate_dashboard_alerts(self):
        """Generate alerts for dashboard"""
        alerts = []

        try:
            # Budget alerts
            if self.budget_utilization > 90:
                alerts.append({
                    'type': 'warning' if self.budget_utilization <= 100 else 'danger',
                    'message': f"Budget utilization is {self.budget_utilization:.1f}%",
                    'icon': 'fa-exclamation-triangle'
                })

            # Timeline alerts
            if self.remaining_days < 0:
                alerts.append({
                    'type': 'danger',
                    'message': f"Project is {abs(self.remaining_days)} days overdue",
                    'icon': 'fa-clock'
                })
            elif self.remaining_days < 7 and self.progress < 90:
                alerts.append({
                    'type': 'warning',
                    'message': f"Only {self.remaining_days} days remaining",
                    'icon': 'fa-clock'
                })

            # Progress alerts
            time_progress = self._calculate_time_based_progress()
            if self.progress < time_progress - 20:
                alerts.append({
                    'type': 'danger',
                    'message': "Project significantly behind schedule",
                    'icon': 'fa-chart-line'
                })

            # Quality alerts
            if hasattr(self, 'quality_score') and self.quality_score < 70:
                alerts.append({
                    'type': 'warning',
                    'message': f"Quality score is low: {self.quality_score:.1f}%",
                    'icon': 'fa-star'
                })

        except Exception as e:
            _logger.error(f"Error generating dashboard alerts for project {self.id}: {e}")

        return alerts
    def agricultural_production_request_action(self):
        """Open production requests view for this project"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Requests'),
            'res_model': 'agricultural.production.request',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
    def action_view_purchases(self):
        """View project purchase orders"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('agricultural_project_id', '=', self.id)],
            'context': {'default_agricultural_project_id': self.id},
        }
    def refresh_dashboard_data(self):
        """Manual refresh of dashboard data"""
        self._compute_dashboard_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        """Calculate project duration in months"""
        for project in self:
            try:
                if project.start_date and project.end_date:
                    delta = relativedelta(project.end_date, project.start_date)
                    project.duration_months = delta.months + (delta.years * 12)
                    if delta.days > 0:  # Add partial month if there are extra days
                        project.duration_months += 1
                else:
                    project.duration_months = 0
            except Exception as e:
                _logger.error(f"Error computing duration for project {project.id}: {e}")
                project.duration_months = 0
    @api.depends('end_date', 'state')
    def _compute_remaining_days(self):
        """Calculate remaining days"""
        for project in self:
            try:
                if project.end_date and project.state not in ['completed', 'cancelled', 'archived']:
                    today = fields.Date.today()
                    if project.end_date >= today:
                        project.remaining_days = (project.end_date - today).days
                    else:
                        project.remaining_days = (project.end_date - today).days  # Negative for overdue
                else:
                    project.remaining_days = 0
            except Exception as e:
                _logger.error(f"Error computing remaining days for project {project.id}: {e}")
                project.remaining_days = 0
    @api.depends('start_date', 'end_date', 'state', 'actual_start_date', 'actual_end_date')
    def _compute_progress(self):
        """Calculate project progress based on various factors"""
        for project in self:
            try:
                total_progress = 0.0
                weight_sum = 0.0

                # If project is completed, progress is 100%
                if project.state in ['completed', 'archived']:
                    project.progress = 100.0
                    continue

                # If project hasn't started, progress is 0%
                if project.state in ['draft', 'submitted', 'under_review']:
                    project.progress = 0.0
                    continue



                # Production requests progress (30% weight)
                requests_weight = 30.0
                if hasattr(project, 'production_request_ids') and project.production_request_ids:
                    requests_completed = project.production_request_ids.filtered(
                        lambda r: r.state in ['completed', 'delivered', 'done']
                    )
                    if len(project.production_request_ids) > 0:
                        requests_progress = (len(requests_completed) / len(project.production_request_ids)) * 100
                        total_progress += requests_progress * requests_weight
                        weight_sum += requests_weight

                # Milestones progress (30% weight)
                milestones_weight = 30.0
                if hasattr(project, 'milestone_ids') and project.milestone_ids:
                    milestones_completed = project.milestone_ids.filtered(lambda m: m.state == 'completed')
                    if len(project.milestone_ids) > 0:
                        milestones_progress = (len(milestones_completed) / len(project.milestone_ids)) * 100
                        total_progress += milestones_progress * milestones_weight
                        weight_sum += milestones_weight

                # Purchase orders progress (bonus weight if exists)
                if hasattr(project, 'purchase_order_ids') and project.purchase_order_ids:
                    purchase_weight = 20.0
                    completed_pos = project.purchase_order_ids.filtered(lambda po: po.state == 'done')
                    if len(project.purchase_order_ids) > 0:
                        po_progress = (len(completed_pos) / len(project.purchase_order_ids)) * 100
                        total_progress += po_progress * purchase_weight
                        weight_sum += purchase_weight

                # Calculate weighted average progress
                if weight_sum > 0:
                    project.progress = min(100.0, total_progress / weight_sum)
                else:
                    # Fallback: use time-based progress if no activities exist
                    project.progress = project._calculate_time_based_progress()

            except Exception as e:
                _logger.error(f"Error computing progress for project {project.id}: {e}")
                project.progress = project._calculate_time_based_progress()
    def _calculate_time_based_progress(self):
        """Calculate progress based on time elapsed"""
        try:
            if not self.start_date or not self.end_date:
                return 0.0

            # Use actual start date if available
            start_date = self.actual_start_date or self.start_date
            today = fields.Date.today()

            if today <= start_date:
                return 0.0
            elif today >= self.end_date:
                return 100.0
            else:
                total_days = (self.end_date - start_date).days
                elapsed_days = (today - start_date).days
                return min(100.0, max(0.0, (elapsed_days / total_days) * 100))
        except Exception as e:
            _logger.error(f"Error calculating time-based progress for project {self.id}: {e}")
            return 0.0
    @api.depends('progress', 'budget_utilization', 'remaining_days', 'state')
    def _compute_health_status(self):
        """Compute project health status based on multiple indicators"""
        for project in self:
            try:
                # If project is completed or cancelled, status is neutral
                if project.state in ['completed', 'cancelled', 'archived']:
                    project.health_status = 'green'
                    continue

                red_flags = 0
                yellow_flags = 0

                # Progress vs Time Check
                time_progress = project._calculate_time_based_progress()
                progress_variance = project.progress - time_progress

                if progress_variance < -25:  # Very behind schedule
                    red_flags += 2
                elif progress_variance < -15:  # Moderately behind
                    red_flags += 1
                elif progress_variance < -10:  # Slightly behind
                    yellow_flags += 1

                # Budget Utilization Check
                if project.budget_utilization > 100:  # Over budget
                    red_flags += 2
                elif project.budget_utilization > 90 and project.progress < 80:  # High budget use with low progress
                    red_flags += 1
                elif project.budget_utilization > 80 and project.progress < 70:  # Medium budget concern
                    yellow_flags += 1

                # Timeline Check
                if project.remaining_days < -7:  # Overdue by more than a week
                    red_flags += 2
                elif project.remaining_days < 0:  # Overdue
                    red_flags += 1
                elif project.remaining_days < 7 and project.progress < 90:  # Tight deadline
                    yellow_flags += 1
                elif project.remaining_days < 14 and project.progress < 75:  # Concerning timeline
                    yellow_flags += 1

                # Risk Level Check
                if hasattr(project, 'risk_level'):
                    if project.risk_level == 'critical':
                        red_flags += 1
                    elif project.risk_level == 'high':
                        yellow_flags += 1

                # Quality Check
                if hasattr(project, 'quality_score') and project.quality_score < 60:
                    red_flags += 1
                elif hasattr(project, 'quality_score') and project.quality_score < 80:
                    yellow_flags += 1

                # Set health status based on flags
                if red_flags >= 3:
                    project.health_status = 'red'
                elif red_flags >= 2 or (red_flags >= 1 and yellow_flags >= 2):
                    project.health_status = 'red'
                elif red_flags >= 1 or yellow_flags >= 2:
                    project.health_status = 'yellow'
                else:
                    project.health_status = 'green'

            except Exception as e:
                _logger.error(f"Error computing health status for project {project.id}: {e}")
                project.health_status = 'green'
    @api.depends('analytic_line_ids.amount', 'purchase_order_ids.amount_total', 'approved_budget', 'total_budget')
    def _compute_financial_data(self):
        """Compute comprehensive financial data"""
        for project in self:
            try:
                # Initialize values
                project.allocated_budget = project.approved_budget or project.total_budget

                # Calculate actual costs from analytic lines
                analytic_cost = 0.0
                if project.analytic_account_id and hasattr(project, 'analytic_line_ids'):
                    analytic_lines = project.analytic_line_ids.filtered(
                        lambda line: line.account_id == project.analytic_account_id
                    )
                    analytic_cost = sum(abs(line.amount) for line in analytic_lines if line.amount < 0)

                # Calculate costs from purchase orders
                purchase_cost = 0.0
                if hasattr(project, 'purchase_order_ids'):
                    confirmed_pos = project.purchase_order_ids.filtered(
                        lambda po: po.state in ['purchase', 'done']
                    )
                    purchase_cost = sum(confirmed_pos.mapped('amount_total'))

                # Calculate costs from stock moves (inventory valuation)
                stock_cost = 0.0
                if hasattr(project, 'stock_move_ids'):
                    consumed_moves = project.stock_move_ids.filtered(
                        lambda sm: sm.state == 'done' and sm.location_dest_id.usage in ['production', 'internal']
                    )
                    stock_cost = sum(consumed_moves.mapped('value'))

                # Set actual cost (take the highest reliable value)
                project.actual_cost = max(analytic_cost, purchase_cost, stock_cost)

                # Committed costs (approved but not yet invoiced)
                if hasattr(project, 'purchase_order_ids'):
                    project.committed_cost = sum(
                        project.purchase_order_ids.filtered(
                            lambda po: po.state == 'purchase' and po.invoice_status not in ['invoiced', 'no']
                        ).mapped('amount_total')
                    )
                else:
                    project.committed_cost = 0.0

                # Pending costs (draft orders)
                if hasattr(project, 'purchase_order_ids'):
                    project.pending_cost = sum(
                        project.purchase_order_ids.filtered(
                            lambda po: po.state in ['draft', 'sent', 'to approve']
                        ).mapped('amount_total')
                    )
                else:
                    project.pending_cost = 0.0

                # Budget calculations
                project.remaining_budget = project.allocated_budget - project.actual_cost - project.committed_cost
                project.budget_variance = project.actual_cost - project.allocated_budget

                # Budget utilization percentage
                if project.allocated_budget > 0:
                    project.budget_utilization = (
                                                         (
                                                                     project.actual_cost + project.committed_cost) / project.allocated_budget
                                                 ) * 100
                else:
                    project.budget_utilization = 0.0

            except Exception as e:
                _logger.error(f"Error computing financial data for project {project.id}: {e}")
                project.allocated_budget = project.total_budget
                project.actual_cost = 0.0
                project.committed_cost = 0.0
                project.pending_cost = 0.0
                project.remaining_budget = project.total_budget
                project.budget_variance = 0.0
                project.budget_utilization = 0.0
    @api.depends('expected_revenue', 'actual_revenue', 'actual_cost', 'total_budget')
    def _compute_profit_loss(self):
        """Calculate profit/loss metrics"""
        for project in self:
            try:
                # Expected profit calculation
                project.expected_profit = (project.expected_revenue or 0.0) - project.total_budget

                # Actual profit calculation
                project.actual_profit = (project.actual_revenue or 0.0) - project.actual_cost

                # Profit margin calculation
                if project.actual_revenue and project.actual_revenue > 0:
                    project.profit_margin = (project.actual_profit / project.actual_revenue) * 100
                elif project.expected_revenue and project.expected_revenue > 0:
                    # Use expected revenue if actual is not available
                    expected_margin = (project.expected_profit / project.expected_revenue) * 100
                    project.profit_margin = expected_margin
                else:
                    project.profit_margin = 0.0

            except Exception as e:
                _logger.error(f"Error computing profit/loss for project {project.id}: {e}")
                project.expected_profit = 0.0
                project.actual_profit = 0.0
                project.profit_margin = 0.0
    @api.depends('analytic_line_ids.amount', 'analytic_line_ids.category_id', 'purchase_order_ids.order_line')
    def _compute_cost_breakdown(self):
        """Break down costs by category"""
        for project in self:
            try:
                # Initialize costs
                project.material_cost = 0.0
                project.labor_cost = 0.0
                project.equipment_cost = 0.0
                project.overhead_cost = 0.0

                # Get costs from analytic lines with categories
                if project.analytic_account_id and hasattr(project, 'analytic_line_ids'):
                    analytic_lines = project.analytic_line_ids.filtered(
                        lambda line: line.account_id == project.analytic_account_id and line.amount < 0
                    )

                    for line in analytic_lines:
                        amount = abs(line.amount)
                        category_name = ''

                        if hasattr(line, 'category_id') and line.category_id:
                            category_name = line.category_id.name.lower()
                        elif hasattr(line, 'name') and line.name:
                            category_name = line.name.lower()

                        # Categorize based on keywords
                        if any(keyword in category_name for keyword in ['material', 'Materials', 'Raw Materials', 'supplies']):
                            project.material_cost += amount
                        elif any(keyword in category_name for keyword in ['labor', 'Workers', 'Wages', 'wages', 'salary']):
                            project.labor_cost += amount
                        elif any(keyword in category_name for keyword in
                                 ['equipment', 'Equipment', 'Machinery', 'machine', 'tool']):
                            project.equipment_cost += amount
                        else:
                            project.overhead_cost += amount

                # Add costs from purchase orders
                if hasattr(project, 'purchase_order_ids'):
                    for po in project.purchase_order_ids.filtered(lambda x: x.state in ['purchase', 'done']):
                        for line in po.order_line:
                            amount = line.price_subtotal
                            category_name = ''

                            if line.product_id and line.product_id.categ_id:
                                category_name = line.product_id.categ_id.name.lower()

                            # Categorize products
                            if any(keyword in category_name for keyword in
                                   ['seed', 'fertilizer', 'chemical', 'Seeds', 'Fertilizers', 'Chemicals', 'pesticide']):
                                project.material_cost += amount
                            elif any(keyword in category_name for keyword in
                                     ['equipment', 'machine', 'tool', 'Equipment', 'Machinery', 'Tools']):
                                project.equipment_cost += amount
                            elif any(keyword in category_name for keyword in
                                     ['service', 'labor', 'Services', 'Workers']):
                                project.labor_cost += amount
                            else:
                                project.overhead_cost += amount

            except Exception as e:
                _logger.error(f"Error computing cost breakdown for project {project.id}: {e}")
                project.material_cost = 0.0
                project.labor_cost = 0.0
                project.equipment_cost = 0.0
                project.overhead_cost = 0.0
    @api.depends('production_request_ids.state')
    def _compute_request_statistics(self):
        """Calculate production request statistics"""
        for project in self:
            try:
                if hasattr(project, 'production_request_ids'):
                    requests = project.production_request_ids
                    project.total_production_requests = len(requests)
                    project.pending_production_requests = len(
                        requests.filtered(lambda r: r.state in ['draft', 'submitted', 'under_review'])
                    )
                    project.approved_production_requests = len(
                        requests.filtered(lambda r: r.state in ['approved', 'in_progress', 'completed', 'done'])
                    )
                else:
                    project.total_production_requests = 0
                    project.pending_production_requests = 0
                    project.approved_production_requests = 0
            except Exception as e:
                _logger.error(f"Error computing request statistics for project {project.id}: {e}")
                project.total_production_requests = 0
                project.pending_production_requests = 0
                project.approved_production_requests = 0
    @api.depends('purchase_order_ids.state', 'purchase_order_ids.amount_total')
    def _compute_purchase_statistics(self):
        """Calculate purchase order statistics"""
        for project in self:
            try:
                if hasattr(project, 'purchase_order_ids'):
                    purchase_orders = project.purchase_order_ids
                    project.total_purchase_orders = len(purchase_orders)
                    project.pending_purchase_orders = len(
                        purchase_orders.filtered(lambda po: po.state in ['draft', 'sent', 'to approve'])
                    )
                    project.total_purchase_amount = sum(purchase_orders.mapped('amount_total'))
                else:
                    project.total_purchase_orders = 0
                    project.pending_purchase_orders = 0
                    project.total_purchase_amount = 0.0
            except Exception as e:
                _logger.error(f"Error computing purchase statistics for project {project.id}: {e}")
                project.total_purchase_orders = 0
                project.pending_purchase_orders = 0
                project.total_purchase_amount = 0.0
    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('agricultural.project') or _('New')
        plan_id = self.env['account.analytic.plan'].search([
            ('name', '=', 'Agricultural Projects')
        ], limit=1)
        # Create analytic account if not provided
        if not vals.get('analytic_account_id'):
            analytic_account = self.env['account.analytic.account'].create({
                'name': vals.get('name', 'Project'),
                'plan_id':plan_id.id,
            })
            vals['analytic_account_id'] = analytic_account.id

        return super(AgriculturalProject, self).create(vals)
    @api.constrains('start_date', 'end_date')
    def _check_project_dates(self):
        """Validate project dates"""
        for project in self:
            if project.start_date and project.end_date and project.end_date < project.start_date:
                raise ValidationError(_('End date cannot be earlier than start date.'))
class Hr(models.Model):
    _inherit = 'hr.employee'
    project_id = fields.Many2one('agricultural.project', string='Project')
class AgriculturalVendorEvaluation(models.Model):
    _name = 'agricultural.vendor.evaluation'
    _description = 'Agricultural Vendor Evaluation'

    project_id = fields.Many2one('agricultural.project', string='Project', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)

    # Evaluation criteria
    quality_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Quality Rating')

    delivery_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Delivery Rating')

    price_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Price Rating')

    service_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Service Rating')

    overall_rating = fields.Float('Overall Rating', compute='_compute_overall_rating', store=True)
    evaluation_date = fields.Date('Evaluation Date', default=fields.Date.today)
    notes = fields.Text('Notes')
    recommend_for_future = fields.Boolean('Recommend for Future Projects')

    @api.depends('quality_rating', 'delivery_rating', 'price_rating', 'service_rating')
    def _compute_overall_rating(self):
        for record in self:
            ratings = [
                int(record.quality_rating) if record.quality_rating else 0,
                int(record.delivery_rating) if record.delivery_rating else 0,
                int(record.price_rating) if record.price_rating else 0,
                int(record.service_rating) if record.service_rating else 0,
            ]
            valid_ratings = [r for r in ratings if r > 0]
            if valid_ratings:
                record.overall_rating = sum(valid_ratings) / len(valid_ratings)
            else:
                record.overall_rating = 0.0
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    household_harvest_id = fields.Many2one('household.harvest', 'Household Harvest')
class AgriculturalProject_Extend(models.Model):
    _inherit = 'agricultural.project'

    # Direct Costs
    budget_allocation = fields.Many2one('account.analytic.account')
    approval_progress = fields.Float(string="approval progress",digits=(10, 2))
    harvest_efficiency = fields.Float(string="harvest efficiency",digits=(10, 2))
    average_yield_per_hectare = fields.Float(string="average yield per hectare",digits=(10, 2))
    direct_material_cost = fields.Monetary(
        'Direct Material Cost',
        compute='_compute_detailed_costs',
        store=True,
        currency_field='currency_id',
        help='Cost of seeds, fertilizers, pesticides'
    )
    color = fields.Integer(
        'Color Index', copy=False,
        store=True
    )
    direct_labor_cost = fields.Monetary(
        'Direct Labor Cost',
        compute='_compute_detailed_costs',
        store=True,
        currency_field='currency_id'
    )
    direct_equipment_cost = fields.Monetary(
        'Direct Equipment Cost',
        compute='_compute_detailed_costs',
        store=True,
        currency_field='currency_id'
    )
    indirect_overhead_cost = fields.Monetary(
        'Indirect Overhead',
        compute='_compute_detailed_costs',
        store=True,
        currency_field='currency_id'
    )
    allocated_overhead = fields.Monetary(
        'Allocated Overhead',
        compute='_compute_allocated_costs',
        store=True,
        currency_field='currency_id',
        help='Overhead allocated based on area/usage'
    )
    total_direct_cost = fields.Monetary(
        'Total Direct Cost',
        compute='_compute_cost_summary',
        store=True,
        currency_field='currency_id'
    )

    total_indirect_cost = fields.Monetary(
        'Total Indirect Cost',
        compute='_compute_cost_summary',
        store=True,
        currency_field='currency_id'
    )

    # Revenue & Profit
    actual_revenue = fields.Monetary(
        'Actual Revenue',
        compute='_compute_revenue_profit',
        store=True,
        currency_field='currency_id'
    )

    expected_revenue = fields.Monetary(
        'Expected Revenue',
        currency_field='currency_id',
        tracking=True
    )

    gross_profit = fields.Monetary(
        'Gross Profit',
        compute='_compute_revenue_profit',
        store=True,
        currency_field='currency_id'
    )

    net_profit = fields.Monetary(
        'Net Profit',
        compute='_compute_revenue_profit',
        store=True,
        currency_field='currency_id'
    )

    profit_margin_percent = fields.Float(
        'Profit Margin %',
        compute='_compute_revenue_profit',
        store=True
    )

    # ==================== FARM LEVEL COST ALLOCATION ====================

    farm_cost_allocation_ids = fields.One2many(
        'farm.cost.allocation',
        'project_id',
        string='Farm Cost Allocations',
        help='Cost allocation to different farm levels'
    )

    farm_level_profit_ids = fields.One2many(
        'farm.level.profit',
        'project_id',
        string='Farm Level Profits',
        help='Profit tracking at each farm level'
    )

    # ==================== AREA-BASED METRICS ====================

    total_project_area = fields.Float(
        'Total Project Area (m²)',
        compute='_compute_area_metrics',
        store=True,
        help='Total area covered by this project'
    )
    total_harvested_quantity = fields.Float(
        'Total Harvest Qty',
        compute='_compute_revenue_profit',
        store=True,
        help='Total area covered by this project'
    )
    completed_harvests = fields.Integer(string="Completed Harvests")
    total_harvests = fields.Integer(string="Total Harvests")
    cost_per_square_meter = fields.Monetary(
        'Cost per m²',
        compute='_compute_area_metrics',
        store=True,
        currency_field='currency_id'
    )
    revenue_per_square_meter = fields.Monetary(
        'Revenue per m²',
        compute='_compute_area_metrics',
        store=True,
        currency_field='currency_id'
    )
    profit_per_square_meter = fields.Monetary(
        'Profit per m²',
        compute='_compute_area_metrics',
        store=True,
        currency_field='currency_id'
    )


    @api.depends(
        'production_request_ids',
        'production_request_ids.state',
        'production_request_ids.line_ids',
        'production_request_ids.line_ids.product_id',
        'production_request_ids.line_ids.quantity',
        'production_request_ids.line_ids.unit_price'
    )
    def _compute_detailed_costs(self):
        """Compute detailed cost breakdown"""
        for project in self:
            direct_material = 0.0
            direct_labor = 0.0
            direct_equipment = 0.0
            indirect_overhead = 0.0

            # Calculate from production requests
            completed_requests = project.production_request_ids.filtered(
                lambda r: r.state in ['transferred', 'completed']
            )

            for request in completed_requests:
                for line in request.line_ids:
                    product = line.product_id
                    cost = line.quantity * line.unit_price

                    # Categorize by product type
                    if product.agricultural_product_type in ['seeds', 'RawMaterials']:
                        direct_material += cost
                    elif product.agricultural_product_type == 'Pesticides':
                        direct_material += cost
                    elif product.categ_id.name in ['Fertilizer', 'Fertilizers']:
                        direct_material += cost
                    elif product.agricultural_product_type == 'equipment':
                        direct_equipment += cost
                    elif product.agricultural_product_type == 'labor':
                        direct_labor += cost
                    else:
                        indirect_overhead += cost

            # Add labor costs from timesheet/payroll if available
            if project.analytic_account_id:
                labor_lines = project.analytic_account_id.line_ids.filtered(
                    lambda l: l.employee_id
                )
                direct_labor += abs(sum(labor_lines.mapped('amount')))

            project.direct_material_cost = direct_material
            project.direct_labor_cost = direct_labor
            project.direct_equipment_cost = direct_equipment
            project.indirect_overhead_cost = indirect_overhead
    def action_recalculate_all_metrics(self):
        """Recalculate all cost and profit metrics"""
        self.ensure_one()

        # Force recomputation of all fields
        self._compute_detailed_costs()
        self._compute_allocated_costs()
        self._compute_cost_summary()
        self._compute_revenue_profit()
        self._compute_area_metrics()

        # Reallocate costs and recalculate profits
        self.action_allocate_costs_to_farms()
        self.action_calculate_farm_profits()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('All metrics recalculated successfully'),
                'type': 'success',
                'sticky': False,
            }
        }
    @api.depends('farm_id', 'farm_id.area_hectares', 'total_direct_cost')
    def _compute_allocated_costs(self):
        """Allocate overhead costs based on area usage"""
        for project in self:
            if not project.farm_id:
                project.allocated_overhead = 0.0
                continue

            # Get farm's total overhead
            farm_overhead = project.farm_id.overhead_costs or 0.0

            # Get total area and project area
            total_farm_area = project.farm_id.total_area or project.farm_id.area_hectares
            project_area = project._get_project_total_area()

            if total_farm_area > 0 and project_area > 0:
                # Allocate proportionally
                allocation_ratio = project_area / total_farm_area
                project.allocated_overhead = farm_overhead * allocation_ratio
            else:
                project.allocated_overhead = 0.0
    @api.depends('direct_material_cost', 'direct_labor_cost', 'direct_equipment_cost',
                 'indirect_overhead_cost', 'allocated_overhead')
    def _compute_cost_summary(self):
        """Compute total costs summary"""
        for project in self:
            project.total_direct_cost = (
                    project.direct_material_cost +
                    project.direct_labor_cost +
                    project.direct_equipment_cost
            )

            project.total_indirect_cost = (
                    project.indirect_overhead_cost +
                    project.allocated_overhead
            )
    @api.depends(
        'total_direct_cost',
        'total_indirect_cost',
        'total_harvested_quantity',
        'harvest_schedule_ids',
        'harvest_schedule_ids.crop_id',
        'harvest_schedule_ids.actual_quantity'
    )
    def _compute_revenue_profit(self):
        """Compute revenue and profit"""
        for project in self:
            # Calculate actual revenue from harvests
            actual_revenue = 0.0

            for harvest in project.harvest_schedule_ids.filtered(lambda h: h.state == 'completed'):
                crop = harvest.crop_id
                quantity = harvest.actual_quantity

                # Get selling price (list price or last sale price)
                price = crop.list_price or crop.standard_price
                actual_revenue += quantity * price

            project.actual_revenue = actual_revenue

            # Calculate total costs
            total_cost = project.total_direct_cost + project.total_indirect_cost

            # Calculate profits
            project.gross_profit = actual_revenue - project.total_direct_cost
            project.net_profit = actual_revenue - total_cost

            # Calculate profit margin
            if actual_revenue > 0:
                project.profit_margin_percent = (project.net_profit / actual_revenue) * 100
            else:
                project.profit_margin_percent = 0.0
    @api.depends('farm_id', 'farm_id.area_hectares', 'total_direct_cost', 'actual_revenue', 'net_profit')
    def _compute_area_metrics(self):
        """Compute per-area metrics"""
        for project in self:
            project_area = project._get_project_total_area()
            project.total_project_area = project_area

            if project_area > 0:
                total_cost = project.total_direct_cost + project.total_indirect_cost
                project.cost_per_square_meter = total_cost / project_area
                project.revenue_per_square_meter = project.actual_revenue / project_area
                project.profit_per_square_meter = project.net_profit / project_area
            else:
                project.cost_per_square_meter = 0.0
                project.revenue_per_square_meter = 0.0
                project.profit_per_square_meter = 0.0
    def _get_project_total_area(self):
        """Get total area covered by project"""
        self.ensure_one()

        if not self.farm_id:
            return 0.0

        # If project is at house level, return house area
        if self.farm_id.level == 'house':
            return self.farm_id.area_hectares or 0.0

        # If at higher level, sum all child house areas
        house_children = self._get_all_house_children(self.farm_id)
        return sum(house_children.mapped('area_hectares'))
    def _get_all_house_children(self, farm):
        """Recursively get all house-level children"""
        houses = self.env['agricultural.farm']

        for child in farm.child_ids:
            if child.level == 'house':
                houses |= child
            else:
                houses |= self._get_all_house_children(child)

        return houses
    def action_allocate_costs_to_farms(self):
        """Allocate project costs to all farm levels"""
        self.ensure_one()

        if not self.farm_id:
            raise UserError(_('No farm assigned to this project.'))

        # Clear existing allocations
        self.farm_cost_allocation_ids.unlink()

        # Get all house-level children
        houses = self._get_all_house_children(self.farm_id)

        if not houses:
            # Project is at house level
            houses = self.farm_id

        total_area = sum(houses.mapped('area_hectares'))

        if total_area <= 0:
            raise UserError(_('Total area is zero. Cannot allocate costs.'))

        total_cost = self.total_direct_cost + self.total_indirect_cost

        # Create allocations for each house
        allocations = []
        for house in houses:
            if house.area_hectares <= 0:
                continue

            area_ratio = house.area_hectares / total_area
            allocated_cost = total_cost * area_ratio

            allocations.append({
                'project_id': self.id,
                'farm_id': house.id,
                'farm_level': house.level,
                'area_square_meters': house.area_hectares,
                'area_ratio': area_ratio * 100,
                'allocated_cost': allocated_cost,
                'cost_per_square_meter': allocated_cost / house.area_hectares if house.area_hectares > 0 else 0,
            })

        self.env['farm.cost.allocation'].create(allocations)

        # Propagate to parent levels
        self._propagate_costs_to_parents()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Costs allocated to %d farm locations') % len(allocations),
                'type': 'success',
            }
        }
    def _propagate_costs_to_parents(self):
        """Propagate costs from houses to parent levels"""
        self.ensure_one()

        # Get all unique parent farms
        house_allocations = self.farm_cost_allocation_ids.filtered(
            lambda a: a.farm_level == 'house'
        )

        parent_farms = house_allocations.mapped('farm_id.parent_id')

        while parent_farms:
            for parent in parent_farms:
                # Sum costs from children
                child_allocations = self.farm_cost_allocation_ids.filtered(
                    lambda a: a.farm_id.parent_id == parent
                )

                if child_allocations:
                    total_child_cost = sum(child_allocations.mapped('allocated_cost'))
                    total_child_area = sum(child_allocations.mapped('area_square_meters'))

                    # Check if allocation already exists
                    existing = self.farm_cost_allocation_ids.filtered(
                        lambda a: a.farm_id == parent
                    )

                    if existing:
                        existing.write({
                            'allocated_cost': total_child_cost,
                            'area_square_meters': total_child_area,
                            'cost_per_square_meter': total_child_cost / total_child_area if total_child_area > 0 else 0,
                        })
                    else:
                        self.env['farm.cost.allocation'].create({
                            'project_id': self.id,
                            'farm_id': parent.id,
                            'farm_level': parent.level,
                            'area_square_meters': total_child_area,
                            'allocated_cost': total_child_cost,
                            'cost_per_square_meter': total_child_cost / total_child_area if total_child_area > 0 else 0,
                        })

            # Move to next level
            parent_farms = parent_farms.mapped('parent_id')
    def action_calculate_farm_profits(self):
        """Calculate profit for each farm level"""
        self.ensure_one()

        # Clear existing profit records
        self.farm_level_profit_ids.unlink()

        # Get harvest data for each farm level
        profit_records = []

        for allocation in self.farm_cost_allocation_ids:
            farm = allocation.farm_id

            # Get harvests for this farm
            harvests = self.harvest_schedule_ids.filtered(
                lambda h: h.farm_id == farm and h.state == 'completed'
            )

            # Calculate revenue
            revenue = 0.0
            total_yield = 0.0

            for harvest in harvests:
                quantity = harvest.actual_quantity
                price = harvest.crop_id.list_price or harvest.crop_id.standard_price
                revenue += quantity * price
                total_yield += quantity

            # Calculate profit
            cost = allocation.allocated_cost
            profit = revenue - cost
            profit_margin = (profit / revenue * 100) if revenue > 0 else 0.0

            profit_records.append({
                'project_id': self.id,
                'farm_id': farm.id,
                'farm_level': farm.level,
                'total_cost': cost,
                'total_revenue': revenue,
                'gross_profit': profit,
                'profit_margin_percent': profit_margin,
                'total_yield_quantity': total_yield,
                'cost_per_unit': cost / total_yield if total_yield > 0 else 0,
                'revenue_per_unit': revenue / total_yield if total_yield > 0 else 0,
            })

        self.env['farm.level.profit'].create(profit_records)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Farm Level Profits'),
            'res_model': 'farm.level.profit',
            'view_mode': 'list,form,pivot,graph',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }
    def action_view_profit_analysis(self):
        """View profit analysis by farm level"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Farm Level Profit Analysis'),
            'res_model': 'farm.level.profit',
            'view_mode': 'list,pivot,graph,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'group_by': ['farm_level', 'farm_id'],
                'pivot_measures': ['total_cost', 'total_revenue', 'gross_profit', 'profit_margin_percent'],
                'graph_type': 'bar',
                'graph_measure': 'gross_profit',
                'graph_groupbys': ['farm_id'],
            }
        }
    def action_export_cost_allocation_excel(self):
        """Export cost allocation to Excel"""
        self.ensure_one()

        # This would typically use xlsxwriter or similar
        # For now, return a wizard to configure export
        return {
            'name': _('Export Cost Allocation'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.cost.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_project_id': self.id}
        }
    def action_view_cost_allocation_report(self):
        """View cost allocation report"""
        self.ensure_one()
class FarmCostAllocation(models.Model):
    _name = 'farm.cost.allocation'
    _description = 'Farm Cost Allocation'
    _order = 'project_id, farm_level, farm_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        'Name',
        compute='_compute_display_name',
        store=True
    )

    # Relations
    project_id = fields.Many2one(
        'agricultural.project',
        'Project',
        required=True,
        ondelete='cascade',
        index=True
    )

    farm_id = fields.Many2one(
        'agricultural.farm',
        'Farm Location',
        required=True,
        ondelete='cascade',
        index=True
    )

    farm_level = fields.Selection([
        ('farm', 'Farm'),
        ('sector', 'Sector'),
        ('unit', 'Unit'),
        ('house', 'House')
    ], string='Level', required=True, index=True)

    parent_allocation_id = fields.Many2one(
        'farm.cost.allocation',
        'Parent Allocation',
        compute='_compute_parent_allocation',
        store=True
    )

    # Area Information
    area_square_meters = fields.Float(
        'Area (m²)',
        required=True,
        digits=(10, 4)
    )

    area_ratio = fields.Float(
        'Area Ratio %',
        digits=(5, 2),
        help='Percentage of total project area'
    )

    # Cost Allocation
    allocated_cost = fields.Monetary(
        'Allocated Cost',
        required=True,
        currency_field='currency_id'
    )

    cost_per_square_meter = fields.Monetary(
        'Cost per m²',
        currency_field='currency_id'
    )

    # Direct vs Indirect
    direct_cost_portion = fields.Monetary(
        'Direct Cost',
        compute='_compute_cost_breakdown',
        store=True,
        currency_field='currency_id'
    )

    indirect_cost_portion = fields.Monetary(
        'Indirect Cost',
        compute='_compute_cost_breakdown',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='project_id.currency_id',
        store=True
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('allocated', 'Allocated'),
        ('adjusted', 'Adjusted'),
        ('finalized', 'Finalized')
    ], default='draft', string='Status')

    # Notes
    allocation_notes = fields.Text('Allocation Notes')

    # Computed
    child_allocation_ids = fields.One2many(
        'farm.cost.allocation',
        'parent_allocation_id',
        string='Child Allocations'
    )

    child_count = fields.Integer(
        'Children')

    # ========== COST ALLOCATION ==========

    material_cost = fields.Monetary(
        'Material Cost',
        compute='_compute_cost_breakdown',
        store=True,
        currency_field='currency_id'
    )

    labor_cost = fields.Monetary(
        'Labor Cost',
        compute='_compute_cost_breakdown',
        store=True,
        currency_field='currency_id'
    )

    equipment_cost = fields.Monetary(
        'Equipment Cost',
        compute='_compute_cost_breakdown',
        store=True,
        currency_field='currency_id'
    )

    overhead_cost = fields.Monetary(
        'Overhead Cost',
        compute='_compute_cost_breakdown',
        store=True,
        currency_field='currency_id'
    )

    allocation_date = fields.Date(
        'Allocation Date',
        default=fields.Date.today
    )

    notes = fields.Text('Notes')

    def action_view_cost_allocation_report(self):
        """View cost allocation report"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Cost Allocation Report'),
            'res_model': 'farm.cost.allocation',
            'view_mode': 'list,pivot,graph',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'group_by': ['farm_level', 'farm_id'],
                'pivot_measures': ['allocated_cost', 'cost_per_square_meter', 'area_square_meters'],
                'pivot_column_groupby': ['farm_level'],
                'pivot_row_groupby': ['farm_id'],
            }
        }

    def action_view_profit_analysis(self):
        """View profit analysis by farm level"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Farm Level Profit Analysis'),
            'res_model': 'farm.level.profit',
            'view_mode': 'list,pivot,graph,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'group_by': ['farm_level', 'farm_id'],
                'pivot_measures': ['total_cost', 'total_revenue', 'gross_profit', 'profit_margin_percent'],
                'graph_type': 'bar',
                'graph_measure': 'gross_profit',
                'graph_groupbys': ['farm_id'],
            }
        }

    def action_generate_cost_report_pdf(self):
        """Generate PDF cost report"""
        self.ensure_one()
        return self.env.ref('agricultural_management.action_report_project_cost_allocation').report_action(self)

    def action_export_cost_allocation_excel(self):
        """Export cost allocation to Excel"""
        self.ensure_one()

        # This would typically use xlsxwriter or similar
        # For now, return a wizard to configure export
        return {
            'name': _('Export Cost Allocation'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.cost.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_project_id': self.id}
        }

    def action_recalculate_all_metrics(self):
        """Recalculate all cost and profit metrics"""
        self.ensure_one()

        # Force recomputation of all fields
        self._compute_detailed_costs()
        self._compute_allocated_costs()
        self._compute_cost_summary()
        self._compute_revenue_profit()
        self._compute_area_metrics()

        # Reallocate costs and recalculate profits
        self.action_allocate_costs_to_farms()
        self.action_calculate_farm_profits()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('All metrics recalculated successfully'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.depends('project_id', 'farm_id', 'farm_level')
    def _compute_display_name(self):
        for record in self:
            if record.project_id and record.farm_id:
                record.display_name = f"{record.project_id.name} - {record.farm_id.name} ({record.farm_level})"
            else:
                record.display_name = 'New Allocation'

    @api.depends('farm_id', 'farm_id.parent_id', 'project_id')
    def _compute_parent_allocation(self):
        for record in self:
            if record.farm_id and record.farm_id.parent_id:
                parent_alloc = self.search([
                    ('project_id', '=', record.project_id.id),
                    ('farm_id', '=', record.farm_id.parent_id.id)
                ], limit=1)
                record.parent_allocation_id = parent_alloc
            else:
                record.parent_allocation_id = False

    @api.depends('allocated_cost', 'area_ratio', 'project_id.total_direct_cost',
                 'project_id.total_indirect_cost')
    def _compute_cost_breakdown(self):
        for record in self:
            if not record.project_id or not record.allocated_cost:
                record.direct_cost_portion = 0.0
                record.indirect_cost_portion = 0.0
                record.material_cost = 0.0
                record.labor_cost = 0.0
                record.equipment_cost = 0.0
                record.overhead_cost = 0.0
                continue

            project = record.project_id
            ratio = record.area_ratio / 100 if record.area_ratio else 0

            # Allocate proportionally
            record.direct_cost_portion = project.total_direct_cost * ratio
            record.indirect_cost_portion = project.total_indirect_cost * ratio

            # Detailed breakdown
            record.material_cost = project.direct_material_cost * ratio
            record.labor_cost = project.direct_labor_cost * ratio
            record.equipment_cost = project.direct_equipment_cost * ratio
            record.overhead_cost = (project.indirect_overhead_cost + project.allocated_overhead) * ratio

    @api.depends('child_allocation_ids')
    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_allocation_ids)

    # ========== ACTION METHODS ==========

    def action_view_children(self):
        """View child allocations"""
        self.ensure_one()
        return {
            'name': _('Child Allocations'),
            'type': 'ir.actions.act_window',
            'res_model': 'farm.cost.allocation',
            'view_mode': 'list,form',
            'domain': [('parent_allocation_id', '=', self.id)],
            'context': {'default_project_id': self.project_id.id}
        }
    def action_view_farm(self):
        """View associated farm"""
        self.ensure_one()
        return {
            'name': _('Farm Location'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.farm',
            'view_mode': 'form',
            'res_id': self.farm_id.id,
        }
    def action_finalize(self):
        """Finalize the allocation"""
        self.write({'state': 'finalized'})
        return True
class FarmLevelProfit(models.Model):
    _name = 'farm.level.profit'
    _description = 'Farm Level Profit Analysis'
    _order = 'project_id, farm_level, farm_id'
    _rec_name = 'display_name'

    # ========== BASIC FIELDS ==========

    display_name = fields.Char(
        'Name',
        compute='_compute_display_name',
        store=True
    )

    project_id = fields.Many2one(
        'agricultural.project',
        'Project',
        required=True,
        ondelete='cascade',
        index=True
    )

    farm_id = fields.Many2one(
        'agricultural.farm',
        'Farm Location',
        required=True,
        ondelete='cascade',
        index=True
    )

    farm_level = fields.Selection([
        ('farm', 'Farm'),
        ('sector', 'Sector'),
        ('unit', 'Unit'),
        ('house', 'House')
    ], string='Level', required=True, index=True)

    # ========== CURRENCY ==========

    currency_id = fields.Many2one(
        'res.currency',
        related='project_id.currency_id',
        store=True
    )

    # ========== COST DATA ==========

    total_cost = fields.Monetary(
        'Total Cost',
        currency_field='currency_id',
        required=True
    )

    direct_cost = fields.Monetary(
        'Direct Cost',
        currency_field='currency_id'
    )

    indirect_cost = fields.Monetary(
        'Indirect Cost',
        currency_field='currency_id'
    )

    # ========== REVENUE DATA ==========

    total_revenue = fields.Monetary(
        'Total Revenue',
        currency_field='currency_id',
        required=True
    )

    expected_revenue = fields.Monetary(
        'Expected Revenue',
        currency_field='currency_id'
    )

    revenue_variance = fields.Monetary(
        'Revenue Variance',
        compute='_compute_variances',
        store=True,
        currency_field='currency_id'
    )

    # ========== PROFIT DATA ==========

    gross_profit = fields.Monetary(
        'Gross Profit',
        currency_field='currency_id',
        help='Revenue - Direct Costs'
    )

    net_profit = fields.Monetary(
        'Net Profit',
        compute='_compute_net_profit',
        store=True,
        currency_field='currency_id',
        help='Revenue - Total Costs'
    )

    profit_margin_percent = fields.Float(
        'Profit Margin %',
        digits=(5, 2)
    )

    roi_percent = fields.Float(
        'ROI %',
        compute='_compute_roi',
        store=True,
        digits=(5, 2)
    )

    # ========== YIELD DATA ==========

    total_yield_quantity = fields.Float(
        'Total Yield',
        digits='Product Unit of Measure'
    )

    expected_yield_quantity = fields.Float(
        'Expected Yield',
        digits='Product Unit of Measure'
    )

    yield_variance = fields.Float(
        'Yield Variance',
        compute='_compute_variances',
        store=True,
        digits='Product Unit of Measure'
    )

    yield_efficiency_percent = fields.Float(
        'Yield Efficiency %',
        compute='_compute_yield_efficiency',
        store=True,
        digits=(5, 2)
    )

    # ========== UNIT METRICS ==========

    cost_per_unit = fields.Monetary(
        'Cost per Unit',
        currency_field='currency_id'
    )

    revenue_per_unit = fields.Monetary(
        'Revenue per Unit',
        currency_field='currency_id'
    )

    profit_per_unit = fields.Monetary(
        'Profit per Unit',
        compute='_compute_per_unit_metrics',
        store=True,
        currency_field='currency_id'
    )

    # ========== AREA METRICS ==========

    area_square_meters = fields.Float(
        'Area (m²)',
        related='farm_id.area_hectares',
        store=True
    )

    cost_per_square_meter = fields.Monetary(
        'Cost per m²',
        compute='_compute_per_area_metrics',
        store=True,
        currency_field='currency_id'
    )

    revenue_per_square_meter = fields.Monetary(
        'Revenue per m²',
        compute='_compute_per_area_metrics',
        store=True,
        currency_field='currency_id'
    )

    profit_per_square_meter = fields.Monetary(
        'Profit per m²',
        compute='_compute_per_area_metrics',
        store=True,
        currency_field='currency_id'
    )

    # ========== STATUS & NOTES ==========

    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('finalized', 'Finalized')
    ], default='draft', tracking=True)

    calculation_date = fields.Date(
        'Calculation Date',
        default=fields.Date.today
    )

    notes = fields.Text('Analysis Notes')

    # ========== PERFORMANCE INDICATORS ==========

    performance_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
        ('loss', 'Loss Making')
    ],
        string='Performance Rating',
        compute='_compute_performance_rating',
        store=True
    )

    color = fields.Integer(
        'Color',
        compute='_compute_color'
    )

    # ========== COMPUTE METHODS ==========

    @api.depends('project_id', 'farm_id', 'farm_level')
    def _compute_display_name(self):
        for record in self:
            if record.project_id and record.farm_id:
                record.display_name = f"{record.project_id.name} - {record.farm_id.name} Profit"
            else:
                record.display_name = 'New Profit Analysis'

    @api.depends('total_revenue', 'total_cost')
    def _compute_net_profit(self):
        for record in self:
            record.net_profit = record.total_revenue - record.total_cost

    @api.depends('net_profit', 'total_cost')
    def _compute_roi(self):
        for record in self:
            if record.total_cost > 0:
                record.roi_percent = (record.net_profit / record.total_cost) * 100
            else:
                record.roi_percent = 0.0

    @api.depends('total_revenue', 'expected_revenue', 'total_yield_quantity', 'expected_yield_quantity')
    def _compute_variances(self):
        for record in self:
            record.revenue_variance = record.total_revenue - record.expected_revenue
            record.yield_variance = record.total_yield_quantity - record.expected_yield_quantity

    @api.depends('total_yield_quantity', 'expected_yield_quantity')
    def _compute_yield_efficiency(self):
        for record in self:
            if record.expected_yield_quantity > 0:
                record.yield_efficiency_percent = (record.total_yield_quantity / record.expected_yield_quantity) * 100
            else:
                record.yield_efficiency_percent = 0.0

    @api.depends('net_profit', 'total_yield_quantity')
    def _compute_per_unit_metrics(self):
        for record in self:
            if record.total_yield_quantity > 0:
                record.profit_per_unit = record.net_profit / record.total_yield_quantity
            else:
                record.profit_per_unit = 0.0

    @api.depends('total_cost', 'total_revenue', 'net_profit', 'area_square_meters')
    def _compute_per_area_metrics(self):
        for record in self:
            if record.area_square_meters > 0:
                record.cost_per_square_meter = record.total_cost / record.area_square_meters
                record.revenue_per_square_meter = record.total_revenue / record.area_square_meters
                record.profit_per_square_meter = record.net_profit / record.area_square_meters
            else:
                record.cost_per_square_meter = 0.0
                record.revenue_per_square_meter = 0.0
                record.profit_per_square_meter = 0.0

    @api.depends('profit_margin_percent', 'net_profit')
    def _compute_performance_rating(self):
        for record in self:
            if record.net_profit < 0:
                record.performance_rating = 'loss'
            elif record.profit_margin_percent >= 30:
                record.performance_rating = 'excellent'
            elif record.profit_margin_percent >= 20:
                record.performance_rating = 'good'
            elif record.profit_margin_percent >= 10:
                record.performance_rating = 'average'
            else:
                record.performance_rating = 'poor'

    @api.depends('performance_rating')
    def _compute_color(self):
        color_map = {
            'excellent': 10,  # Green
            'good': 7,  # Light green
            'average': 3,  # Yellow
            'poor': 1,  # Red
            'loss': 9  # Dark red
        }
        for record in self:
            record.color = color_map.get(record.performance_rating, 0)

    # ========== ACTION METHODS ==========

    def action_view_farm(self):
        """View associated farm"""
        self.ensure_one()
        return {
            'name': _('Farm Location'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.farm',
            'view_mode': 'form',
            'res_id': self.farm_id.id,
        }

    def action_view_project(self):
        """View associated project"""
        self.ensure_one()
        return {
            'name': _('Project'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.project',
            'view_mode': 'form',
            'res_id': self.project_id.id,
            'target': 'current',
        }

    def action_view_cost_allocation(self):
        """View related cost allocation"""
        self.ensure_one()

        allocation = self.env['farm.cost.allocation'].search([
            ('project_id', '=', self.project_id.id),
            ('farm_id', '=', self.farm_id.id)
        ], limit=1)

        if not allocation:
            raise UserError(_('No cost allocation found for this farm level.'))

        return {
            'name': _('Cost Allocation'),
            'type': 'ir.actions.act_window',
            'res_model': 'farm.cost.allocation',
            'view_mode': 'form',
            'res_id': allocation.id,
            'target': 'current',
        }

    def action_view_harvests(self):
        """View harvests for this farm"""
        self.ensure_one()

        return {
            'name': _('Harvests'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.harvest.schedule',
            'view_mode': 'list,form,calendar',
            'domain': [
                ('project_id', '=', self.project_id.id),
                ('farm_id', '=', self.farm_id.id),
                ('state', '=', 'completed')
            ],
            'context': {'create': False}
        }

    def action_approve(self):
        """Approve profit analysis"""
        self.write({'state': 'approved'})

        self.message_post(
            body=_('Profit analysis approved by %s') % self.env.user.name,
            subject=_('Approved'),
            message_type='notification'
        )

        return True

    def action_finalize(self):
        """Finalize profit analysis"""
        if self.state != 'approved':
            raise UserError(_('Can only finalize approved profit analyses.'))

        self.write({'state': 'finalized'})

        self.message_post(
            body=_('Profit analysis finalized by %s') % self.env.user.name,
            subject=_('Finalized'),
            message_type='notification'
        )

        return True

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
        return True

    def action_generate_profit_report(self):
        """Generate detailed profit report"""
        self.ensure_one()

        return self.env.ref(
            'agricultural_management.action_report_farm_level_profit'
        ).report_action(self)

    def action_compare_with_siblings(self):
        """Compare with sibling farms (same parent)"""
        self.ensure_one()

        if not self.farm_id.parent_id:
            raise UserError(_('This farm has no parent. Cannot compare with siblings.'))

        sibling_farms = self.farm_id.parent_id.child_ids

        return {
            'name': _('Sibling Farm Comparison'),
            'type': 'ir.actions.act_window',
            'res_model': 'farm.level.profit',
            'view_mode': 'list,pivot,graph',
            'domain': [
                ('project_id', '=', self.project_id.id),
                ('farm_id', 'in', sibling_farms.ids)
            ],
            'context': {
                'pivot_measures': ['total_cost', 'total_revenue', 'net_profit', 'profit_margin_percent'],
                'pivot_row_groupby': ['farm_id'],
                'graph_type': 'bar',
                'graph_measure': 'net_profit',
                'graph_groupbys': ['farm_id'],
            }
        }

    def action_export_to_excel(self):
        """Export profit data to Excel"""
        self.ensure_one()

        return {
            'name': _('Export Profit Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'farm.profit.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_profit_id': self.id,
                'default_project_id': self.project_id.id
            }
        }

    def _get_performance_insights(self):
        """Get performance insights and recommendations"""
        self.ensure_one()

        insights = []

        # Cost efficiency insight
        if self.cost_per_square_meter > 0:
            avg_cost = self._get_average_cost_per_sqm()
            if avg_cost > 0:
                variance_pct = ((self.cost_per_square_meter - avg_cost) / avg_cost) * 100
                if variance_pct > 20:
                    insights.append({
                        'type': 'warning',
                        'category': 'cost',
                        'message': f'Cost per m² is {variance_pct:.1f}% above average',
                        'recommendation': 'Review cost allocation and identify cost reduction opportunities'
                    })
                elif variance_pct < -20:
                    insights.append({
                        'type': 'success',
                        'category': 'cost',
                        'message': f'Cost per m² is {abs(variance_pct):.1f}% below average',
                        'recommendation': 'Excellent cost management'
                    })

        # Profit margin insight
        if self.profit_margin_percent < 10:
            insights.append({
                'type': 'danger',
                'category': 'profit',
                'message': f'Profit margin is low at {self.profit_margin_percent:.1f}%',
                'recommendation': 'Consider increasing prices or reducing costs'
            })
        elif self.profit_margin_percent > 30:
            insights.append({
                'type': 'success',
                'category': 'profit',
                'message': f'Excellent profit margin of {self.profit_margin_percent:.1f}%',
                'recommendation': 'Maintain current practices'
            })

        # Yield efficiency insight
        if self.yield_efficiency_percent < 80:
            insights.append({
                'type': 'warning',
                'category': 'yield',
                'message': f'Yield efficiency is only {self.yield_efficiency_percent:.1f}%',
                'recommendation': 'Investigate factors affecting yield performance'
            })
        elif self.yield_efficiency_percent > 100:
            insights.append({
                'type': 'success',
                'category': 'yield',
                'message': f'Exceeded expected yield by {self.yield_efficiency_percent - 100:.1f}%',
                'recommendation': 'Document success factors for replication'
            })

        # ROI insight
        if self.roi_percent < 15:
            insights.append({
                'type': 'warning',
                'category': 'roi',
                'message': f'ROI is low at {self.roi_percent:.1f}%',
                'recommendation': 'Review investment efficiency'
            })
        elif self.roi_percent > 40:
            insights.append({
                'type': 'success',
                'category': 'roi',
                'message': f'Excellent ROI of {self.roi_percent:.1f}%',
                'recommendation': 'Consider expanding operations'
            })

        return insights

    def _get_average_cost_per_sqm(self):
        """Get average cost per square meter for comparison"""
        all_profits = self.search([
            ('project_id', '=', self.project_id.id),
            ('farm_level', '=', self.farm_level),
            ('id', '!=', self.id)
        ])

        if not all_profits:
            return 0.0

        total_cost = sum(all_profits.mapped('cost_per_square_meter'))
        return total_cost / len(all_profits)

    def action_show_insights(self):
        """Show performance insights"""
        self.ensure_one()

        insights = self._get_performance_insights()

        if not insights:
            message = _('No specific insights available. Performance is within normal ranges.')
        else:
            message = '<ul>'
            for insight in insights:
                icon = {
                    'success': '✅',
                    'warning': '⚠️',
                    'danger': '❌'
                }.get(insight['type'], 'ℹ️')

                message += f"<li><strong>{icon} {insight['category'].upper()}</strong>: "
                message += f"{insight['message']}<br/>"
                message += f"<em>Recommendation: {insight['recommendation']}</em></li>"
            message += '</ul>'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Performance Insights'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
    def get_comparison_data(self, comparison_type='siblings'):
        """Get comparison data for charts"""
        self.ensure_one()

        if comparison_type == 'siblings':
            if not self.farm_id.parent_id:
                return []
            domain = [
                ('project_id', '=', self.project_id.id),
                ('farm_id', 'in', self.farm_id.parent_id.child_ids.ids)
            ]
        elif comparison_type == 'same_level':
            domain = [
                ('project_id', '=', self.project_id.id),
                ('farm_level', '=', self.farm_level)
            ]
        else:
            domain = [('project_id', '=', self.project_id.id)]

        profits = self.search(domain)

        return [{
            'farm': p.farm_id.name,
            'cost': float(p.total_cost),
            'revenue': float(p.total_revenue),
            'profit': float(p.net_profit),
            'margin': float(p.profit_margin_percent),
            'roi': float(p.roi_percent),
        } for p in profits]

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set calculation date and state"""
        records = super().create(vals_list)

        for record in records:
            record.message_post(
                body=_('Profit analysis created for %s') % record.farm_id.name,
                subject=_('Created'),
                message_type='notification'
            )

        return records

    def write(self, vals):
        """Override write to track state changes"""
        result = super().write(vals)

        if 'state' in vals and vals['state'] in ['approved', 'finalized']:
            for record in self:
                record.message_post(
                    body=_('State changed to %s') % dict(
                        record._fields['state'].selection
                    ).get(vals['state']),
                    subject=_('Status Update'),
                    message_type='notification'
                )

        return result

    def unlink(self):
        """Override unlink to prevent deletion of finalized records"""
        if any(record.state == 'finalized' for record in self):
            raise UserError(_('Cannot delete finalized profit analyses.'))

        return super().unlink()

    def get_summary_data(self):
        """Get summary data for reporting"""
        self.ensure_one()

        return {
            'farm_name': self.farm_id.name,
            'farm_level': dict(self._fields['farm_level'].selection).get(self.farm_level),
            'project_name': self.project_id.name,
            'area': self.area_square_meters,
            'costs': {
                'total': float(self.total_cost),
                'direct': float(self.direct_cost),
                'indirect': float(self.indirect_cost),
                'per_sqm': float(self.cost_per_square_meter),
                'per_unit': float(self.cost_per_unit),
            },
            'revenue': {
                'total': float(self.total_revenue),
                'expected': float(self.expected_revenue),
                'variance': float(self.revenue_variance),
                'per_sqm': float(self.revenue_per_square_meter),
                'per_unit': float(self.revenue_per_unit),
            },
            'profit': {
                'gross': float(self.gross_profit),
                'net': float(self.net_profit),
                'margin_pct': float(self.profit_margin_percent),
                'roi_pct': float(self.roi_percent),
                'per_sqm': float(self.profit_per_square_meter),
                'per_unit': float(self.profit_per_unit),
            },
            'yield': {
                'total': float(self.total_yield_quantity),
                'expected': float(self.expected_yield_quantity),
                'variance': float(self.yield_variance),
                'efficiency_pct': float(self.yield_efficiency_percent),
            },
            'performance': {
                'rating': self.performance_rating,
                'rating_label': dict(
                    self._fields['performance_rating'].selection
                ).get(self.performance_rating),
            }
        }

    def _get_benchmark_data(self):
        """Get benchmark data for industry comparison"""
        # This could pull from external data or historical averages
        return {
            'target_profit_margin': 25.0,
            'target_roi': 30.0,
            'target_yield_efficiency': 90.0,
            'industry_avg_cost_per_sqm': 50.0,
            'industry_avg_revenue_per_sqm': 75.0,
        }

    def compare_to_benchmark(self):
        """Compare performance to benchmarks"""
        self.ensure_one()

        benchmarks = self._get_benchmark_data()

        comparison = {
            'profit_margin': {
                'actual': self.profit_margin_percent,
                'target': benchmarks['target_profit_margin'],
                'variance': self.profit_margin_percent - benchmarks['target_profit_margin'],
                'status': 'above' if self.profit_margin_percent >= benchmarks['target_profit_margin'] else 'below'
            },
            'roi': {
                'actual': self.roi_percent,
                'target': benchmarks['target_roi'],
                'variance': self.roi_percent - benchmarks['target_roi'],
                'status': 'above' if self.roi_percent >= benchmarks['target_roi'] else 'below'
            },
            'yield_efficiency': {
                'actual': self.yield_efficiency_percent,
                'target': benchmarks['target_yield_efficiency'],
                'variance': self.yield_efficiency_percent - benchmarks['target_yield_efficiency'],
                'status': 'above' if self.yield_efficiency_percent >= benchmarks['target_yield_efficiency'] else 'below'
            },
        }

        return comparison


