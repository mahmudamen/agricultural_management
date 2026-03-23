# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class HarvestBatch(models.Model):
    _name = 'harvest.batch'
    _description = 'Harvest Batch Collection & Sorting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'batch_date desc, name desc'

    # ==================== IDENTIFICATION ====================
    name = fields.Char(
        'Batch Number',
        required=True,
        copy=False,
        default='New',
        tracking=True,
        index=True
    )
    batch_date = fields.Date(
        'Batch Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    # ==================== RELATIONSHIPS ====================
    schedule_id = fields.Many2one(
        'agricultural.harvest.schedule',
        'Harvest Schedule',
        required=True,
        tracking=True,
        ondelete='restrict',
        help="Source harvest schedule with generated lots"
    )

    project_id = fields.Many2one(
        'agricultural.project',
        'Project',
        related='schedule_id.project_id',
        store=True,
        readonly=True
    )

    farm_id = fields.Many2one(
        'agricultural.farm',
        'Farm',
        related='schedule_id.farm_id',
        store=True,
        readonly=True
    )

    crop_id = fields.Many2one(
        'product.product',
        'Crop Product',
        related='schedule_id.crop_id',
        store=True,
        readonly=True
    )

    uom_id = fields.Many2one(
        'uom.uom',
        'Unit of Measure',
        related='crop_id.uom_id',
        readonly=True
    )

    # ==================== TEAM ====================
    responsible_id = fields.Many2one(
        'res.users',
        'Responsible',
        default=lambda self: self.env.user,
        tracking=True
    )

    worker_ids = fields.Many2many(
        'hr.employee',
        'harvest_batch_worker_rel',
        'batch_id',
        'employee_id',
        string='Team Members'
    )

    # ==================== COLLECTION QUANTITIES ====================
    estimated_quantity = fields.Float(
        'Estimated Quantity',
        related='schedule_id.estimated_quantity',
        readonly=True,
        help="From harvest schedule"
    )
    total_collection_qty = fields.Float(
        'Total Collection Quantity',
        help="From harvest schedule"
    )
    total_sorting_qty = fields.Float(
        'Total Sorting Quantity',
        help="From harvest schedule"
    )
    actual_quantity = fields.Float(
        'Actual Collected Quantity',
        compute='_compute_collection_quantities',
        store=True,
        digits='Product Unit of Measure',
        help="Total collected from lots"
    )

    collected_lot_ids = fields.Many2many(
        'stock.lot',
        'harvest_batch_lot_rel',
        'batch_id',
        'lot_id',
        string='Collected Lots',
        help="Lots collected for this batch"
    )

    lot_count = fields.Integer(
        'Number of Lots',
        compute='_compute_lot_count'
    )

    # ==================== SORTING ====================
    sorting_line_ids = fields.One2many(
        'harvest.sorting.line',
        'harvest_batch_id',
        'Sorting Lines'
    )

    sorting_line_count = fields.Integer(
        'Sorting Lines',
        compute='_compute_counts'
    )

    # ==================== WEIGHTS & WASTE ====================
    total_weight = fields.Float(
        'Total Collected Weight',
        compute='_compute_totals',
        store=True,
        digits='Product Unit of Measure',
        help='Total weight collected'
    )

    sorted_weight = fields.Float(
        'Sorted Weight',
        compute='_compute_totals',
        store=True,
        digits='Product Unit of Measure',
        help='Weight after sorting'
    )
    total_completed_qty = fields.Float(
        'Total Completed Qty',
        #compute='_compute_totals',
        store=True,
        digits='Product Unit of Measure',
        help='Total Completed Qty'
    )
    waste_weight = fields.Float(
        'Waste Weight',
        compute='_compute_totals',
        store=True,
        digits='Product Unit of Measure'
    )

    waste_percentage = fields.Float(
        'Waste %',
        compute='_compute_totals',
        store=True
    )

    # ==================== FINANCIAL ====================
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    batch_cost = fields.Monetary(
        'Batch Cost',
        compute='_compute_financials',
        store=True,
        currency_field='currency_id'
    )

    batch_revenue = fields.Monetary(
        'Batch Revenue',
        compute='_compute_financials',
        store=True,
        currency_field='currency_id'
    )

    batch_profit = fields.Monetary(
        'Batch Profit',
        compute='_compute_financials',
        store=True,
        currency_field='currency_id'
    )

    profit_margin = fields.Float(
        'Profit Margin %',
        compute='_compute_financials',
        store=True
    )

    # ==================== STOCK OPERATIONS ====================
    collection_picking_ids = fields.One2many(
        'stock.picking',
        'harvest_batch_id',
        string='Collection Pickings',
        domain=[('harvest_stage', '=', 'collection')]
    )

    sorting_picking_ids = fields.One2many(
        'stock.picking',
        'harvest_batch_id',
        string='Sorting Pickings',
        domain=[('harvest_stage', '=', 'sorting')]
    )

    picking_count = fields.Integer(
        'Pickings',
        compute='_compute_counts'
    )

    # ==================== ACCOUNTING ====================
    account_move_ids = fields.One2many(
        'account.move',
        'harvest_batch_id',
        string='Journal Entries'
    )

    account_move_count = fields.Integer(
        'Journal Entries',
        compute='_compute_counts'
    )

    # ==================== STATE ====================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('collection', 'Collecting'),
        ('collected', 'Collected'),
        ('sorting', 'Sorting'),
        ('sorted', 'Sorted'),
        ('quality', 'Quality Check'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], default='draft', required=True, tracking=True, copy=False)

    rejection_reason = fields.Text('Rejection Reason')
    notes = fields.Text('Notes')

    # ==================== COMPUTE METHODS ====================

    @api.depends('collected_lot_ids')
    def _compute_lot_count(self):
        for batch in self:
            batch.lot_count = len(batch.collected_lot_ids)

    @api.depends('collected_lot_ids', 'collected_lot_ids.product_qty')
    def _compute_collection_quantities(self):
        for batch in self:
            batch.actual_quantity = sum(batch.collected_lot_ids.mapped('product_qty'))

    @api.depends('actual_quantity', 'sorting_line_ids.final_weight_kg')
    def _compute_totals(self):
        for batch in self:
            batch.total_weight = batch.actual_quantity
            batch.sorted_weight = sum(batch.sorting_line_ids.mapped('final_weight_kg'))
            batch.waste_weight = batch.total_weight - batch.sorted_weight
            batch.waste_percentage = (
                (batch.waste_weight / batch.total_weight * 100)
                if batch.total_weight > 0 else 0
            )

    @api.depends('sorting_line_ids.revenue', 'sorting_line_ids.cost')
    def _compute_financials(self):
        for batch in self:
            batch.batch_revenue = sum(batch.sorting_line_ids.mapped('revenue'))
            batch.batch_cost = sum(batch.sorting_line_ids.mapped('cost'))
            batch.batch_profit = batch.batch_revenue - batch.batch_cost
            batch.profit_margin = (
                (batch.batch_profit / batch.batch_revenue * 100)
                if batch.batch_revenue > 0 else 0
            )

    def _compute_counts(self):
        for batch in self:
            batch.sorting_line_count = len(batch.sorting_line_ids)
            batch.picking_count = len(batch.collection_picking_ids + batch.sorting_picking_ids)
            batch.account_move_count = len(batch.account_move_ids)

    # ==================== CRUD ====================

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('harvest.batch') or 'New'
        return super(HarvestBatch, self).create(vals)

    def write(self, vals):
        if 'state' in vals:
            for record in self:
                old_state = dict(record._fields['state'].selection).get(record.state)
                new_state = dict(record._fields['state'].selection).get(vals['state'])
                record.message_post(
                    body=_("State changed from %s to %s") % (old_state, new_state),
                    subject=_("Status Update")
                )
        return super(HarvestBatch, self).write(vals)

    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise UserError(
                    _("Cannot delete batch '%s' in state '%s'. Cancel it first.") %
                    (record.name, record.state)
                )
        return super(HarvestBatch, self).unlink()

    # ==================== CONSTRAINTS ====================

    @api.constrains('batch_date')
    def _check_batch_date(self):
        for batch in self:
            if batch.batch_date > fields.Date.today():
                raise ValidationError(_("Batch date cannot be in the future"))

    @api.constrains('schedule_id')
    def _check_schedule_state(self):
        for batch in self:
            if batch.schedule_id.state not in ['processing', 'completed']:
                raise ValidationError(
                    _("Can only create batch from processed or completed harvest schedules")
                )

    # ==================== WORKFLOW ACTIONS ====================

    def action_start_collection(self):
        """Start collecting from harvest schedule lots"""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_("Only draft batches can start collection"))

        if not self.schedule_id.lot_ids:
            raise UserError(
                _("No lots available in harvest schedule '%s'. Process the schedule first.") %
                self.schedule_id.name
            )

        # Auto-collect all available lots from schedule
        available_lots = self.schedule_id.lot_ids.filtered(
            lambda l: l.product_qty > 0 and not l.quarantine
        )

        if not available_lots:
            raise UserError(_("No available lots to collect (all may be in quarantine or empty)"))

        self.collected_lot_ids = [(6, 0, available_lots.ids)]
        self.state = 'collection'

        self.message_post(
            body=_("Collection started. %d lots assigned for collection.") % len(available_lots),
            subject=_("Collection Started")
        )

        return True

    def action_complete_collection(self):
        """Complete collection and create stock movements"""
        self.ensure_one()

        if self.state != 'collection':
            raise UserError(_("Batch must be in collection state"))

        if not self.collected_lot_ids:
            raise UserError(_("No lots collected"))

        # Create collection picking
        picking = self._create_collection_picking()

        self.state = 'collected'

        self.message_post(
            body=_("Collection completed. Total collected: %.2f %s from %d lots") % (
                self.actual_quantity,
                self.uom_id.name,
                len(self.collected_lot_ids)
            ),
            subject=_("Collection Completed")
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Collection Transfer'),
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def _create_collection_picking(self):
        """Create picking to collect harvest from lots to sorting area"""
        self.ensure_one()

        # Get locations
        source_location = self.schedule_id.destination_location_id
        dest_location = self._get_sorting_location()

        if not source_location or not dest_location:
            raise UserError(_("Source or sorting location not configured"))

        # Get picking type
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
        ], limit=1)

        if not picking_type:
            raise UserError(_("No internal transfer operation type found"))

        # Create picking
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': f"{self.schedule_id.name} - {self.name}",
            'harvest_batch_id': self.id,
            'harvest_stage': 'collection',
            'scheduled_date': fields.Datetime.now(),
            'agricultural_project_id': self.project_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        # Create moves for each lot
        for lot in self.collected_lot_ids.filtered(lambda l: l.product_qty > 0):
            move_vals = {
                'name': f"{lot.product_id.name} - Lot {lot.name}",
                'product_id': lot.product_id.id,
                'product_uom_qty': lot.product_qty,
                'product_uom': lot.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'origin': self.name,
            }

            move = self.env['stock.move'].create(move_vals)

            # Create move line with lot
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': lot.product_id.id,
                'product_uom_id': lot.product_uom_id.id,
                'quantity': lot.product_qty,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'lot_id': lot.id,
            })

        if not picking.move_ids_without_package:
            picking.unlink()
            raise UserError(_("No valid products to transfer"))

        # Confirm and assign
        picking.action_confirm()
        picking.action_assign()

        return picking

    def action_start_sorting(self):
        """Start sorting operations"""
        self.ensure_one()

        if self.state != 'collected':
            raise UserError(_("Complete collection before sorting"))

        if self.actual_quantity <= 0:
            raise UserError(_("No quantity collected to sort"))

        self.state = 'sorting'

        self.message_post(
            body=_("Sorting started. Total to sort: %.2f %s") % (
                self.actual_quantity,
                self.uom_id.name
            ),
            subject=_("Sorting Started")
        )

        # Open sorting wizard
        return {
            'name': _('Sort Batch'),
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.sorting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_harvest_batch_id': self.id,
                'default_product_id': self.crop_id.id,
                'default_initial_weight_kg': self.actual_quantity,
                'default_project_id': self.project_id.id,
            }
        }

    def action_complete_sorting(self):
        """Complete sorting and move to quality check"""
        self.ensure_one()

        if self.state != 'sorting':
            raise UserError(_("Batch must be in sorting state"))

        if not self.sorting_line_ids:
            raise UserError(_("No sorting lines created. Complete sorting first."))

        # Check if all sorting lines are confirmed
        unconfirmed = self.sorting_line_ids.filtered(lambda l: l.state == 'draft')
        if unconfirmed:
            raise UserError(
                _("Some sorting lines are not confirmed. Please confirm all sorting lines first.")
            )

        self.state = 'sorted'

        self.message_post(
            body=_("Sorting completed. Sorted: %.2f %s, Waste: %.2f %s (%.1f%%)") % (
                self.sorted_weight,
                self.uom_id.name,
                self.waste_weight,
                self.uom_id.name,
                self.waste_percentage
            ),
            subject=_("Sorting Completed")
        )

        # Auto-start quality check
        return self.action_quality_check()

    def action_approve(self):
        """Approve batch after quality check"""
        self.ensure_one()

        if self.state != 'quality':
            raise UserError(_("Only batches in quality check can be approved"))

        # Verify all sorting lines are approved
        unapproved_lines = self.sorting_line_ids.filtered(lambda l: l.state not in ['sorted', 'approved'])
        if unapproved_lines:
            raise UserError(
                _("Cannot approve batch. Some sorting lines are not ready: %s") %
                ", ".join(unapproved_lines.mapped('name'))
            )

        # Update all sorting lines to approved
        self.sorting_line_ids.write({'state': 'approved'})

        self.state = 'approved'

        self.message_post(
            body=_("✅ Batch approved by %s\n"
                   "Total Revenue: %s %s\n"
                   "Total Cost: %s %s\n"
                   "Profit: %s %s (%.1f%% margin)") % (
                     self.env.user.name,
                     self.batch_revenue, self.currency_id.symbol,
                     self.batch_cost, self.currency_id.symbol,
                     self.batch_profit, self.currency_id.symbol,
                     self.profit_margin
                 ),
            subject=_("Batch Approved")
        )

        # Create completion stock movements
        self._create_completion_pickings()

        # Notify stakeholders
        self._notify_approval()

        return True

    def action_reject(self):
        """Reject batch with reason"""
        self.ensure_one()

        if self.state not in ['quality', 'sorted']:
            raise UserError(_("Only batches in quality check or sorted state can be rejected"))

        # Open wizard to get rejection reason
        return {
            'name': _('Reject Batch'),
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.batch.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_batch_id': self.id}
        }

    def _perform_rejection(self, reason):
        """Internal method to reject with reason"""
        self.ensure_one()

        self.state = 'rejected'
        self.rejection_reason = reason

        # Update sorting lines
        self.sorting_line_ids.write({'state': 'rejected'})

        self.message_post(
            body=_("❌ Batch rejected by %s\nReason: %s") % (
                self.env.user.name,
                reason
            ),
            subject=_("Batch Rejected")
        )

        # Create activity for responsible user
        self.activity_schedule(
            'mail.mail_activity_data_warning',
            user_id=self.responsible_id.id,
            summary=_('Batch Rejected'),
            note=_('Batch %s was rejected. Reason: %s') % (self.name, reason)
        )

    def action_cancel(self):
        """Cancel batch"""
        self.ensure_one()

        if self.state == 'approved':
            raise UserError(_("Cannot cancel approved batches"))

        # Cancel all pickings
        all_pickings = self.collection_picking_ids + self.sorting_picking_ids
        for picking in all_pickings:
            if picking.state not in ['done', 'cancel']:
                picking.action_cancel()

        # Cancel accounting entries
        for move in self.account_move_ids:
            if move.state == 'draft':
                move.button_cancel()

        # Update sorting lines
        self.sorting_line_ids.write({'state': 'draft'})

        self.state = 'cancelled'

        self.message_post(
            body=_("Batch cancelled by %s") % self.env.user.name,
            subject=_("Batch Cancelled")
        )

    def action_reset_to_draft(self):
        """Reset batch to draft"""
        self.ensure_one()

        if self.state == 'approved':
            raise UserError(_("Cannot reset approved batches"))

        # Check for completed stock movements
        done_pickings = (self.collection_picking_ids + self.sorting_picking_ids).filtered(
            lambda p: p.state == 'done'
        )
        if done_pickings:
            raise UserError(_("Cannot reset batch with completed stock movements"))

        # Check for posted accounting entries
        posted_moves = self.account_move_ids.filtered(lambda m: m.state == 'posted')
        if posted_moves:
            raise UserError(_("Cannot reset batch with posted accounting entries"))

        self.state = 'draft'
        self.rejection_reason = False

        # Reset sorting lines
        self.sorting_line_ids.write({'state': 'draft'})

        self.message_post(
            body=_("Batch reset to draft by %s") % self.env.user.name,
            subject=_("Reset to Draft")
        )

    # ==================== STOCK MOVEMENT HELPERS ====================

    def _create_completion_pickings(self):
        """Create pickings to move sorted products to warehouse"""
        self.ensure_one()

        if not self.sorting_line_ids:
            return False

        dest_location = self._get_warehouse_location()
        source_location = self._get_sorting_location()

        # Get picking type
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
        ], limit=1)

        if not picking_type:
            _logger.warning("No internal picking type found")
            return False

        # Create picking for each sorted product variant
        pickings = self.env['stock.picking']

        for line in self.sorting_line_ids.filtered(lambda l: l.final_weight_kg > 0 and l.product_variant_id):
            picking_vals = {
                'picking_type_id': picking_type.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'origin': f"{self.name} - {line.name}",
                'harvest_batch_id': self.id,
                'harvest_stage': 'completed',
                'scheduled_date': fields.Datetime.now(),
                'agricultural_project_id': self.project_id.id,
            }

            picking = self.env['stock.picking'].create(picking_vals)

            # Create move
            move_vals = {
                'name': f"{line.product_variant_id.name} - {line.name}",
                'product_id': line.product_variant_id.id,
                'product_uom_qty': line.final_weight_kg,
                'product_uom': line.product_variant_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'origin': self.name,
                'company_id': self.company_id.id,
            }

            move = self.env['stock.move'].create(move_vals)

            # Confirm and process
            picking.action_confirm()
            picking.action_assign()
            move.quantity_done = line.final_weight_kg
            picking.button_validate()

            pickings |= picking

        if pickings:
            self.message_post(
                body=_("Created %d completion pickings for warehouse transfer") % len(pickings),
                subject=_("Stock Movements")
            )

        return pickings

    def _get_sorting_location(self):
        """Get or create sorting location"""
        location = self.env['stock.location'].search([
            ('usage', '=', 'production'),
            ('name', 'ilike', 'sorting'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not location:
            location = self.env['stock.location'].search([
                ('usage', '=', 'production'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

        if not location:
            # Create sorting location
            warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if warehouse:
                location = self.env['stock.location'].create({
                    'name': 'Sorting Area',
                    'usage': 'production',
                    'location_id': warehouse.view_location_id.id,
                    'company_id': self.company_id.id,
                })

        if not location:
            raise UserError(_("Please configure a sorting/production location"))

        return location

    def _get_warehouse_location(self):
        """Get main warehouse stock location"""
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not warehouse:
            raise UserError(_("No warehouse configured for company"))

        return warehouse.lot_stock_id

    # ==================== NOTIFICATION METHODS ====================

    def _notify_approval(self):
        """Notify stakeholders of batch approval"""
        self.ensure_one()

        # Notify project manager
        if self.project_id and self.project_id.user_id:
            self.message_post(
                body=_("✅ Batch %s has been approved\n"
                       "Total Revenue: %s %s\n"
                       "Total Cost: %s %s\n"
                       "Profit: %s %s (%.1f%% margin)") % (
                         self.name,
                         self.batch_revenue, self.currency_id.symbol,
                         self.batch_cost, self.currency_id.symbol,
                         self.batch_profit, self.currency_id.symbol,
                         self.profit_margin
                     ),
                subject=_("Batch Approved"),
                partner_ids=[self.project_id.user_id.partner_id.id]
            )

    # ==================== VIEW ACTIONS ====================

    def action_view_lots(self):
        """View collected lots"""
        self.ensure_one()
        return {
            'name': _('Collected Lots - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.collected_lot_ids.ids)],
            'context': {'create': False}
        }

    def action_view_sorting_lines(self):
        """View sorting lines"""
        self.ensure_one()
        return {
            'name': _('Sorting Lines - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.sorting.line',
            'view_mode': 'list,form',
            'domain': [('harvest_batch_id', '=', self.id)],
            'context': {
                'default_harvest_batch_id': self.id,
                'default_project_id': self.project_id.id,
                'group_by': ['grade', 'size_category']
            }
        }

    def action_view_schedule(self):
        """View harvest schedule"""
        self.ensure_one()
        return {
            'name': _('Harvest Schedule'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.harvest.schedule',
            'res_id': self.schedule_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def action_view_pickings(self):
        """View all pickings"""
        self.ensure_one()
        picking_ids = (self.collection_picking_ids + self.sorting_picking_ids).ids

        return {
            'name': _('Stock Pickings - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', picking_ids)],
            'context': {'search_default_group_by_harvest_stage': 1}
        }

    def action_view_accounting_entries(self):
        """View accounting entries"""
        self.ensure_one()
        return {
            'name': _('Journal Entries - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('harvest_batch_id', '=', self.id)],
            'context': {'create': False}
        }

    def action_view_project(self):
        """View project"""
        self.ensure_one()
        if not self.project_id:
            raise UserError(_("No project associated"))

        return {
            'name': _('Agricultural Project'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.project',
            'res_id': self.project_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def action_view_farm(self):
        """View farm"""
        self.ensure_one()
        if not self.farm_id:
            raise UserError(_("No farm associated"))

        return {
            'name': _('Farm'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.farm',
            'res_id': self.farm_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
class HarvestSortingLine(models.Model):
    _name = 'harvest.sorting.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Harvest Sorting Line'
    _order = 'sequence, create_date desc'
    _check_company_auto = True

    # Identification
    name = fields.Char('Reference', default='New')
    harvest_batch_id = fields.Many2one(
        'harvest.batch', 'Harvest Batch', required=True,
        tracking=True
    )
    total_cost = fields.Float('Total Harvest Quantity', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    gross_profit = fields.Float('Total Harvest Quantity', store=True)
    profit_margin_percent = fields.Float('Total Harvest Quantity', store=True)
    quality_score = fields.Float('Total Harvest Quantity', store=True)
    total_amount = fields.Monetary('Total Amount', required=False, currency_field='currency_id', tracking=True)
    project_id = fields.Many2one(
        'agricultural.project',
        'Agricultural Project',
        tracking=True
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cost Center',
        tracking=True, copy=False,
        help='Analytic account for cost tracking'
    )
    notes = fields.Text(string='Notes')
    picking_id = fields.Many2one('stock.picking', 'Related Picking')
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    invoice_id = fields.Many2one('account.move', 'Source Invoice')
    household_harvest_id = fields.Many2one(
        'household.harvest', 'Source Contribution',tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        index=True
    )
    weight_kg = fields.Float(
        'Final Weight (KG)', store=True,
        help='Add final weight in kilograms'
    )
    final_weight_kg = fields.Float(
        'Final Weight (KG)', store=True,
        help='Add final weight in kilograms'
    )
    # Related fields
    schedule_id = fields.Many2one(
        'agricultural.harvest.schedule', 'Schedule',
        related='harvest_batch_id.schedule_id', store=True
    )
    product_id = fields.Many2one(
        'product.product', 'Raw Product',store=True
    )
    price_unit = fields.Float(
        string='Unit Price',  digits='Product Price',
        help="Order line Unit price")
    date = fields.Date(string='Date')
    quantity = fields.Float(
        'Lot Quantity',
        digits='Product Unit of Measure',
        required=True,
        tracking=True
    )
    # Sorting results
    grade = fields.Selection([
        ('a', 'Grade A'),
        ('b', 'Grade B'),
        ('c', 'Grade C'),
        ('rejected', 'Rejected')
    ], 'Quality Grade', required=True, tracking=True)
    size_category = fields.Selection([
        ('xs', 'Extra Small'),
        ('s', 'Small'),
        ('m', 'Medium'),
        ('l', 'Large'),
        ('xl', 'Extra Large')
    ], 'Size Category', required=True, tracking=True)
    initial_weight = fields.Float(
        'Input Weight (kg)', required=True, digits='Product Unit of Measure'
    )
    final_weight = fields.Float(
        'Output Weight (kg)', required=True, digits='Product Unit of Measure'
    )
    waste_weight = fields.Float(
        'Waste (kg)', compute='_compute_waste', store=True
    )
    waste_percentage = fields.Float(
        'Waste %', compute='_compute_waste', store=True
    )
    product_variant_id = fields.Many2one(
        'product.product', 'Sorted Product', tracking=True
    )
    # State
    state = fields.Selection([
        ('draft', 'Recorded'),
        ('sorted', 'Sorted'),
        ('quality', 'Quality Checked'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='draft', tracking=True)
    quality_status = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Passed'),
        ('fail', 'Failed')
    ], 'Quality Status', compute='_compute_quality_status', store=True)
    # Technical
    sequence = fields.Integer('Sequence', default=10)
    # Stock Relations
    sorting_move_id = fields.Many2one('stock.move', 'Sorting Move', readonly=True)
    completion_move_id = fields.Many2one('stock.move', 'Completion Move', readonly=True)
    completion_picking_id = fields.Many2one('stock.picking', 'Completion Picking', readonly=True)
    # Accounting Relations
    sorting_account_move_id = fields.Many2one('account.move', 'Sorting Entry', readonly=True)
    completion_account_move_id = fields.Many2one('account.move', 'Completion Entry', readonly=True)
    uom_id = fields.Many2one(
        'uom.uom',
        'Unit of Measure',
        #related='harvest_batch_id.product_id.uom_id'
    )
    revenue = fields.Float('Total Harvest Quantity', store=True)
    cost = fields.Float('Total Harvest Quantity', store=True)
    # Computed fields
    @api.depends('initial_weight', 'final_weight')
    def _compute_waste(self):
        for line in self:
            waste = line.initial_weight - line.final_weight
            waste_pct = (waste / line.initial_weight * 100) if line.initial_weight > 0 else 0
            line.update({
                'waste_weight': waste,
                'waste_percentage': waste_pct
            })
    def action_confirm(self):
        """Override to create stock move and accounting"""
        self.action_confirm_sorting()

        # Create stock move from sorting to completed
        self._create_sorting_stock_move()
    def _create_sorting_stock_move(self):
        """Create stock move from sorting location to completed location"""
        self.ensure_one()

        if self.sorting_move_id:
            return self.sorting_move_id

        # Get locations
        source_location = self.harvest_batch_id._get_sorting_location()
        dest_location = self.harvest_batch_id._get_completed_location()

        if not source_location or not dest_location:
            _logger.warning("Sorting or completed location not configured")
            return False

        # Create picking for sorted product
        picking_type = self.harvest_batch_id._get_internal_picking_type(source_location)

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': f"{self.harvest_batch_id.name} - Sorting",
            'harvest_batch_id': self.harvest_batch_id.id,
            'harvest_stage': 'sorting',
            'scheduled_date': fields.Datetime.now(),
        }

        picking = self.env['stock.picking'].create(picking_vals)

        # Create stock move for sorted product
        move_vals = {
            'name': f"{self.product_variant_id.name} - {self.complete_item_code}",
            'product_id': self.product_variant_id.id,
            'product_uom_qty': self.final_weight_kg,
            'product_uom': self.product_variant_id.uom_id.id,
            'picking_id': picking.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.harvest_batch_id.name,
            'company_id': self.env.company.id,
            'sorting_line_id': self.id,
        }

        move = self.env['stock.move'].create(move_vals)
        move._action_confirm()
        move._action_assign()
        move.quantity_done = self.final_weight_kg
        move._action_done()

        self.sorting_move_id = move
        self.stock_move_id = move  # Also update the main stock_move_id

        return move
    def action_sort(self):
        """Mark product as ready for sale and move to completed location"""
        # Create stock move to final location
        self._create_completion_stock_move()
        # Create completion accounting entry
        self._create_completion_accounting_entry()
    def _create_completion_stock_move(self):
        """Move from sorting to completed/finished goods location"""
        self.ensure_one()

        if self.completion_move_id:
            return self.completion_move_id

        # Get locations
        source_location = self.harvest_batch_id._get_sorting_location()
        dest_location = self._get_finished_goods_location()

        if not source_location or not dest_location:
            _logger.warning("Sorting or finished goods location not configured")
            return False

        # Create picking
        picking_type = self.harvest_batch_id._get_internal_picking_type(source_location)

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': f"{self.harvest_batch_id.name} - Completed",
            'harvest_batch_id': self.harvest_batch_id.id,
            'harvest_stage': 'completed',
            'scheduled_date': fields.Datetime.now(),
            'agricultural_project_id': self.project_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)
        self.completion_picking_id = picking

        # Create stock move
        move_vals = {
            'name': f"{self.product_variant_id.name} - Completed",
            'product_id': self.product_variant_id.id,
            'product_uom_qty': self.final_weight_kg,
            'product_uom': self.product_variant_id.uom_id.id,
            'picking_id': picking.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.harvest_batch_id.name,
            'company_id': self.env.company.id,
            'sorting_line_id': self.id,
        }

        move = self.env['stock.move'].create(move_vals)
        move._action_confirm()
        move._action_assign()
        move.quantity_done = self.final_weight_kg
        move._action_done()

        self.completion_move_id = move

        return move
    def _create_completion_accounting_entry(self):
        """Create accounting entry for completed harvest (WIP to Finished Goods)"""
        self.ensure_one()

        company = self.env.company

        if not company.stock_accounting_active:
            return False

        journal = company.stock_journal
        if not journal:
            return False

        # Get accounts
        wip_account = company.wip_account or company.property_stock_account_output
        finished_goods_account = self._get_finished_goods_account()

        if not wip_account or not finished_goods_account:
            _logger.error("WIP or Finished Goods account not configured")
            return False

        # Calculate final product value
        final_value = self.final_weight_kg * self.unit_cost

        # Get analytic account
        analytic_account = self.analytic_account_id
        analytic_distribution = {str(analytic_account.id): 100} if analytic_account else False

        move_lines = []

        # Debit: Finished Goods Inventory
        move_lines.append((0, 0, {
            'name': f'Completed Harvest - {self.product_variant_id.name}',
            'account_id': finished_goods_account.id,
            'debit': final_value,
            'credit': 0.0,
            'product_id': self.product_variant_id.id,
            'quantity': self.final_weight_kg,
            'product_uom_id': self.product_variant_id.uom_id.id,
            'analytic_distribution': analytic_distribution,
            'sorting_line_id': self.id,
        }))

        # Credit: WIP Account
        move_lines.append((0, 0, {
            'name': f'From WIP - {self.product_variant_id.name}',
            'account_id': wip_account.id,
            'debit': 0.0,
            'credit': final_value,
            'product_id': self.product_variant_id.id,
            'quantity': self.final_weight_kg,
            'product_uom_id': self.product_variant_id.uom_id.id,
            'sorting_line_id': self.id,
        }))

        account_move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'{self.harvest_batch_id.name} - Completed - {self.complete_item_code}',
            'line_ids': move_lines,
            'harvest_batch_id': self.harvest_batch_id.id,
            'sorting_line_id': self.id,
            'agricultural_project_id': self.project_id.id,
        }

        try:
            account_move = self.env['account.move'].create(account_move_vals)

            if company.auto_post_stock_entries:
                account_move.action_post()

            self.completion_account_move_id = account_move

            self.message_post(
                body=f'Completion accounting entry created: {account_move.name}',
                subject='Completion Entry Created'
            )

            return account_move
        except Exception as e:
            _logger.error(f"Error creating completion accounting entry: {str(e)}")
            return False
    def _get_finished_goods_account(self):
        """Get finished goods stock account"""
        company = self.env.company

        # Try to get from product category
        if self.product_variant_id.categ_id:
            account = self.product_variant_id.categ_id.property_stock_valuation_account_id
            if account:
                return account

        # Default to company stock output account
        return company.property_stock_account_output or company.property_stock_account_input
    def _get_finished_goods_location(self):
        """Get finished goods location"""
        # Search for stock location (warehouse)
        location = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('name', 'ilike', 'stock'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not location:
            # Get default stock location
            warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if warehouse:
                location = warehouse.lot_stock_id

        return location
    def action_done(self, partner_id=None):
        """Override to include accounting for cost of goods sold"""

        # Create COGS accounting entry when delivery is validated
        if self.state == 'sorted':
            self._create_cogs_accounting_entry()
            self.state = 'approved'
    def _create_cogs_accounting_entry(self):
        """Create Cost of Goods Sold entry when product is delivered"""
        self.ensure_one()

        company = self.env.company

        if not company.stock_accounting_active:
            return False

        journal = company.stock_journal
        if not journal:
            return False

        # Get accounts
        stock_account = self._get_finished_goods_account()
        cogs_account = self._get_cogs_account()

        if not stock_account or not cogs_account:
            _logger.error("Stock or COGS account not configured")
            return False

        # Calculate COGS
        cogs_value = self.cost  # Already calculated: final_weight_kg * unit_cost

        # Get analytic account
        analytic_account = self.analytic_account_id
        analytic_distribution = {str(analytic_account.id): 100} if analytic_account else False

        move_lines = []

        # Debit: Cost of Goods Sold (Expense)
        move_lines.append((0, 0, {
            'name': f'COGS - {self.product_variant_id.name}',
            'account_id': cogs_account.id,
            'debit': cogs_value,
            'credit': 0.0,
            'product_id': self.product_variant_id.id,
            'quantity': self.final_weight_kg,
            'product_uom_id': self.product_variant_id.uom_id.id,
            'analytic_distribution': analytic_distribution,
            'sorting_line_id': self.id,
        }))

        # Credit: Finished Goods Inventory
        move_lines.append((0, 0, {
            'name': f'Inventory Reduction - {self.product_variant_id.name}',
            'account_id': stock_account.id,
            'debit': 0.0,
            'credit': cogs_value,
            'product_id': self.product_variant_id.id,
            'quantity': self.final_weight_kg,
            'product_uom_id': self.product_variant_id.uom_id.id,
            'sorting_line_id': self.id,
        }))

        account_move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'{self.harvest_batch_id.name} - COGS - {self.complete_item_code}',
            'line_ids': move_lines,
            'harvest_batch_id': self.harvest_batch_id.id,
            'sorting_line_id': self.id,
            'agricultural_project_id': self.project_id.id,
        }

        try:
            account_move = self.env['account.move'].create(account_move_vals)

            if company.auto_post_stock_entries:
                account_move.action_post()

            self.message_post(
                body=f'COGS accounting entry created: {account_move.name}',
                subject='COGS Entry Created'
            )

            return account_move
        except Exception as e:
            _logger.error(f"Error creating COGS accounting entry: {str(e)}")
            return False
    def _get_cogs_account(self):
        """Get Cost of Goods Sold account"""
        company = self.env.company

        # Try to get from product category
        if self.product_variant_id.categ_id:
            account = self.product_variant_id.categ_id.property_account_expense_categ_id
            if account:
                return account

        # Default to company COGS account
        return company.cogs_fertilizers or company.property_account_expense_categ_id
    def action_cancel(self):
        pass
    def action_reset_to_draft(self):
        pass
    # Business methods
    def action_confirm_sorting(self):
        """
        Confirm sorting results, create product variant, and create stock movement.
        This is a critical step that transitions the sorting line from draft to sorted state.
        """
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft sorting lines can be confirmed."))
            if not record.initial_weight or not record.final_weight:
                raise UserError(_("Initial and final weights must be set."))
            if record.final_weight > record.initial_weight:
                raise UserError(_("Final weight cannot exceed initial weight."))

            try:
                # Create the classified product variant
                #record._create_product_variant()

                # Create the stock movement for the sorted product
                #record._create_stock_move()

                # Update state for both sorting line and source harvest
                record.state = 'sorted'
                record.household_harvest_id.state = 'sorted'

                # Update related batch status
                if all(line.state in ['sorted', 'quality', 'approved']
                       for line in record.harvest_batch_id.sorting_line_ids):
                    record.harvest_batch_id.state = 'sorted'

                record.message_post(
                    body=_("Sorting confirmed for %s. Created variant: %s. Quantity: %.2f kg") % (
                        record.product_variant_id.display_name,
                        record.product_variant_id.default_code,
                        record.final_weight
                    ),
                    subject=_("Sorting Confirmed")
                )
            except Exception as e:
                _logger.error("Error confirming sorting: %s", str(e))
                raise UserError(_("Error confirming sorting: %s") % str(e))

        return True
    def action_open_sorting_wizard(self):
        """
        Open sorting wizard with context from current sorting line.
        Used for editing or re-sorting existing lines.
        """
        self.ensure_one()

        return {
            'name': _('Sort Harvest'),
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.sorting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sorting_line_id': self.id,
                'default_household_harvest_id': self.household_harvest_id.id,
                'default_harvest_batch_id': self.harvest_batch_id.id,
                'default_product_id': self.product_id.id,
                'default_quantity': self.quantity,
                'default_initial_weight_kg': self.initial_weight,
                'default_final_weight_kg': self.final_weight,
                'default_quality_grade': self.grade,
                'default_size_category': self.size_category,
                'default_unit_cost': self.unit_cost if hasattr(self, 'unit_cost') else 0.0,
                'default_analytic_account_id': self.analytic_account_id.id,
                'default_notes': self.notes,
            }
        }
    def action_open_wizard(self):
        """
        Open sorting wizard for creating new sorting from household harvest.
        This is called from the sorting line to split into multiple grades.
        """
        self.ensure_one()

        if self.state not in ['draft']:
            raise UserError(_('Only draft sorting lines can be re-sorted.'))

        return {
            'name': _('Split into Grades'),
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.sorting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sorting_line_id': self.id,
                'default_household_harvest_id': self.household_harvest_id.id,
                'default_harvest_batch_id': self.harvest_batch_id.id,
                'default_product_id': self.product_id.id,
                'default_quantity': self.quantity or self.initial_weight,
                'default_uom_id': self.uom_id.id,
                'default_analytic_account_id': self.analytic_account_id.id,
            }
        }
    def action_create_from_harvest(self):
        """
        Open wizard to create sorting line from household harvest.
        Called from household harvest record.
        """
        return {
            'name': _('Create Sorting Line'),
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.sorting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_household_harvest_id': self.household_harvest_id.id,
                'default_harvest_batch_id': self.harvest_batch_id.id,
                'default_product_id': self.product_id.id,
                'default_initial_weight_kg': self.household_harvest_id.total_quantity if self.household_harvest_id else 0.0,
                'default_analytic_account_id': self.analytic_account_id.id,
            }
        }
    # Alternative: Batch action for multiple lines
    def action_batch_sort_wizard(self):
        """
        Open wizard for batch sorting multiple lines.
        """
        if len(self) > 1:
            # For multiple records, open a different view or handle differently
            return {
                'name': _('Batch Sort Harvest'),
                'type': 'ir.actions.act_window',
                'res_model': 'harvest.sorting.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_harvest_batch_id': self.mapped('harvest_batch_id')[0].id if self.mapped(
                        'harvest_batch_id') else False,
                    'sorting_line_ids': self.ids,
                }
            }
        else:
            return self.action_open_wizard()
class HarvestSortingWizard(models.TransientModel):
    _name = 'harvest.sorting.wizard'
    _description = 'Harvest Sorting Wizard'

    sorting_line_id = fields.Many2one('harvest.sorting.line', string='Sorting Line')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    # Split quantities by grade
    grade_a_qty = fields.Float(string='Grade A Quantity',
                               digits='Product Unit of Measure')
    grade_b_qty = fields.Float(string='Grade B Quantity',
                               digits='Product Unit of Measure')
    grade_c_qty = fields.Float(string='Grade C Quantity',
                               digits='Product Unit of Measure')
    rejected_qty = fields.Float(string='Rejected Quantity',
                                digits='Product Unit of Measure')
    total_qty = fields.Float(string='Total Quantity', compute='_compute_total_qty')
    quantity = fields.Float(string='Original Quantity')
    # Prices per grade
    grade_a_price = fields.Float(string='Grade A Price', digits='Product Price')
    grade_b_price = fields.Float(string='Grade B Price', digits='Product Price')
    grade_c_price = fields.Float(string='Grade C Price', digits='Product Price')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    notes = fields.Text(string='Notes')
    harvest_batch_id = fields.Many2one('harvest.batch', 'Harvest Batch', required=False)
    household_harvest_id = fields.Many2one('household.harvest', 'Household Harvest')
    quality_grade = fields.Selection([
        ('a', 'Grade A - Premium'),
        ('b', 'Grade B - Standard'),
        ('c', 'Grade C - Commercial'),
        ('rejected', 'Rejected')
    ], string='Quality Grade', required=True, default='b')
    size_category = fields.Selection([
        ('xs', 'Extra Small'),
        ('s', 'Small'),
        ('m', 'Medium'),
        ('l', 'Large'),
        ('xl', 'Extra Large')
    ], string='Size Category', required=True, default='m')
    initial_weight_kg = fields.Float('Initial Weight (kg)', required=True)
    final_weight_kg = fields.Float('Final Weight (kg)', required=True)
    unit_selling_price = fields.Monetary('Unit Selling Price', currency_field='currency_id', required=True)
    unit_cost = fields.Monetary('Unit Cost', currency_field='currency_id', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    @api.depends('grade_a_qty', 'grade_b_qty', 'grade_c_qty', 'rejected_qty')
    def _compute_total_qty(self):
        for wizard in self:
            wizard.total_qty = (wizard.grade_a_qty + wizard.grade_b_qty +
                                wizard.grade_c_qty + wizard.rejected_qty)
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            # Set default prices based on product
            self.grade_a_price = self.product_id.list_price
            self.grade_b_price = self.product_id.list_price * 0.8
            self.grade_c_price = self.product_id.list_price * 0.6
    def action_process_sorting(self):
        self.ensure_one()
        # Validate total quantity
        if self.total_qty != self.quantity:
            raise UserError(_(
                'Total sorted quantity (%.2f) must equal original quantity (%.2f).'
            ) % (self.total_qty, self.quantity))
        sorting_lines = []
        # Create line for Grade A
        if self.grade_a_qty > 0:
            sorting_lines.append(self._create_sorting_line('a', self.grade_a_qty,
                                                           self.grade_a_price))

        # Create line for Grade B
        if self.grade_b_qty > 0:
            sorting_lines.append(self._create_sorting_line('b', self.grade_b_qty,
                                                           self.grade_b_price))
        # Create line for Grade C
        if self.grade_c_qty > 0:
            sorting_lines.append(self._create_sorting_line('c', self.grade_c_qty,
                                                           self.grade_c_price))
        # Create line for Rejected
        if self.rejected_qty > 0:
            sorting_lines.append(self._create_sorting_line('rejected', self.rejected_qty, 0))

        # Update original line state if exists
        if self.sorting_line_id:
            self.sorting_line_id.state = 'sorted'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sorted Lines'),
            'res_model': 'harvest.sorting.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', sorting_lines)],
            'context': {'create': False}
        }
    def _create_sorting_line(self, grade, quantity, price):
        values = {
            'harvest_batch_id': self.sorting_line_id.harvest_batch_id.id if self.sorting_line_id else False,
            'product_id': self.product_id.id,
            'quantity': quantity,
            'uom_id': self.uom_id.id,
            'grade': grade,
            'price_unit': price,
            'state': 'confirmed',
            'notes': self.notes,
        }
        if self.sorting_line_id:
            values.update({
                'analytic_account_id': self.sorting_line_id.analytic_account_id.id,
                'project_id': self.sorting_line_id.project_id.id,
            })

        line = self.env['harvest.sorting.line'].create(values)
        return line.id
    def action_quick_sort(self):
        """Quick sort with automatic distribution"""
        self.ensure_one()
        # Auto distribute: 60% A, 25% B, 10% C, 5% Rejected
        self.grade_a_qty = self.quantity * 0.60
        self.grade_b_qty = self.quantity * 0.25
        self.grade_c_qty = self.quantity * 0.10
        self.rejected_qty = self.quantity * 0.05

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.sorting.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
    @api.onchange('household_harvest_id')
    def _onchange_household_harvest(self):
        if self.household_harvest_id:
            self.initial_weight_kg = self.household_harvest_id.total_quantity
    def action_create_sorting_line(self):
        """Create sorting line from wizard"""
        self.ensure_one()
        sorting_line_vals = {
            'household_harvest_id': self.household_harvest_id.id,
            'harvest_batch_id': self.harvest_batch_id.id,
            'warehouse_code_id': self.warehouse_code_id.id,
            'material_classification_id': self.material_classification_id.id,
            'color_classification_id': self.color_classification_id.id,
            'material_number_id': self.material_number_id.id,
            'quality_grade': self.quality_grade,
            'size_category': self.size_category,
            'initial_weight_kg': self.initial_weight_kg,
            'final_weight_kg': self.final_weight_kg,
            'unit_selling_price': self.unit_selling_price,
            'unit_cost': self.unit_cost,
            'analytic_account_id': self.analytic_account_id.id,
            'notes': self.notes,
        }

        sorting_line = self.env['harvest.sorting.line'].create(sorting_line_vals)
        sorting_line.action_confirm_sorting()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sorting Line'),
            'res_model': 'harvest.sorting.line',
            'res_id': sorting_line.id,
            'view_mode': 'form',
            'target': 'current'
        }
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    # Harvest Integration Fields
    harvest_batch_id = fields.Many2one(
        'harvest.batch', 'Harvest Batch',
        index=True, ondelete='cascade',
        help="Related harvest batch operation"
    )
    harvest_stage = fields.Selection([
        ('collection', 'Collection'),
        ('sorting', 'Sorting'),
        ('completed', 'Completed'),
    ], string='Harvest Stage',
        help="Stage in the harvest workflow")
    # Analytic Integration
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account',
        compute='_compute_analytic_account', store=True,
        help="Automatically determined analytic account"
    )

    @api.depends('harvest_batch_id.project_id.analytic_account_id',
                 'move_ids.analytic_account_id')  # Changed from move_lines to move_ids
    def _compute_analytic_account(self):
        for record in self:
            # Priority 1: Analytic account from project
            if record.harvest_batch_id and record.harvest_batch_id.project_id.analytic_account_id:
                record.analytic_account_id = record.harvest_batch_id.project_id.analytic_account_id.id
            # Priority 2: Analytic account from first move line
            elif record.move_ids and record.move_ids[:1].analytic_account_id:  # Changed here
                record.analytic_account_id = record.move_ids[:1].analytic_account_id.id
            else:
                record.analytic_account_id = False

    def action_validate_harvest(self):
        """Harvest-specific validation with accounting"""
        for record in self:
            # Standard validation
            res = record.button_validate()

            # Create harvest accounting entries
            record._create_harvest_account_entries()

            # Post quality checks
            record._create_quality_checks()

            return res

    def _create_harvest_account_entries(self):
        """Create specialized accounting entries for harvest moves"""
        # This method would be implemented based on harvest stage and movement type
        pass

    def _create_quality_checks(self):
        """Auto-create quality checks based on harvest stage"""
        if self.harvest_stage == 'completed':
            # Create quality checks for finished products
            pass
class StockMove(models.Model):
    _inherit = 'stock.move'

    # Harvest Integration Fields
    household_harvest_id = fields.Many2one(
        'household.harvest', 'Household Harvest',
        index=True,
        help="Related household contribution"
    )
    sorting_line_id = fields.Many2one(
        'harvest.sorting.line', 'Sorting Line',
        index=True, ondelete='set null',
        help="Related sorting operation"
    )
    # Analytic Integration
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account',
        help="Analytic account for cost tracking"
    )

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
        """Override to add harvest-specific accounting logic"""
        lines = super()._create_account_move_line(credit_account_id, debit_account_id, journal_id)

        # Add analytic distribution for harvest operations
        for line in lines:
            if self.sorting_line_id and self.sorting_line_id.analytic_account_id:
                line[2]['analytic_distribution'] = {str(self.sorting_line_id.analytic_account_id.id): 100}
            elif self.household_harvest_id and self.household_harvest_id.farmer_analytic_account_id:
                line[2]['analytic_distribution'] = {str(self.household_harvest_id.farmer_analytic_account_id.id): 100}
            elif self.analytic_account_id:
                line[2]['analytic_distribution'] = {str(self.analytic_account_id.id): 100}

        return lines
class AccountMove(models.Model):
    _inherit = 'account.move'

    # Harvest Integration Fields
    harvest_batch_id = fields.Many2one(
        'harvest.batch', 'Harvest Batch',
        index=True, ondelete='set null',
        help="Related harvest batch operation"
    )
    sorting_line_id = fields.Many2one(
        'harvest.sorting.line', 'Sorting Line',
        index=True, ondelete='set null',
        help="Related sorting operation"
    )

    # Harvest-specific State
    harvest_state = fields.Selection([
        ('draft', 'Draft'),
        ('harvest_posted', 'Posted'),
        ('harvest_reconciled', 'Reconciled')
    ], string='Harvest Accounting State', default='draft')

    def action_post_harvest(self):
        """Harvest-specific posting with additional validation"""
        self.ensure_one()
        # Additional validation for harvest operations
        if self.harvest_batch_id and self.harvest_batch_id.state != 'approved':
            raise UserError(_("Cannot post accounting for unapproved harvest batches"))

        self.action_post()
        self.harvest_state = 'harvest_posted'

    def action_harvest_reconcile(self):
        """Special reconciliation for harvest operations"""
        self.ensure_one()
        # Implementation would handle farm-specific reconciliation
        self.harvest_state = 'harvest_reconciled'
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Full Harvest Integration
    harvest_batch_id = fields.Many2one(
        'harvest.batch', 'Harvest Batch',
        index=True, ondelete='set null',
        help="Related harvest batch operation"
    )
    sorting_line_id = fields.Many2one(
        'harvest.sorting.line', 'Sorting Line',
        index=True, ondelete='set null',
        help="Related sorting operation"
    )


    # Farm-specific Fields
    farm_id = fields.Many2one(
        'agricultural.farm', 'Farm',
        compute='_compute_farm', store=True,
        help="Farm associated with this transaction"
    )
    harvest_date = fields.Date(
        'Harvest Date', compute='_compute_harvest_date', store=True,
        help="Date of harvest operation"
    )
    @api.depends('harvest_batch_id', 'sorting_line_id', 'household_harvest_id')
    def _compute_farm(self):
        for record in self:
            if record.harvest_batch_id and record.harvest_batch_id.schedule_id.farm_id:
                record.farm_id = record.harvest_batch_id.schedule_id.farm_id.id
            elif record.sorting_line_id and record.sorting_line_id.harvest_batch_id.schedule_id.farm_id:
                record.farm_id = record.sorting_line_id.harvest_batch_id.schedule_id.farm_id.id
            elif record.household_harvest_id and record.household_harvest_id.harvest_batch_id.schedule_id.farm_id:
                record.farm_id = record.household_harvest_id.harvest_batch_id.schedule_id.farm_id.id
            else:
                record.farm_id = False
    @api.depends('harvest_batch_id', 'sorting_line_id', 'household_harvest_id')
    def _compute_harvest_date(self):
        for record in self:
            if record.harvest_batch_id:
                record.harvest_date = record.harvest_batch_id.harvest_date
            elif record.sorting_line_id:
                record.harvest_date = record.sorting_line_id.date
            elif record.household_harvest_id:
                record.harvest_date = record.household_harvest_id.harvest_date
            else:
                record.harvest_date = False
class AgriculturalFarm(models.Model):
    _inherit = 'agricultural.farm'

    @api.onchange('location_id')
    def _onchange_location_id(self):
        """Set analytic account when location changes"""
        if self.location_id:
            # Try to find or create analytic account for this location
            if not self.analytic_account_id:
                analytic = self.env['account.analytic.account'].search([
                    ('name', '=', self.name),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)

                if not analytic:
                    # Create analytic account for farm
                    analytic = self.env['account.analytic.account'].create({
                        'name': f"{self.name} - Farm",
                        'code': self.code or self.name[:10],
                        'company_id': self.env.company.id,
                        'plan_id': self.env['account.analytic.plan'].search([], limit=1).id,
                    })

                self.analytic_account_id = analytic
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Harvest Accounting Accounts
    wip_account = fields.Many2one('account.account',
                                  related='company_id.wip_account',
                                  string='Work in Progress Account',
                                  readonly=False,
                                  domain=[('deprecated', '=', False)])

    waste_expense_account = fields.Many2one('account.account',
                                            related='company_id.waste_expense_account',
                                            string='Waste Expense Account',
                                            readonly=False,
                                            domain=[('deprecated', '=', False)])

    finished_goods_account = fields.Many2one('account.account',
                                             related='company_id.finished_goods_account',
                                             string='Finished Goods Account',
                                             readonly=False,
                                             domain=[('deprecated', '=', False)])
class ResCompany(models.Model):
    _inherit = 'res.company'

    wip_account = fields.Many2one('account.account',
                                  string='Work in Progress Account',
                                  domain=[('deprecated', '=', False)])

    waste_expense_account = fields.Many2one('account.account',
                                            string='Waste Expense Account',
                                            domain=[('deprecated', '=', False)])

    finished_goods_account = fields.Many2one('account.account',
                                             string='Finished Goods Account',
                                             domain=[('deprecated', '=', False)])
class HarvestBatchRejectWizard(models.TransientModel):
    _name = 'harvest.batch.reject.wizard'
    _description = 'Harvest Batch Rejection Wizard'

    batch_id = fields.Many2one('harvest.batch', 'Batch', required=True)
    rejection_reason = fields.Text('Rejection Reason', required=True)

    def action_confirm_rejection(self):
        """Confirm rejection with reason"""
        self.ensure_one()
        self.batch_id._perform_rejection(self.rejection_reason)
        return {'type': 'ir.actions.act_window_close'}





