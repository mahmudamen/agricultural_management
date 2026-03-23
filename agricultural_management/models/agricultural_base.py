from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_round, float_compare
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AgriculturalFarm(models.Model):
    _name = 'agricultural.farm'
    _description = 'Agricultural Farm Management'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='Farm Name',
        required=True,
        tracking=True,
        translate=True,
        help='Farm location name',
        index=True
    )
    code = fields.Char(
        string='Farm Code',
        copy=False,
        tracking=True,
        help='Unique farm code',
        index=True,
        required=True
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        translate=True,
        tracking=True, copy=False,
        index=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Used to order locations', copy=False,
        index=True
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True, copy=False,
        index=True
    )
    location = fields.Char(string='Location Address',
        tracking=True,
        required=True,
        help='Physical location address'
    )
    parent_id = fields.Many2one(
        'agricultural.farm',
        string='Parent Farm/Section',
        index=True,
        ondelete='cascade',
        tracking=True, copy=False,
        domain="[('level', '!=', 'house')]"
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        'agricultural.farm',
        'parent_id', copy=False,
        string='Child Locations'
    )
    level = fields.Selection([
        ('farm', 'Farm'),
        ('sector', 'Sector'),
        ('unit','unit'),
        ('house', 'House')
    ], string="Level",
        default="house",
        tracking=True,
        copy=False,
        index=True)
    farm_type = fields.Selection([
        ('crop', 'Crop Farm'),
        ('livestock', 'Livestock Farm'),
        ('mixed', 'Mixed Farm'),
        ('greenhouse', 'Greenhouse')
    ], string='Farm Type',
        tracking=True, copy=False,
        index=True)
    color = fields.Integer(
        'Color Index',
        compute='_compute_color', copy=False,
        store=True
    )
    color_hex = fields.Char(
        string='Hex Color',
        compute='_compute_color', copy=False,
        store=True
    )
    area_hectares = fields.Float(
        string='Area (Meter)',
        digits=(10, 4),
        tracking=True,
        help='Farm area in Meter'
    )
    cultivated_area_hectares = fields.Float(
        string='Cultivated Area (Meter)',
        digits='Product Unit of Measure',
        tracking=True,
        help='Currently cultivated area in Meter'
    )
    available_area_hectares = fields.Float(
        string='Available Area (Meter)',
        compute='_compute_area_calculations',
        store=True,
        digits='Product Unit of Measure',
        help='Available area for cultivation'
    )
    area_utilization_percentage = fields.Float(
        string='Area Utilization %',
        compute='_compute_area_calculations',
        store=True,
        digits='Discount',
        help='Percentage of area being utilized'
    )
    total_area = fields.Float(
        string='Total Area (Including Children)',
        compute='_compute_total_area',
        store=True,
        digits='Product Unit of Measure',
        help='Total area including children'
    )
    soil_type = fields.Selection([
        ('clay', 'Clay'),
        ('sandy', 'Sandy'),
        ('loam', 'Loam'),
        ('silt', 'Silt'),
        ('peat', 'Peat'),
        ('chalk', 'Chalk')
    ], string='Soil Type', tracking=True)
    irrigation_type = fields.Selection([
        ('drip', 'Drip Irrigation'),
        ('sprinkler', 'Sprinkler'),
        ('flood', 'Flood Irrigation'),
        ('manual', 'Manual Watering'),
        ('smart', 'Smart Irrigation System')
    ], string='Irrigation Type', tracking=True)
    house_type = fields.Selection([
        ('glass', 'Glass Greenhouses'),
        ('plastic', 'Plastic Greenhouses'),
        ('fiberglass', 'Fiberglass Greenhouses'),
        ('net', 'Net Houses'),
        ('polycarbonate', 'Polycarbonate Greenhouses'),
        ('climate_controlled', 'Climate Controlled Greenhouses')
    ], string='House Type')
    climate_controlled = fields.Boolean(
        string='Climate Controlled',
        help='Has climate control systems'
    )
    farm_manager = fields.Many2one(
        'hr.employee',
        string='Farm Manager',
        tracking=True,
        domain="[('active', '=', True)]"
    )
    agricultural_engineer = fields.Many2one(
        'hr.employee',
        string='Agricultural Engineer',
        tracking=True,
        domain="[('active', '=', True)]"
    )
    veterinarian = fields.Many2one(
        'hr.employee',
        string='Veterinarian',
        tracking=True,
        domain="[('active', '=', True)]"
    )
    worker_ids = fields.Many2many(
        'hr.employee',
        'farm_worker_rel',
        'farm_id',
        'employee_id',
        string='Workers',
        domain="[('active', '=', True)]"
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Responsible User',
        tracking=True,
        default=lambda self: self.env.user,
        domain="[('active', '=', True)]"
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        index=True
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cost Center',
        tracking=True, copy=False,
        help='Analytic account for cost tracking'
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse', copy=False,
        tracking=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Stock Location', copy=False,
        domain="[('usage', 'in', ['internal', 'transit'])]"
    )
    picking_type_harvest_id = fields.Many2one(
        'stock.picking.type',
        string='Harvest Operation', copy=False,
        domain="[('code', '=', 'internal')]"
    )
    picking_type_internal_id = fields.Many2one(
        'stock.picking.type',
        string='Internal Transfers', copy=False,
        domain="[('code', '=', 'internal')]"
    )
    current_crop_ids = fields.Many2many(
        'product.product',
        'farm_current_crop_rel',
        'farm_id',
        'product_id',
        string='Current Crops', copy=False,
        domain="[('categ_id.name', 'ilike', 'Crop')]"
    )
    child_count = fields.Integer(
        string='Child Count',
        compute='_compute_counts',
        store=True
    )
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_counts',
        store=True
    )
    sector_count = fields.Integer(
        string='Sector Count',
        compute='_compute_level_counts',
        store=True
    )
    unit_count = fields.Integer(
        string='Unit Count',
        compute='_compute_level_counts',
        store=True
    )
    house_count = fields.Integer(
        string='House Count',
        compute='_compute_level_counts',
        store=True
    )
    analytic_line_count = fields.Integer(
        string='Analytic Entries',
        compute='_compute_analytic_stats',
        store=True
    )
    project_count = fields.Integer(
        string='Projects',
        compute='_compute_analytic_stats', copy=False,
        store=True
    )
    produced_product_ids = fields.Many2many(
        'product.product',
        'farm_produced_product_rel',
        'farm_id',
        'product_id',
        string='Produced Products',
        compute='_compute_product_lists', copy=False,
        store=True
    )
    consumed_product_ids = fields.Many2many(
        'product.product',
        'farm_consumed_product_rel',
        'farm_id',
        'product_id',
        string='Consumed Products',
        compute='_compute_product_lists', copy=False,
        store=True
    )
    seed_product_ids = fields.Many2many(
        'product.product',
        'farm_seed_product_rel',
        'farm_id',
        'product_id',
        string='Seed Products', copy=False,
        compute='_compute_product_lists',
        store=True
    )
    total_cost = fields.Monetary(
        string='Total Costs',
        compute='_compute_financial_stats',
        store=True, copy=False,
        currency_field='currency_id'
    )
    total_wages = fields.Monetary(
        string='Total Wages',
        compute='_compute_financial_stats',
        store=True,
        currency_field='currency_id'
    )
    total_expenses = fields.Monetary(
        string='Total Expenses',
        compute='_compute_financial_stats',
        store=True,
        currency_field='currency_id'
    )
    seed_costs = fields.Monetary(
        string='Seed Costs',
        compute='_compute_financial_stats',
        store=True,
        currency_field='currency_id'
    )
    total_sales = fields.Monetary(
        string='Total Sales',
        compute='_compute_financial_stats',
        store=True,
        currency_field='currency_id'
    )
    profit_loss = fields.Monetary(
        string="Profit/Loss",
        compute="_compute_profit_loss",
        store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    cost_allocation_ids = fields.One2many(
        'agri.cost.allocation',
        'farm_id',
        string='Cost Allocations',
        copy=False
    )
    overhead_costs = fields.Monetary(
        string='Overhead Costs',
        compute='_compute_financial_stats',
        store=True,
        currency_field='currency_id'
    )
    cost_calculation_ids = fields.One2many(
        'agri.cost.calculation',
        'farm_id',
        string='Cost Calculations',
        copy=False
    )
    project_ids = fields.One2many(
        'agricultural.project',
        'farm_id',
        string='Agricultural Projects',
        copy=False
    )
    cost_per_hectare = fields.Monetary(
        string='Cost per Hectare',
        compute='_compute_cost_per_hectare',
        store=True,
        currency_field='currency_id'
    )
    revenue_per_hectare = fields.Monetary(
        string='Revenue per Hectare',
        compute='_compute_revenue_per_hectare',
        store=True,
        currency_field='currency_id'
    )
    stock_move_ids = fields.One2many(
        'stock.move',
        'agricultural_farm_id',
        string='Stock Movements',
        copy=False
    )
    inventory_stage_ids = fields.One2many(
        'agri.inventory.stage',
        'farm_id',
        string='Inventory Stages',
        copy=False
    )
    fertilizer_costs = fields.Float('Fertilizer Costs', compute='_compute_financial_stats', store=True)
    pesticide_costs = fields.Float('Pesticide Costs', compute='_compute_financial_stats', store=True)
    labor_costs = fields.Float('Labor Costs', compute='_compute_financial_stats', store=True)
    equipment_costs = fields.Float('Equipment Costs', compute='_compute_financial_stats', store=True)
    total_costs = fields.Float('Total Costs', compute='_compute_financial_stats', store=True)
    total_revenue = fields.Float('Total Revenue', compute='_compute_financial_stats', store=True)
    profit_margin = fields.Float('Profit Margin', compute='_compute_financial_stats', store=True)
    # Add these fields after analytic_account_id field
    asset_account_id = fields.Many2one(
        'account.account',
        string='Asset Account',
        domain="[('account_type', '=', 'asset_non_current'), ('company_id', '=', company_id)]",
        help='Account for tracking farm fixed assets',
        copy=False,
        tracking=True
    )
    expense_account_id = fields.Many2one(
        'account.account',
        string='Direct Cost Account',
        help='Account for tracking direct costs',
        copy=False,
        tracking=True
    )
    # Add this field with other field definitions
    farm_account_count = fields.Integer(
        string='Farm Accounts',
        compute='_compute_farm_account_count',
        store=True
    )
    harvest_id = fields.Many2one('agricultural.harvest.schedule', string='harvest schedule')
    # ========================
    # SQL Constraints
    # ========================

    def batch_create_farm_integrations(self):
        """Batch create accounts, stock locations, and analytic accounts for multiple farms"""
        results = {
            'success': [],
            'failed': [],
            'skipped': [],
            'stats': {
                'accounts_created': 0,
                'locations_created': 0,
                'analytic_accounts_created': 0
            }
        }

        for farm in self:
            farm_result = {
                'farm': farm.name,
                'accounts': False,
                'location': False,
                'analytic': False,
                'errors': []
            }

            try:
                # 1. Create Farm Accounts
                existing_accounts = self.env['account.account'].search([
                    ('agricultural_farm_id', '=', farm.id)
                ])

                if len(existing_accounts) >= 2:
                    farm_result['accounts'] = 'skipped'
                else:
                    account_result = farm.create_farm_accounts()
                    if isinstance(account_result, dict) and 'created' in account_result:
                        farm_result['accounts'] = 'created'
                        farm_result['asset_code'] = account_result['asset_account'].code
                        farm_result['expense_code'] = account_result['expense_account'].code
                        results['stats']['accounts_created'] += 1

                # 2. Create Stock Location
                if not farm.location_id:
                    location = farm.create_stock_location()
                    farm_result['location'] = 'created'
                    farm_result['location_name'] = location.name
                    results['stats']['locations_created'] += 1
                else:
                    farm_result['location'] = 'exists'

                # 3. Create Analytic Account
                if not farm.analytic_account_id:
                    analytic = farm.create_analytic_account()
                    farm_result['analytic'] = 'created'
                    farm_result['analytic_name'] = analytic.name
                    results['stats']['analytic_accounts_created'] += 1
                else:
                    farm_result['analytic'] = 'exists'

                # If everything went well
                if not farm_result['errors']:
                    results['success'].append(farm_result)

            except Exception as e:
                farm_result['errors'].append(str(e))
                results['failed'].append(farm_result)
                _logger.error(f"Error creating integrations for farm {farm.name}: {str(e)}")

        return results
    def action_batch_create_integrations(self):
        """Action to create integrations for selected farms from list view"""
        if not self:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Please select at least one farm!'),
                    'type': 'warning',
                }
            }

        results = self.batch_create_farm_integrations()

        # Simple notification
        success_msg = _('Success: %d farms') % len(results['success'])
        failed_msg = _('Failed: %d farms') % len(results['failed'])

        notification_type = 'success' if not results['failed'] else 'warning'
        title = _('Integration Complete')
        message = f"{success_msg}, {failed_msg}"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
            }
        }
    def batch_create_farm_accounts(self):
        """Batch create accounts for multiple farms"""
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }

        for farm in self:
            try:
                # Check if accounts already exist
                existing = self.env['account.account'].search([
                    ('agricultural_farm_id', '=', farm.id)
                ])

                if len(existing) >= 2:
                    results['skipped'].append({
                        'farm': farm.name,
                        'reason': 'Accounts already exist'
                    })
                    continue

                result = farm.create_farm_accounts()

                if isinstance(result, dict) and 'created' in result:
                    results['success'].append({
                        'farm': farm.name,
                        'asset_code': result['asset_account'].code,
                        'expense_code': result['expense_account'].code
                    })
            except Exception as e:
                results['failed'].append({
                    'farm': farm.name,
                    'error': str(e)
                })
                _logger.error(f"Error creating accounts for farm {farm.name}: {str(e)}")

        return results
    @api.depends('asset_account_id', 'expense_account_id')
    def _compute_farm_account_count(self):
        for record in self:
            count = 0
            if record.asset_account_id:
                count += 1
            if record.expense_account_id:
                count += 1
            record.farm_account_count = count
    def _get_next_account_code(self, account_type, company_id):
        """Get next available account code for the given account type"""
        AccountAccount = self.env['account.account']
        # Find max code for the account type
        accounts = AccountAccount.search([
            ('account_type', '=', account_type),
            ('code', '!=', False)
        ], order='code desc', limit=1)
        if accounts and accounts.code:
            try:
                # Try to convert to integer and add 100
                max_code = int(accounts.code)
                next_code = str(max_code + 100)
            except ValueError:
                # If code contains letters, extract numbers
                import re
                numbers = re.findall(r'\d+', accounts.code)
                if numbers:
                    max_num = int(numbers[0])
                    next_code = str(max_num + 100)
                else:
                    # Fallback to default based on account type
                    next_code = self._get_default_code(account_type)
        else:
            # No existing accounts, use default
            next_code = self._get_default_code(account_type)

        # Ensure the code doesn't already exist
        while AccountAccount.search_count([
            ('code', '=', next_code),
        ]) > 0:
            next_code = str(int(next_code) + 100)

        return next_code
    def _get_default_code(self, account_type):
        """Get default starting code for account type"""
        default_codes = {
            'asset_non_current': '11201000000',  # Fixed assets starting code
            'expense_direct_cost': '50101000000',  # Direct cost starting code
            'asset_current': '11101000000',
            'expense': '50001000000',
        }
        return default_codes.get(account_type, '10000')
    def create_farm_accounts(self):
        """Create specific accounts for farm - Assets Non-Current and Direct Cost Expenses"""
        self.ensure_one()
        AccountAccount = self.env['account.account']
        # Get the company's chart of accounts
        company = self.company_id or self.env.company
        # Check if accounts already exist for this farm
        existing_accounts = AccountAccount.search([
            ('agricultural_farm_id', '=', self.id),
        ])
        if existing_accounts:
            asset_acc = existing_accounts.filtered(lambda a: a.account_type == 'asset_non_current')
            expense_acc = existing_accounts.filtered(lambda a: a.account_type == 'expense_direct_cost')
            if asset_acc and expense_acc:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Info'),
                        'message': _('Accounts already exist for this farm!\nAsset: %s\nExpense: %s') % (
                            asset_acc[0].code, expense_acc[0].code
                        ),
                        'type': 'info',
                        'sticky': False,
                    }
                }

        accounts_created = []
        # 1. Get next available code for Assets Non-Current
        asset_code = self._get_next_account_code('asset_non_current', company.id)
        # Create Assets Non-Current Account
        asset_account_vals = {
            'name': f"Raw Materials Warehouse - {self.name}",
            'code': asset_code,
            'account_type': 'asset_non_current',
            'reconcile': False,
            'deprecated': False,
            'agricultural_farm_id': self.id,
        }

        try:
            asset_account = AccountAccount.create(asset_account_vals)
            accounts_created.append(asset_account)
            _logger.info(
                f"Created Asset Non-Current account: {asset_account.code} - {asset_account.name} for farm {self.name}")
        except Exception as e:
            _logger.error(f"Error creating asset account for farm {self.name}: {str(e)}")
            raise

        # 2. Get next available code for Direct Cost Expenses
        expense_code = self._get_next_account_code('expense_direct_cost', company.id)
        # Create Direct Cost Expense Account
        expense_account_vals = {
            'name': f"Soil & Fertilizer Expense - {self.name}",
            'code': expense_code,
            'account_type': 'expense_direct_cost',
            'reconcile': False,
            'deprecated': False,
            'agricultural_farm_id': self.id,
        }

        try:
            expense_account = AccountAccount.create(expense_account_vals)
            accounts_created.append(expense_account)
            _logger.info(
                f"Created Direct Cost account: {expense_account.code} - {expense_account.name} for farm {self.name}")
        except Exception as e:
            _logger.error(f"Error creating expense account for farm {self.name}: {str(e)}")
            raise

        # Store references to created accounts
        self.write({
            'asset_account_id': asset_account.id,
            'expense_account_id': expense_account.id
        })

        # Post message to chatter
        if accounts_created:
            message = _('<b>Farm Accounts Created Successfully:</b><br/><ul>')
            for acc in accounts_created:
                message += f"<li><b>{acc.code}</b> - {acc.name} ({dict(acc._fields['account_type'].selection).get(acc.account_type)})</li>"
            message += '</ul>'

            self.message_post(
                body=message,
                subject=_('Farm Accounts Created'),
                message_type='notification'
            )

        return {
            'asset_account': asset_account,
            'expense_account': expense_account,
            'created': accounts_created
        }
    def action_create_farm_accounts(self):
        """Action to create farm accounts from UI"""
        self.ensure_one()
        try:
            result = self.create_farm_accounts()
            # If result is a notification (accounts exist), return it
            if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
                return result
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(
                        'Farm accounts created successfully!<br/><b>Asset Account:</b> %s<br/><b>Expense Account:</b> %s') % (
                                   result['asset_account'].code,
                                   result['expense_account'].code
                               ),
                    'type': 'success',
                    'sticky': True,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error creating farm accounts: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    def action_view_farm_accounts(self):
        """View all accounts linked to this farm"""
        self.ensure_one()
        return {
            'name': _('Farm Accounts - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'list,form',
            'domain': [('agricultural_farm_id', '=', self.id)],
            'context': {
                'default_agricultural_farm_id': self.id,
            }
        }
    @api.model
    def get_farm_accounts_report(self):
        """Get report of all farm accounts"""
        farms_with_accounts = self.search([
            '|',
            ('asset_account_id', '!=', False),
            ('expense_account_id', '!=', False)
        ])

        report_data = []
        for farm in farms_with_accounts:
            report_data.append({
                'farm_id': farm.id,
                'farm_name': farm.name,
                'farm_code': farm.code,
                'asset_account': farm.asset_account_id.code if farm.asset_account_id else '',
                'expense_account': farm.expense_account_id.code if farm.expense_account_id else '',
                'has_both': bool(farm.asset_account_id and farm.expense_account_id)
            })

        return report_data
    @api.depends('stock_move_ids', 'project_ids')
    def _compute_product_lists(self):
        """Compute product lists based on stock moves and projects"""
        for record in self:
            # Get produced products (outgoing moves from internal locations)
            produced_moves = record.stock_move_ids.filtered(
                lambda m: m.location_id.usage == 'internal' and
                          m.location_dest_id.usage in ['customer', 'transit'] and
                          m.state == 'done'
            )
            record.produced_product_ids = produced_moves.mapped('product_id')

            # Get consumed products (incoming moves to internal locations)
            consumed_moves = record.stock_move_ids.filtered(
                lambda m: m.location_id.usage in ['supplier', 'transit'] and
                          m.location_dest_id.usage == 'internal' and
                          m.state == 'done'
            )
            record.consumed_product_ids = consumed_moves.mapped('product_id')

            # Get seed products specifically
            seed_moves = consumed_moves.filtered(
                lambda m: m.product_id.agricultural_product_type == 'seeds'
            )
            record.seed_product_ids = seed_moves.mapped('product_id')
    @api.depends('cost_allocation_ids', 'stock_move_ids', 'project_ids')
    def _compute_financial_stats(self):
        """Compute comprehensive financial statistics"""
        for record in self:
            # Get all cost allocations for this farm
            allocations = record.cost_allocation_ids.filtered(lambda a: a.state == 'allocated')

            # Calculate different cost categories
            material_costs = allocations.filtered(lambda a: a.cost_category == 'direct_material')
            labor_costs = allocations.filtered(lambda a: a.cost_category == 'direct_labor')
            overhead_allocations = allocations.filtered(lambda a: a.cost_category == 'overhead')

            record.total_expenses = sum(material_costs.mapped('total_amount'))
            record.total_wages = sum(labor_costs.mapped('total_amount'))
            record.overhead_costs = sum(overhead_allocations.mapped('total_amount'))

            # Calculate specific material costs
            seed_allocations = material_costs.filtered(
                lambda a: any(line.product_id.agricultural_product_type == 'seeds'
                              for line in a.allocation_line_ids if line.product_id)
            )
            fertilizer_allocations = material_costs.filtered(
                lambda a: any(line.product_id.agricultural_product_type == 'fertilizers'
                              for line in a.allocation_line_ids if line.product_id)
            )
            pesticide_allocations = material_costs.filtered(
                lambda a: any(line.product_id.agricultural_product_type == 'pesticides'
                              for line in a.allocation_line_ids if line.product_id)
            )

            record.seed_costs = sum(seed_allocations.mapped('total_amount'))
            record.fertilizer_costs = sum(fertilizer_allocations.mapped('total_amount'))
            record.pesticide_costs = sum(pesticide_allocations.mapped('total_amount'))

            # Total costs
            record.total_cost = record.total_expenses + record.total_wages + record.overhead_costs

            # Calculate sales from stock moves (outgoing to customers)
            sales_moves = record.stock_move_ids.filtered(
                lambda m: m.location_dest_id.usage == 'customer' and m.state == 'done'
            )
            record.total_sales = sum(move.product_id.list_price * move.product_qty for move in sales_moves)
    @api.depends('total_sales', 'total_cost')
    def _compute_profit_loss(self):
        """Compute profit or loss"""
        for record in self:
            record.profit_loss = record.total_sales - record.total_cost
    @api.depends('total_cost', 'cultivated_area_hectares')
    def _compute_cost_per_hectare(self):
        """Compute cost per hectare"""
        for record in self:
            if record.cultivated_area_hectares > 0:
                record.cost_per_hectare = record.total_cost / record.cultivated_area_hectares
            else:
                record.cost_per_hectare = 0
    @api.depends('total_sales', 'cultivated_area_hectares')
    def _compute_revenue_per_hectare(self):
        """Compute revenue per hectare"""
        for record in self:
            if record.cultivated_area_hectares > 0:
                record.revenue_per_hectare = record.total_sales / record.cultivated_area_hectares
            else:
                record.revenue_per_hectare = 0
    @api.depends('level')
    def _compute_color(self):
        """Compute color based on level"""
        color_map = {
            'farm': 1,  # Red
            'sector': 3,  # Yellow
            'house': 2,  # Orange
        }
        hex_color_map = {
            'farm': '#FF0000',
            'sector': '#FFFF00',
            'house': '#FFA500',
        }

        for record in self:
            record.color = color_map.get(record.level, 0)
            record.color_hex = hex_color_map.get(record.level, '#FFFFFF')
    @api.constrains('parent_id')
    def _check_parent_id(self):
        """Check for recursion in hierarchy"""
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive farm locations.'))
    @api.constrains('level', 'parent_id')
    def _check_hierarchy_consistency(self):
        """Ensure hierarchy consistency"""
        for record in self:
            if record.level == 'house' and record.child_ids:
                raise ValidationError(_('House level cannot have child locations!'))

            if record.parent_id:
                expected_levels = {
                    'farm': ['sector'],
                    'sector': ['house']
                }
                expected_level = expected_levels.get(record.parent_id.level, [])
                pass
                '''
                if expected_level and record.level not in expected_level:
                    raise ValidationError(_(
                        'Level hierarchy violation! A %s can only contain %s levels.'
                    ) % (record.parent_id.level, ', '.join(expected_level)))
                '''

    @api.constrains('area_hectares', 'cultivated_area_hectares')
    def _check_area_consistency(self):
        """Check area consistency"""
        for record in self:
            if float_compare(record.cultivated_area_hectares, record.area_hectares, precision_digits=4) > 0:
                raise ValidationError(_('Cultivated area cannot exceed total area!'))
    def create_stock_location(self):
        """Create stock location for house with enhanced logic"""
        if self.location_id:
            return self.location_id
        stocklocation = self.env['stock.location']
        # Find parent location
        parent_location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        if self.parent_id and self.parent_id.location_id:
            parent_location = self.parent_id.location_id
        location = stocklocation.create({
            'name': f"{self.display_name}",
            'usage': 'internal',
            'location_id': parent_location.id if parent_location else False,
            'company_id': self.company_id.id,
        })

        self.location_id = location.id
        return location
    def create_analytic_account(self):
        """Create analytic account for cost tracking"""
        self.ensure_one()
        if self.analytic_account_id:
            return self.analytic_account_id
        plan_id = self.env['account.analytic.plan'].search([
            ('name', '=', 'Agricultural Projects')
        ], limit=1)
        AnalyticAccount = self.env['account.analytic.account']
        # Find parent analytic account
        analytic_account = AnalyticAccount.create({
            'name': f"{self.display_name} - Cost Center",
            'code': self.code,
            'company_id': self.company_id.id,
            'plan_id': plan_id.id,
        })

        self.analytic_account_id = analytic_account.id
        return analytic_account
    def get_cost_allocation_percentage(self):
        """Calculate cost allocation percentage based on area"""
        self.ensure_one()
        if not self.parent_id:
            return 100.0

        total_sibling_area = sum(self.parent_id.child_ids.mapped('cultivated_area_hectares'))
        if total_sibling_area == 0:
            return 0.0

        return (self.cultivated_area_hectares / total_sibling_area) * 100
    def allocate_costs_to_children(self, total_amount, cost_category='overhead'):
        """Allocate costs to child farms based on their area"""
        self.ensure_one()
        if not self.child_ids:
            return

        CostAllocation = self.env['agri.cost.allocation']

        # Create main allocation record
        allocation = CostAllocation.create({
            'name': f"Cost Allocation - {self.display_name}",
            'farm_id': self.id,
            'cost_category': cost_category,
            'total_amount': total_amount,
            'allocation_method': 'area_based',
            'account_id': self.analytic_account_id.id if self.analytic_account_id else False,
        })

        allocation.action_confirm()
        allocation.action_allocate()

        return allocation
    def get_production_summary(self, date_from=None, date_to=None):
        """Get production summary for the farm"""
        self.ensure_one()

        domain = [('agricultural_farm_id', '=', self.id), ('state', '=', 'done')]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        moves = self.env['stock.move'].search(domain)

        # Group by product
        production_data = {}
        for move in moves:
            product = move.product_id
            if product not in production_data:
                production_data[product] = {
                    'product': product,
                    'produced_qty': 0,
                    'consumed_qty': 0,
                    'revenue': 0,
                    'cost': 0
                }

            if move.location_dest_id.usage == 'customer':
                # Outgoing - production
                production_data[product]['produced_qty'] += move.product_qty
                production_data[product]['revenue'] += move.product_qty * product.list_price
            elif move.location_id.usage == 'supplier':
                # Incoming - consumption
                production_data[product]['consumed_qty'] += move.product_qty
                production_data[product]['cost'] += move.product_qty * product.standard_price

        return list(production_data.values())
    def action_view_cost_allocations(self):
        """Action to view cost allocations"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cost Allocations'),
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form',
        }
    def action_view_greenhouse_management(self):
        """Action to view greenhouse management"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Greenhouse Management'),
            'res_model': 'agricultural.farm',
            'view_mode': 'list,form',
        }
    def action_calculate_costs(self):
        """Action to calculate costs for current period"""
        self.ensure_one()

        # Get current month date range
        today = fields.Date.context_today(self)
        date_from = today.replace(day=1)
        date_to = (date_from + relativedelta(months=1)) - timedelta(days=1)

        # Create cost calculation
        calculation = self.env['agri.cost.calculation'].create({
            'name': f"Cost Calculation - {self.display_name} - {today.strftime('%B %Y')}",
            'date_from': date_from,
            'date_to': date_to,
            'farm_id': self.id,
        })

        calculation.action_calculate_costs()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Cost Calculation'),
            'res_model': 'agri.cost.calculation',
            'res_id': calculation.id,
            'view_mode': 'form',
            'target': 'current',
        }
    def get_cost_breakdown_data(self):
        """Get cost breakdown data for reporting"""
        self.ensure_one()
        return {
            'farm_name': self.display_name,
            'total_cost': self.total_cost,
            'seed_costs': self.seed_costs,
            'fertilizer_costs': self.fertilizer_costs,
            'pesticide_costs': self.pesticide_costs,
            'labor_costs': self.total_wages,
            'overhead_costs': self.overhead_costs,
            'cost_per_hectare': self.cost_per_hectare,
            'area_utilization': self.area_utilization_percentage,
            'profit_loss': self.profit_loss,
        }
    @api.depends('area_hectares', 'cultivated_area_hectares')
    def _compute_area_calculations(self):
        """Compute area-related calculations"""
        for record in self:
            record.available_area_hectares = record.area_hectares - record.cultivated_area_hectares
            if record.area_hectares > 0:
                record.area_utilization_percentage = (record.cultivated_area_hectares / record.area_hectares) * 100
            else:
                record.area_utilization_percentage = 0
    @api.depends('child_ids.area_hectares', 'area_hectares')
    def _compute_total_area(self):
        """Compute total area including children"""
        for record in self:
            if record.child_ids:
                record.total_area = sum(record.child_ids.mapped('area_hectares'))
            else:
                record.total_area = record.area_hectares
    @api.depends('child_ids', 'worker_ids')
    def _compute_counts(self):
        """Compute basic count fields"""
        for record in self:
            record.child_count = len(record.child_ids)
            record.employee_count = len(record.worker_ids)
    @api.depends('child_ids.level')
    def _compute_level_counts(self):
        """Compute level-specific counts"""
        for record in self:
            record.sector_count = len(record.child_ids.filtered(lambda x: x.level == 'sector'))
            record.house_count = len(record.child_ids.filtered(lambda x: x.level == 'house'))
            record.unit_count = len(record.child_ids.filtered(lambda x: x.level == 'unit'))
    def _compute_greenhouse_stats(self):
        """Compute greenhouse statistics"""
        for record in self:
            record.greenhouse_count = 0
    @api.depends('project_ids.state')
    def _compute_project_stats(self):
        """Compute project statistics"""
        for record in self:
            record.active_project_count = len(
                record.project_ids.filtered(lambda p: p.state not in ['cancelled', 'done']))
    @api.depends('analytic_account_id')
    def _compute_analytic_stats(self):
        """Compute analytic account statistics"""
        for record in self:
            if record.analytic_account_id:
                record.analytic_line_count = self.env['account.analytic.line'].search_count([
                    ('account_id', '=', record.analytic_account_id.id)
                ])
                record.project_count = len(record.project_ids)
            else:
                record.analytic_line_count = 0
                record.project_count = 0
    @api.depends('name', 'code', 'parent_id.display_name')
    def _compute_display_name(self):
        """Enhanced display name computation"""
        for record in self:
            if record.parent_id:
                record.display_name = f"{record.name}"
            else:
                record.display_name = f"[{record.code}] {record.name}" if record.code else record.name
    @api.depends('company_id')
    def _compute_currency_id(self):
        """Compute currency based on company with safe handling"""
        for record in self:
            try:
                if record.company_id and record.company_id.currency_id:
                    record.currency_id = record.company_id.currency_id
                else:
                    # Fallback to default currency
                    default_currency = self.env.company.currency_id
                    if default_currency:
                        record.currency_id = default_currency
                    else:
                        # Last resort - get any currency
                        currency = self.env['res.currency'].search([], limit=1)
                        record.currency_id = currency.id if currency else False
            except Exception as e:
                _logger.warning(f"Error computing currency for farm {record.id}: {e}")
                record.currency_id = False
    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure code is unique"""
        for record in self:
            if record.code:
                existing = self.search([
                    ('code', '=', record.code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('Farm code "%s" already exists!') % record.code)
    @api.constrains('area_hectares')
    def _check_area_positive(self):
        """Ensure area is positive"""
        for record in self:
            if record.area_hectares and record.area_hectares <= 0:
                raise ValidationError(_('Area cannot be negative!'))
    @api.model_create_multi
    def create(self, vals_list):
        """Optimized create with batch processing and proper currency handling"""
        # Process each record's values
        for vals in vals_list:
            # Auto-generate codes
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('agricultural.farm') or 'FARM'

            # Set default company if not provided
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id

        # Create records with proper transaction handling
        try:
            records = super().create(vals_list)

            # Batch setup after creation
            farms_need_cost_center = records.filtered(lambda r: not r.analytic_account_id)
            houses_need_location = records.filtered(lambda r: r.level == 'house' and not r.location_id)

            if farms_need_cost_center:
                farms_need_cost_center._batch_setup_cost_centers()

            if houses_need_location:
                houses_need_location._batch_setup_stock_locations()

            return records

        except Exception as e:
            _logger.error(f"Error creating agricultural farm records: {e}")
            # Re-raise the exception to maintain transaction integrity
            raise
    def write(self, vals):
        """Optimized write with change tracking"""
        # Track significant changes
        update_children_fields = ['responsible_user_id', 'company_id', 'farm_manager', 'warehouse_id']
        should_update_children = any(field in vals for field in update_children_fields)

        # Validate parent changes
        if 'parent_id' in vals:
            farms_with_children = self.filtered(lambda r: r.child_ids)
            if farms_with_children:
                raise UserError(_('Cannot change parent when there are child locations!'))

        result = super().write(vals)

        # Update children if needed
        if should_update_children:
            farms_and_sectors = self.filtered(lambda r: r.level in ['farm', 'sector'])
            if farms_and_sectors:
                farms_and_sectors._batch_update_children_data(vals)

        # Setup missing cost centers or locations
        if 'level' in vals:
            new_houses = self.filtered(lambda r: r.level == 'house' and not r.location_id)
            if new_houses:
                new_houses._batch_setup_stock_locations()

        return result
    @api.ondelete(at_uninstall=False)
    def _unlink_except_with_children(self):
        """Prevent deletion of farms with children"""
        if self.filtered(lambda r: r.child_ids):
            raise UserError(_('Cannot delete farms that have child locations!'))
    def _batch_setup_cost_centers(self):
        """Batch setup of cost centers for multiple farms"""

        AnalyticAccount = self.env['account.analytic.account']
        AnalyticPlan = self.env['account.analytic.plan']

        # Get or create default plan
        default_plan = AnalyticPlan.search([
            ('name', '=', 'Agricultural Projects')
        ], limit=1)

        if not default_plan:
            default_plan = AnalyticPlan.sudo().create({
                'name': 'Agricultural Projects',
                'default_applicability': 'optional',
                'description': 'Default plan for agricultural project cost tracking',
            })


        # Batch create analytic accounts
        create_vals = []
        for farm in self:
            if not farm.analytic_account_id:
                create_vals.append({
                    'name': f"{farm.code} - {farm.name}",
                    'plan_id': default_plan.id,
                    'company_id': farm.company_id.id,
                    'partner_id': farm.company_id.partner_id.id,
                })

        if create_vals:
            accounts = AnalyticAccount.create(create_vals)
            for farm, account in zip(self, accounts):
                farm.analytic_account_id = account.id
    def _batch_setup_stock_locations(self):
        """Batch setup of stock locations for multiple houses"""
        if not self:
            return

        stocklocation = self.env['stock.location']

        # Get default parent location
        default_parent = self.env.ref('stock.stock_location_stock', False)

        create_vals = []
        location_map = {}

        for house in self:
            if house.level != 'house' or house.location_id:
                continue

            # Use warehouse location if available
            parent_location = default_parent
            if house.warehouse_id and house.warehouse_id.lot_stock_id:
                parent_location = house.warehouse_id.lot_stock_id

            create_vals.append({
                'name': f"{house.code} - {house.name}",
                'location_id': parent_location.id,
                'usage': 'internal',
                'company_id': house.company_id.id,
            })
            location_map[len(create_vals) - 1] = house

        if create_vals:
            locations = stocklocation.create(create_vals)
            for index, location in enumerate(locations):
                house = location_map[index]
                house.location_id = location.id
    def _batch_update_children_data(self, update_vals):
        """Batch update children data"""
        if not self:
            return

        # Get all children that need updates
        all_children = self.env['agricultural.farm']
        for farm in self:
            all_children |= farm.child_ids

        if not all_children:
            return

        # Prepare update values
        child_update_vals = {}
        for field in ['responsible_user_id', 'company_id', 'farm_manager', 'warehouse_id']:
            if field in update_vals:
                child_update_vals[field] = update_vals[field]

        if child_update_vals:
            all_children.write(child_update_vals)

            # Recursive update for sectors
            sectors = all_children.filtered(lambda r: r.level == 'sector')
            if sectors:
                sectors._batch_update_children_data(child_update_vals)
    def action_view_children(self):
        """View child locations with enhanced context"""
        self.ensure_one()
        return {
            'name': _('Sub Locations - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.farm',
            'view_mode': 'list,form,kanban',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_responsible_user_id': self.responsible_user_id.id,
                'default_company_id': self.company_id.id,
                'default_farm_manager': self.farm_manager.id if self.farm_manager else False,
                'default_warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
                'group_by': 'level',
            }
        }
    def action_view_financial_dashboard(self):
        """View comprehensive financial dashboard"""
        self.ensure_one()
        if not self.analytic_account_id:
            raise UserError(_('No cost center configured for this farm!'))

        return {
            'name': _('Financial Dashboard - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'pivot,graph,list',
            'domain': self._get_analytic_domain(),
            'context': {
                'search_default_group_by_date': 1,
                'search_default_group_by_product': 1,
                'pivot_measures': ['amount'],
                'graph_measure': 'amount',
                'graph_type': 'bar',
            }
        }
    def action_view_employees(self):
        """View all assigned employees"""
        self.ensure_one()
        employee_ids = self._get_all_employee_ids()

        return {
            'name': _('Farm Employees - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', employee_ids)],
            'context': {
                'search_default_group_by_job': 1,
            }
        }
    def action_view_stock_dashboard(self):
        """View stock movements dashboard"""
        self.ensure_one()
        location_ids = self._get_all_location_ids()

        if not location_ids:
            raise UserError(_('No stock locations configured for this farm!'))

        return {
            'name': _('Stock Dashboard - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_mode': 'list,graph,pivot',
            'domain': [
                '|',
                ('location_id', 'in', location_ids),
                ('location_dest_id', 'in', location_ids)
            ],
            'context': {
                'search_default_group_by_product': 1,
                'search_default_group_by_date': 1,
                'pivot_measures': ['qty_done'],
            }
        }
    def action_production_request(self):
        """Create production request"""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Production Request"),
            'res_model': 'agricultural.production.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_farm_id': self.id,
                'default_responsible_user_id': self.responsible_user_id.id,
            }
        }
    def _get_analytic_domain(self):
        """Get domain for analytic queries"""
        account_ids = self._get_analytic_account_ids()
        return [('account_id', 'in', account_ids)]
    def _get_all_employee_ids(self):
        """Get all employee IDs associated with this farm"""
        employee_ids = []
        if self.farm_manager:
            employee_ids.append(self.farm_manager.id)
        if self.agricultural_engineer:
            employee_ids.append(self.agricultural_engineer.id)
        if self.veterinarian:
            employee_ids.append(self.veterinarian.id)
        employee_ids.extend(self.worker_ids.ids)
        return employee_ids
    def _get_all_location_ids(self):
        """Get all stock location IDs for this farm"""
        location_ids = []
        if self.location_id:
            location_ids.append(self.location_id.id)

        if self.level == 'farm':
            descendants = self.search([
                ('parent_path', 'like', f"{self.parent_path}%"),
                ('id', '!=', self.id),
                ('location_id', '!=', False)
            ])
            location_ids.extend(descendants.mapped('location_id.id'))

        return location_ids
    @api.model
    def get_farm_statistics(self, domain=None):
        """Get comprehensive farm statistics"""
        if domain is None:
            domain = [('level', '=', 'farm')]

        farms = self.search(domain)

        return {
            'total_farms': len(farms),
            'total_area': sum(farms.mapped('total_area')),
            'total_sectors': sum(farms.mapped('sector_count')),
            'total_houses': sum(farms.mapped('house_count')),
            'total_employees': sum(farms.mapped('employee_count')),
            'financial_summary': {
                'total_costs': sum(farms.mapped('total_cost')),
                'total_sales': sum(farms.mapped('total_sales')),
                'total_profit': sum(farms.mapped('profit_loss')),
                'total_wages': sum(farms.mapped('total_wages')),
            },
            'farms_data': [self._get_farm_summary(farm) for farm in farms]
        }
    def _get_farm_summary(self, farm):
        """Get summary data for a single farm"""
        return {
            'id': farm.id,
            'name': farm.name,
            'code': farm.code,
            'level': farm.level,
            'manager': farm.farm_manager.name if farm.farm_manager else '',
            'area': farm.total_area,
            'employee_count': farm.employee_count,
            'profit_loss': farm.profit_loss,
            'children_count': {
                'sectors': farm.sector_count,
                'units': farm.unit_count,
                'houses': farm.house_count,
            }
        }
    @api.model
    def get_hierarchy_list(self, farm_id=None):
        """Get complete hierarchy list"""
        if farm_id:
            root_farms = self.browse(farm_id)
        else:
            root_farms = self.search([('level', '=', 'farm')])

        return [self._build_list_node(farm) for farm in root_farms]
    def _build_list_node(self, node):
        """Build list node recursively"""
        return {
            'id': node.id,
            'name': node.display_name,
            'level': node.level,
            'color': node.color_hex,
            'area': node.total_area,
            'employee_count': node.employee_count,
            'profit_loss': float(node.profit_loss),
            'children': [self._build_list_node(child) for child in node.child_ids]
        }
    @api.model
    def create_farm_hierarchy(self, farm_data):
        """Create complete farm hierarchy from data structure"""

        def create_node(data, parent_id=None):
            node_vals = {
                'name': data['name'],
                'code': data.get('code'),
                'parent_id': parent_id,
                'area_hectares': data.get('area_hectares', 0.0),
                'farm_type': data.get('farm_type'),
                'soil_type': data.get('soil_type'),
                'irrigation_type': data.get('irrigation_type'),
            }

            # Add other fields if provided
            for field in ['responsible_user_id', 'company_id', 'farm_manager', 'warehouse_id']:
                if field in data:
                    node_vals[field] = data[field]

            node = self.create(node_vals)

            # Create children recursively
            for child_data in data.get('children', []):
                create_node(child_data, node.id)

            return node

        return create_node(farm_data)
    def export_hierarchy(self):
        """Export farm hierarchy to dictionary"""
        self.ensure_one()

        def export_node(node):
            data = {
                'name': node.name,
                'code': node.code,
                'level': node.level,
                'area_hectares': node.area_hectares,
                'farm_type': node.farm_type,
                'soil_type': node.soil_type,
                'irrigation_type': node.irrigation_type,
                'house_type': node.house_type,
                'location': node.location,
                'children': [export_node(child) for child in node.child_ids]
            }
            return data

        return export_node(self)
    def get_farm_kpis(self):
        """Get Key Performance Indicators for the farm"""
        self.ensure_one()

        # Calculate efficiency metrics
        revenue_per_hectare = (self.total_sales / self.total_area) if self.total_area else 0
        cost_per_hectare = (self.total_cost / self.total_area) if self.total_area else 0
        profit_margin = ((self.total_sales - self.total_cost) / self.total_sales * 100) if self.total_sales else 0
        employees_per_hectare = (self.employee_count / self.total_area) if self.total_area else 0

        return {
            'financial': {
                'revenue_per_hectare': revenue_per_hectare,
                'cost_per_hectare': cost_per_hectare,
                'profit_margin': profit_margin,
                'total_profit': self.profit_loss,
            },
            'operational': {
                'total_area': self.total_area,
                'employees_per_hectare': employees_per_hectare,
                'total_employees': self.employee_count,
            },
            'structure': {
                'total_sectors': self.sector_count,
                'total_houses': self.house_count,
                'hierarchy_depth': len(self.parent_path.split('/')) if self.parent_path else 1,
            }
        }
    def action_view_financial_report(self):
        """View comprehensive financial report"""
        self.ensure_one()
        if not self.analytic_account_id:
            raise UserError(_('No cost center configured for this farm!'))

        return {
            'name': _('Financial Report - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'pivot,graph,list',
            'domain': self._get_analytic_domain(),
            'context': {
                'search_default_group_by_account': 1,
                'search_default_group_by_date': 1,
                'search_default_group_by_product': 1,
                'pivot_measures': ['amount'],
                'graph_measure': 'amount',
                'graph_type': 'bar',
            }
        }
    def action_view_cost_analysis(self):
        """View detailed cost analysis"""
        self.ensure_one()
        if not self.analytic_account_id:
            raise UserError(_('No cost center configured for this farm!'))

        return {
            'name': _('Cost Analysis - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'pivot,graph,list',
            'domain': self._get_analytic_domain() + [('amount', '<', 0)],
            'context': {
                'search_default_group_by_product': 1,
                'search_default_group_by_general_account': 1,
                'pivot_measures': ['amount'],
                'graph_measure': 'amount',
            }
        }
    def action_view_production_report(self):
        """View production and sales report"""
        self.ensure_one()
        location_ids = self._get_all_location_ids()

        if not location_ids:
            raise UserError(_('No stock locations configured for this farm!'))

        return {
            'name': _('Production Report - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_mode': 'pivot,graph,list',
            'domain': self._get_stock_domain(),
            'context': {
                'search_default_group_by_product': 1,
                'search_default_group_by_date': 1,
                'pivot_measures': ['qty_done'],
                'graph_measure': 'qty_done',
            }
        }
    def action_view_wage_report(self):
        """View wage and payroll report"""
        self.ensure_one()
        employee_ids = self._get_all_employee_ids()

        if not employee_ids:
            raise UserError(_('No employees assigned to this farm!'))

        # Check if hr_payroll module is installed
        if 'hr.payslip' not in self.env:
            raise UserError(_('Payroll module is not installed!'))

        return {
            'name': _('Wage Report - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form,pivot',
            'domain': [('employee_id', 'in', employee_ids)],
            'context': {
                'search_default_group_by_employee': 1,
                'search_default_group_by_date': 1,
            }
        }
    def action_dashboard_report(self):
        """Open comprehensive dashboard"""
        self.ensure_one()
        return {
            'name': _('Farm Dashboard - %s') % self.name,
            'type': 'ir.actions.client',
            'tag': 'farm_dashboard',
            'context': {
                'farm_id': self.id,
                'farm_data': self._get_farm_summary(self),
            }
        }
    def action_view_analytic_lines(self):
        """View analytic lines"""
        self.ensure_one()
        if not self.analytic_account_id:
            raise UserError(_('No cost center configured for this farm!'))

        return {
            'name': _('Cost Center Analytics - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'list,graph,pivot',
            'domain': self._get_analytic_domain(),
            'context': {
                'search_default_group_by_date': 1,
                'search_default_group_by_product': 1,
            }
        }
    def action_setup_cost_center(self):
        """Setup cost center if not exists"""
        self.ensure_one()
        if not self.analytic_account_id:
            self._setup_cost_center()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Cost center has been created successfully!'),
                    'type': 'success',
                }
            }
        else:
            raise UserError(_('Cost center already exists for this farm!'))
    def action_setup_stock_location(self):
        """Setup stock location for houses"""
        self.ensure_one()
        if self.level != 'house':
            raise UserError(_('Stock locations can only be created for houses!'))

        if not self.location_id:
            self._setup_stock_location()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Stock location has been created successfully!'),
                    'type': 'success',
                }
            }
        else:
            raise UserError(_('Stock location already exists for this house!'))
    def _get_stock_domain(self):
        """Get domain for stock queries"""
        self.ensure_one()
        location_ids = self._get_all_location_ids()
        if not location_ids:
            return [('id', '=', False)]  # Return empty domain if no locations

        return [
            '|',
            ('location_id', 'in', location_ids),
            ('location_dest_id', 'in', location_ids)
        ]
    def _setup_stock_location(self):
        """Setup stock location for house level"""
        self.ensure_one()
        if self.level != 'house' or self.location_id:
            return

        stocklocation = self.env['stock.location']

        # Find or create parent location
        parent_location = self.env.ref('stock.stock_location_stock', False)
        if self.warehouse_id and self.warehouse_id.lot_stock_id:
            parent_location = self.warehouse_id.lot_stock_id

        location = stocklocation.create({
            'name': f"{self.code or self.name} - Stock",
            'location_id': parent_location.id,
            'usage': 'internal',
            'company_id': self.company_id.id,
        })

        self.location_id = location.id
        return location
    def _setup_cost_center(self):
        """Setup cost center (analytic account) for the farm"""
        self.ensure_one()
        if self.analytic_account_id:
            return self.analytic_account_id

        AnalyticAccount = self.env['account.analytic.account']
        AnalyticPlan = self.env['account.analytic.plan']

        # Get or create default analytic plan
        default_plan = AnalyticPlan.search([
            ('name', '=', 'Agricultural Projects')
        ], limit=1)

        if not default_plan:
            default_plan = AnalyticPlan.create({
                'name': 'Agricultural Projects',
                'default_applicability': 'optional',
                'description': 'Default plan for agricultural project cost tracking',
            })

        # Create analytic account
        account = AnalyticAccount.create({
            'name': f"{self.code or 'FARM'} - {self.name}",
            'plan_id': default_plan.id,
            'company_id': self.company_id.id,
        })

        self.analytic_account_id = account.id
        return account
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        """Enhanced name search including code and location"""
        args = args or []
        domain = []

        if name:
            domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('display_name', operator, name),
                ('location', operator, name)
            ]

        # Use the provided order or fall back to the model's default order
        search_order = order or self._order

        return self._search(domain + args, limit=limit, order=search_order, access_rights_uid=name_get_uid)
    def name_get(self):
        """Enhanced name_get with context awareness"""
        result = []
        for record in self:
            name = record.display_name or record.name
            if self.env.context.get('show_full_path') and record.parent_id:
                name = f"{record.parent_id.name} / {name}"
            result.append((record.id, name))
        return result
    def _validate_prices(self):
        """Validate prices against market rates - placeholder implementation"""
        # This would contain price validation logic
        # For now, we'll add a simple implementation
        pass
    def agricultural_production_request_action(self):
        """Create production request action"""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Production Request"),
            'res_model': 'agricultural.production.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_farm_id': self.id,
                'default_responsible_user_id': self.responsible_user_id.id,
            }
        }
    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        """Update fields based on parent"""
        if self.parent_id:
            self.responsible_user_id = self.parent_id.responsible_user_id
            self.company_id = self.parent_id.company_id
            if not self.farm_manager and self.parent_id.level == 'farm':
                self.farm_manager = self.parent_id.farm_manager
            if not self.warehouse_id:
                self.warehouse_id = self.parent_id.warehouse_id
    @api.onchange('level')
    def _onchange_level(self):
        """Clear inappropriate fields based on level"""
        if self.level == 'house':
            # Houses can have specific types
            pass
        elif self.level in ['farm', 'sector']:
            # Clear house-specific fields
            self.house_type = False
    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        """Update picking types when warehouse changes"""
        if self.warehouse_id:
            self.picking_type_harvest_id = self.warehouse_id.in_type_id
            self.picking_type_internal_id = self.warehouse_id.int_type_id
    def action_view_cost_center(self):
        """View cost center analytics"""
        self.ensure_one()
        if not self.analytic_account_id:
            raise UserError(_('No cost center configured for this farm!'))

        return {
            'name': _('Cost Center Analytics - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'list,graph,pivot',
            'domain': [('account_id', '=', self.analytic_account_id.id)],
            'context': {
                'search_default_group_by_date': 1,
                'search_default_group_by_product': 1,
            }
        }
    def action_view_sectors(self):
        """View sectors under this farm"""
        self.ensure_one()
        return {
            'name': _('Sectors - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.farm',
            'view_mode': 'list,form,kanban',
            'domain': [('parent_id', '=', self.id), ('level', '=', 'sector')],
            'context': {
                'default_parent_id': self.id,
                'default_level': 'sector',
                'default_responsible_user_id': self.responsible_user_id.id,
                'default_company_id': self.company_id.id,
                'default_farm_manager': self.farm_manager.id if self.farm_manager else False,
            }
        }
    def action_view_houses(self):
        """View houses under this farm"""
        self.ensure_one()
        return {
            'name': _('Houses - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.farm',
            'view_mode': 'list,form,kanban',
            'domain': [('parent_id', 'child_of', self.id), ('level', '=', 'house')],
            'context': {
                'default_level': 'house',
                'default_responsible_user_id': self.responsible_user_id.id,
                'default_company_id': self.company_id.id,
                'default_farm_manager': self.farm_manager.id if self.farm_manager else False,
            }
        }
    def action_view_projects(self):
        """View projects related to this farm"""
        self.ensure_one()
        if not self.analytic_account_id:
            raise UserError(_('No cost center configured for this farm!'))

        # Check if project module exists
        if 'project.project' not in self.env:
            raise UserError(_('Project module is not installed!'))

        return {
            'name': _('Projects - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'list,form,kanban',
            'domain': [('analytic_account_id', '=', self.analytic_account_id.id)],
            'context': {
                'default_analytic_account_id': self.analytic_account_id.id,
            }
        }
    def action_view_current_crops(self):
        """View current crops"""
        self.ensure_one()
        return {
            'name': _('Current Crops - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', self.current_crop_ids.ids)],
            'context': {
                'search_default_categ_id': 'Crop',
            }
        }
    def action_view_produced_products(self):
        """View produced products"""
        self.ensure_one()
        return {
            'name': _('Produced Products - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', self.produced_product_ids.ids)],
            'context': {'create': False}
        }
    def action_view_consumed_products(self):
        """View consumed products"""
        self.ensure_one()
        return {
            'name': _('Consumed Products - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', self.consumed_product_ids.ids)],
            'context': {'create': False}
        }
    def action_view_seed_products(self):
        """View seed products"""
        self.ensure_one()
        return {
            'name': _('Seed Products - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', self.seed_product_ids.ids)],
            'context': {'create': False}
        }
    def action_open_warehouse(self):
        """Open warehouse management"""
        self.ensure_one()
        if not self.warehouse_id:
            raise UserError(_('No warehouse configured for this farm!'))

        return {
            'name': _('Warehouse - %s') % self.warehouse_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.warehouse',
            'res_id': self.warehouse_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    def action_open_location(self):
        """Open stock location"""
        self.ensure_one()
        if not self.location_id:
            raise UserError(_('No stock location configured for this farm!'))

        return {
            'name': _('Stock Location - %s') % self.location_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.location',
            'res_id': self.location_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    def action_view_stock_quants(self):
        """View stock quantities"""
        self.ensure_one()
        location_ids = self._get_all_location_ids()

        if not location_ids:
            raise UserError(_('No stock locations configured!'))

        return {
            'name': _('Stock Quantities - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'list',
            'domain': [('location_id', 'in', location_ids)],
            'context': {
                'search_default_internal_loc': 1,
                'search_default_productgroup': 1,
            }
        }
    def action_view_inventory(self):
        """View inventory adjustments"""
        self.ensure_one()
        location_ids = self._get_all_location_ids()

        if not location_ids:
            raise UserError(_('No stock locations configured!'))

        return {
            'name': _('Inventory Adjustments - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.inventory',
            'view_mode': 'list,form',
            'domain': [('location_ids', 'in', location_ids)],
            'context': {
                'default_location_ids': [(6, 0, location_ids)],
            }
        }
    def action_create_production_request(self):
        """Create production request"""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Production Request"),
            'res_model': 'agricultural.production.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_farm_id': self.id,
                'default_responsible_user_id': self.responsible_user_id.id,
            }
        }

    def action_setup_farm(self):
        """Setup farm wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Farm Setup"),
            'res_model': 'agricultural.farm.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_farm_id': self.id,
            }
        }
    def action_view_purchase_orders(self):
        """View purchase orders for this farm"""
        self.ensure_one()
        if not self.analytic_account_id:
            raise UserError(_('No cost center configured for this farm!'))

        return {
            'name': _('Purchase Orders - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [
                '|',
                ('order_line.analytic_distribution', 'like', str(self.analytic_account_id.id)),
                ('partner_id', '=', self.company_id.partner_id.id)
            ],
            'context': {
                'default_analytic_distribution': {str(self.analytic_account_id.id): 100},
            }
        }
    def action_view_sale_orders(self):
        """View sale orders for this farm"""
        self.ensure_one()
        if not self.analytic_account_id:
            raise UserError(_('No cost center configured for this farm!'))

        return {
            'name': _('Sale Orders - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                'order_line.analytic_distribution', 'like', str(self.analytic_account_id.id)
            ],
            'context': {
                'default_analytic_distribution': {str(self.analytic_account_id.id): 100},
            }
        }
    def action_toggle_active(self):
        """Toggle active status"""
        for record in self:
            record.active = not record.active
    def action_archive(self):
        """Archive farm"""
        self.write({'active': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Archived'),
                'message': _('Farm has been archived successfully'),
                'type': 'success',
            }
        }
    def action_unarchive(self):
        """Unarchive farm"""
        self.write({'active': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Restored'),
                'message': _('Farm has been restored successfully'),
                'type': 'success',
            }
        }
    def action_view_all_children(self):
        """View all child locations"""
        self.ensure_one()
        return {
            'name': _('All Sub-Locations - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.farm',
            'view_mode': 'list,form,kanban',
            'domain': [('parent_id', 'child_of', self.id), ('id', '!=', self.id)],
            'context': {
                'group_by': 'level',
                'expand': 1,
            }
        }
    def action_print_farm_report(self):
        """Print farm report"""
        return self.env.ref('agricultural_management.action_report_farm').report_action(self)
    def action_export_farm_data(self):
        """Export farm data"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/export_farm/{self.id}',
            'target': 'self',
        }
    def get_farm_hierarchy_data(self):
        """Get hierarchy data for this farm"""
        return {
            'farm': self.read(['id', 'name', 'code', 'level', 'area_hectares'])[0],
            'sectors': self.child_ids.filtered(lambda x: x.level == 'sector').read(['id', 'name', 'code']),
            'houses': self.search([('parent_id', 'child_of', self.id), ('level', '=', 'house')]).read(
                ['id', 'name', 'code']),
        }
    def get_financial_summary(self):
        """Get financial summary"""
        return {
            'total_cost': self.total_cost,
            'total_sales': self.total_sales,
            'profit_loss': self.profit_loss,
            'total_wages': self.total_wages,
            'seed_costs': self.seed_costs,
            'total_expenses': self.total_expenses,
        }
    def _get_analytic_account_ids(self):
        """Get all analytic account IDs for this farm and descendants with safe handling"""
        self.ensure_one()
        account_ids = []

        try:
            if self.analytic_account_id:
                account_ids.append(self.analytic_account_id.id)

            # Only search for descendants if this is a saved record and it's a farm level
            if (self.level == 'farm' and
                    self.id and
                    not str(self.id).startswith('NewId')):

                try:
                    # Safer approach without using parent_path initially
                    descendants = self.search([
                        ('id', 'child_of', self.id),
                        ('id', '!=', self.id),
                        ('analytic_account_id', '!=', False)
                    ])
                    account_ids.extend(descendants.mapped('analytic_account_id.id'))
                except Exception as search_error:
                    _logger.warning(f"Error searching descendants for farm {self.id}: {search_error}")
                    # Try to rollback this specific query
                    try:
                        self._cr.rollback_to_savepoint('before_descendants_search')
                    except:
                        pass
        except Exception as e:
            _logger.warning(f"Error getting analytic account IDs for farm {self.id}: {e}")

        return account_ids

    # ========== OWL DASHBOARD DATA ==========
    @api.model
    def get_dashboard_data(self):
        """Return aggregated KPI data for the OWL Dashboard."""
        farms = self.search([('active', '=', True)])
        projects = self.env['agricultural.project'].search([])
        requests = self.env['agricultural.production.request'].search([('state', '=', 'draft')])

        farm_data = []
        total_revenue = 0.0
        total_cost = 0.0
        total_area = 0.0

        for farm in farms.filtered(lambda f: f.level in ('farm', 'sector')):
            rev = farm.total_sales or 0.0
            cost = farm.total_cost or 0.0
            area = farm.area_hectares or 0.0
            profit = rev - cost
            margin = round((profit / rev * 100), 1) if rev > 0 else 0.0

            total_revenue += rev
            total_cost += cost
            total_area += area

            farm_data.append({
                'id': farm.id,
                'name': farm.name or '',
                'level': farm.level or '',
                'area': round(area, 2),
                'revenue': round(rev, 2),
                'cost': round(cost, 2),
                'profit': round(profit, 2),
                'margin': margin,
            })

        net_profit = total_revenue - total_cost
        profit_margin = round((net_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0

        return {
            'kpis': {
                'total_farms': len(farms),
                'total_area': round(total_area, 2),
                'total_revenue': round(total_revenue, 2),
                'total_cost': round(total_cost, 2),
                'net_profit': round(net_profit, 2),
                'profit_margin': profit_margin,
                'active_projects': len(projects.filtered(
                    lambda p: p.state not in ('cancelled', 'completed')
                )),
                'pending_requests': len(requests),
                'harvest_count': self.env['agricultural.harvest.schedule'].search_count([]),
                'yield_efficiency': round(
                    (total_revenue / total_cost * 100) if total_cost > 0 else 0, 1
                ),
            },
            'farms': sorted(farm_data, key=lambda f: f['revenue'], reverse=True)[:10],
            'cost_breakdown': {
                'materials': 35,
                'labor': 30,
                'equipment': 20,
                'overhead': 15,
            },
        }
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Reverse relationships for agricultural farms
    managed_farm_ids = fields.One2many(
        'agricultural.farm',
        'farm_manager',
        string='Managed Farms',
        help='Farms where this employee is the manager'
    )

    engineered_farm_ids = fields.One2many(
        'agricultural.farm',
        'agricultural_engineer',
        string='Engineered Farms',
        help='Farms where this employee is the agricultural engineer'
    )

    veterinary_farm_ids = fields.One2many(
        'agricultural.farm',
        'veterinarian',
        string='Veterinary Farms',
        help='Farms where this employee is the veterinarian'
    )

    # Many2many reverse relationship for workers
    worker_farm_ids = fields.Many2many(
        'agricultural.farm',
        'farm_worker_rel',
        'employee_id',
        'farm_id',
        string='Working Farms',
        help='Farms where this employee works'
    )

    # Computed fields for counts
    managed_farm_count = fields.Integer(
        string='Managed Farms Count',
        compute='_compute_farm_counts'
    )

    engineered_farm_count = fields.Integer(
        string='Engineered Farms Count',
        compute='_compute_farm_counts'
    )

    veterinary_farm_count = fields.Integer(
        string='Veterinary Farms Count',
        compute='_compute_farm_counts'
    )

    worker_farm_count = fields.Integer(
        string='Working Farms Count',
        compute='_compute_farm_counts'
    )

    total_farm_count = fields.Integer(
        string='Total Related Farms',
        compute='_compute_farm_counts'
    )

    @api.depends('managed_farm_ids', 'engineered_farm_ids', 'veterinary_farm_ids', 'worker_farm_ids')
    def _compute_farm_counts(self):
        for employee in self:
            employee.managed_farm_count = len(employee.managed_farm_ids)
            employee.engineered_farm_count = len(employee.engineered_farm_ids)
            employee.veterinary_farm_count = len(employee.veterinary_farm_ids)
            employee.worker_farm_count = len(employee.worker_farm_ids)

            # Calculate total unique farms
            all_farms = (employee.managed_farm_ids |
                         employee.engineered_farm_ids |
                         employee.veterinary_farm_ids |
                         employee.worker_farm_ids)
            employee.total_farm_count = len(all_farms)
class ResUsers(models.Model):
    _inherit = 'res.users'

    # Reverse relationship for responsible farms
    responsible_farm_ids = fields.One2many(
        'agricultural.farm',
        'responsible_user_id',
        string='Responsible Farms',
        help='Farms where this user is responsible'
    )
    responsible_farm_count = fields.Integer(
        string='Responsible Farms Count',
    )

    # ========== AGRICULTURAL GROUP FIELDS FOR USER FORM ==========
    agricultural_role = fields.Selection([
        ('', ''),
        ('user', 'User'),
        ('engineer', 'Engineer / Agronomist'),
        ('manager', 'Manager'),
    ], string='Agricultural Role',
       compute='_compute_agricultural_groups',
       inverse='_inverse_agricultural_role', store=False)

    is_agri_warehouse_manager = fields.Boolean(
        'Warehouse Manager',
        compute='_compute_agricultural_groups',
        inverse='_inverse_agri_warehouse', store=False)

    is_agri_purchase_manager = fields.Boolean(
        'Purchase Manager',
        compute='_compute_agricultural_groups',
        inverse='_inverse_agri_purchase', store=False)

    is_agri_accountant = fields.Boolean(
        'Agricultural Accountant',
        compute='_compute_agricultural_groups',
        inverse='_inverse_agri_accountant', store=False)

    is_agri_section_user = fields.Boolean(
        'Section User',
        compute='_compute_agricultural_groups',
        inverse='_inverse_agri_section_user', store=False)

    is_agri_section_manager = fields.Boolean(
        'Section Manager',
        compute='_compute_agricultural_groups',
        inverse='_inverse_agri_section_manager', store=False)

    is_agri_post_entry = fields.Boolean(
        'Post Journal Entries',
        compute='_compute_agricultural_groups',
        inverse='_inverse_agri_post_entry', store=False)

    is_agri_reset_entry = fields.Boolean(
        'Reset Entries to Draft',
        compute='_compute_agricultural_groups',
        inverse='_inverse_agri_reset_entry', store=False)

    def _compute_agricultural_groups(self):
        for user in self:
            user.is_agri_warehouse_manager = user.has_group('agricultural_management.group_inventory_manager')
            user.is_agri_purchase_manager = user.has_group('agricultural_management.group_purchase_manager')
            user.is_agri_accountant = user.has_group('agricultural_management.group_accounts')
            user.is_agri_section_user = user.has_group('agricultural_management.group_section_user')
            user.is_agri_section_manager = user.has_group('agricultural_management.group_section_manager')
            user.is_agri_post_entry = user.has_group('agricultural_management.group_post_journal_entry')
            user.is_agri_reset_entry = user.has_group('agricultural_management.group_reset_journal_entry')
            # Selection: highest role wins
            if user.has_group('agricultural_management.group_agricultural_manager'):
                user.agricultural_role = 'manager'
            elif user.has_group('agricultural_management.group_agricultural_engineer'):
                user.agricultural_role = 'engineer'
            elif user.has_group('agricultural_management.group_agricultural_user'):
                user.agricultural_role = 'user'
            else:
                user.agricultural_role = ''

    def _set_agri_group(self, xmlid, value):
        group = self.env.ref(xmlid, raise_if_not_found=False)
        if not group:
            return
        # Odoo 19: use direct SQL on res_groups_users_rel
        if value:
            self.env.cr.execute("""
                INSERT INTO res_groups_users_rel (gid, uid)
                SELECT %s, %s WHERE NOT EXISTS (
                    SELECT 1 FROM res_groups_users_rel WHERE gid = %s AND uid = %s
                )
            """, (group.id, self.id, group.id, self.id))
        else:
            self.env.cr.execute("""
                DELETE FROM res_groups_users_rel WHERE gid = %s AND uid = %s
            """, (group.id, self.id))
        self.env.registry.clear_cache()

    def _inverse_agricultural_role(self):
        manager_g = self.env.ref('agricultural_management.group_agricultural_manager', False)
        engineer_g = self.env.ref('agricultural_management.group_agricultural_engineer', False)
        user_g = self.env.ref('agricultural_management.group_agricultural_user', False)
        for user in self:
            # Remove all first
            for g in [manager_g, engineer_g, user_g]:
                if g:
                    self.env.cr.execute(
                        "DELETE FROM res_groups_users_rel WHERE gid = %s AND uid = %s",
                        (g.id, user.id)
                    )
            # Add selected
            target = None
            if user.agricultural_role == 'manager':
                target = manager_g
            elif user.agricultural_role == 'engineer':
                target = engineer_g
            elif user.agricultural_role == 'user':
                target = user_g
            if target:
                self.env.cr.execute("""
                    INSERT INTO res_groups_users_rel (gid, uid)
                    SELECT %s, %s WHERE NOT EXISTS (
                        SELECT 1 FROM res_groups_users_rel WHERE gid = %s AND uid = %s
                    )
                """, (target.id, user.id, target.id, user.id))
            self.env.registry.clear_cache()

    def _inverse_agri_warehouse(self):
        for u in self:
            u._set_agri_group('agricultural_management.group_inventory_manager', u.is_agri_warehouse_manager)

    def _inverse_agri_purchase(self):
        for u in self:
            u._set_agri_group('agricultural_management.group_purchase_manager', u.is_agri_purchase_manager)

    def _inverse_agri_accountant(self):
        for u in self:
            u._set_agri_group('agricultural_management.group_accounts', u.is_agri_accountant)

    def _inverse_agri_section_user(self):
        for u in self:
            u._set_agri_group('agricultural_management.group_section_user', u.is_agri_section_user)

    def _inverse_agri_section_manager(self):
        for u in self:
            u._set_agri_group('agricultural_management.group_section_manager', u.is_agri_section_manager)

    def _inverse_agri_post_entry(self):
        for u in self:
            u._set_agri_group('agricultural_management.group_post_journal_entry', u.is_agri_post_entry)

    def _inverse_agri_reset_entry(self):
        for u in self:
            u._set_agri_group('agricultural_management.group_reset_journal_entry', u.is_agri_reset_entry)

    @api.depends('responsible_farm_ids')
    def _compute_responsible_farm_count(self):
        for user in self:
            user.responsible_farm_count = len(user.responsible_farm_ids)
class ResCompany(models.Model):
    _inherit = 'res.company'

    # Reverse relationship for company farms
    farm_ids = fields.One2many(
        'agricultural.farm',
        'company_id',
        string='Agricultural Farms',
        help='All farms belonging to this company'
    )

    farm_count = fields.Integer(
        string='Farms Count',
        compute='_compute_farm_count'
    )

    total_farm_area = fields.Float(
        string='Total Farm Area (Hectares)',
        compute='_compute_farm_statistics',
        digits=(10, 2)
    )

    active_farm_count = fields.Integer(
        string='Active Farms Count',
        compute='_compute_farm_statistics'
    )

    @api.depends('farm_ids')
    def _compute_farm_count(self):
        for company in self:
            company.farm_count = len(company.farm_ids)

    @api.depends('farm_ids.area_hectares', 'farm_ids.active')
    def _compute_farm_statistics(self):
        for company in self:
            active_farms = company.farm_ids.filtered('active')
            company.active_farm_count = len(active_farms)
            company.total_farm_area = sum(active_farms.mapped('area_hectares'))
class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # Reverse relationship for farms using this analytic account
    farm_ids = fields.One2many(
        'agricultural.farm',
        'analytic_account_id',
        string='Agricultural Farms',
        help='Farms using this analytic account'
    )
    date = fields.Date(string="Date")
    ref = fields.Char(string="ref")
    account_id = fields.Many2one('account.account')
    unit_amount = fields.Float()
    farm_count = fields.Integer(
        string='Farms Count',
        compute='_compute_farm_count'
    )
    project_id = fields.Many2one('agricultural.project')
    amount = fields.Float('Amount', digits=(12, 2), store=True)

    @api.depends('farm_ids')
    def _compute_farm_count(self):
        for account in self:
            account.farm_count = len(account.farm_ids)
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    # Reverse relationship for farms using this warehouse
    farm_ids = fields.One2many(
        'agricultural.farm',
        'warehouse_id',
        string='Agricultural Farms',
        help='Farms using this warehouse'
    )

    farm_count = fields.Integer(
        string='Farms Count',
        compute='_compute_farm_count'
    )
    harvest_schedule_ids = fields.One2many('agricultural.harvest.schedule', 'warehouse_id')
    @api.depends('farm_ids')
    def _compute_farm_count(self):
        for warehouse in self:
            warehouse.farm_count = len(warehouse.farm_ids)
class StockLocation(models.Model):
    _inherit = 'stock.location'

    # Reverse relationship for farms using this location
    farm_ids = fields.One2many(
        'agricultural.farm',
        'location_id',
        string='Agricultural Farms',
        help='Farms using this stock location'
    )

    farm_count = fields.Integer(
        string='Farms Count',
        compute='_compute_farm_count'
    )

    @api.depends('farm_ids')
    def _compute_farm_count(self):
        for location in self:
            location.farm_count = len(location.farm_ids)
class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    # Reverse relationships for harvest and internal operations
    harvest_farm_ids = fields.One2many(
        'agricultural.farm',
        'picking_type_harvest_id',
        string='Harvest Farms',
        help='Farms using this picking type for harvest operations'
    )

    internal_farm_ids = fields.One2many(
        'agricultural.farm',
        'picking_type_internal_id',
        string='Internal Transfer Farms',
        help='Farms using this picking type for internal transfers'
    )

    harvest_farm_count = fields.Integer(
        string='Harvest Farms Count',
        compute='_compute_farm_counts'
    )

    internal_farm_count = fields.Integer(
        string='Internal Transfer Farms Count',
        compute='_compute_farm_counts'
    )

    total_farm_count = fields.Integer(
        string='Total Related Farms',
        compute='_compute_farm_counts'
    )

    @api.depends('harvest_farm_ids', 'internal_farm_ids')
    def _compute_farm_counts(self):
        for picking_type in self:
            picking_type.harvest_farm_count = len(picking_type.harvest_farm_ids)
            picking_type.internal_farm_count = len(picking_type.internal_farm_ids)

            # Calculate total unique farms
            all_farms = picking_type.harvest_farm_ids | picking_type.internal_farm_ids
            picking_type.total_farm_count = len(all_farms)
class ResCurrency(models.Model):
    _inherit = 'res.currency'

    # Reverse relationship for farms using this currency
    farm_ids = fields.One2many(
        'agricultural.farm',
        'currency_id',
        string='Agricultural Farms',
        help='Farms using this currency'
    )

    farm_count = fields.Integer(
        string='Farms Count',
        compute='_compute_farm_count'
    )

    @api.depends('farm_ids')
    def _compute_farm_count(self):
        for currency in self:
            currency.farm_count = len(currency.farm_ids)
class AgriculturalCostAllocation(models.Model):
    _name = 'agri.cost.allocation'
    _description = 'Agricultural Cost Allocation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Reference', required=True, copy=False, readonly=True, default=lambda x: _('New'))
    date = fields.Date('Allocation Date', required=True, default=fields.Date.context_today, tracking=True)
    farm_id = fields.Many2one('agricultural.farm', 'Farm', required=True, tracking=True)
    project_id = fields.Many2one('agricultural.project', 'Project')
    production_request_id = fields.Many2one('agricultural.production.request', 'Production Request')
    company_id = fields.Many2one('res.company', related='farm_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='farm_id.currency_id', store=True)
    cost_category = fields.Selection([
        ('direct_material', 'Direct Materials'),
        ('seeds', 'Seeds'),
        ('fertilizers', 'Fertilizers'),
        ('pesticides', 'Pesticides & Chemicals'),
        ('direct_labor', 'Direct Labor'),
        ('machinery', 'Machinery & Equipment'),
        ('utilities', 'Utilities (Water, Electricity)'),
        ('fuel', 'Fuel & Energy'),
        ('maintenance', 'Maintenance & Repairs'),
        ('overhead', 'Overhead Costs'),
        ('depreciation', 'Depreciation'),
        ('insurance', 'Insurance'),
        ('transportation', 'Transportation'),
        ('packaging', 'Packaging Materials'),
        ('other', 'Other Costs')
    ], 'Cost Category', required=True, tracking=True)
    allocation_method = fields.Selection([
        ('area_based', 'Area Based'),
        ('project_based', 'Project Based'),
        ('direct_assignment', 'Direct Assignment'),
        ('plant_count', 'Plant Count Based'),
        ('production_volume', 'Production Volume'),
        ('labor_hours', 'Labor Hours'),
        ('equal_distribution', 'Equal Distribution')
    ], 'Allocation Method', required=True, default='area_based', tracking=True)
    total_amount = fields.Monetary('Total Amount', required=True, currency_field='currency_id', tracking=True)
    allocated_amount = fields.Monetary('Total Allocated', compute='_compute_allocated_totals', store=True,
                                       currency_field='currency_id')
    remaining_amount = fields.Monetary('Remaining Amount', compute='_compute_allocated_totals', store=True,
                                       currency_field='currency_id')
    allocation_percentage = fields.Float('Allocation %', digits='Discount', default=100.0)
    source_document = fields.Char('Source Document', help='Reference to source invoice, receipt, etc.')
    vendor_id = fields.Many2one('res.partner', 'Vendor',
                                domain="[('is_company', '=', True), ('supplier_rank', '>', 0)]")
    invoice_id = fields.Many2one('account.move', 'Source Invoice')
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order')
    account_id = fields.Many2one('account.account', 'Account')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    journal_id = fields.Many2one('account.journal', 'Journal')
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    allocation_line_ids = fields.One2many('agri.cost.allocation.line', 'allocation_id', 'Allocation Lines',
                                          copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('allocated', 'Allocated'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], 'Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')
    line_count = fields.Integer('Allocation Lines', compute='_compute_line_count', store=True)

    # Constraints

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('agri.cost.allocation') or _('New')
        return super().create(vals)

    @api.depends('allocation_line_ids.amount')
    def _compute_allocated_totals(self):
        for allocation in self:
            total_allocated = sum(allocation.allocation_line_ids.mapped('amount'))
            allocation.allocated_amount = total_allocated
            allocation.remaining_amount = allocation.total_amount - total_allocated

    @api.depends('allocation_line_ids')
    def _compute_line_count(self):
        for allocation in self:
            allocation.line_count = len(allocation.allocation_line_ids)

    def action_confirm(self):
        """Confirm allocation and create lines"""
        for allocation in self:
            if allocation.state != 'draft':
                raise UserError(_('Only draft allocations can be confirmed.'))

            # Clear existing lines
            allocation.allocation_line_ids.unlink()

            # Create allocation lines based on method
            allocation._create_allocation_lines()
            allocation.state = 'confirmed'

    def action_allocate(self):
        """Mark allocation as allocated"""
        for allocation in self:
            if allocation.state != 'confirmed':
                raise UserError(_('Only confirmed allocations can be allocated.'))

            if not allocation.allocation_line_ids:
                raise UserError(_('Cannot allocate without allocation lines.'))

            allocation.state = 'allocated'

    def action_post(self):
        """Create journal entries and mark as posted"""
        for allocation in self:
            if allocation.state != 'allocated':
                raise UserError(_('Only allocated cost allocations can be posted.'))

            if allocation.move_id:
                continue

            # Create journal entry
            move_vals = allocation._prepare_journal_entry()
            move = self.env['account.move'].create(move_vals)
            move.action_post()

            allocation.move_id = move.id
            allocation.state = 'posted'

    def action_cancel(self):
        """Cancel allocation"""
        for allocation in self:
            if allocation.state == 'posted' and allocation.move_id:
                raise UserError(_('Cannot cancel posted allocations. Reverse the journal entry first.'))

            allocation.state = 'cancelled'

    def action_reset_to_draft(self):
        """Reset to draft"""
        for allocation in self:
            if allocation.state == 'posted':
                raise UserError(_('Cannot reset posted allocations to draft.'))

            allocation.state = 'draft'

    def _create_allocation_lines(self):
        """Create allocation lines based on allocation method"""
        self.ensure_one()

        if self.allocation_method == 'area_based':
            self._create_area_based_allocation()
        elif self.allocation_method == 'project_based':
            self._create_project_based_allocation()
        elif self.allocation_method == 'direct_assignment':
            self._create_direct_assignment()
        elif self.allocation_method == 'plant_count':
            self._create_plant_count_allocation()
        elif self.allocation_method == 'equal_distribution':
            self._create_equal_distribution()

    def _create_area_based_allocation(self):
        """Create area-based allocation lines"""
        if self.farm_id:
            # Direct assignment to specific greenhouse
            self._create_allocation_line(self.farm_id, 100.0)
        else:
            # Allocate to all greenhouses based on area
            greenhouses = self.farm_id.filtered(lambda g: g.level == 'house')
            total_area = sum(greenhouses.mapped('area_hectares'))

            if total_area > 0:
                for greenhouse in greenhouses:
                    if greenhouse.area_hectares > 0:
                        percentage = (greenhouse.area_hectares / total_area) * 100
                        self._create_allocation_line(greenhouse, percentage)

    def _create_project_based_allocation(self):
        """Create project-based allocation lines"""
        if self.project_id:
            # Allocate to specific project's greenhouse
            if self.project_id.farm_id:
                self._create_allocation_line(self.project_id.farm_id, 100.0, self.project_id)
        else:
            # Allocate to all active projects
            projects = self.farm_id.project_ids.filtered(lambda p: p.state not in ['cancelled', 'done'])
            if projects:
                percentage_per_project = 100.0 / len(projects)
                for project in projects:
                    if project.farm_id:
                        self._create_allocation_line(project.farm_id, percentage_per_project, project)

    def _create_direct_assignment(self):
        """Create direct assignment (100% to specified greenhouse)"""
        if not self.farm_id:
            raise UserError(_('Direct assignment requires a specific greenhouse to be selected.'))

        self._create_allocation_line(self.farm_id, 100.0)

    def _create_plant_count_allocation(self):
        """Create allocation based on plant count"""
        greenhouses = self.farm_id.filtered(lambda g: g.level == 'house')
        total_plants = sum(greenhouses.mapped('current_plants'))

        if total_plants > 0:
            for greenhouse in greenhouses:
                if greenhouse.current_plants > 0:
                    percentage = (greenhouse.current_plants / total_plants) * 100
                    self._create_allocation_line(greenhouse, percentage)

    def _create_equal_distribution(self):
        """Create equal distribution among active greenhouses"""
        greenhouses = self.farm_id.filtered(lambda g: g.level == 'house')

        if greenhouses:
            percentage_per_greenhouse = 100.0 / len(greenhouses)
            for greenhouse in greenhouses:
                self._create_allocation_line(greenhouse, percentage_per_greenhouse)

    def _create_allocation_line(self, greenhouse, percentage, project=None):
        """Create individual allocation line"""
        amount = self.total_amount * (percentage / 100) * (self.allocation_percentage / 100)

        vals = {
            'allocation_id': self.id,
            'farm_id': greenhouse.id,
            'project_id': project.id if project else None,
            'percentage': percentage,
            'amount': amount,
            'area_m2': greenhouse.area_hectares,
            'plant_count': greenhouse.current_plants,
        }

        return self.env['agri.cost.allocation.line'].create(vals)

    def _prepare_journal_entry(self):
        """Prepare journal entry for cost allocation"""
        self.ensure_one()

        move_lines = []

        # Credit line (source account)
        if self.account_id:
            credit_line = (0, 0, {
                'name': f"Cost Allocation - {self.name}",
                'account_id': self.account_id.id,
                'credit': self.total_amount,
                'debit': 0,
                'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else None,
            })
            move_lines.append(credit_line)

        # Debit lines (allocation to greenhouses)
        for line in self.allocation_line_ids:
            if line.farm_id.analytic_account_id:
                debit_line = (0, 0, {
                    'name': f"Allocated to {line.farm_id.name}",
                    'account_id': self.account_id.id,
                    'debit': line.amount,
                    'credit': 0,
                    'analytic_account_id': line.farm_id.analytic_account_id.id,
                })
                move_lines.append(debit_line)

        return {
            'journal_id': self.journal_id.id or self.env['account.journal'].search([('type', '=', 'general')],
                                                                                   limit=1).id,
            'date': self.date,
            'ref': self.name,
            'line_ids': move_lines,
        }
class AgriculturalCostAllocationLine(models.Model):
    _name = 'agri.cost.allocation.line'
    _description = 'Agricultural Cost Allocation Line'
    _rec_name = 'display_name'

    allocation_id = fields.Many2one('agri.cost.allocation', 'Allocation')
    farm_id = fields.Many2one('agricultural.farm', 'farm', required=True)
    project_id = fields.Many2one('agricultural.project', 'Project')
    production_request_id = fields.Many2one('agricultural.production.request', 'Production Request')
    # Display Name
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    # Allocation Details
    percentage = fields.Float('Percentage %', digits='Discount')
    amount = fields.Monetary('Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', related='allocation_id.currency_id', store=True)
    # Reference Data (for calculation basis)
    area_m2 = fields.Float('Area (m²)', digits='Product Unit of Measure')
    plant_count = fields.Integer('Plant Count')
    production_volume = fields.Float('Production Volume', digits='Product Unit of Measure')
    labor_hours = fields.Float('Labor Hours', digits='Product Unit of Measure')

    # Dates for tracking
    date_from = fields.Date('Date From', related='allocation_id.date', store=True)
    allocation_date = fields.Date('Allocation Date', related='allocation_id.date', store=True)
    # Status
    state = fields.Selection(related='allocation_id.state', store=True)
    cost_per_m2 = fields.Monetary('Cost per m²', compute='_compute_cost_ratios', store=True,
                                  currency_field='currency_id')
    cost_per_plant = fields.Monetary('Cost per Plant', compute='_compute_cost_ratios', store=True,
                                     currency_field='currency_id')
    cost_per_hour = fields.Monetary('Cost per Hour', compute='_compute_cost_ratios', store=True,
                                    currency_field='currency_id')
    cost_category = fields.Selection(related='allocation_id.cost_category', store=True)
    allocation_method = fields.Selection(related='allocation_id.allocation_method', store=True)
    notes = fields.Text(string='Notes')
    @api.depends('farm_id.name', 'allocation_id.name', 'percentage')
    def _compute_display_name(self):
        for line in self:
            if line.farm_id and line.allocation_id:
                line.display_name = f"{line.allocation_id.name} - {line.farm_id.name} ({line.percentage:.2f}%)"
            else:
                line.display_name = "Cost Allocation Line"

    @api.depends('amount', 'area_m2', 'plant_count', 'labor_hours')
    def _compute_cost_ratios(self):
        for line in self:
            # Cost per m²
            if line.area_m2 > 0:
                line.cost_per_m2 = line.amount / line.area_m2
            else:
                line.cost_per_m2 = 0

            # Cost per plant
            if line.plant_count > 0:
                line.cost_per_plant = line.amount / line.plant_count
            else:
                line.cost_per_plant = 0

            # Cost per hour
            if line.labor_hours > 0:
                line.cost_per_hour = line.amount / line.labor_hours
            else:
                line.cost_per_hour = 0

    def action_view_greenhouse(self):
        """View the associated greenhouse"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Greenhouse'),
            'res_model': 'agricultural.farm',
            'res_id': self.farm_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_project(self):
        """View the associated project"""
        self.ensure_one()
        if not self.project_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project'),
            'res_model': 'agricultural.project',
            'res_id': self.project_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
class AgriculturalCostCalculation(models.Model):
    _name = 'agri.cost.calculation'
    _description = 'Agricultural Cost Calculation & Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char('Calculation Name', required=True, tracking=True)
    code = fields.Char('Reference Code', copy=False, readonly=True, default=lambda x: _('New'))
    # Date Range
    date_from = fields.Date('Date From', required=True, tracking=True)
    date_to = fields.Date('Date To', required=True, tracking=True)
    calculation_date = fields.Date('Calculation Date', required=True, tracking=True)
    period_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Period')
    ], 'Period Type', default='monthly', tracking=True)
    area_hectares = fields.Float(
        string='Area (Meter)',
        digits=(10, 4),
        tracking=True,
        help='Farm area in Meter'
    )
    cost_per_hectare = fields.Monetary(
        string='Cost per Hectare',
        compute='_compute_cost_per_hectare',
        store=True,
        currency_field='currency_id'
    )
    cost_per_unit = fields.Monetary('Cost per Unit',  store=True,
                                    currency_field='currency_id')
    # Scope
    farm_id = fields.Many2one('agricultural.farm', 'Farm', required=True, tracking=True)
    project_ids = fields.Many2many(
        'agricultural.project',
        string='Projects',
        domain="[('farm_id', '=', farm_id)]"
    )
    project_id = fields.Many2one('agricultural.project', 'Project', required=True)
    company_id = fields.Many2one('res.company', related='farm_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='farm_id.currency_id', store=True)
    # Cost Breakdown - Direct Costs
    direct_material_cost = fields.Monetary('Direct Materials', currency_field='currency_id',
                                           compute='_compute_cost_breakdown', store=True)
    seed_costs = fields.Monetary('Seeds', currency_field='currency_id',
                                 compute='_compute_cost_breakdown', store=True)
    fertilizer_costs = fields.Monetary('Fertilizers', currency_field='currency_id',
                                       compute='_compute_cost_breakdown', store=True)
    pesticide_costs = fields.Monetary('Pesticides', currency_field='currency_id',
                                      compute='_compute_cost_breakdown', store=True)
    direct_labor_cost = fields.Monetary('Direct Labor', currency_field='currency_id',
                                        compute='_compute_cost_breakdown', store=True)

    # Cost Breakdown - Indirect Costs
    overhead_cost = fields.Monetary('Overhead Costs', currency_field='currency_id',
                                    compute='_compute_cost_breakdown', store=True)
    utilities_cost = fields.Monetary('Utilities', currency_field='currency_id',
                                     compute='_compute_cost_breakdown', store=True)
    maintenance_cost = fields.Monetary('Maintenance', currency_field='currency_id',
                                       compute='_compute_cost_breakdown', store=True)
    depreciation_cost = fields.Monetary('Depreciation', currency_field='currency_id',
                                        compute='_compute_cost_breakdown', store=True)
    transportation_cost = fields.Monetary('Transportation', currency_field='currency_id',
                                          compute='_compute_cost_breakdown', store=True)
    packaging_cost = fields.Monetary('Packaging', currency_field='currency_id',
                                     compute='_compute_cost_breakdown', store=True)

    # Total Costs
    total_direct_cost = fields.Monetary('Total Direct Costs', currency_field='currency_id',
                                        compute='_compute_totals', store=True)
    total_indirect_cost = fields.Monetary('Total Indirect Costs', currency_field='currency_id',
                                          compute='_compute_totals', store=True)
    total_cost = fields.Monetary('Total Cost', currency_field='currency_id',
                                 compute='_compute_totals', store=True)

    # Production Data
    total_production_qty = fields.Float('Total Production', digits='Product Unit of Measure',
                                        compute='_compute_production_data', store=True)
    total_area_m2 = fields.Float('Total Area (m²)', digits='Product Unit of Measure',
                                 compute='_compute_production_data', store=True)
    total_plants = fields.Integer('Total Plants', compute='_compute_production_data', store=True)

    # Cost Analysis
    cost_per_kg = fields.Monetary('Cost per kg', currency_field='currency_id',
                                  compute='_compute_cost_analysis', store=True)
    cost_per_m2 = fields.Monetary('Cost per m²', currency_field='currency_id',
                                  compute='_compute_cost_analysis', store=True)
    cost_per_plant = fields.Monetary('Cost per Plant', currency_field='currency_id',
                                     compute='_compute_cost_analysis', store=True)

    # Revenue Analysis
    total_revenue = fields.Monetary('Total Revenue', currency_field='currency_id',
                                    compute='_compute_revenue_analysis', store=True)
    gross_profit = fields.Monetary('Gross Profit', currency_field='currency_id',
                                   compute='_compute_revenue_analysis', store=True)
    profit_margin = fields.Float('Profit Margin %', digits='Discount',
                                 compute='_compute_revenue_analysis', store=True)

    # Lines
    cost_line_ids = fields.One2many('agri.cost.calculation.line', 'calculation_id', 'Cost Details')
    production_line_ids = fields.One2many('agri.production.calculation.line', 'calculation_id',
                                          'Production Details')
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculating', 'Calculating'),
        ('calculated', 'Calculated'),
        ('validated', 'Validated'),
        ('cancelled', 'Cancelled')
    ], 'Status', default='draft', tracking=True)

    # Statistics
    line_count = fields.Integer('Cost Lines', compute='_compute_line_count', store=True)
    greenhouse_count = fields.Integer('Greenhouses', compute='_compute_counts', store=True)
    project_count = fields.Integer('Projects', compute='_compute_counts', store=True)

    # Constraints


    # Add the missing action methods
    def action_calculate(self):
        """Calculate costs for the cost calculation"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft calculations can be calculated.'))

        try:
            # Perform cost calculations
            self._calculate_all_costs()

            # Update state
            self.write({'state': 'calculated'})

            # Log message
            self.message_post(body=_('Costs have been calculated successfully.'))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Cost calculation completed successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error during cost calculation: %s') % str(e))
    def action_recalculate(self):
        """Recalculate costs"""
        self.ensure_one()
        if self.state not in ['calculated', 'confirmed']:
            raise UserError(_('Only calculated records can be recalculated.'))

        try:
            # Reset calculations
            self._reset_calculations()

            # Recalculate
            self._calculate_all_costs()

            # Update state
            self.write({'state': 'calculated'})

            self.message_post(body=_('Costs have been recalculated successfully.'))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Cost recalculation completed successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error during recalculation: %s') % str(e))
    def action_reset(self):
        """Reset calculation to draft state"""
        self.ensure_one()

        # Reset all calculated values
        self._reset_calculations()

        # Update state
        self.write({'state': 'draft'})

        self.message_post(body=_('Calculation has been reset to draft.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Calculation reset to draft successfully.'),
                'type': 'info',
                'sticky': False,
            }
        }
    def action_confirm(self):
        """Confirm the cost calculation"""
        self.ensure_one()
        if self.state != 'calculated':
            raise UserError(_('Only calculated records can be confirmed.'))

        self.write({'state': 'confirmed'})
        self.message_post(body=_('Cost calculation has been confirmed.'))

        return True
    def action_cancel(self):
        """Cancel the cost calculation"""
        self.ensure_one()
        if self.state == 'confirmed':
            raise UserError(_('Cannot cancel confirmed calculations.'))

        self.write({'state': 'cancelled'})
        self.message_post(body=_('Cost calculation has been cancelled.'))

        return True
    def _calculate_all_costs(self):
        """Main cost calculation logic"""
        self.ensure_one()

        # Calculate direct material costs
        self._calculate_direct_material_costs()

        # Calculate indirect material costs
        self._calculate_indirect_material_costs()

        # Calculate labor costs
        self._calculate_labor_costs()

        # Calculate overhead costs
        self._calculate_overhead_costs()

        # Calculate totals
        self._calculate_totals()
    def _calculate_direct_material_costs(self):
        """Calculate direct material costs from production requests"""
        direct_cost = 0.0

        # Get production requests for this farm/project
        requests = self.env['agricultural.production.request'].search([
            ('farm_id', '=', self.farm_id.id if hasattr(self, 'farm_id') else False),
            ('project_id', '=', self.project_id.id if hasattr(self, 'project_id') else False),
            ('state', 'in', ['completed', 'transferred']),
        ])

        for request in requests:
            for line in request.request_line_ids:
                if line.cost_center_type == 'direct':
                    direct_cost += line.approved_cost or line.estimated_cost or 0.0

        # Update the direct material cost field if it exists
        if hasattr(self, 'direct_material_cost'):
            self.direct_material_cost = direct_cost

        return direct_cost
    def _calculate_indirect_material_costs(self):
        """Calculate indirect material costs"""
        indirect_cost = 0.0

        # Get production requests for indirect materials
        requests = self.env['agricultural.production.request'].search([
            ('farm_id', '=', self.farm_id.id if hasattr(self, 'farm_id') else False),
            ('project_id', '=', self.project_id.id if hasattr(self, 'project_id') else False),
            ('state', 'in', ['completed', 'transferred']),
        ])

        for request in requests:
            for line in request.request_line_ids:
                if line.cost_center_type == 'indirect':
                    indirect_cost += line.approved_cost or line.estimated_cost or 0.0

        # Update the indirect material cost field if it exists
        if hasattr(self, 'indirect_material_cost'):
            self.indirect_material_cost = indirect_cost

        return indirect_cost
    def _calculate_labor_costs(self):
        """Calculate labor costs"""
        labor_cost = 0.0

        # Calculate labor costs from various sources
        # This would depend on your labor tracking system

        if hasattr(self, 'labor_cost'):
            self.labor_cost = labor_cost

        return labor_cost
    def _calculate_overhead_costs(self):
        """Calculate overhead costs"""
        overhead_cost = 0.0

        # Calculate overhead allocation
        # This would depend on your overhead allocation method

        if hasattr(self, 'overhead_cost'):
            self.overhead_cost = overhead_cost

        return overhead_cost
    def _calculate_totals(self):
        """Calculate total costs"""
        total_cost = 0.0

        # Sum up all cost components
        if hasattr(self, 'direct_material_cost'):
            total_cost += self.direct_material_cost or 0.0
        if hasattr(self, 'indirect_material_cost'):
            total_cost += self.indirect_material_cost or 0.0
        if hasattr(self, 'labor_cost'):
            total_cost += self.labor_cost or 0.0
        if hasattr(self, 'overhead_cost'):
            total_cost += self.overhead_cost or 0.0

        # Update total cost field if it exists
        if hasattr(self, 'total_cost'):
            self.total_cost = total_cost
    def _reset_calculations(self):
        """Reset all calculated values to zero"""
        reset_vals = {}

        # Reset cost fields if they exist
        cost_fields = ['direct_material_cost', 'indirect_material_cost',
                       'labor_cost', 'overhead_cost', 'total_cost']

        for field in cost_fields:
            if hasattr(self, field):
                reset_vals[field] = 0.0

        if reset_vals:
            self.write(reset_vals)
    # Add the missing action methods
    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('agri.cost.calculation') or _('New')
        return super().create(vals)
    @api.depends('cost_line_ids')
    def _compute_line_count(self):
        for calc in self:
            calc.line_count = len(calc.cost_line_ids)
    @api.depends('project_ids')
    def _compute_counts(self):
        for calc in self:
            calc.greenhouse_count = 0
            calc.project_count = len(calc.project_ids) if calc.project_ids else len(calc.farm_id.project_ids)

    @api.depends('cost_line_ids.amount', 'cost_line_ids.cost_category')
    def _compute_cost_breakdown(self):
        for calc in self:
            lines = calc.cost_line_ids

            # Direct Material Costs
            calc.seed_costs = sum(lines.filtered(lambda l: l.cost_category == 'seeds').mapped('amount'))
            calc.fertilizer_costs = sum(lines.filtered(lambda l: l.cost_category == 'fertilizers').mapped('amount'))
            calc.pesticide_costs = sum(lines.filtered(lambda l: l.cost_category == 'pesticides').mapped('amount'))
            calc.direct_material_cost = sum(lines.filtered(
                lambda l: l.cost_category in ['direct_material', 'seeds', 'fertilizers', 'pesticides']).mapped(
                'amount'))

            # Labor Costs
            calc.direct_labor_cost = sum(lines.filtered(lambda l: l.cost_category == 'direct_labor').mapped('amount'))

            # Indirect Costs
            calc.overhead_cost = sum(lines.filtered(lambda l: l.cost_category == 'overhead').mapped('amount'))
            calc.utilities_cost = sum(lines.filtered(lambda l: l.cost_category == 'utilities').mapped('amount'))
            calc.maintenance_cost = sum(lines.filtered(lambda l: l.cost_category == 'maintenance').mapped('amount'))
            calc.depreciation_cost = sum(lines.filtered(lambda l: l.cost_category == 'depreciation').mapped('amount'))
            calc.transportation_cost = sum(
                lines.filtered(lambda l: l.cost_category == 'transportation').mapped('amount'))
            calc.packaging_cost = sum(lines.filtered(lambda l: l.cost_category == 'packaging').mapped('amount'))

    @api.depends('direct_material_cost', 'direct_labor_cost', 'overhead_cost', 'utilities_cost',
                 'maintenance_cost', 'depreciation_cost', 'transportation_cost', 'packaging_cost')
    def _compute_totals(self):
        for calc in self:
            calc.total_direct_cost = calc.direct_material_cost + calc.direct_labor_cost
            calc.total_indirect_cost = (calc.overhead_cost + calc.utilities_cost + calc.maintenance_cost +
                                        calc.depreciation_cost + calc.transportation_cost + calc.packaging_cost)
            calc.total_cost = calc.total_direct_cost + calc.total_indirect_cost
    @api.depends('project_ids', 'production_line_ids.quantity')
    def _compute_production_data(self):
        for calc in self:
            # Get relevant greenhouses
            greenhouses = calc.farm_id if calc.farm_id.id else calc.farm_id

            # Calculate totals
            calc.total_area_m2 = sum(greenhouses.mapped('area_hectares'))
            calc.total_plants = sum(greenhouses.mapped('current_plants'))
            calc.total_production_qty = sum(calc.production_line_ids.mapped('quantity'))
    @api.depends('total_cost', 'total_production_qty', 'total_area_m2', 'total_plants')
    def _compute_cost_analysis(self):
        for calc in self:
            # Cost per kg
            if calc.total_production_qty > 0:
                calc.cost_per_kg = calc.total_cost / calc.total_production_qty
            else:
                calc.cost_per_kg = 0

            # Cost per m²
            if calc.total_area_m2 > 0:
                calc.cost_per_m2 = calc.total_cost / calc.total_area_m2
            else:
                calc.cost_per_m2 = 0

            # Cost per plant
            if calc.total_plants > 0:
                calc.cost_per_plant = calc.total_cost / calc.total_plants
            else:
                calc.cost_per_plant = 0
    @api.depends('production_line_ids.revenue')
    def _compute_revenue_analysis(self):
        for calc in self:
            calc.total_revenue = sum(calc.production_line_ids.mapped('revenue'))
            calc.gross_profit = calc.total_revenue - calc.total_cost

            if calc.total_revenue > 0:
                calc.profit_margin = (calc.gross_profit / calc.total_revenue) * 100
            else:
                calc.profit_margin = 0
    def action_calculate_costs(self):
        """Calculate all costs for the specified period"""
        for calc in self:
            if calc.state not in ['draft', 'calculated']:
                raise UserError(_('Only draft or calculated cost calculations can be recalculated.'))

            calc.state = 'calculating'

            try:
                # Clear existing lines
                calc.cost_line_ids.unlink()
                calc.production_line_ids.unlink()

                # Calculate costs
                calc._calculate_direct_costs()
                calc._calculate_indirect_costs()
                calc._calculate_production_data()

                calc.state = 'calculated'

            except Exception as e:
                calc.state = 'draft'
                raise UserError(_('Error calculating costs: %s') % str(e))
    def _calculate_direct_costs(self):
        """Calculate direct costs from stock moves and allocations"""
        self.ensure_one()

        # Get cost allocations in date range
        domain = [
            ('farm_id', '=', self.farm_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'allocated')
        ]

        if self.farm_id:
            domain.append(('level', 'in', ['house']))

        allocations = self.env['agri.cost.allocation'].search(domain)

        # Create cost lines from allocations
        for allocation in allocations:
            for line in allocation.allocation_line_ids:
                if not self.farm_id or line.farm_id in self.farm_id:
                    self._create_cost_line(allocation.cost_category, line.amount, allocation, line.farm_id)
    def _calculate_indirect_costs(self):
        """Calculate indirect costs (utilities, maintenance, etc.)"""
        # This can be extended based on specific business logic
        pass
    def _calculate_production_data(self):
        """Calculate production data from stock moves"""
        self.ensure_one()

        # Get stock moves for production (outgoing moves to customers)
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'done'),
            ('location_dest_id.usage', '=', 'customer')
        ]

        if self.farm_id:
            domain.append(('level', 'in', ['house']))
        elif self.farm_id:
            domain.append(('agricultural_farm_id', '=', self.farm_id.id))

        production_moves = self.env['stock.move'].search(domain)

        # Group by product and create production lines
        product_data = {}
        for move in production_moves:
            product = move.product_id
            if product not in product_data:
                product_data[product] = {
                    'quantity': 0,
                    'revenue': 0,
                    'cost': 0
                }

            product_data[product]['quantity'] += move.product_qty
            product_data[product]['revenue'] += move.product_qty * product.list_price
            product_data[product]['cost'] += move.value

        # Create production lines
        for product, data in product_data.items():
            self._create_production_line(product, data['quantity'], data['revenue'], data['cost'])
    def _create_cost_line(self, cost_category, amount, allocation=None, greenhouse=None):
        """Create cost calculation line"""
        vals = {
            'calculation_id': self.id,
            'cost_category': cost_category,
            'amount': amount,
            'allocation_id': allocation.id if allocation else None,
            'farm_id': greenhouse.id if greenhouse else None,
            'project_id': allocation.project_id.id if allocation and allocation.project_id else None,
        }
        return self.env['agri.cost.calculation.line'].create(vals)
    def _create_production_line(self, product, quantity, revenue, cost):
        """Create production calculation line"""
        vals = {
            'calculation_id': self.id,
            'product_id': product.id,
            'quantity': quantity,
            'revenue': revenue,
            'cost': cost,
            'unit_price': product.list_price,
            'profit': revenue - cost,
        }
        return self.env['agri.production.calculation.line'].create(vals)
    def action_validate(self):
        """Validate the calculation"""
        for calc in self:
            if calc.state != 'calculated':
                raise UserError(_('Only calculated cost calculations can be validated.'))
            calc.state = 'validated'
    def action_reset_to_draft(self):
        """Reset to draft"""
        for calc in self:
            if calc.state == 'validated':
                raise UserError(_('Cannot reset validated calculations to draft.'))
            calc.state = 'draft'
    def get_cost_summary_by_category(self):
        """Get cost summary grouped by category"""
        self.ensure_one()
        summary = {}
        for line in self.cost_line_ids:
            if line.cost_category not in summary:
                summary[line.cost_category] = 0
            summary[line.cost_category] += line.amount
        return summary
    def get_cost_summary_by_greenhouse(self):
        """Get cost summary grouped by greenhouse"""
        self.ensure_one()
        summary = {}
        for line in self.cost_line_ids:
            greenhouse = line.farm_id.name if line.farm_id else 'Unassigned'
            if greenhouse not in summary:
                summary[greenhouse] = 0
            summary[greenhouse] += line.amount
        return summary
class AgriculturalCostCalculationLine(models.Model):
    _name = 'agri.cost.calculation.line'
    _description = 'Agricultural Cost Calculation Line'
    _rec_name = 'display_name'

    calculation_id = fields.Many2one('agri.cost.calculation', 'Calculation', required=True, ondelete='cascade')
    unit_price = fields.Float('Unit Price', digits='Product Price')
    estimated_cost = fields.Float('Estimated Cost', store=True)
    approved_cost = fields.Float('Approved Cost')
    subtotal = fields.Monetary('Subtotal', currency_field='currency_id', store=True)
    # Cost Details
    cost_category = fields.Selection([
        ('direct_material', 'Direct Materials'),
        ('seeds', 'Seeds'),
        ('fertilizers', 'Fertilizers'),
        ('pesticides', 'Pesticides & Chemicals'),
        ('direct_labor', 'Direct Labor'),
        ('machinery', 'Machinery & Equipment'),
        ('utilities', 'Utilities'),
        ('fuel', 'Fuel & Energy'),
        ('maintenance', 'Maintenance & Repairs'),
        ('overhead', 'Overhead Costs'),
        ('depreciation', 'Depreciation'),
        ('insurance', 'Insurance'),
        ('transportation', 'Transportation'),
        ('packaging', 'Packaging Materials'),
        ('other', 'Other Costs')
    ], 'Cost Category', required=True)

    amount = fields.Monetary('Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', related='calculation_id.currency_id', store=True)

    # References
    allocation_id = fields.Many2one('agri.cost.allocation', 'Source Allocation')
    allocation_method = fields.Selection(related='allocation_id.allocation_method', store=True)
    farm_id = fields.Many2one('agricultural.farm', 'Greenhouse')
    project_id = fields.Many2one('agricultural.project', 'Project')
    product_id = fields.Many2one('product.product', 'Product')

    # Additional Details
    description = fields.Text('Description')
    quantity = fields.Float('Quantity', digits='Product Unit of Measure')
    unit_cost = fields.Monetary('Unit Cost', currency_field='currency_id')

    # Computed Fields
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)

    # Related Fields
    date_from = fields.Date(related='calculation_id.date_from', store=True)
    date_to = fields.Date(related='calculation_id.date_to', store=True)

    @api.depends('cost_category', 'amount', 'farm_id')
    def _compute_display_name(self):
        for line in self:
            category_name = dict(line._fields['cost_category'].selection).get(line.cost_category, 'Unknown')
            greenhouse_name = line.farm_id.name if line.farm_id else 'All'
            line.display_name = f"{category_name} - {greenhouse_name}: {line.amount}"

    @api.onchange('quantity', 'unit_cost')
    def _onchange_quantity_unit_cost(self):
        if self.quantity and self.unit_cost:
            self.amount = self.quantity * self.unit_cost
class AgriculturalProductionCalculationLine(models.Model):
    _name = 'agri.production.calculation.line'
    _description = 'Agricultural Production Calculation Line'
    _rec_name = 'display_name'

    calculation_id = fields.Many2one('agri.cost.calculation', 'Calculation', required=True, ondelete='cascade')

    # Product Information
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_category_id = fields.Many2one('product.category', related='product_id.categ_id', store=True)

    # Production Data
    quantity = fields.Float('Quantity Produced', digits='Product Unit of Measure', required=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id', store=True)

    # Financial Data
    unit_price = fields.Monetary('Unit Price', currency_field='currency_id')
    revenue = fields.Monetary('Revenue', currency_field='currency_id')
    cost = fields.Monetary('Production Cost', currency_field='currency_id')
    profit = fields.Monetary('Profit', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='calculation_id.currency_id', store=True)

    # Analysis
    profit_margin = fields.Float('Profit Margin %', compute='_compute_profit_margin', store=True, digits='Discount')
    cost_per_unit = fields.Monetary('Cost per Unit', compute='_compute_cost_per_unit', store=True,
                                    currency_field='currency_id')

    # References
    farm_id = fields.Many2one('agricultural.farm', 'Primary Greenhouse')
    project_id = fields.Many2one('agricultural.project', 'Project')

    # Quality Data
    quality_grade = fields.Selection([
        ('premium', 'Premium'),
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
        ('reject', 'Reject')
    ], 'Average Quality Grade')

    # Computed Fields
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    notes = fields.Text('Notes')
    # Related Fields
    date_from = fields.Date(related='calculation_id.date_from', store=True)
    date_to = fields.Date(related='calculation_id.date_to', store=True)

    @api.depends('product_id', 'quantity', 'revenue')
    def _compute_display_name(self):
        for line in self:
            if line.product_id:
                line.display_name = f"{line.product_id.name}: {line.quantity} {line.uom_id.name if line.uom_id else 'units'}"
            else:
                line.display_name = "Production Line"

    @api.depends('revenue', 'profit')
    def _compute_profit_margin(self):
        for line in self:
            if line.revenue > 0:
                line.profit_margin = (line.profit / line.revenue) * 100
            else:
                line.profit_margin = 0

    @api.depends('cost', 'quantity')
    def _compute_cost_per_unit(self):
        for line in self:
            if line.quantity > 0:
                line.cost_per_unit = line.cost / line.quantity
            else:
                line.cost_per_unit = 0

    @api.onchange('quantity', 'unit_price')
    def _onchange_quantity_price(self):
        if self.quantity and self.unit_price:
            self.revenue = self.quantity * self.unit_price

    @api.onchange('revenue', 'cost')
    def _onchange_revenue_cost(self):
        if self.revenue and self.cost:
            self.profit = self.revenue - self.cost
class AgriculturalInventoryStage(models.Model):
    _name = 'agri.inventory.stage'
    _description = 'Agricultural Inventory Stage Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, date desc'

    name = fields.Char('Stage Name', required=True, tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    date = fields.Datetime('Stage Date', required=True, default=fields.Datetime.now, tracking=True)

    # References
    farm_id = fields.Many2one('agricultural.farm', 'Farm', required=True, tracking=True)
    project_id = fields.Many2one('agricultural.project', 'Project', tracking=True)
    production_request_id = fields.Many2one('agricultural.production.request', 'Production Request')
    product_id = fields.Many2one('product.product', 'Product', required=True, tracking=True)

    company_id = fields.Many2one('res.company', related='farm_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='farm_id.currency_id', store=True)

    # Stage Information
    stage_type = fields.Selection([
        ('seeding', 'Seeding'),
        ('germination', 'Germination'),
        ('transplanting', 'Transplanting'),
        ('cultivation', 'Cultivation'),
        ('inspection', 'Quality Inspection'),
        ('treatment', 'Treatment/Care'),
        ('harvest', 'Harvest'),
        ('processing', 'Processing'),
        ('grading', 'Grading/Sorting'),
        ('packing', 'Packing'),
        ('storage', 'Storage'),
        ('shipping', 'Shipping Preparation'),
        ('waste_management', 'Waste Management')
    ], 'Stage Type', required=True, tracking=True)

    # Quantities
    quantity_in = fields.Float('Quantity In', digits='Product Unit of Measure', tracking=True)
    quantity_out = fields.Float('Quantity Out', digits='Product Unit of Measure', tracking=True)
    quantity_loss = fields.Float('Quantity Loss', digits='Product Unit of Measure', tracking=True)
    quantity_waste = fields.Float('Quantity Waste', digits='Product Unit of Measure')
    quantity_remaining = fields.Float('Quantity Remaining', compute='_compute_quantity_remaining', store=True)

    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True)

    # Quality Information
    quality_grade = fields.Selection([
        ('premium', 'Premium'),
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
        ('reject', 'Reject')
    ], 'Quality Grade', tracking=True)

    quality_score = fields.Float('Quality Score', digits='Discount', help='Quality score out of 100')
    defect_rate = fields.Float('Defect Rate %', digits='Discount')

    # Environmental Conditions
    temperature = fields.Float('Temperature (°C)')
    humidity = fields.Float('Humidity (%)')
    ph_level = fields.Float('pH Level', digits='Discount')
    light_exposure = fields.Float('Light Exposure (hours)')

    # Cost Information
    stage_cost = fields.Monetary('Stage Cost', currency_field='currency_id', tracking=True)
    labor_cost = fields.Monetary('Labor Cost', currency_field='currency_id')
    material_cost = fields.Monetary('Material Cost', currency_field='currency_id')
    equipment_cost = fields.Monetary('Equipment Cost', currency_field='currency_id')
    accumulated_cost = fields.Monetary('Accumulated Cost', compute='_compute_accumulated_cost', store=True,
                                       currency_field='currency_id')

    # Processing Details
    processing_method = fields.Char('Processing Method')
    equipment_used = fields.Char('Equipment Used')
    chemicals_used = fields.Text('Chemicals/Treatments Used')

    # Stock Movement Integration
    stock_move_ids = fields.One2many('stock.move', 'inventory_stage_id', 'Related Stock Moves')
    picking_id = fields.Many2one('stock.picking', 'Related Picking')
    location_id = fields.Many2one('stock.location', 'Location')
    location_dest_id = fields.Many2one('stock.location', 'Destination Location')

    # Personnel
    responsible_user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, tracking=True)
    worker_ids = fields.Many2many('hr.employee', string='Workers Involved')
    supervisor_id = fields.Many2one('hr.employee', 'Supervisor')

    # Documentation
    notes = fields.Text('Notes')
    images = fields.Binary('Stage Images', attachment=True)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', 'Attachments',
                                     domain=[('res_model', '=', 'agri.inventory.stage')])

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], 'Status', default='draft', tracking=True)
    description = fields.Text('description')
    # Computed Fields
    loss_percentage = fields.Float('Loss %', compute='_compute_loss_percentage', store=True, digits='Discount')
    efficiency_score = fields.Float('Efficiency Score', compute='_compute_efficiency_score', store=True,
                                    digits='Discount')

    # Constraints
    def action_confirm(self):
        pass

    @api.depends('quantity_in', 'quantity_out', 'quantity_loss', 'quantity_waste')
    def _compute_quantity_remaining(self):
        for stage in self:
            stage.quantity_remaining = stage.quantity_in - stage.quantity_out - stage.quantity_loss - stage.quantity_waste

    @api.depends('quantity_in', 'quantity_loss', 'quantity_waste')
    def _compute_loss_percentage(self):
        for stage in self:
            if stage.quantity_in > 0:
                total_loss = stage.quantity_loss + stage.quantity_waste
                stage.loss_percentage = (total_loss / stage.quantity_in) * 100
            else:
                stage.loss_percentage = 0

    @api.depends('labor_cost', 'material_cost', 'equipment_cost')
    def _compute_stage_cost_total(self):
        for stage in self:
            stage.stage_cost = stage.labor_cost + stage.material_cost + stage.equipment_cost

    @api.depends('stage_cost', 'project_id')
    def _compute_accumulated_cost(self):
        for stage in self:
            if stage.project_id:
                previous_stages = self.search([
                    ('project_id', '=', stage.project_id.id),
                    ('product_id', '=', stage.product_id.id),
                    ('sequence', '<=', stage.sequence),
                    ('id', '!=', stage.id)
                ])
                stage.accumulated_cost = stage.stage_cost + sum(previous_stages.mapped('stage_cost'))
            else:
                stage.accumulated_cost = stage.stage_cost

    @api.depends('quantity_in', 'quantity_out', 'loss_percentage', 'quality_score')
    def _compute_efficiency_score(self):
        for stage in self:
            if stage.quantity_in > 0:
                # Calculate efficiency based on output ratio, loss percentage, and quality
                output_ratio = stage.quantity_out / stage.quantity_in if stage.quantity_in > 0 else 0
                loss_factor = (100 - stage.loss_percentage) / 100 if stage.loss_percentage else 1
                quality_factor = stage.quality_score / 100 if stage.quality_score else 1

                # Weighted efficiency score
                stage.efficiency_score = (output_ratio * 0.4 + loss_factor * 0.3 + quality_factor * 0.3) * 100
            else:
                stage.efficiency_score = 0

    # Constraint Methods
    @api.constrains('quantity_in', 'quantity_out', 'quantity_loss', 'quantity_waste')
    def _check_quantity_balance(self):
        for stage in self:
            if stage.quantity_out + stage.quantity_loss + stage.quantity_waste > stage.quantity_in:
                raise ValidationError(_(
                    'Total output, loss, and waste (%.2f) cannot exceed input quantity (%.2f)!'
                ) % (stage.quantity_out + stage.quantity_loss + stage.quantity_waste, stage.quantity_in))

    @api.constrains('temperature')
    def _check_temperature_range(self):
        for stage in self:
            if stage.temperature and (stage.temperature < -50 or stage.temperature > 60):
                raise ValidationError(_('Temperature must be between -50°C and 60°C!'))

    @api.constrains('ph_level')
    def _check_ph_level(self):
        for stage in self:
            if stage.ph_level and (stage.ph_level < 0 or stage.ph_level > 14):
                raise ValidationError(_('pH level must be between 0 and 14!'))

    # Business Methods
    def action_start_stage(self):
        """Start the inventory stage"""
        for stage in self:
            if stage.state != 'draft':
                raise UserError(_('Only draft stages can be started.'))

            stage.state = 'in_progress'
            stage.date = fields.Datetime.now()

    def action_complete_stage(self):
        """Complete the inventory stage"""
        for stage in self:
            if stage.state != 'in_progress':
                raise UserError(_('Only in-progress stages can be completed.'))

            # Validate required data
            if not stage.quantity_out and not stage.quantity_loss and not stage.quantity_waste:
                raise UserError(_('Please specify output quantities before completing the stage.'))

            stage.state = 'completed'
            stage._create_stock_moves()

    def action_cancel_stage(self):
        """Cancel the inventory stage"""
        for stage in self:
            if stage.state == 'completed':
                raise UserError(_('Cannot cancel completed stages.'))

            stage.state = 'cancelled'

    def action_reset_to_draft(self):
        """Reset stage to draft"""
        for stage in self:
            if stage.state == 'completed' and stage.stock_move_ids:
                raise UserError(_('Cannot reset stages with associated stock moves.'))

            stage.state = 'draft'

    def _create_stock_moves(self):
        """Create stock moves based on stage quantities"""
        self.ensure_one()

        if not self.location_id or not self.location_dest_id:
            return

        StockMove = self.env['stock.move']
        moves = []

        # Create move for output quantity
        if self.quantity_out > 0:
            move_vals = {
                'name': f"{self.name} - Output",
                'product_id': self.product_id.id,
                'product_uom_qty': self.quantity_out,
                'product_uom': self.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'inventory_stage_id': self.id,
                'agricultural_farm_id': self.farm_id.id,
                'agricultural_project_id': self.project_id.id if self.project_id else None,
                'cultivation_stage': self.stage_type,
                'quality_grade': self.quality_grade,
                'temperature_at_harvest': self.temperature,
                'humidity_at_harvest': self.humidity,
                'origin': self.name,
            }
            moves.append(move_vals)

        # Create move for loss/waste to inventory loss location
        if self.quantity_loss > 0 or self.quantity_waste > 0:
            loss_location = self.env.ref('stock.stock_location_inventory', raise_if_not_found=False)
            if loss_location:
                total_loss = self.quantity_loss + self.quantity_waste
                move_vals = {
                    'name': f"{self.name} - Loss/Waste",
                    'product_id': self.product_id.id,
                    'product_uom_qty': total_loss,
                    'product_uom': self.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': loss_location.id,
                    'inventory_stage_id': self.id,
                    'agricultural_farm_id': self.farm_id.id,
                    'origin': self.name,
                }
                moves.append(move_vals)

        # Create and confirm moves
        created_moves = StockMove.create(moves)
        created_moves._action_confirm()
        created_moves._action_done()

        return created_moves

    def get_previous_stage(self):
        """Get the previous stage in sequence"""
        self.ensure_one()
        return self.search([
            ('project_id', '=', self.project_id.id),
            ('product_id', '=', self.product_id.id),
            ('sequence', '<', self.sequence)
        ], order='sequence desc', limit=1)

    def get_next_stage(self):
        """Get the next stage in sequence"""
        self.ensure_one()
        return self.search([
            ('project_id', '=', self.project_id.id),
            ('product_id', '=', self.product_id.id),
            ('sequence', '>', self.sequence)
        ], order='sequence asc', limit=1)

    def create_next_stage(self):
        """Create the next stage based on current output"""
        self.ensure_one()

        if self.state != 'completed':
            raise UserError(_('Cannot create next stage from incomplete stage.'))

        if self.quantity_out <= 0:
            raise UserError(_('No output quantity to transfer to next stage.'))

        # Determine next stage type
        stage_flow = {
            'seeding': 'germination',
            'germination': 'transplanting',
            'transplanting': 'cultivation',
            'cultivation': 'inspection',
            'inspection': 'harvest',
            'harvest': 'processing',
            'processing': 'grading',
            'grading': 'packing',
            'packing': 'storage',
            'storage': 'shipping'
        }

        next_stage_type = stage_flow.get(self.stage_type)
        if not next_stage_type:
            return None

        # Create next stage
        next_stage_vals = {
            'name': f"{dict(self._fields['stage_type'].selection)[next_stage_type]} - {self.product_id.name}",
            'sequence': self.sequence + 10,
            'farm_id': self.farm_id.id,
            'project_id': self.project_id.id,
            'production_request_id': self.production_request_id.id if self.production_request_id else None,
            'product_id': self.product_id.id,
            'stage_type': next_stage_type,
            'quantity_in': self.quantity_out,
            'uom_id': self.uom_id.id,
            'location_id': self.location_dest_id.id,
            'responsible_user_id': self.responsible_user_id.id,
        }

        return self.create(next_stage_vals)

    def action_view_stock_moves(self):
        """View related stock moves"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Moves'),
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('inventory_stage_id', '=', self.id)],
            'context': {'default_inventory_stage_id': self.id},
        }

    def action_view_cost_allocations(self):
        """View cost allocations affecting this stage"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cost Allocations'),
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form',
            'domain': [
                '|',
                ('farm_id', '=', self.farm_id.id),
                ('project_id', '=', self.project_id.id)
            ],
        }

    def get_stage_performance_data(self):
        """Get performance data for this stage"""
        self.ensure_one()

        return {
            'stage_name': self.name,
            'stage_type': dict(self._fields['stage_type'].selection)[self.stage_type],
            'efficiency_score': self.efficiency_score,
            'loss_percentage': self.loss_percentage,
            'quality_score': self.quality_score,
            'cost_per_unit_out': self.stage_cost / self.quantity_out if self.quantity_out > 0 else 0,
            'output_ratio': self.quantity_out / self.quantity_in if self.quantity_in > 0 else 0,
            'duration_hours': (
                                          fields.Datetime.now() - self.date).total_seconds() / 3600 if self.state == 'in_progress' else 0,
        }

    @api.model
    def get_stage_summary_by_type(self, farm_id, date_from=None, date_to=None):
        """Get summary statistics by stage type"""
        domain = [('farm_id', '=', farm_id), ('state', '=', 'completed')]

        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        stages = self.search(domain)

        summary = {}
        for stage in stages:
            stage_type = stage.stage_type
            if stage_type not in summary:
                summary[stage_type] = {
                    'count': 0,
                    'total_input': 0,
                    'total_output': 0,
                    'total_loss': 0,
                    'total_cost': 0,
                    'avg_efficiency': 0,
                    'avg_quality': 0,
                }

            summary[stage_type]['count'] += 1
            summary[stage_type]['total_input'] += stage.quantity_in
            summary[stage_type]['total_output'] += stage.quantity_out
            summary[stage_type]['total_loss'] += stage.quantity_loss + stage.quantity_waste
            summary[stage_type]['total_cost'] += stage.stage_cost
            summary[stage_type]['avg_efficiency'] += stage.efficiency_score
            summary[stage_type]['avg_quality'] += stage.quality_score or 0

        # Calculate averages
        for stage_type, data in summary.items():
            if data['count'] > 0:
                data['avg_efficiency'] /= data['count']
                data['avg_quality'] /= data['count']
                data['loss_rate'] = (data['total_loss'] / data['total_input']) * 100 if data['total_input'] > 0 else 0
                data['cost_per_unit'] = data['total_cost'] / data['total_output'] if data['total_output'] > 0 else 0

        return summary

    # Onchange Methods
    @api.onchange('stage_type')
    def _onchange_stage_type(self):
        if self.stage_type:
            # Auto-set name based on stage type
            stage_name = dict(self._fields['stage_type'].selection)[self.stage_type]
            product_name = self.product_id.name if self.product_id else 'Product'
            self.name = f"{stage_name} - {product_name}"

    @api.onchange('labor_cost', 'material_cost', 'equipment_cost')
    def _onchange_cost_components(self):
        self.stage_cost = self.labor_cost + self.material_cost + self.equipment_cost
class AccountAccountInherit(models.Model):
    _inherit = 'account.account'

    agricultural_farm_id = fields.Many2one(
        'agricultural.farm',
        string='Agricultural Farm',
        help='Link this account to a specific farm',
        index=True,
        copy=False,
        tracking=True
    )

    is_farm_account = fields.Boolean(
        string='Is Farm Account',
        compute='_compute_is_farm_account',
        store=True,
        help='Indicates if this account is linked to a farm'
    )

    @api.depends('agricultural_farm_id')
    def _compute_is_farm_account(self):
        for record in self:
            record.is_farm_account = bool(record.agricultural_farm_id)
class Category(models.Model):
    _inherit = "product.category"

    expense_direct_cost = fields.Many2one('account.account',readonly=False,string="Expense Account",help="Used Materials Cost Account")
    stock_move_main = fields.Many2one('account.account',readonly=False,string="Stock Account",help="Main Warehouse Stock Account")