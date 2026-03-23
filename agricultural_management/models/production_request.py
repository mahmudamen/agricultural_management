from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.tools import float_compare, float_is_zero
import logging

_logger = logging.getLogger(__name__)

class ProductionRequest(models.Model):
    _name = 'agricultural.production.request'
    _description = 'Production Request Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Request Number', required=True, copy=False, readonly=True,translate=True, tracking=True,
                       default=lambda self: _('New'))
    farm_id = fields.Many2one('agricultural.farm', 'Farm', required=True, tracking=True)
    requested_by = fields.Many2one('hr.employee', 'Requested By', required=True,
                                   default=lambda self: self.env.user.employee_id, tracking=True)
    request_date = fields.Date('Request Date', required=True, default=fields.Date.today, tracking=True)
    required_date = fields.Date('Required Date', required=False, default=fields.Date.today,tracking=True)
    priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')
    ], 'Priority', default='normal', tracking=True)
    # Request Lines
    line_ids = fields.One2many('agricultural.production.request.line', 'request_id', 'Request Lines')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=False
    )
    # Approval Fields
    dr_approved_by = fields.Many2one('hr.employee', 'Dr./Engineer Approved By', tracking=True)
    dr_approval_date = fields.Datetime('Dr./Engineer Approval Date', tracking=True)
    dr_approval_notes = fields.Text('Dr./Engineer Notes')
    warehouse_approved_by = fields.Many2one('hr.employee', 'Warehouse Manager Approved By', tracking=True)
    warehouse_approval_date = fields.Datetime('Warehouse Approval Date', tracking=True)
    warehouse_approval_notes = fields.Text('Warehouse Manager Notes')
    accounts_approved_by = fields.Many2one('hr.employee', 'Accounts Approved By', tracking=True)
    accounts_approval_date = fields.Datetime('Accounts Approval Date', tracking=True)
    accounts_approval_notes = fields.Text('Accounts Notes')
    total_estimated_cost = fields.Float('Total Estimated Cost', compute='_compute_totals', store=True)
    total_approved_cost = fields.Float('Total Approved Cost', compute='_compute_totals', store=True)
    budget_allocation = fields.Many2one('account.analytic.account', 'Budget Allocation')
    project_id = fields.Many2one('agricultural.project', 'Project', required=True)
    request_type = fields.Selection([
        ('seeds', 'Seeds Request'),
        ('fertilizers', 'Fertilizers Request'),
        ('pesticides', 'Pesticides Request'),
        ('equipment', 'Equipment Request'),
        ('labor', 'Labor Request'),
        ('mixed', 'Mixed Request')
    ], required=True, default='mixed')
    picking_count = fields.Integer('Picking Count')
    approved_date = fields.Date('Approved Date', readonly=True)
    delivery_date = fields.Date('Delivery Date')
    approved_by = fields.Many2one('hr.employee', 'Approved By', readonly=True)
    request_line_ids = fields.One2many('agricultural.production.request.line',
                                       'request_id', 'Request Lines')
    estimated_cost = fields.Monetary('Estimated Cost', currency_field='currency_id',
                                     compute='_compute_costs', store=True)
    actual_cost = fields.Monetary('Actual Cost', currency_field='currency_id')
    total_cost = fields.Monetary('Total Cost', currency_field='currency_id',
                                 compute='_compute_costs', store=True)
    purchase_order_ids = fields.One2many('purchase.order', 'agricultural_request_id',
                                         'Purchase Orders')
    delivery_note = fields.Text('Delivery Notes')
    completion_remarks = fields.Text('Completion Remarks')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('dr_approved', 'Dr. Approved'),
        ('inventory_review', 'Inventory Review'),
        ('transfer_ready', 'Transfer Ready'),
        ('transferred', 'Transferred to Farm'),
        ('rfq_needed', 'RFQ Required'),
        ('rfq_pending', 'RFQ Pending'),
        ('purchase_approved', 'Purchase Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)
    # Role-specific approval fields
    inventory_reviewed_by = fields.Many2one('hr.employee', 'Reviewed By (Inventory)', tracking=True)
    inventory_review_date = fields.Datetime('Inventory Review Date', tracking=True)
    inventory_notes = fields.Text('Inventory Manager Notes')
    transfer_approved_by = fields.Many2one('hr.employee', 'Transfer Approved By', tracking=True)
    transfer_approval_date = fields.Datetime('Transfer Approval Date', tracking=True)
    completion_approved_by = fields.Many2one('hr.employee', 'Completed By', tracking=True)
    completion_date = fields.Datetime('Completion Date', tracking=True)
    # New fields for inventory tracking
    availability_status = fields.Selection([
        ('all_available', 'All Available'),
        ('some_available', 'Some Available'),
        ('few_available', 'Few Available'),
        ('none_available', 'None Available')
    ], string='Availability Status', compute='_compute_availability_status', store=True)
    total_available_lines = fields.Integer('Available Lines', compute='_compute_availability_counts')
    total_unavailable_lines = fields.Integer('Unavailable Lines', compute='_compute_availability_counts')
    total_partial_lines = fields.Integer('Partial Lines', compute='_compute_availability_counts')
    # Related documents
    stock_move_ids = fields.One2many('stock.move', 'agricultural_request_id', 'Stock Moves')
    rfq_ids = fields.One2many('purchase.order', 'agricultural_request_id', 'RFQs Created')
    # Add this field to your Production Request model
    line_count = fields.Integer('Lines Count', compute='_compute_line_count', store=True)
    stock_picking_ids = fields.One2many(
        'stock.picking',
        'agricultural_request_id',
        string='Stock Pickings'
    )
    account_move_ids = fields.One2many(
        'account.move',
        'agricultural_request_id',
        string='Account Moves'
    )
    account_move_line_ids = fields.One2many(
        'account.move.line',
        'agricultural_request_id',
        string='Account Moves'
    )
    cost_variance = fields.Monetary('Cost Variance',
                                    compute='_compute_cost_variance', store=True)
    cost_variance_percent = fields.Float('Variance %',
                                         compute='_compute_cost_variance', store=True)
    asset_account_id = fields.Many2one(
        'account.account',
        string='Asset Account',
        related="farm_id.asset_account_id",
        help='Account for tracking farm fixed assets',
        copy=False,
        tracking=True
    )
    expense_account_id = fields.Many2one(
        'account.account',
        string='Direct Cost Account',
        related="farm_id.expense_account_id",
        help='Account for tracking direct costs',
        copy=False,
        tracking=True
    )
    move_count = fields.Integer('Move Count')
    account_move_count = fields.Integer('Journal Entry Count')
    lot_count = fields.Integer(string='Lot Count')
    product_id = fields.Many2one('product.product', 'Product')
    quantity = fields.Float(
        'Lot Quantity',
        digits='Product Unit of Measure',
        required=False,
        tracking=True
    )
    note = fields.Text('Delivery Notes')
    rfq_count = fields.Integer(string='Rfq Count')
    available_qty = fields.Float('Available Quantity', digits='Product Unit of Measure')
    to_procure_qty = fields.Float('To Procure Quantity', digits='Product Unit of Measure')
    price = fields.Float('Price', digits='Product Unit of Measure')
    subtotal = fields.Float('SubTotal', digits='Product Unit of Measure')

    line_preview = fields.Html(
        string='Lines Preview',
        compute='_compute_line_preview',
        sanitize=False
    )

    @api.depends('line_ids', 'line_ids.product_id', 'line_ids.quantity', 'line_ids.uom_id',
                 'line_ids.availability_status')
    def _compute_line_preview(self):
        """Generate HTML preview of top 3 lines with modern styling"""
        for record in self:
            if not record.line_ids:
                record.line_preview = '<div class="text-muted" style="text-align: center; padding: 8px; font-size: 10px;">No items</div>'
                continue

            html_parts = []
            for line in record.line_ids[:3]:
                product_name = line.product_id.name or 'Undefined'
                qty = line.quantity
                uom = line.uom_id.name or ''

                # Availability color
                if line.availability_status == 'available':
                    border_color = '#10b981'
                    icon = 'fa-check-circle'
                    icon_color = '#10b981'
                elif line.availability_status == 'partial':
                    border_color = '#f59e0b'
                    icon = 'fa-exclamation-circle'
                    icon_color = '#f59e0b'
                else:
                    border_color = '#ef4444'
                    icon = 'fa-times-circle'
                    icon_color = '#ef4444'

                html_parts.append(f'''
                    <div style="background: #f9fafb; border-right: 3px solid {border_color}; 
                                border-radius: 6px; padding: 8px; margin-bottom: 6px;
                                transition: all 0.2s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="flex-grow: 1;">
                                <div style="font-weight: 600; font-size: 10px; color: #1f2937; 
                                          margin-bottom: 3px; overflow: hidden; text-overflow: ellipsis; 
                                          white-space: nowrap;">
                                    {product_name}
                                </div>
                                <div style="font-size: 9px; color: #6b7280;">
                                    <i class="fa fa-cube" style="font-size: 8px; margin-left: 3px;"></i>
                                    {qty} {uom}
                                </div>
                            </div>
                            <div>
                                <i class="fa {icon}" style="color: {icon_color}; font-size: 12px;"></i>
                            </div>
                        </div>
                    </div>
                ''')

            if len(record.line_ids) > 3:
                remaining = len(record.line_ids) - 3
                html_parts.append(f'''
                    <div style="text-align: center; padding: 4px; margin-top: 4px;">
                        <small style="color: #9ca3af; font-size: 9px; font-weight: 500;">
                            + {remaining} more items...
                        </small>
                    </div>
                ''')

            record.line_preview = ''.join(html_parts)
    # Add these compute methods to your ProductionRequest class
    def action_view_lines(self):
        """Action to view request lines"""
        self.ensure_one()
        return {
            'name': _('Request Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.production.request.line',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {
                'default_request_id': self.id,
                'default_location_id': self.farm_id.location_id.id if self.farm_id.location_id else False,
            }
        }
    @api.depends('line_ids')
    def _compute_line_count(self):
        """Compute total number of lines"""
        for record in self:
            record.line_count = len(record.line_ids)
    @api.depends('line_ids', 'line_ids.availability_status')
    def _compute_availability_counts(self):
        """Compute counts for each availability status"""
        for record in self:
            record.total_available_lines = len(record.line_ids.filtered(
                lambda l: l.availability_status == 'available'
            ))
            record.total_partial_lines = len(record.line_ids.filtered(
                lambda l: l.availability_status == 'partial'
            ))
            record.total_unavailable_lines = len(record.line_ids.filtered(
                lambda l: l.availability_status == 'unavailable'
            ))
    @api.depends('total_available_lines', 'total_unavailable_lines', 'total_partial_lines', 'line_count')
    def _compute_availability_status(self):
        """Compute overall availability status based on line availability"""
        for record in self:
            if record.line_count == 0:
                record.availability_status = 'none_available'
            elif record.total_available_lines == record.line_count:
                record.availability_status = 'all_available'
            elif record.total_available_lines >= record.line_count * 0.7:
                record.availability_status = 'some_available'
            elif record.total_available_lines > 0:
                record.availability_status = 'few_available'
            else:
                record.availability_status = 'none_available'
    @api.depends('line_ids', 'line_ids.estimated_cost', 'line_ids.subtotal')
    def _compute_costs(self):
        """Compute estimated and total costs"""
        for record in self:
            record.estimated_cost = sum(line.estimated_cost for line in record.line_ids)
            record.total_cost = sum(line.subtotal for line in record.line_ids)
    @api.depends('estimated_cost', 'total_cost')
    def _compute_cost_variance(self):
        """Compute cost variance and percentage"""
        for record in self:
            record.cost_variance = record.total_cost - record.estimated_cost
            if record.estimated_cost:
                record.cost_variance_percent = (record.cost_variance / record.estimated_cost) * 100
            else:
                record.cost_variance_percent = 0.0
    @api.depends('line_ids')
    def _compute_totals(self):
        """Compute total estimated and approved costs"""
        for record in self:
            record.total_estimated_cost = sum(line.estimated_cost for line in record.line_ids)
            record.total_approved_cost = sum(line.approved_cost for line in record.line_ids)
    def check_stock_availability(self):
        """Check stock availability for all lines and refresh view"""
        self.ensure_one()

        # Update availability for each line
        for line in self.request_line_ids:
            if line.product_id:
                available_qty = self._get_available_quantity(line.product_id)
                line.write({'available_qty': available_qty})
                self.write({'state': 'transfer_ready'})

        # Force compute methods to run
        self.request_line_ids._compute_availability_status()
        self.request_line_ids._compute_unavailable_qty()
        self._compute_availability_status()
        self._compute_availability_counts()

        # Flush to database
        self.env.flush_all()

        # Return action to reload the current form view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    def _get_available_quantity(self, product):
        """Get available quantity for a product from main warehouse"""
        if not product:
            return 0.0

        try:
            # Get main warehouse location
            main_location = self._get_main_location()
            if not main_location:
                _logger.warning("No main warehouse location found")
                return 0.0

            # Search quants at main location
            domain = [
                ('product_id', '=', product.id),
                ('location_id', '=', main_location.id),
            ]

            quants = self.env['stock.quant'].search(domain)
            available_qty = 0.0

            for quant in quants:
                if hasattr(quant, 'available_quantity'):
                    available_qty += quant.available_quantity
                else:
                    available_qty += max(0, quant.quantity - quant.reserved_quantity)

            return max(0.0, available_qty)

        except Exception as e:
            _logger.error(f"Error getting available quantity for {product.name}: {str(e)}")
            return 0.0
    def check_stock_availability_with_message(self):
        """Check stock availability and show detailed message"""
        self.ensure_one()

        updated_count = 0
        available_count = 0
        partial_count = 0
        unavailable_count = 0

        # Update availability for each line
        for line in self.request_line_ids:
            if line.product_id:
                old_qty = line.available_qty
                new_qty = self._get_available_quantity(line.product_id)

                line.write({'available_qty': new_qty})

                if old_qty != new_qty:
                    updated_count += 1

        # Force compute methods
        self.request_line_ids._compute_availability_status()
        self.request_line_ids._compute_unavailable_qty()
        self._compute_availability_status()
        self._compute_availability_counts()

        # Count statuses
        for line in self.request_line_ids:
            if line.availability_status == 'available':
                available_count += 1
            elif line.availability_status == 'partial':
                partial_count += 1
            else:
                unavailable_count += 1

        # Flush to database
        self.env.flush_all()

        # Prepare summary message
        message = f"""
        <div style="text-align: right; direction: rtl;">
            <strong>Availability Check Results:</strong><br/>
            <ul style="list-style: none; padding: 10px;">
                <li>✅ Fully Available: {available_count}</li>
                <li>⚠️ Partially Available: {partial_count}</li>
                <li>❌ Not Available: {unavailable_count}</li>
            </ul>
            <small>Updated {updated_count} from {len(self.request_line_ids)} item(s)</small>
        </div>
        """

        # Post message to chatter
        self.message_post(
            body=message,
            subject='Stock availability check completed',
            message_type='notification'
        )

        # Return reload action
        return True
    def _get_preferred_supplier(self, product):
        """Get preferred supplier for a product"""
        if not product:
            return False

        supplier_info = product.seller_ids.filtered(lambda s: s.product_id == product)[:1]
        if supplier_info:
            return supplier_info.partner_id

        if product.seller_ids:
            return product.seller_ids[0].partner_id

        return False
    def _create_rfqs_for_unavailable(self):
        """Create RFQs for unavailable items"""
        unavailable_lines = self.request_line_ids.filtered(
            lambda l: l.unavailable_qty > 0 and l.availability_status in ['unavailable', 'partial']
        )

        if not unavailable_lines:
            return 0

        rfq_count = 0
        supplier_groups = {}

        for line in unavailable_lines:
            supplier = self._get_preferred_supplier(line.product_id)
            supplier_key = supplier if supplier else 'no_supplier'

            if supplier_key not in supplier_groups:
                supplier_groups[supplier_key] = []
            supplier_groups[supplier_key].append(line)

        for supplier_key, lines in supplier_groups.items():
            rfq_vals = {
                'agricultural_request_id': self.id,
                'origin': f'Agricultural Request: {self.name}',
                'date_planned': self.required_date or fields.Datetime.now(),
                'order_line': [],
                'company_id': self.env.company.id,
            }

            if supplier_key != 'no_supplier':
                rfq_vals['partner_id'] = supplier_key.id

            for line in lines:
                qty_to_purchase = line.unavailable_qty

                if qty_to_purchase > 0:
                    rfq_line_vals = {
                        'product_id': line.product_id.id,
                        'name': line.description or line.product_id.name,
                        'product_qty': qty_to_purchase,
                        'product_uom': line.uom_id.id,
                        'price_unit': line.unit_price or 0.0,
                        'date_planned': self.required_date or fields.Datetime.now(),
                    }
                    rfq_vals['order_line'].append((0, 0, rfq_line_vals))

            if rfq_vals['order_line']:
                rfq = self.env['purchase.order'].create(rfq_vals)

                for i, line in enumerate([l for l in lines if l.unavailable_qty > 0]):
                    if i < len(rfq.order_line):
                        line.rfq_line_id = rfq.order_line[i].id
                        line.state = 'rfq_pending'

                rfq_count += 1

        return rfq_count
    def action_create_rfq_for_missing(self):
        """Create RFQ for missing/unavailable items"""
        missing_lines = self.request_line_ids.filtered(
            lambda l: l.availability_status in ['unavailable', 'partial'] and l.unavailable_qty > 0
        )

        if not missing_lines:
            raise UserError(_("No missing items found to create RFQ."))

        rfq_count = self._create_rfqs_for_unavailable()
        self.write({'state': 'rfq_pending'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('RFQ Created'),
                'message': _('Request for Quotation created for %s missing items.') % len(missing_lines),
                'type': 'success',
                'sticky': False,
            }
        }
    def action_submit(self):
        """Submit request"""
        if not self.request_line_ids:
            raise UserError(_('Please add at least one request line before submitting.'))


        self._calculate_estimated_costs()
        self.write({'state': 'submitted'})
        self._send_approval_notification('agricultural_management.group_agricultural_engineer')
        return {
            'name': _('Production Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.production.request',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'form_view_initial_mode': 'edit',
            },
            'params': {
                'message': _('%d lines added successfully.') % (len(self.request_line_ids)),
                'type': 'success',
            }
        }
    def _calculate_estimated_costs(self):
        """Calculate initial estimated costs"""
        for line in self.request_line_ids:
            if not line.unit_price:
                line.unit_price = self._get_product_cost(line.product_id)
            line.estimated_cost = line.quantity * line.unit_price
    def _get_product_cost(self, product):
        """Get product cost from various sources"""
        if product.standard_price:
            return product.standard_price

        last_purchase = self.env['purchase.order.line'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'done')
        ], limit=1, order='date_order desc')

        if last_purchase:
            return last_purchase.price_unit

        return product.list_price or 0.0
    def _send_notification(self, group_external_id, message):
        """Send notification to specific group"""
        try:
            group = self.env.ref(group_external_id)
            if group and group.users:
                self.message_subscribe(partner_ids=group.users.partner_id.ids)
                self.message_post(
                    body=f'{message}: {self.name}',
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment'
                )
        except ValueError:
            _logger.warning(f"Group {group_external_id} not found")
    @api.depends('account_move_ids')
    def _compute_account_move_count(self):
        """Count related journal entries"""
        for record in self:
            record.account_move_count = len(record.account_move_ids)
    def _get_stock_account_by_product_and_location(self, product, location):
        """
        Automatically determine stock account based on:
        1. Product category (fertilizers/pesticides/seeds)
        2. Location type (main warehouse or farm/branch)
        """
        company = self.env.company

        # Determine if location is main warehouse or farm/branch
        is_main_location = self._is_main_warehouse_location(location)

        # Get product category
        category_name = product.categ_id.name.lower() if product.categ_id else ''

        # Map to appropriate stock account from config
        if 'fertilizer' in category_name or 'fertilizer' in category_name or 'fertilizer' in category_name:
            return company.stock_fertilizers_main if is_main_location else company.stock_fertilizers_branch
        elif 'pesticide' in category_name or 'pesticide' in category_name:
            return company.stock_pesticides_main if is_main_location else company.stock_pesticides_branch
        elif 'seed' in category_name or 'Seeds' in category_name or 'seed' in category_name:
            return company.stock_seeds_main if is_main_location else company.stock_seeds_branch
        else:
            # Default to fertilizers account if category not recognized
            _logger.warning(f"Product category '{category_name}' not recognized, using fertilizers account")
            return company.stock_fertilizers_main if is_main_location else company.stock_fertilizers_branch
    def _is_main_warehouse_location(self, location):
        """Check if location belongs to main warehouse"""
        main_warehouse = self._get_main_location()
        if main_warehouse:
            return location.id == main_warehouse.id

        # Fallback: check location name/code
        main_location = self._get_main_location()
        if main_location:
            return location.id == main_location.id

        return False
    def _get_cogs_account_by_product(self, product):
        """Get COGS account based on product category"""
        company = self.env.company
        category_name = product.categ_id.name.lower() if product.categ_id else ''

        if 'fertilizer' in category_name or 'fertilizer' in category_name:
            return company.cogs_fertilizers
        elif 'pesticide' in category_name or 'pesticide' in category_name:
            return company.cogs_pesticides
        elif 'seed' in category_name or 'Seeds' in category_name:
            return company.cogs_seeds
        else:
            return company.cogs_fertilizers  # Default
    def _create_accounting_entry_for_transfer(self, picking):
        """
        Create accounting entry when stock is transferred
        Uses accounts from ResConfigSettings automatically
        """
        company = self.env.company
        journal = company.internal_transfer_journal or company.stock_journal
        if not journal:
            _logger.warning('No journal configured for stock transfers')
            return False
        move_lines = []
        for move in picking.move_ids_without_package:
            product = move.product_id
            quantity = move.product_uom_qty
            # Get product cost
            cost = product.standard_price or product.lst_price or 0.0
            total_value = quantity * cost

            if total_value <= 0:
                _logger.warning(f"Zero value for product {product.name}, skipping accounting")
                continue

            # Automatically determine accounts based on config
            source_account = self._get_stock_account_by_product_and_location(
                product, move.location_id
            )
            dest_account = self._get_stock_account_by_product_and_location(
                product, move.location_dest_id
            )

            if not source_account or not dest_account:
                _logger.error(f"Missing stock accounts for {product.name}")
                continue

            # Prepare description
            description = f'{product.name} - {self.farm_id.name} ({self.name})'

            # If transferring between same account type, use transit account
            if source_account == dest_account:
                transit_account = company.goods_in_transit
                if not transit_account:
                    _logger.warning("No transit account configured")
                    continue

                # Debit: Goods in Transit
                move_lines.append((0, 0, {
                    'name': f'{description} - In Transit',
                    'account_id': transit_account.id,
                    'debit': total_value,
                    'credit': 0.0,
                    'product_id': product.id,
                    'quantity': quantity,
                    'product_uom_id': move.product_uom.id,
                    'analytic_distribution': {
                        str(self.budget_allocation.id): 100
                    } if self.budget_allocation else False,
                    'agricultural_request_id': self.id,
                }))

                # Credit: Source Stock
                move_lines.append((0, 0, {
                    'name': f'{description} - From {move.location_id.name}',
                    'account_id': source_account.id,
                    'debit': 0.0,
                    'credit': total_value,
                    'product_id': product.id,
                    'quantity': quantity,
                    'product_uom_id': move.product_uom.id,
                    'agricultural_request_id': self.id,
                }))
            else:
                # Direct transfer between different location types
                # Debit: Destination Stock (Farm)
                move_lines.append((0, 0, {
                    'name': f'{description} - To Farm',
                    'account_id': dest_account.id,
                    'debit': total_value,
                    'credit': 0.0,
                    'product_id': product.id,
                    'quantity': quantity,
                    'product_uom_id': move.product_uom.id,
                    'analytic_distribution': {
                        str(self.budget_allocation.id): 100
                    } if self.budget_allocation else False,
                    'agricultural_request_id': self.id,
                }))

                # Credit: Source Stock (Main Warehouse)
                move_lines.append((0, 0, {
                    'name': f'{description} - From Warehouse',
                    'account_id': source_account.id,
                    'debit': 0.0,
                    'credit': total_value,
                    'product_id': product.id,
                    'quantity': quantity,
                    'product_uom_id': move.product_uom.id,
                    'agricultural_request_id': self.id,
                }))

        if not move_lines:
            _logger.info("No valid move lines to create journal entry")
            return False

        # Create account move
        account_move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'{self.name} - {picking.name}',
            'line_ids': move_lines,
            'agricultural_request_id': self.id,
            'agricultural_project_id': self.project_id.id if self.project_id else False,
        }

        try:
            account_move = self.env['account.move'].create(account_move_vals)

            # Auto post if configured
            if company.auto_post_stock_entries:
                account_move.action_post()
                _logger.info(f"Journal entry {account_move.name} posted automatically")
            else:
                _logger.info(f"Journal entry {account_move.name} created in draft")

            # Post message to request
            self.message_post(
                body=f'Journal Entry created: {account_move.name} for picking {picking.name}',
                subject='Accounting Entry Created'
            )

            return account_move

        except Exception as e:
            _logger.error(f"Error creating journal entry: {str(e)}")
            return False
    def _create_accounting_entry_for_consumption(self, move_line):
        """
        Create accounting entry when items are consumed at farm
        Records expense using COGS accounts
        """
        if not self.env.company.stock_accounting_active:
            return False

        company = self.env.company
        journal = company.stock_journal

        if not journal:
            return False

        product = move_line.product_id
        quantity = move_line.delivered_qty
        cost = product.standard_price or product.lst_price or 0.0
        total_value = quantity * cost

        if total_value <= 0:
            return False

        # Get accounts automatically
        stock_account = self._get_stock_account_by_product_and_location(
            product, self.farm_id.location_id
        )
        cogs_account = self._get_cogs_account_by_product(product)

        if not stock_account or not cogs_account:
            _logger.error(f"Missing accounts for consumption of {product.name}")
            return False

        move_lines = [
            # Debit: Cost of Goods Used (Expense)
            (0, 0, {
                'name': f'{product.name} - Consumed at {self.farm_id.name}',
                'account_id': cogs_account.id,
                'debit': total_value,
                'credit': 0.0,
                'product_id': product.id,
                'quantity': quantity,
                'product_uom_id': move_line.uom_id.id,
                'analytic_distribution': {
                    str(self.budget_allocation.id): 100
                } if self.budget_allocation else False,
                'agricultural_request_id': self.id,
            }),

            # Credit: Stock Account
            (0, 0, {
                'name': f'{product.name} - Stock Reduction',
                'account_id': stock_account.id,
                'debit': 0.0,
                'credit': total_value,
                'product_id': product.id,
                'quantity': quantity,
                'product_uom_id': move_line.uom_id.id,
                'agricultural_request_id': self.id,
            }),
        ]

        # Create account move
        account_move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'{self.name} - Consumption',
            'line_ids': move_lines,
            'agricultural_request_id': self.id,
            'agricultural_project_id': self.project_id.id if self.project_id else False,
        }

        try:
            account_move = self.env['account.move'].create(account_move_vals)

            if company.auto_post_stock_entries:
                account_move.action_post()

            return account_move
        except Exception as e:
            _logger.error(f"Error creating consumption entry: {str(e)}")
            return False
    # ==================== EXISTING METHODS WITH ACCOUNTING ====================
    def _create_transfers_from_main_location(self, main_location):
        """Create transfers from main location to farm location WITH ACCOUNTING"""
        available_lines = self.request_line_ids.filtered(lambda l: l.available_qty > 0)

        if not available_lines:
            return 0

        # Create picking
        picking_vals = {
            'picking_type_id': self._get_internal_picking_type(main_location).id,
            'location_id': main_location.id,
            'location_dest_id': self.farm_id.location_id.id,
            'origin': self.name,
            'agricultural_project_id': self.project_id.id,
            'agricultural_request_id': self.id,
            'partner_id': self.requested_by.user_partner_id.id if self.requested_by and self.requested_by.user_partner_id else False,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        # Create stock moves
        for line in available_lines:
            if line.available_qty > 0:
                transfer_qty = min(line.available_qty, line.quantity)

                move_vals = {
                    'name': f'{line.product_id.name} - {self.name}',
                    'product_id': line.product_id.id,
                    'product_uom_qty': transfer_qty,
                    'product_uom': line.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': main_location.id,
                    'location_dest_id': self.farm_id.location_id.id,
                    'agricultural_request_id': self.id,
                    'origin': self.name,
                    'company_id': self.env.company.id,
                }

                move = self.env['stock.move'].create(move_vals)
                line.stock_move_id = move.id



            # ✅ CREATE ACCOUNTING ENTRY AUTOMATICALLY
            try:
                self._create_accounting_entry_for_transfer(picking)
                _logger.info(f"Accounting entry created for picking {picking.name}")
            except Exception as e:
                _logger.error(f"Failed to create accounting entry: {str(e)}")
                # Don't fail the transfer, just log the error

        self.env.flush_all()
        self.env.cr.commit()
        return 1
    def _create_transfers_from_main_warehouse(self, main_warehouse):
        """Create transfers from main warehouse to farm location WITH ACCOUNTING"""
        available_lines = self.request_line_ids.filtered(lambda l: l.available_qty > 0)

        if not available_lines:
            return 0

        # Create single picking for all available items
        picking_vals = {
            'picking_type_id': self._get_internal_picking_type(main_warehouse).id,
            'location_id': main_warehouse.id,
            'location_dest_id': self.farm_id.location_id.id,
            'origin': self.name,
            'agricultural_project_id': self.project_id.id,
            'agricultural_request_id': self.id,
            'partner_id': self.farm_id.partner_id.id if self.farm_id.partner_id else False,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        # Create stock moves for each available line
        for line in available_lines:
            if line.available_qty > 0:
                transfer_qty = min(line.available_qty, line.quantity)

                move_vals = {
                    'name': f'{line.product_id.name} - {self.name}',
                    'product_id': line.product_id.id,
                    'product_uom_qty': transfer_qty,
                    'product_uom': line.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': main_warehouse.id,
                    'location_dest_id': self.farm_id.location_id.id,
                    'agricultural_request_id': self.id,
                    'origin': self.name,
                    'company_id': self.env.company.id,
                }

                move = self.env['stock.move'].create(move_vals)
                line.stock_move_id = move.id

        # Confirm and assign the picking
        picking.action_confirm()
        if picking.state == 'confirmed':
            picking.action_assign()

        # Validate and create accounting
        if picking.state == 'assigned':
            picking.button_validate()

            # ✅ CREATE ACCOUNTING ENTRY
            try:
                self._create_accounting_entry_for_transfer(picking)
            except Exception as e:
                _logger.error(f"Accounting entry failed: {str(e)}")

        self.env.flush_all()
        self.env.cr.commit()
        return 1
    def _create_internal_transfers(self):
        """Create internal stock moves for available items WITH ACCOUNTING"""
        available_lines = self.request_line_ids.filtered(
            lambda l: l.available_qty > 0 and l.availability_status in ['available', 'partial']
        )

        if not available_lines:
            return 0

        picking_count = 0

        # Group by warehouse location to create separate pickings
        location_groups = {}
        for line in available_lines:
            location = line.warehouse_location
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append(line)

        # Create picking for each location group
        for location, lines in location_groups.items():
            picking_type = self._get_internal_picking_type(location)

            if not picking_type:
                continue

            # Create stock picking
            picking_vals = {
                'picking_type_id': picking_type.id,
                'location_id': location.id,
                'location_dest_id': self.farm_id.location_id.id,
                'origin': self.name,
                'agricultural_request_id': self.id,
                'agricultural_project_id': self.project_id.id,
                'partner_id': self.requested_by.user_partner_id.id if self.requested_by and self.requested_by.user_partner_id else False,
            }
            picking = self.env['stock.picking'].create(picking_vals)

            # Create stock moves for each line
            for line in lines:
                transfer_qty = min(line.available_qty, line.quantity)

                if transfer_qty > 0:
                    move_vals = {
                        'name': f'{line.product_id.name} - {self.name}',
                        'product_id': line.product_id.id,
                        'product_uom_qty': transfer_qty,
                        'product_uom': line.uom_id.id,
                        'picking_id': picking.id,
                        'location_id': location.id,
                        'location_dest_id': self.farm_id.location_id.id,
                        'agricultural_request_id': self.id,
                        'origin': self.name,
                        'company_id': self.env.company.id,
                    }
                    move = self.env['stock.move'].create(move_vals)
                    line.stock_move_id = move.id
            picking_count += 1

        return picking_count
    # ==================== HELPER METHODS ====================
    def _get_internal_picking_type(self, location):
        """Get internal picking type for the location"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('default_location_src_id', '=', location.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if picking_type:
            return picking_type

        # Fallback to any internal picking type
        return self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
    def _get_main_location(self):
        """Get the main location for stock checking"""
        return self.env['stock.location'].search([
            ('company_id', '=', self.env.company.id),
            ('is_main_warehouse', '=', True)
        ], limit=1)
    # ==================== COMPUTE METHODS ===================
    @api.depends('request_line_ids')
    def _compute_line_count(self):
        for request in self:
            request.line_count = len(request.request_line_ids)
    @api.depends('request_line_ids.availability_status')
    def _compute_availability_counts(self):
        for record in self:
            lines = record.request_line_ids
            record.total_available_lines = len(lines.filtered(lambda l: l.availability_status == 'available'))
            record.total_partial_lines = len(lines.filtered(lambda l: l.availability_status == 'partial'))
            record.total_unavailable_lines = len(lines.filtered(lambda l: l.availability_status == 'unavailable'))
    @api.depends('request_line_ids.availability_status')
    def _compute_availability_status(self):
        for record in self:
            if not record.request_line_ids:
                record.availability_status = 'none_available'
                continue

            available_count = len(record.request_line_ids.filtered(lambda l: l.availability_status == 'available'))
            total_count = len(record.request_line_ids)

            if available_count == total_count:
                record.availability_status = 'all_available'
            elif available_count >= total_count * 0.5:
                record.availability_status = 'some_available'
            elif available_count > 0:
                record.availability_status = 'few_available'
            else:
                record.availability_status = 'none_available'
    @api.depends('request_line_ids.estimated_cost', 'request_line_ids.approved_cost')
    def _compute_totals(self):
        for record in self:
            record.total_estimated_cost = sum(record.request_line_ids.mapped('estimated_cost'))
            record.total_approved_cost = sum(record.request_line_ids.mapped('approved_cost'))
    # ==================== ONCHANGE METHODS ====================
    @api.onchange('farm_id')
    def _onchange_farm_id(self):
        if self.farm_id:
            if self.farm_id.analytic_account_id:
                self.budget_allocation = self.farm_id.analytic_account_id.id
            else:
                self.budget_allocation = False
            if self.farm_id.expense_account_id:
                self.expense_account_id = self.farm_id.expense_account_id.id
            else:
                self.expense_account_id = False
            if self.farm_id.asset_account_id:
                self.asset_account_id = self.farm_id.asset_account_id.id
            else:
                self.asset_account_id = False

            if self.farm_id.location_id:
                for line in self.request_line_ids:
                    line.location_id = self.farm_id.location_id.id
            else:
                for line in self.request_line_ids:
                    line.location_id = False
                return {
                    'warning': {
                        'title': _('No Location Found'),
                        'message': _('The selected farm "%s" does not have any location assigned.') % self.farm_id.name
                    }
                }
        else:
            self.budget_allocation = False
            for line in self.request_line_ids:
                line.location_id = False
    # ==================== ACTION METHODS ====================
    def action_proceed_with_available(self):
        """Create transfers from main location to farm location WITH ACCOUNTING"""
        main_location = self._get_main_location()
        if not main_location:
            raise UserError(_("No main location configured for transfers."))

        # Check availability first
        self.check_stock_availability()

        RequestLine = self.env['agricultural.production.request.line']

        missing_lines = self.request_line_ids.filtered(
            lambda l: l.availability_status in ['unavailable', 'partial'] and l.unavailable_qty > 0
        )

        available_lines = self.request_line_ids.filtered(
            lambda l: l.availability_status == 'available' and l.available_qty >= l.quantity
        )

        if missing_lines:
            for missing in missing_lines:
                missing.write({'state': 'rfq_needed'})
            self.env.flush_all()
            self.env.cr.commit()

        if available_lines:
            # ✅ CREATE TRANSFERS WITH ACCOUNTING
            picking_count = self._create_transfers_from_main_location(main_location)
            self.env.flush_all()
            self.env.cr.commit()

            if picking_count > 0:
                for ava in available_lines:
                    ava.write({'state': 'transferred'})
                self.env.flush_all()
                self.env.cr.commit()
        else:
            self.write({'state': 'rfq_needed'})
    def action_view_account_move(self):
        """View related journal entries"""
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('agricultural_request_id', '=', self.id)],
            'context': {
                'default_agricultural_request_id': self.id,
                'create': False,
            }
        }
    def action_view_account_move_line(self):
        """View related journal entry lines"""
        self.ensure_one()
        return {
            'name': _('Journal Entry Lines'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'account.move.line',
            'domain': [('agricultural_request_id', '=', self.id)],
            'context': {
                'default_agricultural_request_id': self.id,
            }
        }
    def action_view_stock_moves(self):
        """View related stock moves"""
        self.ensure_one()
        return {
            'name': _('Stock Moves'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'stock.move',
            'domain': [('agricultural_request_id', '=', self.id)],
            'context': {
                'default_agricultural_request_id': self.id,
                'search_default_done': 1,
            }
        }
    def action_view_stock_picking(self):
        """View related stock pickings"""
        self.ensure_one()
        return {
            'name': _('Stock Pickings'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'stock.picking',
            'domain': [('agricultural_request_id', '=', self.id)],
            'context': {
                'default_agricultural_request_id': self.id,
            }
        }
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('agricultural.production.request') or _('New')
        return super().create(vals)
    @api.constrains('required_date', 'request_date')
    def _check_dates(self):
        for record in self:
            if record.required_date < record.request_date:
                raise ValidationError(_('Required date cannot be before request date.'))
    def _handle_all_available(self):
        """Handle case when all items are available"""
        self.write({'state': 'all_available'})

        # ✅ CREATE TRANSFERS WITH ACCOUNTING
        self._create_internal_transfers()
        self._send_approval_notification('agricultural_management.group_inventory_manager')
    def _send_approval_notification(self, group_external_id):
        """Send notification to approval group"""
        try:
            group = self.env.ref(group_external_id)
            if group and group.users:
                self.message_subscribe(partner_ids=group.users.partner_id.ids)
                self.message_post(
                    body=f'Production Request {self.name} requires approval.',
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment'
                )
        except ValueError:
            _logger.warning(f"Group {group_external_id} not found for notification")
    def _update_request_state_based_on_availability(self):
        """Update request state based on overall availability"""
        if not self.line_ids:
            return

        # Count availability status
        available_lines = self.line_ids.filtered(lambda l: l.availability_status == 'available')
        partial_lines = self.line_ids.filtered(lambda l: l.availability_status == 'partial')
        unavailable_lines = self.line_ids.filtered(lambda l: l.availability_status == 'unavailable')

        total_lines = len(self.line_ids)

        # Create availability summary message
        message = f"""
        Total Items: {total_lines}
        Fully Available: {len(available_lines)}
        Partially Available: {len(partial_lines)}
        Not Available: {len(unavailable_lines)}
        """

        # Determine new state based on availability
        old_state = self.state
        new_state = old_state
        state_message = ""

        if len(available_lines) == total_lines:
            # All items fully available
            if self.state in ['draft', 'submitted', 'dr_approved', 'inventory_review']:
                new_state = 'transfer_ready'
                state_message = "All Items Available - Ready for transfer"

        elif len(unavailable_lines) == total_lines:
            # No items available at all
            if self.state in ['draft', 'submitted', 'dr_approved', 'inventory_review']:
                new_state = 'rfq_needed'
                state_message = "No exist items Available - required Request Purchase"

        elif len(partial_lines) > 0 or (len(available_lines) > 0 and len(unavailable_lines) > 0):
            # Mixed availability - some available, some not
            if self.state in ['draft', 'submitted', 'dr_approved']:
                new_state = 'inventory_review'
                state_message = "availability Partial - needs Review Stock"
            elif self.state == 'inventory_review':
                # Stay in review state
                state_message = "No still in Review Stock - availability Partial"

        else:
            # Default case - keep current state
            state_message = "has been Check Stock"

        # Update state if it changed
        if old_state != new_state:
            self.write({'state': new_state})
            state_message = f"has been change Status from {dict(self._fields['state'].selection)[old_state]} to {dict(self._fields['state'].selection)[new_state]}"

        # Post comprehensive message to chatter
        full_message = f"""
        <b>Check availability Stock:</b><br/>
        {message}<br/>
        <b>status Request:</b> {state_message}
        """

        self.message_post(
            body=full_message,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )

        # Log detailed availability per product
        for line in self.line_ids:
            if line.availability_status != 'available':
                line_message = f"""
                fromProduct: {line.product_id.name}<br/>
                Required: {line.quantity} {line.uom_id.name}<br/>
                Available: {line.available_qty} {line.uom_id.name}<br/>
                Status: {dict(line._fields['availability_status'].selection)[line.availability_status]}
                """

                self.message_post(
                    body=line_message,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
    def get_availability_summary_data(self):
        """Get structured availability summary data"""
        self.ensure_one()

        if not self.line_ids:
            return {
                'total_items': 0,
                'available_items': 0,
                'partial_items': 0,
                'unavailable_items': 0,
                'availability_percentage': 0,
                'details': []
            }

        available_lines = self.line_ids.filtered(lambda l: l.availability_status == 'available')
        partial_lines = self.line_ids.filtered(lambda l: l.availability_status == 'partial')
        unavailable_lines = self.line_ids.filtered(lambda l: l.availability_status == 'unavailable')

        total_lines = len(self.line_ids)
        availability_percentage = (len(available_lines) / total_lines * 100) if total_lines > 0 else 0

        details = []
        for line in self.line_ids:
            details.append({
                'product_name': line.product_id.name,
                'requested_qty': line.quantity,
                'available_qty': line.available_qty,
                'unavailable_qty': line.unavailable_qty,
                'status': line.availability_status,
                'status_display': dict(line._fields['availability_status'].selection)[line.availability_status],
                'uom': line.uom_id.name,
                'location': line.warehouse_location.name if line.warehouse_location else 'N/A'
            })

        return {
            'total_items': total_lines,
            'available_items': len(available_lines),
            'partial_items': len(partial_lines),
            'unavailable_items': len(unavailable_lines),
            'availability_percentage': round(availability_percentage, 2),
            'details': details
        }
    def action_refresh_line_availability(self, line_id):
        """Refresh availability for a specific line"""
        line = self.line_ids.filtered(lambda l: l.id == line_id)
        if not line:
            return False

        stock_location = self._get_stock_location_for_check()
        available_qty = self._get_product_stock_qty(line.product_id, stock_location)

        line.write({'available_qty': available_qty})
        line._compute_availability_status()
        line._compute_unavailable_qty()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    def is_transfer_ready(self):
        """Check if request is ready for transfer (all items available)"""
        self.ensure_one()
        if not self.line_ids:
            return False

        available_lines = self.line_ids.filtered(lambda l: l.availability_status == 'available')
        return len(available_lines) == len(self.line_ids)
    def get_items_needing_procurement(self):
        """Get list of items that need procurement"""
        self.ensure_one()
        return self.line_ids.filtered(lambda l: l.availability_status in ['unavailable', 'partial'])
    def action_dr_approve(self):
        """Dr/Engineer approval - review and approve costs"""
        if not self.env.user.has_group('agricultural_management.group_agricultural_engineer'):
            raise UserError(_('Only Dr./Engineers can approve production requests.'))
        # Check availability and update status
        self._check_and_update_availability()
        # Determine final state based on availability
        final_state = self._determine_final_state()
        self.write({
            'state': final_state,
            'dr_approved_by': self.env.user.employee_id.id,
            'dr_approval_date': datetime.now()
        })

        # Notify inventory manager
        if final_state == 'inventory_review':
            self._send_notification('agricultural_management.group_inventory_manager',
                                    'Production Request ready for inventory review')
        elif final_state == 'available':
            self._send_notification('agricultural_management.group_inventory_manager',
                                    'Production Request approved - all items available')

        if not self.total_estimated_cost:
            raise UserError("Please calculate estimated costs before approval")

        self.write({
            'state': 'dr_approved',
            'dr_approved_by': self.env.user.employee_id.id,
            'dr_approval_date': fields.Datetime.now(),
        })
        self._update_approved_costs()
        return True
    def action_inventory_review(self):
        """Inventory review - check availability and update costs"""
        if not self.env.user.has_group('agricultural_management.group_inventory_manager'):
            raise UserError(_('Only Inventory Managers can review inventory.'))

        # Check availability
        self._check_inventory_availability()

        self.write({
            'inventory_reviewed_by': self.env.user.employee_id.id,
            'inventory_review_date': datetime.now()
        })

        # Process based on availability
        if self.availability_status == 'all_available':
            self.write({'state': 'transfer_ready'})
            self._create_internal_transfers()
        elif self.availability_status in ['some_available', 'few_available']:
            self.write({'state': 'transfer_ready'})
            self._create_internal_transfers()  # For available items
            self._create_rfqs_for_unavailable()  # For unavailable items
            # Notify purchase manager
            self._send_notification('agricultural_management.group_purchase_manager',
                                    'RFQ required for unavailable items')
        else:
            self.write({'state': 'rfq_needed'})
            self._create_rfqs_for_unavailable()
            # Notify purchase manager
            self._send_notification('agricultural_management.group_purchase_manager',
                                    'Full procurement required')
        self._check_and_update_availability()
        self._calculate_transfer_costs()
        self.write({'state': 'inventory_review'})
        return True
    def action_accounts_approve(self):
        """Accounts approval - final cost verification"""


        self.write({
            'state': 'transferred',
            'accounts_approved_by': self.env.user.employee_id.id,
            'accounts_approval_date': fields.Datetime.now(),
        })
        return True
    def _update_approved_costs(self):
        """Update approved costs after DR approval"""
        for line in self.request_line_ids:
            line.approved_cost = line.estimated_cost
    def _calculate_transfer_costs(self):
        """Calculate costs for internal transfers"""
        for line in self.request_line_ids:
            if line.availability_status in ['available', 'partial']:
                # Use standard cost for internal transfers
                line.unit_price = line.product_id.standard_price
                line.estimated_cost = min(line.quantity, line.available_qty) * line.unit_price
    def _create_purchase_orders(self):
        """Create purchase orders for unavailable items with proper costing"""
        unavailable_lines = self.request_line_ids.filtered(
            lambda l: l.availability_status in ['unavailable', 'partial']
        )

        if not unavailable_lines:
            return

        # Group by vendor
        vendor_groups = self._group_lines_by_vendor(unavailable_lines)

        for vendor, lines in vendor_groups.items():
            po_vals = {
                'partner_id': vendor.id,
                'origin': self.name,
                'agricultural_request_id': self.id,
                'currency_id': self.currency_id.id,
                'order_line': self._prepare_po_lines(lines),
            }

            po = self.env['purchase.order'].create(po_vals)
            self._link_po_to_lines(po, lines)
    def _prepare_po_lines(self, lines):
        """Prepare purchase order lines with proper costing"""
        po_lines = []
        for line in lines:
            qty_to_purchase = line.quantity - (line.available_qty if line.availability_status == 'partial' else 0)

            po_line_vals = {
                'product_id': line.product_id.id,
                'product_qty': qty_to_purchase,
                'product_uom': line.uom_id.id,
                'price_unit': line.unit_price,
                'name': line.description or line.product_id.name,
                'date_planned': self.required_date,
            }
            po_lines.append((0, 0, po_line_vals))

        return po_lines
    @api.depends('total_estimated_cost', 'actual_cost')
    def _compute_cost_variance(self):
        for record in self:
            record.cost_variance = record.actual_cost - record.total_estimated_cost
            if record.total_estimated_cost:
                record.cost_variance_percent = (record.cost_variance / record.total_estimated_cost) * 100
            else:
                record.cost_variance_percent = 0
    def _create_stock_moves_for_lines(self):
        """Create stock moves for each production request line"""
        StockMove = self.env['stock.move']

        for line in self.request_line_ids:
            if line.quantity <= 0:
                continue

            # Get company from current user or environment
            company_id = self.env.company.id

            # Create stock move for availability checking
            move_vals = {
                'name': f"{self.name} - {line.product_id.name}",
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'location_id': line.warehouse_location.id,  # Use warehouse_location
                'location_dest_id': self.farm_id.location_id.id,  # Destination location
                'state': 'draft',
                'origin': self.name,
            }

            # Create the stock move
            stock_move = StockMove.create(move_vals)

            # Link the stock move to the line
            line.stock_move_id = stock_move.id
    def _check_and_update_availability(self):
        """Check product availability and update line status"""
        for line in self.request_line_ids:
            if not line.product_id:
                continue

            # Get available quantity from stock
            available_qty = self._get_available_quantity(line.product_id)

            # Update line availability fields
            line.write({
                'available_qty': available_qty,
            })
    def _validate_stock_availability(self):
        """Validate stock availability for all requested items"""
        for line in self.request_line_ids:
            available_qty = self.env['stock.quant']._get_available_quantity(
                line.product_id, line.warehouse_location
            )
            if available_qty < line.quantity:
                raise UserError(_(
                    'Insufficient stock for %s. Available: %s, Requested: %s'
                ) % (line.product_id.name, available_qty, line.quantity))
    def _update_availability_from_main_location(self, main_location):
        """Update availability from main location stock"""
        if not self.product_id or not main_location:
            self.available_qty = 0.0
            return

        # Get available quantity from main location
        available_qty = self._get_product_qty_in_location(
            self.product_id,
            main_location
        )

        self.write({
            'available_qty': available_qty,
        })
    def _get_product_qty_in_location(self, product, location):
        """Get available quantity for product in specific location"""
        if not product or not location:
            return 0.0

        try:
            # Method 1: Direct quant search
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id),
            ])

            available_qty = 0.0
            for quant in quants:
                available_qty += max(0, quant.quantity - quant.reserved_quantity)

            return available_qty

        except Exception:
            # Method 2: Using product context
            try:
                return product.with_context(
                    location=location.id,
                    compute_child=False
                ).qty_available
            except:
                return 0.0
    def action_view_stock_move(self):
        """Open the related stock move"""
        if not self.stock_move_id:
            return False

        return {
            'name': _('Stock Move'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'form',
            'res_id': self.stock_move_id.id,
            'target': 'current',
        }
    def action_view_purchase_line(self):
        """Open the related purchase order line"""
        if not self.rfq_line_id:
            return False

        return {
            'name': _('Purchase Order Line'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_mode': 'form',
            'res_id': self.rfq_line_id.id,
            'target': 'current',
        }
    def _update_availability_from_stock(self):
        """Update availability fields from current stock levels"""
        if not self.product_id or not self.location_id:
            self.available_qty = 0.0
            return

        # Get current stock level
        available_qty = self._get_product_available_qty()

        self.write({
            'available_qty': available_qty,
        })
    def _get_product_available_qty(self):
        """Get available quantity for the product in location"""
        if not self.product_id or not self.location_id:
            return 0.0

        try:
            # Use product context to get quantity at specific location
            product_with_location = self.product_id.with_context(
                location=self.location_id.id,
                compute_child=True
            )
            return max(0.0, product_with_location.qty_available)
        except Exception:
            return 0.0
    @api.depends('delivered_qty', 'quantity')
    def _compute_remaining_qty(self):
        """Compute remaining quantity to be delivered"""
        for line in self:
            line.remaining_qty = line.quantity - line.delivered_qty
    @api.onchange('farm_id')
    def _onchange_farm_id(self):
        """Handle farm change and set related fields"""
        if self.farm_id:
            # Set budget allocation
            if self.farm_id.analytic_account_id:
                self.budget_allocation = self.farm_id.analytic_account_id.id
            else:
                self.budget_allocation = False
            if self.farm_id.expense_account_id:
                self.expense_account_id = self.farm_id.expense_account_id.id
            else:
                self.expense_account_id = False
            if self.farm_id.asset_account_id:
                self.asset_account_id = self.farm_id.asset_account_id.id
            else:
                self.asset_account_id = False

            # Set location for lines
            if self.farm_id.location_id:
                # Set location for all existing lines
                for line in self.request_line_ids:
                    line.location_id = self.farm_id.location_id.id
            else:
                # Clear location for all lines
                for line in self.request_line_ids:
                    line.location_id = False
                return {
                    'warning': {
                        'title': _('No Location Found'),
                        'message': _(
                            'The selected farm "%s" does not have any location assigned. Please configure a location for this farm first.') % self.farm_id.name
                    }
                }
        else:
            self.budget_allocation = False
            for line in self.request_line_ids:
                line.location_id = False
    def action_proceed_with_partial(self):
        """Proceed with available items and create RFQ for missing ones"""
        # Transfer available items
        available_result = self.action_proceed_with_available()

        # Also create RFQ for missing items
        missing_lines = self.request_line_ids.filtered(
            lambda l: l.availability_status in ['unavailable', 'partial'] and l.unavailable_qty > 0
        )

        if missing_lines:
            self.action_create_rfq_for_missing()
            self.write({'state': 'rfq_pending'})
        else:
            self.write({'state': 'inventory_review'})

        return available_result
    def action_wait_for_rfq(self):
        """Create RFQs for unavailable items and wait for procurement"""
        # Check availability first
        self.check_stock_availability()

        # Create RFQs for unavailable items
        rfq_count = self._create_rfqs_for_unavailable()

        if rfq_count > 0:
            self.write({'state': 'rfq_pending'})

            # Send notification
            self._send_procurement_notification()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('RFQs Created'),
                    'message': _('%s RFQ(s) have been created for unavailable items.') % rfq_count,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No RFQs Needed'),
                    'message': _('All items are available or no unavailable items found.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
    def _send_procurement_notification(self):
        """Send notification about RFQ creation"""
        # Get procurement managers
        group = self.env.ref('purchase.group_purchase_manager', raise_if_not_found=False)
        if group:
            self._send_notification(
                'purchase.group_purchase_manager',
                f'RFQs created for Agricultural Request {self.name}'
            )
    def action_view_purchase_orders(self):
        """View related purchase orders"""
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if len(self.purchase_order_ids) > 1:
            action['domain'] = [('id', 'in', self.purchase_order_ids.ids)]
        elif len(self.purchase_order_ids) == 1:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = self.purchase_order_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    def action_view_stock_pickings(self):
        """View related stock pickings"""
        action = self.env.ref('stock.action_picking_list_all').read()[0]
        if len(self.stock_picking_ids) > 1:
            action['domain'] = [('id', 'in', self.stock_picking_ids.ids)]
        elif len(self.stock_picking_ids) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = self.stock_picking_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    def _determine_final_state(self):
        """Determine the final state based on availability of all lines"""
        if not self.request_line_ids:
            return 'inventory_review'

        # Refresh the availability status for all lines
        for line in self.request_line_ids:
            line._compute_availability_status()

        # Check if all items are available
        available_lines = self.request_line_ids.filtered(lambda l: l.availability_status == 'available')
        unavailable_lines = self.request_line_ids.filtered(lambda l: l.availability_status == 'unavailable')
        self.write({'approved_date': datetime.today().date()})
        if len(available_lines) == len(self.request_line_ids):
            return 'dr_approved'
        elif len(unavailable_lines) > 0:
            return 'inventory_review'  # Need to review unavailable items
        else:
            return 'inventory_review'  # Partial availability needs review
    @api.depends('request_line_ids')
    def _compute_line_count(self):
        for request in self:
            request.line_count = len(request.request_line_ids)
    def action_open_template_wizard(self):
        """Open template selection wizard"""
        return {
            'name': _('Select Production Templates'),
            'type': 'ir.actions.act_window',
            'res_model': 'request.template.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_merge_mode': 'append',
            }
        }
    def action_clear_all_lines(self):
        """Clear all production request lines and refresh GUI"""
        if self.request_line_ids:
            # Delete all lines
            self.request_line_ids.unlink()

            # Return action to refresh the current form and show notification
            return {
                'type': 'ir.actions.act_window',
                'name': _('Production Request'),
                'res_model': 'agricultural.production.request',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'form_view_initial_mode': 'edit',
                },
                'flags': {
                    'mode': 'edit',
                },
                'params': {
                    'message': _('All production lines have been cleared.'),
                    'type': 'success',
                }
            }
        else:
            # No lines to clear - just show notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No lines to clear.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
    def action_add_quick_template(self, template_id):
        """Quick add a specific template"""
        template = self.env['agricultural.production.request.template'].browse(template_id)
        if not template.exists():
            return False

        # Get current max sequence
        max_sequence = max(self.request_line_ids.mapped('sequence')) if self.request_line_ids else 0

        # Add template lines
        for template_line in template.template_line_ids:
            max_sequence += 10
            self.request_line_ids.create({
                'request_id': self.id,
                'sequence': max_sequence,
                'product_id': template_line.product_id.id,
                'description': template_line.description,
                'quantity': template_line.quantity,
                'uom_id': template_line.uom_id.id,
                'cost_center_type': template_line.cost_center_type,
                'unit_price': template_line.unit_price,
                'template_id': template.id,
            })

        # Track usage
        template.increment_usage()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Template "%s" added successfully.') % template.name,
                'type': 'success',
            }
        }
    @api.depends('request_line_ids.availability_status')
    def _compute_availability_counts(self):
        for record in self:
            lines = record.request_line_ids
            record.total_available_lines = len(lines.filtered(lambda l: l.availability_status == 'available'))
            record.total_partial_lines = len(lines.filtered(lambda l: l.availability_status == 'partial'))
            record.total_unavailable_lines = len(lines.filtered(lambda l: l.availability_status == 'unavailable'))
    def action_approve(self):
        self.state = 'approved'
        self.approved_date = fields.Date.today()
        self.approved_by = self.env.user.employee_id
        self.message_post(body=_("Request approved"))

        # Auto-create purchase orders if needed
        self._create_purchase_orders()
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('agricultural.production.request') or _('New')
        return super().create(vals)
    @api.constrains('required_date', 'request_date')
    def _check_dates(self):
        for record in self:
            if record.required_date < record.request_date:
                raise ValidationError(_('Required date cannot be before request date.'))
    def _check_inventory_availability(self):
        """Check availability for all request lines"""
        for line in self.request_line_ids:
            # Get available quantity from stock
            available_qty = self._get_available_stock(
                line.product_id,
                line.location_id
            )
            line.available_qty = min(available_qty, line.quantity)
    def _get_available_stock(self, product, location):
        """Get available stock quantity for product at location"""
        stock_quant = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id),
        ])
        return sum(stock_quant.mapped('available_quantity'))
    def _process_inventory_results(self):
        """Process inventory check results"""
        if self.availability_status == 'all_available':
            self._handle_all_available()
        elif self.availability_status in ['some_available', 'few_available']:
            self._handle_partial_available()
        else:
            self._handle_none_available()

        def _handle_all_available(self):
            """Handle case when all items are available"""

        self.write({'state': 'all_available'})

        # Create internal transfers for all items
        self._create_internal_transfers()

        # Create disbursement request

        # Notify warehouse manager
        self._send_approval_notification('agricultural_management.group_inventory_manager')
    def _handle_partial_available(self):
        """Handle case when some items are available"""
        if self.availability_status == 'some_available':
            self.write({'state': 'some_available'})
        else:
            self.write({'state': 'few_available'})

        self._create_internal_transfers()
        self._create_rfqs_for_unavailable()
        self._send_approval_notification('agricultural_management.group_inventory_manager')
        self._send_procurement_notification()
    def _handle_none_available(self):
        """Handle case when no items are available"""
        self.write({'state': 'procurement_needed'})

        # Create RFQs for all items
        self._create_rfqs_for_unavailable()

        # Notify procurement team
        self._send_procurement_notification()
    def action_warehouse_approve(self):
        """Warehouse Manager approval"""
        if not self.env.user.has_group('agricultural_management.group_inventory_manager'):
            raise UserError(_('Only Warehouse Managers can approve warehouse requests.'))

        # Validate stock availability
        self._validate_stock_availability()

        self.write({
            'state': 'transferred',
            'warehouse_approved_by': self.env.user.employee_id.id,
            'warehouse_approval_date': datetime.now()
        })

        self._send_approval_notification('agricultural_management.group_accounts')
    def action_cancel(self):
        if self.state in ['disbursed']:
            raise UserError(_('Cannot cancel a disbursed request.'))
        self.write({'state': 'cancelled'})
    def action_wait_for_procurement(self):
        """Wait for procurement to complete"""
        self.write({'state': 'procurement_needed'})
    def action_complete_delivery(self):
        """Mark request as completed"""
        if self.state in ['partial_delivery', 'ready_for_delivery']:
            self.write({'state': 'completed'})
    def action_approve_transfer(self):
        """Inventory Manager approves transfer to farm"""
        if not self.env.user.has_group('agricultural_management.group_inventory_manager'):
            raise UserError(_('Only Inventory Managers can approve transfers.'))

        # Execute the transfers
        for move in self.stock_move_ids:
            if move.state in ['assigned', 'confirmed']:
                move.action_done()

        self.write({
            'state': 'transferred',
            'transfer_approved_by': self.env.user.employee_id.id,
            'transfer_approval_date': datetime.now()
        })

        # If no RFQ needed, notify accounts for completion
        if not self.rfq_ids or all(rfq.state in ['purchase', 'done'] for rfq in self.rfq_ids):
            self._send_notification('agricultural_management.group_accounts',
                                    'Request ready for completion')
    def action_complete_request(self):
        """Accounts/Finance completes the request"""
        if not self.env.user.has_group('agricultural_management.group_accounts'):
            raise UserError(_('Only Accounts team can complete requests.'))

        self.write({
            'state': 'completed',
            'completion_approved_by': self.env.user.employee_id.id,
            'completion_date': datetime.now()
        })
    @api.depends('line_ids')
    def _compute_line_count(self):
        for request in self:
            request.line_count = len(request.line_ids)
    @api.onchange('farm_id')
    def _onchange_farm_id(self):
        if self.farm_id and self.farm_id.analytic_account_id:
            self.budget_allocation = self.farm_id.analytic_account_id.id
        else:
            self.budget_allocation = False
        if self.farm_id.expense_account_id:
            self.expense_account_id = self.farm_id.expense_account_id.id
        else:
            self.expense_account_id = False
        if self.farm_id.asset_account_id:
            self.asset_account_id = self.farm_id.asset_account_id.id
        else:
            self.asset_account_id = False
    @api.depends('request_line_ids.availability_status')
    def _compute_availability_counts(self):
        for record in self:
            lines = record.request_line_ids
            record.total_available_lines = len(lines.filtered(lambda l: l.availability_status == 'available'))
            record.total_partial_lines = len(lines.filtered(lambda l: l.availability_status == 'partial'))
            record.total_unavailable_lines = len(lines.filtered(lambda l: l.availability_status == 'unavailable'))
    @api.depends('request_line_ids.subtotal', 'actual_cost')
    def _compute_costs(self):
        for record in self:
            record.estimated_cost = sum(record.request_line_ids.mapped('subtotal'))
            record.total_cost = record.actual_cost or record.estimated_cost
    @api.depends('line_ids.estimated_cost', 'line_ids.approved_cost')
    def _compute_totals(self):
        for record in self:
            record.total_estimated_cost = sum(record.line_ids.mapped('estimated_cost'))
            record.total_approved_cost = sum(record.line_ids.mapped('approved_cost'))
    @api.constrains('required_date', 'request_date')
    def _check_dates(self):
        for record in self:
            if record.required_date < record.request_date:
                raise ValidationError(_('Required date cannot be before request date.'))
class ProductionRequestLine(models.Model):
    _name = 'agricultural.production.request.line'
    _description = 'Production Request Line'

    request_id = fields.Many2one('agricultural.production.request', 'Production Request',
                                 required=True, ondelete='cascade')
    dr_approved_by = fields.Many2one(related='request_id.dr_approved_by', string='Approved By', tracking=True)
    dr_approval_date = fields.Datetime(related="request_id.dr_approval_date",string='Approval Date', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    # Product Information
    product_id = fields.Many2one('product.product', 'Product', required=True)
    description = fields.Text('Description')
    quantity = fields.Float('Quantity', required=True, digits='Product Unit of Measure')
    to_procure_qty = fields.Float('To Procure Quantity', digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True)
    price = fields.Float('Price', digits='Product Unit of Measure')
    # Warehouse Information
    warehouse_location = fields.Many2one(
        'stock.location',related="request_id.farm_id.location_id",
        string="Warehouse Location"
    )
    location_id = fields.Many2one(
        'stock.location', related="request_id.farm_id.location_id",
        string="Location"
    )
    cost_center_type = fields.Selection([
        ('direct', 'Direct Material'),
        ('indirect', 'Indirect Material')
    ], 'Cost Center Type', required=True, default='direct')
    # Financial Information
    unit_price = fields.Float('Unit Price', digits='Product Price')
    estimated_cost = fields.Float('Estimated Cost', compute='_compute_costs', store=True)
    approved_cost = fields.Float('Approved Cost')
    # Account Linking
    expense_account = fields.Many2one('account.account', 'Expense Account')
    provision_account = fields.Many2one('account.account', 'Provision Account')
    # Approval Notes
    warehouse_notes = fields.Text('Warehouse Notes')
    accounts_notes = fields.Text('Accounts Notes')
    subtotal = fields.Monetary('Subtotal', currency_field='currency_id',
                               compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one('res.currency', related='request_id.currency_id')
    # Delivery tracking
    delivered_qty = fields.Float('Delivered Quantity', default=0.0)
    remaining_qty = fields.Float('Remaining Quantity', compute='_compute_remaining_qty')
    # Availability tracking
    available_qty = fields.Float('Available Quantity', digits='Product Unit of Measure')
    unavailable_qty = fields.Float('Unavailable Quantity', compute='_compute_unavailable_qty', store=True)
    availability_status = fields.Selection([
        ('available', 'Fully Available'),
        ('partial', 'Partially Available'),
        ('unavailable', 'Not Available')
    ], string='Availability', compute='_compute_availability_status', store=True)
    # Update the state field
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('dr_approved', 'Dr. Approved'),
        ('inventory_review', 'Inventory Review'),
        ('transfer_ready', 'Transfer Ready'),
        ('transferred', 'Transferred to Farm'),
        ('rfq_needed', 'RFQ Required'),
        ('rfq_pending', 'RFQ Pending'),
        ('purchase_approved', 'Purchase Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)
    # Stock move tracking
    stock_move_id = fields.Many2one('stock.move', 'Related Stock Move')
    rfq_line_id = fields.Many2one('purchase.order.line', 'RFQ Line')
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'agricultural_request_id',
        string='Purchase Orders'
    )
    stock_picking_ids = fields.One2many(
        'stock.picking',
        'agricultural_request_id',
        string='Stock Pickings'
    )
    stock_move_ids = fields.One2many(
        'stock.move',
        'agricultural_request_id',
        string='Stock Moves'
    )
    expense_direct_cost = fields.Many2one(
        'account.account',
        check_company=True,
        related='product_id.categ_id.expense_direct_cost',
        readonly=False,
        string="Category Expense Account",
        help="Raw Materials Cost Account"
    )
    stock_move_main = fields.Many2one(
        'account.account',
        check_company=True,
        related='product_id.categ_id.stock_move_main',
        readonly=False,
        string="Stock Account",
        help="Main Warehouse Stock Account"
    )
    # Add to your ProductionRequest class


    # Add these compute methods to your ProductionRequestLine class
    @api.depends('product_id', 'quantity')
    def _compute_costs(self):
        """Compute estimated cost based on product standard price"""
        for line in self:
            if line.product_id:
                line.estimated_cost = line.product_id.standard_price * line.quantity
            else:
                line.estimated_cost = 0.0
    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        """Compute line subtotal"""
        for line in self:
            line.subtotal = line.quantity * line.unit_price
    @api.depends('quantity', 'delivered_qty')
    def _compute_remaining_qty(self):
        """Compute remaining quantity to be delivered"""
        for line in self:
            line.remaining_qty = line.quantity - line.delivered_qty
    @api.depends('quantity', 'available_qty')
    def _compute_unavailable_qty(self):
        """Compute unavailable quantity"""
        for line in self:
            line.unavailable_qty = max(0, line.quantity - line.available_qty)
    @api.depends('product_id', 'quantity', 'location_id')
    def _compute_availability_status(self):
        """Compute availability status based on stock"""
        for line in self:
            if not line.product_id or not line.location_id:
                line.available_qty = 0.0
                line.availability_status = 'unavailable'
                continue

            # Get available quantity from the specific location
            stock_quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
            ])

            available_qty = sum(stock_quant.mapped('quantity')) - sum(stock_quant.mapped('reserved_quantity'))
            line.available_qty = available_qty

            if available_qty >= line.quantity:
                line.availability_status = 'available'
            elif available_qty > 0:
                line.availability_status = 'partial'
            else:
                line.availability_status = 'unavailable'
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-fill fields when product is selected"""
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.unit_price = self.product_id.standard_price
            self.description = self.product_id.name or self.product_id.display_name
    # ==================== COMPUTE METHODS ====================
    @api.depends('quantity', 'available_qty')
    def _compute_unavailable_qty(self):
        """Compute unavailable quantity = requested - available"""
        for line in self:
            if line.quantity > 0 and line.available_qty >= 0:
                line.unavailable_qty = max(0.0, line.quantity - line.available_qty)
            else:
                line.unavailable_qty = line.quantity if line.quantity > 0 else 0.0
    @api.depends('quantity', 'available_qty')
    def _compute_availability_status(self):
        """Compute availability status: available/partial/unavailable"""
        for line in self:
            if not line.product_id or line.quantity <= 0:
                line.availability_status = 'unavailable'
                continue

            if line.available_qty >= line.quantity:
                line.availability_status = 'available'
            elif line.available_qty > 0:
                line.availability_status = 'partial'
            else:
                line.availability_status = 'unavailable'
    @api.depends('quantity', 'unit_price')
    def _compute_costs(self):
        """Compute estimated cost and subtotal"""
        for line in self:
            line.estimated_cost = line.quantity * line.unit_price
            line.subtotal = line.estimated_cost

            # Auto-set approved cost if not set
            if not line.approved_cost:
                line.approved_cost = line.estimated_cost
    @api.depends('quantity', 'delivered_qty')
    def _compute_remaining_qty(self):
        """Compute remaining quantity to be delivered"""
        for line in self:
            line.remaining_qty = max(0.0, line.quantity - line.delivered_qty)
    # ==================== ONCHANGE METHODS ====================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Handle product change - set UOM, price, description, accounts"""
        if self.product_id:
            # Set basic product info
            self.uom_id = self.product_id.uom_id
            self.description = self.product_id.display_name
            self.warehouse_location = self.request_id.farm_id.location_id.id
            # Set price from product or supplier
            if self.product_id.seller_ids:
                # Use supplier price if available
                self.unit_price = self.product_id.seller_ids[0].price
            else:
                # Use standard/list price
                self.unit_price = self.product_id.standard_price or self.product_id.lst_price

            # Set expense account from product category
            if self.product_id.categ_id and self.product_id.categ_id.property_account_expense_categ_id:
                self.expense_account = self.product_id.categ_id.property_account_expense_categ_id
    # ==================== HELPER METHODS ====================
    def _set_default_warehouse_location(self):
        """Set default source warehouse location"""
        if not self.request_id:
            return

        main_warehouse = self.request_id._get_main_location()
        if main_warehouse and main_warehouse:
            self.warehouse_location = main_warehouse.id
        else:
            main_location = self.request_id._get_main_location()
            if main_location:
                self.warehouse_location = main_location.id
    def _set_default_destination_location(self):
        """Set default destination location (farm)"""
        if not self.request_id:
            return

        if self.request_id.farm_id and self.request_id.farm_id.location_id:
            self.location_id = self.request_id.farm_id.location_id.id
    def _update_availability_from_stock(self):
        """Update availability from current stock levels"""
        self.ensure_one()

        if not self.product_id:
            self.available_qty = 0.0
            return

        # Get available quantity from warehouse location
        available_qty = self._get_product_available_qty()

        self.write({'available_qty': available_qty})
    def _get_product_available_qty(self):
        """Get available quantity for product at warehouse location"""
        self.ensure_one()

        if not self.product_id:
            return 0.0

        # Use warehouse_location if set
        location = self.warehouse_location

        # Fallback to main warehouse/location
        if not location and self.request_id:
            main_warehouse = self.request_id._get_main_location()
            if main_warehouse:
                location = main_warehouse
            else:
                location = self.request_id._get_main_location()

        if not location:
            return 0.0

        return self._get_product_qty_in_location(self.product_id, location)

    def _update_availability_from_main_location(self, main_location):
        """Update availability from specific main location"""
        self.ensure_one()

        if not self.product_id or not main_location:
            self.available_qty = 0.0
            return

        available_qty = self._get_product_qty_in_location(self.product_id, main_location)
        self.write({'available_qty': available_qty})
    def _update_availability_from_main_warehouse(self, main_warehouse):
        """Update availability from main warehouse"""
        self.ensure_one()

        if not self.product_id or not main_warehouse:
            self.available_qty = 0.0
            return

        location = main_warehouse if main_warehouse else main_warehouse
        available_qty = self._get_product_qty_in_location(self.product_id, location)
        self.write({'available_qty': available_qty})
    # ==================== ACTION METHODS ====================
    def action_check_availability(self):
        """Manually check and update availability for this line"""
        self.ensure_one()
        self._update_availability_from_stock()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Availability Updated'),
                'message': _('Available: %s %s') % (self.available_qty, self.uom_id.name),
                'type': 'success',
                'sticky': False,
            }
        }
    def action_view_stock_move(self):
        """Open the related stock move"""
        self.ensure_one()

        if not self.stock_move_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Stock Move'),
                    'message': _('No stock move has been created for this line yet.'),
                    'type': 'warning',
                }
            }

        return {
            'name': _('Stock Move'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'form',
            'res_id': self.stock_move_id.id,
            'target': 'current',
        }
    def action_view_purchase_line(self):
        """Open the related purchase order line"""
        self.ensure_one()

        if not self.rfq_line_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No RFQ Line'),
                    'message': _('No RFQ line has been created for this item yet.'),
                    'type': 'warning',
                }
            }

        return {
            'name': _('Purchase Order Line'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_mode': 'form',
            'res_id': self.rfq_line_id.id,
            'target': 'current',
        }
    def action_view_purchase_order(self):
        """View the purchase order for this line"""
        self.ensure_one()

        if not self.rfq_line_id or not self.rfq_line_id.order_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Purchase Order'),
                    'message': _('No purchase order exists for this line.'),
                    'type': 'warning',
                }
            }

        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.rfq_line_id.order_id.id,
            'target': 'current',
        }
    def action_view_request(self):
        """Open the production request form"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Request'),
            'res_model': 'agricultural.production.request',
            'view_mode': 'form',
            'res_id': self.request_id.id,
            'target': 'current',
        }
    # ==================== BATCH OPERATIONS ====================
    def batch_update_availability(self):
        """Update availability for multiple lines at once"""
        for line in self:
            try:
                line._update_availability_from_stock()
            except Exception as e:
                _logger.error(f"Failed to update availability for line {line.id}: {str(e)}")
                continue

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Availability Updated'),
                'message': _('%s line(s) updated successfully') % len(self),
                'type': 'success',
            }
        }
    # ==================== CONSTRAINTS ====================
    @api.constrains('quantity')
    def _check_quantity(self):
        """Ensure quantity is positive"""
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
    @api.constrains('unit_price')
    def _check_unit_price(self):
        """Ensure unit price is not negative"""
        for line in self:
            if line.unit_price < 0:
                raise ValidationError(_('Unit price cannot be negative.'))
    # ==================== CRUD OVERRIDES ====================
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults and check availability"""
        lines = super().create(vals_list)

        # Auto-update availability after creation
        for line in lines:
            try:
                if line.product_id and line.warehouse_location:
                    line._update_availability_from_stock()
            except Exception as e:
                _logger.warning(f"Could not auto-update availability for new line: {str(e)}")

        return lines
    def write(self, vals):
        """Override write to recalculate availability when relevant fields change"""
        res = super().write(vals)

        # Recalculate availability if product or location changed
        if 'product_id' in vals or 'warehouse_location' in vals:
            for line in self:
                try:
                    if line.product_id and line.warehouse_location:
                        line._update_availability_from_stock()
                except Exception as e:
                    _logger.warning(f"Could not update availability after write: {str(e)}")

        return res
    def unlink(self):
        """Override unlink to handle related records"""
        # Check if any line is in a state that prevents deletion
        for line in self:
            if line.state in ['transferred', 'completed']:
                raise UserError(
                    _('Cannot delete line "%s" because it has already been transferred or completed.') % line.product_id.name)

        return super().unlink()
    # ==================== NAME & DISPLAY ====================
    @api.depends('quantity', 'available_qty')
    def _compute_availability_status(self):
        """Compute availability status based on quantity comparison"""
        for line in self:
            if not line.product_id or line.quantity <= 0:
                line.availability_status = 'unavailable'
            elif line.available_qty >= line.quantity:
                line.availability_status = 'available'
            elif line.available_qty > 0:
                line.availability_status = 'partial'
            else:
                line.availability_status = 'unavailable'
    @api.depends('quantity', 'available_qty')
    def _compute_unavailable_qty(self):
        """Compute unavailable quantity"""
        for line in self:
            if line.quantity > 0 and line.available_qty >= 0:
                line.unavailable_qty = max(0, line.quantity - line.available_qty)
            else:
                line.unavailable_qty = line.quantity
    @api.depends('quantity', 'unit_price')
    def _compute_costs(self):
        for line in self:
            line.estimated_cost = line.quantity * line.unit_price
            if not line.approved_cost:
                line.approved_cost = line.estimated_cost
    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
    @api.depends('quantity', 'delivered_qty')
    def _compute_remaining_qty(self):
        for line in self:
            line.remaining_qty = line.quantity - line.delivered_qty
    def _update_availability_from_main_stock(self):
        """Update availability from main warehouse stock"""
        if not self.product_id :
            self.available_qty = 0.0
            return

        # Get available quantity from main warehouse
        available_qty = self._get_product_qty_in_location(
            self.product_id,
        )

        self.write({
            'available_qty': available_qty,
        })
    def action_view_purchase_orders(self):
        """View related purchase orders"""
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if len(self.purchase_order_ids) > 1:
            action['domain'] = [('id', 'in', self.purchase_order_ids.ids)]
        elif len(self.purchase_order_ids) == 1:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = self.purchase_order_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    def agricultural_production_request_line_action(self):
        """Open the production request form view with details"""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Production Request Details"),
            'res_model': 'agricultural.production.request',
            'view_mode': 'form',
            'view_id': self.env.ref('agricultural_management.view_agricultural_production_request_form').id,
            'res_id': self.request_id.id,
            'target': 'current',
            'context': dict(self.env.context),
        }
class StockMove(models.Model):
    _inherit = 'stock.move'

    agricultural_project_id = fields.Many2one(
        'agricultural.project',
        string='Agricultural Project',
        ondelete='cascade'
    )
    agricultural_request_id = fields.Many2one(
        'agricultural.production.request',
        string='Agricultural Request'
    )
    # Agricultural Extensions
    agricultural_farm_id = fields.Many2one('agricultural.farm', 'Farm')
    production_request_id = fields.Many2one('agricultural.production.request', 'Production Request')
    cultivation_stage = fields.Selection([
        ('seeding', 'Seeding'),
        ('germination', 'Germination'),
        ('transplanting', 'Transplanting'),
        ('growth', 'Vegetative Growth'),
        ('flowering', 'Flowering'),
        ('fruiting', 'Fruiting'),
        ('harvest', 'Harvest'),
        ('post_harvest', 'Post Harvest'),
        ('processing', 'Processing'),
        ('packaging', 'Packaging'),
        ('storage', 'Storage'),
        ('shipping', 'Shipping')
    ], 'Cultivation Stage')
    # Quality tracking
    quality_grade = fields.Selection([
        ('premium', 'Premium'),
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
        ('reject', 'Reject')
    ], 'Quality Grade')
    # Environmental data
    temperature_at_harvest = fields.Float('Temperature at Harvest (°C)')
    humidity_at_harvest = fields.Float('Humidity at Harvest (%)')
    harvest_date = fields.Date('Harvest Date')
    inventory_stage_id = fields.Many2one(
        'agri.inventory.stage',
        'Inventory Stage',
        help='Agricultural inventory stage that generated this move'
    )

    # Additional computed fields for better integration
    stage_type = fields.Selection(
        related='inventory_stage_id.stage_type',
        string='Stage Type',
        store=True
    )
    stage_quality_grade = fields.Selection(
        related='inventory_stage_id.quality_grade',
        string='Quality Grade',
        store=True
    )
    stage_efficiency_score = fields.Float(
        related='inventory_stage_id.efficiency_score',
        string='Stage Efficiency',
        store=True
    )

    def _get_agricultural_stage_cost(self):
        """Get cost from agricultural stage"""
        if self.inventory_stage_id:
            return self.inventory_stage_id.stage_cost
        return 0
    def action_view_inventory_stage(self):
        """View related inventory stage"""
        if not self.inventory_stage_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'name': _('Inventory Stage'),
            'res_model': 'agri.inventory.stage',
            'res_id': self.inventory_stage_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    def _get_agricultural_cost_allocation(self):
        """Get cost allocation for agricultural moves"""
        if self.agricultural_farm_id:
            allocations = self.env['agri.cost.allocation'].search([
                ('farm_id', '=', self.agricultural_farm_id.id),
                ('state', '=', 'allocated'),
                ('date', '<=', self.date)
            ], order='date desc', limit=1)
            return allocations.total_amount if allocations else 0
        return 0
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    agricultural_request_id = fields.Many2one(
        'agricultural.production.request',
        string='Agricultural Request'
    )
    agricultural_project_id = fields.Many2one(
        'agricultural.project',
        string='Agricultural Project',
        ondelete='cascade'
    )
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    agricultural_project_id = fields.Many2one(
        'agricultural.project',
        string='Agricultural Project',
        ondelete='cascade'
    )
    agricultural_request_id = fields.Many2one(
        'agricultural.production.request',
        string='Agricultural Request'
    )
    purchase_type = fields.Selection([
        ('seeds', 'Seeds'),
        ('fertilizer', 'Fertilizer'),
        ('pesticide', 'Pesticide'),
        ('equipment', 'Equipment'),
        ('tools', 'Tools'),
        ('other', 'Other'),
    ], string='Purchase Type')
    crop_related = fields.Char('Related Crop')
    season = fields.Selection([
        ('spring', 'Spring'),
        ('summer', 'Summer'),
        ('autumn', 'Autumn'),
        ('winter', 'Winter'),
    ], string='Season')
    def action_view_agricultural_request(self):
        """Open the related agricultural request"""
        if self.agricultural_request_id:
            return {
                'name': _('Agricultural Request'),
                'type': 'ir.actions.act_window',
                'res_model': 'agricultural.production.request',
                'view_mode': 'form',
                'res_id': self.agricultural_request_id.id,
                'target': 'current',
            }
class Location(models.Model):
    _inherit = "stock.location"

    is_main_warehouse = fields.Boolean(string='Main Warehouse',default=False,tracking=True,help='There is one central warehouse')
    usage = fields.Selection(selection_add=[('agriculture', 'Agricultural')], ondelete={'agriculture': 'cascade'})
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_main_warehouse = fields.Boolean(string='Main Warehouse',default=False,tracking=True,help='There is one central warehouse')
class StockPickingAccount(models.Model):
    _inherit = 'stock.picking'

    agricultural_journal_entry_id = fields.Many2one(
        'account.move',
        string='Agricultural Journal Entry',
        readonly=True
    )

    def button_validate(self):
        """Override to create journal entries for agricultural transfers"""
        # Call original validation
        result = super().button_validate()
        for i in self:
            i.agricultural_request_id.action_warehouse_approve()

        # Create journal entries for internal transfers from main warehouse
        if self._should_create_agricultural_entry():
            try:
                self._create_agricultural_journal_entry()
                self._create_agricultural_journal_second_entry()
                self.env.flush_all()
                self.env.cr.commit()
                _logger.info(f"Agricultural journal entry created for picking {self.name}")
            except Exception as e:
                _logger.error(f"Error creating agricultural journal entry for {self.name}: {str(e)}")
                # Continue without blocking the validation

        return result

    def _should_create_agricultural_entry(self):
        """Check if should create agricultural journal entry"""
        # Skip if already has journal entry
        if self.agricultural_journal_entry_id:
            return False
        else:
            return True

    def _create_agricultural_journal_entry(self):
        """Create agricultural journal entry for the picking"""
        if self.move_ids_without_package:
            # Filter valid moves from main warehouse
            valid_moves = self.move_ids_without_package.filtered(
                lambda m: m.state == 'done' and
                          m.product_id.categ_id and
                          not float_is_zero(m.product_qty, precision_digits=2)
            )

            # Group moves by product category to get journal
            categories = valid_moves.mapped('product_id.categ_id')

            # Get journal from first category
            journal = self._get_journal_from_category(categories[0])
            if not journal:
                _logger.warning(f"No journal found for picking {self.name}")


            # Prepare journal entry
            move_vals = {
                'journal_id': journal.id,
                'date': self.date_done.date() if self.date_done else fields.Date.today(),
                'ref': f'Stock Transfer: {self.name}',
                'move_type': 'entry',
                'agricultural_project_id':self.agricultural_project_id.id,
                'agricultural_request_id':self.agricultural_request_id.id,
                'line_ids': [],
            }

            # Create lines for each valid move
            for move in valid_moves:
                lines = self._prepare_move_lines(move)
                if lines:
                    move_vals['line_ids'].extend(lines)

            # Create journal entry if we have lines
            if move_vals['line_ids']:
                # Validate that entry is balanced
                total_debit = sum(line[2]['debit'] for line in move_vals['line_ids'])
                total_credit = sum(line[2]['credit'] for line in move_vals['line_ids'])

                if float_is_zero(total_debit - total_credit, precision_digits=2):
                    journal_entry = self.env['account.move'].create(move_vals)
                    self.agricultural_journal_entry_id = journal_entry.id

                    # Add message to picking
                    self.message_post(
                        body=f"Agricultural Journal Entry Created: <a href='/web#id={journal_entry.id}&model=account.move'>{journal_entry.name}</a>",
                        message_type='comment'
                    )

                    return journal_entry
                else:
                    _logger.error(
                        f"Unbalanced journal entry for picking {self.name}: Debit {total_debit}, Credit {total_credit}")
    def _create_agricultural_journal_second_entry(self):
        """Create agricultural journal entry for the picking"""
        if self.move_ids_without_package:
            # Filter valid moves from main warehouse
            valid_moves = self.move_ids_without_package.filtered(
                lambda m: m.state == 'done' and
                          m.product_id.categ_id and
                          not float_is_zero(m.product_qty, precision_digits=2)
            )

            # Group moves by product category to get journal
            categories = valid_moves.mapped('product_id.categ_id')

            # Get journal from first category
            journal = self._get_journal_from_category(categories[0])
            if not journal:
                _logger.warning(f"No journal found for picking {self.name}")
            move_vals = {
                'journal_id': journal.id,
                'date': self.date_done.date() if self.date_done else fields.Date.today(),
                'ref': f'Stock Transfer: {self.name}',
                'move_type': 'entry',
                'agricultural_project_id':self.agricultural_project_id.id,
                'agricultural_request_id':self.agricultural_request_id.id,
                'line_ids': [],
            }

            for move in valid_moves:
                lines = self._prepare_move_second_lines(move)
                if lines:
                    move_vals['line_ids'].extend(lines)

            # Create journal entry if we have lines
            if move_vals['line_ids']:
                # Validate that entry is balanced
                total_debit = sum(line[2]['debit'] for line in move_vals['line_ids'])
                total_credit = sum(line[2]['credit'] for line in move_vals['line_ids'])

                if float_is_zero(total_debit - total_credit, precision_digits=2):
                    journal_entry = self.env['account.move'].create(move_vals)
                    self.agricultural_journal_entry_id = journal_entry.id

                    # Add message to picking
                    self.message_post(
                        body=f"Agricultural Journal Entry Created: <a href='/web#id={journal_entry.id}&model=account.move'>{journal_entry.name}</a>",
                        message_type='comment'
                    )

                    return journal_entry
                else:
                    _logger.error(
                        f"Unbalanced journal entry for picking {self.name}: Debit {total_debit}, Credit {total_credit}")
    def _get_journal_from_category(self, category):
        """Get journal from product category"""
        # First try category's stock journal
        if hasattr(category, 'property_stock_journal') and category.property_stock_journal:
            return category.property_stock_journal

        # Fallback: Search for miscellaneous journal
        journal = self.env['account.journal'].search([
            ('code', '=', 'STJ'),
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if journal:
            return journal

        # Final fallback: Any general journal
        return self.env['account.journal'].search([
            ('type', '=', 'STJ'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
    def _prepare_move_lines(self, move):
        """Prepare journal lines for stock move"""
        lines = []

        category = move.product_id.categ_id
        if not category:
            return lines

        # Get accounts from product category
        #input_account = getattr(category, 'expense_direct_cost', None)
        output_account = getattr(category, 'stock_move_main', None)
        input_account = self.agricultural_request_id.farm_id.expense_account_id
        #output_account = self.agricultural_request_id.farm_id.asset_account_id.id
        if not input_account or not output_account:
            _logger.warning(f"Missing stock accounts for category {category.name}")
            return lines

        # Calculate move value
        unit_price = move.product_id.standard_price or move.product_id.list_price or 0.0
        move_value = unit_price * move.product_qty

        if float_is_zero(move_value, precision_digits=2):
            return lines

        # Line description
        description = f'{move.product_id.name} - {move.location_id.name} <-- {move.location_dest_id.name}'

        # Common line fields
        common_vals = {
            'product_id': move.product_id.id,
            'quantity': move.product_qty,
            'product_uom_id': move.product_uom.id,
        }

        # Debit line (input account - destination)
        debit_line = {
            'name': description,
            'account_id': input_account.id,
            'agricultural_project_id':self.agricultural_project_id.id,
            'agricultural_request_id': self.agricultural_request_id.id,
            'debit': move_value,
            'credit': 0.0,
            **common_vals
        }
        lines.append((0, 0, debit_line))

        # Credit line (output account - source)
        credit_line = {
            'name': description,
            'account_id': output_account.id,
            'agricultural_project_id': self.agricultural_project_id.id,
            'agricultural_request_id': self.agricultural_request_id.id,
            'debit': 0.0,
            'credit': move_value,
            **common_vals
        }
        lines.append((0, 0, credit_line))

        return lines
    def _prepare_move_second_lines(self, move):
        """Prepare journal lines for stock move"""
        lines = []

        category = move.product_id.categ_id
        if not category:
            return lines

        # Get accounts from product category
        #input_account = getattr(category, 'expense_direct_cost', None)
        input_account = self.agricultural_request_id.farm_id.asset_account_id
        output_account = self.agricultural_request_id.farm_id.expense_account_id
        #output_account = self.agricultural_request_id.farm_id.asset_account_id.id
        if not input_account or not output_account:
            _logger.warning(f"Missing stock accounts for category {category.name}")
            return lines

        # Calculate move value
        unit_price = move.product_id.standard_price or move.product_id.list_price or 0.0
        move_value = unit_price * move.product_qty

        if float_is_zero(move_value, precision_digits=2):
            return lines

        # Line description
        description = f'{move.product_id.name} - {move.location_id.name} <-- {move.location_dest_id.name}'

        # Common line fields
        common_vals = {
            'product_id': move.product_id.id,
            'quantity': move.product_qty,
            'product_uom_id': move.product_uom.id,
        }

        # Debit line (input account - destination)
        debit_line = {
            'name': description,
            'account_id': input_account.id,
            'agricultural_project_id':self.agricultural_project_id.id,
            'agricultural_request_id': self.agricultural_request_id.id,
            'debit': move_value,
            'credit': 0.0,
            **common_vals
        }
        lines.append((0, 0, debit_line))

        # Credit line (output account - source)
        credit_line = {
            'name': description,
            'account_id': output_account.id,
            'agricultural_project_id': self.agricultural_project_id.id,
            'agricultural_request_id': self.agricultural_request_id.id,
            'debit': 0.0,
            'credit': move_value,
            **common_vals
        }
        lines.append((0, 0, credit_line))

        return lines
    def action_view_journal_entry(self):
        """View the created journal entry"""
        if not self.agricultural_journal_entry_id:
            raise UserError(_("No journal entry found for this transfer."))

        return {
            'name': _('Agricultural Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.agricultural_journal_entry_id.id,
            'target': 'current',
        }
    def action_create_journal_entry_manual(self):
        """Manual button to create journal entry"""
        if self.agricultural_journal_entry_id:
            raise UserError(_("Journal entry already exists for this picking"))

        if not self._should_create_agricultural_entry():
            raise UserError(
                _("This picking is not eligible for journal entry creation. Make sure it's an internal transfer from main warehouse."))

        try:
            entry = self._create_agricultural_journal_entry()
            if entry:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': f'Journal entry {entry.name} created successfully',
                        'type': 'success',
                    }
                }
            else:
                raise UserError(_("Could not create journal entry. Check product category configuration."))
        except Exception as e:
            raise UserError(_(f"Error creating journal entry: {str(e)}"))
class AccountMove(models.Model):
    _inherit = 'account.move'

    agricultural_request_id = fields.Many2one(
        'agricultural.production.request',
        string='Agricultural Request'
    )
    agricultural_project_id = fields.Many2one(
        'agricultural.project',
        string='Agricultural Project',
        ondelete='cascade'
    )

    def action_post(self):
        res = super().action_post()
        for i in self:
            i.agricultural_request_id.action_accounts_approve()
        return res
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    agricultural_request_id = fields.Many2one(
        'agricultural.production.request',
        string='Agricultural Request'
    )
    agricultural_project_id = fields.Many2one(
        'agricultural.project',
        string='Agricultural Project',
        ondelete='cascade'
    )






