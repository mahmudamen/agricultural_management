from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AgriculturalProject(models.Model):
    _inherit = 'agricultural.project'

    # Cost Allocation Relations
    cost_allocation_ids = fields.One2many(
        'agri.cost.allocation',
        'project_id',
        string='Cost Allocations'
    )
    cost_calculation_ids = fields.One2many(
        'agri.cost.calculation',
        'project_id',
        string='Cost Calculations'
    )
    # Cost Summary Fields
    total_direct_expenses = fields.Monetary(
        string='Total Direct Expenses',
        compute='_compute_project_costs',
        store=True,
        currency_field='currency_id'
    )

    total_indirect_expenses = fields.Monetary(
        string='Total Indirect Expenses',
        compute='_compute_project_costs',
        store=True,
        currency_field='currency_id'
    )

    total_admin_expenses = fields.Monetary(
        string='Total Administrative Expenses',
        compute='_compute_project_costs',
        store=True,
        currency_field='currency_id'
    )

    total_selling_expenses = fields.Monetary(
        string='Total Selling Expenses',
        compute='_compute_project_costs',
        store=True,
        currency_field='currency_id'
    )

    total_financial_expenses = fields.Monetary(
        string='Total Financial Expenses',
        compute='_compute_project_costs',
        store=True,
        currency_field='currency_id'
    )

    total_other_expenses = fields.Monetary(
        string='Total Other Expenses',
        compute='_compute_project_costs',
        store=True,
        currency_field='currency_id'
    )

    total_project_cost = fields.Monetary(
        string='Total Project Cost',
        compute='_compute_project_costs',
        store=True,
        currency_field='currency_id'
    )

    # Statistics
    allocation_count = fields.Integer(
        string='Allocations',
        compute='_compute_counts'
    )

    calculation_count = fields.Integer(
        string='Calculations',
        compute='_compute_counts'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('cost_allocation_ids', 'cost_allocation_ids.total_amount',
                 'cost_allocation_ids.cost_category')
    def _compute_project_costs(self):
        """Compute project costs from allocations"""
        for project in self:
            allocations = project.cost_allocation_ids.filtered(
                lambda a: a.state in ['allocated', 'posted']
            )

            # Direct expenses (operational)
            direct_categories = ['direct_material', 'seeds', 'fertilizers',
                                 'pesticides', 'direct_labor', 'machinery',
                                 'utilities', 'fuel']
            project.total_direct_expenses = sum(
                allocations.filtered(
                    lambda a: a.cost_category in direct_categories
                ).mapped('total_amount')
            )

            # Indirect expenses
            indirect_categories = ['maintenance', 'overhead']
            project.total_indirect_expenses = sum(
                allocations.filtered(
                    lambda a: a.cost_category in indirect_categories
                ).mapped('total_amount')
            )

            # Administrative expenses
            admin_categories = ['depreciation', 'insurance']
            project.total_admin_expenses = sum(
                allocations.filtered(
                    lambda a: a.cost_category in admin_categories
                ).mapped('total_amount')
            )

            # Selling expenses
            selling_categories = ['transportation', 'packaging']
            project.total_selling_expenses = sum(
                allocations.filtered(
                    lambda a: a.cost_category in selling_categories
                ).mapped('total_amount')
            )

            # Other expenses
            project.total_other_expenses = sum(
                allocations.filtered(
                    lambda a: a.cost_category == 'other'
                ).mapped('total_amount')
            )

            # Financial expenses (will be added from account moves)
            project.total_financial_expenses = 0

            # Total
            project.total_project_cost = (
                    project.total_direct_expenses +
                    project.total_indirect_expenses +
                    project.total_admin_expenses +
                    project.total_selling_expenses +
                    project.total_financial_expenses +
                    project.total_other_expenses
            )

    @api.depends('cost_allocation_ids', 'cost_calculation_ids')
    def _compute_counts(self):
        for project in self:
            project.allocation_count = len(project.cost_allocation_ids)
            project.calculation_count = len(project.cost_calculation_ids)

    def action_view_all_costs(self):
        """View all cost allocations"""
        self.ensure_one()

        return {
            'name': f'Cost Allocations - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
                'default_analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
            },
            'views': [
                (False, 'list'),
                (False, 'form'),
                (False, 'pivot'),
                (False, 'graph'),
            ]
        }

    def action_view_direct_expenses(self):
        """View direct operating expenses (Direct Operating Expenses)"""
        self.ensure_one()

        direct_categories = ['direct_material', 'seeds', 'fertilizers',
                             'pesticides', 'direct_labor', 'machinery',
                             'utilities', 'fuel']

        return {
            'name': f'Direct Operating Expenses - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [
                ('project_id', '=', self.id),
                ('cost_category', 'in', direct_categories),
                ('allocation_method', '=', 'direct_assignment')
            ],
            'context': {
                'default_project_id': self.id,
                'default_allocation_method': 'direct_assignment',
                'default_analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                'search_default_group_by_category': 1,
            }
        }

    def action_view_indirect_operating_expenses(self):
        """View indirect operating expenses (Indirect Operating Expenses)"""
        self.ensure_one()

        indirect_categories = ['maintenance', 'overhead']

        return {
            'name': f'Indirect Operating Expenses - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [
                ('project_id', '=', self.id),
                ('cost_category', 'in', indirect_categories),
                ('allocation_method', 'in', ['area_based', 'plant_count', 'production_volume'])
            ],
            'context': {
                'default_project_id': self.id,
                'default_allocation_method': 'area_based',
                'default_analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                'search_default_group_by_category': 1,
            }
        }

    def action_view_administrative_expenses(self):
        """View administrative expenses (Administrative Expenses)"""
        self.ensure_one()

        admin_categories = ['depreciation', 'insurance']

        return {
            'name': f'Administrative Expenses - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [
                ('project_id', '=', self.id),
                ('cost_category', 'in', admin_categories)
            ],
            'context': {
                'default_project_id': self.id,
                'default_allocation_method': 'area_based',
                'default_analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                'search_default_group_by_category': 1,
            }
        }

    def action_view_selling_expenses(self):
        """View selling & marketing expenses (Selling & Marketing Expenses)"""
        self.ensure_one()

        selling_categories = ['transportation', 'packaging']

        return {
            'name': f'Selling & Marketing Expenses - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [
                ('project_id', '=', self.id),
                ('cost_category', 'in', selling_categories)
            ],
            'context': {
                'default_project_id': self.id,
                'default_allocation_method': 'area_based',
                'default_analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                'search_default_group_by_category': 1,
            }
        }

    def action_view_financial_expenses(self):
        """View financial expenses (Financial Expenses)"""
        self.ensure_one()

        if not self.analytic_account_id:
            raise UserError('Please set an analytic account for this project first.')

        return {
            'name': f'Financial Expenses - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form,pivot',
            'domain': [
                ('analytic_account_id', '=', self.analytic_account_id.id),
                ('account_id.code', '=like', '67%'),  # Financial expense accounts
                ('move_id.state', '=', 'posted')
            ],
            'context': {
                'default_analytic_account_id': self.analytic_account_id.id,
                'default_project_id': self.id,
                'search_default_group_by_account': 1,
            }
        }

    def action_view_other_expenses(self):
        """View other expenses (Other Expenses)"""
        self.ensure_one()

        return {
            'name': f'Other Expenses - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [
                ('project_id', '=', self.id),
                ('cost_category', '=', 'other')
            ],
            'context': {
                'default_project_id': self.id,
                'default_cost_category': 'other',
                'default_analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
            }
        }

    def action_view_cost_calculations(self):
        """View cost calculations"""
        self.ensure_one()

        return {
            'name': f'Cost Calculations - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.calculation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [('project_ids', 'in', [self.id])],
            'context': {
                'default_project_ids': [(6, 0, [self.id])],
            }
        }

    def action_create_cost_calculation(self):
        """Create new cost calculation"""
        self.ensure_one()

        return {
            'name': f'New Cost Calculation - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.calculation',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_project_ids': [(6, 0, [self.id])],
                'default_date_from': fields.Date.today().replace(day=1),
                'default_date_to': fields.Date.today(),
                'default_period_type': 'monthly',
            }
        }

    def action_cost_allocation_wizard(self):
        """Open cost allocation wizard"""
        self.ensure_one()

        if not self.analytic_account_id:
            raise UserError('Please set an analytic account for this project first.')

        return {
            'name': 'Allocate Costs',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_analytic_account_id': self.analytic_account_id.id,
                'default_date': fields.Date.today(),
            }
        }

    def action_cost_summary_dashboard(self):
        """View cost summary dashboard"""
        self.ensure_one()

        return {
            'name': f'Cost Summary - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation.line',
            'view_mode': 'pivot,graph,list',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'pivot_measures': ['amount', 'cost_per_m2', 'cost_per_plant'],
                'pivot_column_groupby': ['allocation_date'],
                'pivot_row_groupby': ['cost_category'],
                'graph_type': 'bar',
                'graph_measure': 'amount',
                'graph_groupbys': ['cost_category'],
            },
            'views': [
                (False, 'pivot'),
                (False, 'graph'),
                (False, 'list'),
            ]
        }

    # ============================================
    # HELPER METHODS
    # ============================================

    def _create_analytic_account(self):
        """Create analytic account for project"""
        self.ensure_one()

        if self.analytic_account_id:
            return self.analytic_account_id

        analytic_account = self.env['account.analytic.account'].create({
            'name': f'{self.name} - {self.code}',
            'code': self.code,
            'plan_id': self.env.ref('analytic.analytic_plan_projects').id,
            'partner_id': self.partner_id.id if self.partner_id else False,
        })

        self.analytic_account_id = analytic_account.id
        return analytic_account

    @api.model
    def create(self, vals):
        """Create analytic account on project creation"""
        project = super().create(vals)
        if not project.analytic_account_id:
            project._create_analytic_account()
        return project

class AgriculturalCostAllocation(models.Model):
    _inherit = 'agri.cost.allocation'

    # Override project_id to make it work properly with search


    # Add source tracking
    source_type = fields.Selection([
        ('inventory', 'Inventory/Stock'),
        ('payroll', 'Payroll/HR'),
        ('accounting', 'General Accounting'),
        ('fixed_assets', 'Fixed Assets Depreciation'),
        ('manual', 'Manual Entry')
    ], string='Source Type', tracking=True, help='Source of expense')

    # Add allocation status
    is_direct = fields.Boolean(
        string='Is Direct Cost',
        compute='_compute_is_direct',
        store=True,
        help='Direct costs are charged directly to cost centers'
    )

    requires_allocation = fields.Boolean(
        string='Requires Allocation',
        compute='_compute_is_direct',
        store=True,
        help='Indirect costs require allocation based on rules'
    )

    @api.depends('cost_category', 'allocation_method')
    def _compute_is_direct(self):
        direct_categories = ['direct_material', 'seeds', 'fertilizers',
                             'pesticides', 'direct_labor']
        for allocation in self:
            allocation.is_direct = (
                    allocation.cost_category in direct_categories and
                    allocation.allocation_method == 'direct_assignment'
            )
            allocation.requires_allocation = not allocation.is_direct
