from email.policy import default

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AgriculturalHarvestSchedule(models.Model):
    _name = 'agricultural.harvest.schedule'
    _description = 'Harvest Schedule Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, id desc'
    _rec_name = 'display_name'
    _check_company_auto = True

    # ========== BASIC INFORMATION ==========
    name = fields.Char(
        'Schedule Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda x: _('New'),
        tracking=True
    )
    display_name = fields.Char(
        'Schedule Reference',
        required=True,
        copy=False,
        compute='_compute_display_name',
        readonly=True,
        index=True,
        tracking=True
    )
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        index=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    project_id = fields.Many2one(
        'agricultural.project',
        'Agricultural Project',
        tracking=True,
    )
    # ========== CROP & LOCATION ==========
    crop_id = fields.Many2one('product.product','Finished Crop', required=True, tracking=True)
    farm_id = fields.Many2one('agricultural.farm','Farm',store=True,readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse','Main Warehouse',related="farm_id.warehouse_id",required=True)
    source_location_id = fields.Many2one('stock.location','Harvest Location', related="farm_id.location_id", required=True, help="Location where crops are being harvested from")
    destination_location_id = fields.Many2one('stock.location','Production Interface',required=True,domain="[('usage','=','production')]", help="Location where harvested products will be stored")
    scrap_location_id = fields.Many2one(
        'stock.location',
        'Transit Location',
        help="Location for rejected/damaged products"
    )
    schedule_type = fields.Selection([
        ('manual', 'Manual Schedule'),
        ('auto_planting', 'Auto from Planting'),
        ('auto_growth', 'Auto from Growth Cycle'),
        ('recurring', 'Recurring Schedule'),
        ('seasonal', 'Seasonal')
    ],
        default='manual',
        required=False,
        tracking=True
    )
    scheduled_date = fields.Date(
        'Schedule Date',
        required=False,
        tracking=True,
        index=True
    )
    scheduled_time = fields.Float('Schedule Time', help="Time of day for harvest (24h format)")
    actual_start_date = fields.Datetime('Actual Start Date', readonly=True, tracking=True)
    actual_end_date = fields.Datetime('Actual End Date', readonly=True, tracking=True)
    duration_hours = fields.Float(
        'Duration (Hours)',
        store=True
    )
    auto_schedule = fields.Boolean('Auto Schedule', default=False)
    planting_date = fields.Date('Related Planting Date')
    growth_cycle_days = fields.Integer('Growth Cycle (Days)', default=90)
    recurring_interval = fields.Integer('Recurring Interval (days)', default=30)
    next_schedule_date = fields.Date('Next Schedule Date')
    estimated_quantity = fields.Float(
        'Expected Quantity',
        required=False,
        digits='Product Unit of Measure',
        tracking=True
    )
    actual_quantity = fields.Float(
        'Actual Quantity',
        digits='Product Unit of Measure',
        tracking=True
    )
    grade_a_quantity = fields.Float(
        'Grade A Quantity',
        digits='Product Unit of Measure'
    )
    grade_b_quantity = fields.Float(
        'Grade B Quantity',
        digits='Product Unit of Measure'
    )
    grade_c_quantity = fields.Float(
        'Grade C Quantity',
        digits='Product Unit of Measure'
    )
    rejected_quantity = fields.Float(
        'Rejected Quantity',
        digits='Product Unit of Measure'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        'Unit of Measure',related="crop_id.uom_id",
    )
    total_graded_quantity = fields.Float(
        'Total Grade',
        compute='_compute_total_graded_quantity',
        store=True,
        digits='Product Unit of Measure'
    )
    quantity_difference = fields.Float(
        'Difference in Quantities',
        compute='_compute_quantity_difference',
        store=True,
        digits='Product Unit of Measure'
    )
    yield_efficiency = fields.Float(
        'Efficiency Production (%)',
        compute='_compute_yield_efficiency',
        store=True,
        group_operator='avg'
    )
    waste_percentage = fields.Float(
        'Percentage Damaged from Crop',
        compute='_compute_waste_percentage',
        store=True
    )
    quality_grade = fields.Selection([
        ('a', 'Grade A - Premium'),
        ('b', 'Grade B - Standard'),
        ('c', 'Grade C - Economy'),
        ('mixed', 'Mixed Grades'),
        ('rejected', 'Rejected')
    ],
        string='Overall Quality Grade',
        tracking=True
    )
    quality_score = fields.Float('Quality Score (0-100)', tracking=True)
    quality_notes = fields.Text('Quality Notes')
    generate_lots = fields.Boolean(
        'Generate Batch from Harvest',
        default=True,
        help="Automatically generate lot numbers for harvested products"
    )
    lot_prefix = fields.Char('Lot Prefix', default='HARV')
    picking_ids = fields.One2many(
        'stock.picking',
        'harvest_schedule_id',
        'Stock Pickings',
        readonly=True
    )
    picking_count = fields.Integer('Picking Count')
    move_ids = fields.One2many(
        'stock.move',
        'harvest_schedule_id',
        'Stock Moves',
        readonly=True
    )
    move_count = fields.Integer('Move Count')
    picking_type_id = fields.Many2one('stock.picking.type','Operation Type',related="farm_id.picking_type_internal_id")
    account_move_ids = fields.One2many('account.move','harvest_schedule_id','Journal Entries',readonly=True)
    account_move_count = fields.Integer('Journal Entry Count')
    harvest_account_id = fields.Many2one(
        'account.account',
        'Harvest Expense Account',
        help="Account for harvest-related expenses"
    )
    inventory_account_id = fields.Many2one('account.account','Inventory Account',domain="[('deprecated', '=', False)]",help="Account for harvested inventory value")
    worker_count = fields.Integer('Worker Count')
    supervisor_id = fields.Many2one('hr.employee', 'Supervisor', tracking=True)
    planned_work_hours = fields.Float('Planned Work Hours')
    actual_work_hours = fields.Float('Actual Work Hours')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('ready', 'Ready for Harvest'),
        ('in_progress', 'In Progress'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
        ('cancelled', 'Cancelled')
    ],
        default='draft',
        tracking=True,
        copy=False
    )
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Very High')
    ],
        default='1',
        tracking=True
    )
    delay_reason = fields.Text('Delay Reason')
    cancellation_reason = fields.Text('Cancellation Reason')
    weather_condition = fields.Selection([
        ('sunny', 'Sunny'),
        ('cloudy', 'Cloudy'),
        ('rainy', 'Rainy'),
        ('windy', 'Windy'),
        ('stormy', 'Stormy')
    ],
        string='Weather Condition'
    )
    temperature = fields.Float('Temperature (°C)')
    humidity = fields.Float('Humidity (%)')
    weather_suitable = fields.Boolean('Weather Suitable', default=True)
    weather_notes = fields.Text('Weather Notes')
    notes = fields.Text('Harvest Notes')
    special_instructions = fields.Text('Special Instructions')
    harvest_method = fields.Text('Harvest Method')
    post_harvest_handling = fields.Text('Post-Harvest Handling Instructions')
    lot_id = fields.Many2one('stock.lot')
    harvest_batch_ids = fields.One2many(
        'harvest.batch', 'schedule_id', string='Harvest Batches',
        help='Breakdown of harvest operations into manageable batches'
    )
    sorting_line_ids = fields.One2many(
        'harvest.sorting.line', 'schedule_id', string='Sorting Lines',
        help='Detailed classification and sorting results'
    )
    total_harvested_qty = fields.Float(
        'Total Harvested', compute='_compute_harvest_totals', store=True,
        help='Total raw harvest weight (kg)'
    )
    total_sorted_qty = fields.Float(
        'Total Sorted', compute='_compute_harvest_totals', store=True,
        help='Total sorted weight after processing (kg)'
    )
    total_waste_qty = fields.Float(
        'Total Waste', compute='_compute_harvest_totals', store=True,
        help='Weight lost during processing (kg)'
    )
    sorting_completion = fields.Float(
        'Sorting Completion %', compute='_compute_harvest_totals', store=True,
        help='Progress of sorting operations'
    )
    # Add field to track generated lots
    lot_ids = fields.One2many(
        'stock.lot',
        'harvest_schedule_id',
        string='Generated Lots',
        readonly=True
    )
    lot_count = fields.Integer(
        string='Lot Count',
        compute='_compute_lot_count'
    )

    def action_view_quantity_breakdown(self):
        """Show quantity breakdown in a wizard"""
        self.ensure_one()
        return {
            'name': _('Quantity Breakdown'),
            'type': 'ir.actions.act_window',
            'res_model': 'harvest.quantity.breakdown.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_harvest_id': self.id,
                'default_estimated_quantity': self.estimated_quantity,
                'default_actual_quantity': self.actual_quantity,
                'default_grade_a_quantity': self.grade_a_quantity,
                'default_grade_b_quantity': self.grade_b_quantity,
                'default_grade_c_quantity': self.grade_c_quantity,
                'default_rejected_quantity': self.rejected_quantity,
            }
        }
    @api.constrains('grade_a_quantity', 'grade_b_quantity', 'grade_c_quantity', 'rejected_quantity', 'actual_quantity')
    def _check_graded_quantities(self):
        """Validate that graded quantities don't exceed actual quantity"""
        for record in self:
            if record.actual_quantity > 0:
                total_graded = (
                        record.grade_a_quantity +
                        record.grade_b_quantity +
                        record.grade_c_quantity +
                        record.rejected_quantity
                )

                if total_graded > record.actual_quantity:
                    raise ValidationError(
                        _("Total graded quantity (%.2f %s) cannot exceed actual harvested quantity (%.2f %s)") % (
                            total_graded,
                            record.uom_id.name,
                            record.actual_quantity,
                            record.uom_id.name
                        )
                    )
    def action_auto_distribute_quantity(self):
        """Auto-distribute estimated quantity to grades based on default percentages"""
        self.ensure_one()

        if not self.estimated_quantity:
            raise UserError(_("Please set estimated quantity first."))

        # Default distribution percentages
        grade_a_pct = 0.30  # 30% Grade A
        grade_b_pct = 0.50  # 50% Grade B
        grade_c_pct = 0.15  # 15% Grade C
        rejected_pct = 0.05  # 5% Rejected

        self.write({
            'grade_a_quantity': self.estimated_quantity * grade_a_pct,
            'grade_b_quantity': self.estimated_quantity * grade_b_pct,
            'grade_c_quantity': self.estimated_quantity * grade_c_pct,
            'rejected_quantity': self.estimated_quantity * rejected_pct,
        })

        self.message_post(
            body=_(
                "Quantities auto-distributed based on standard percentages: A(30%%), B(50%%), C(15%%), Rejected(5%%)")
        )
    @api.depends('grade_a_quantity', 'grade_b_quantity', 'grade_c_quantity', 'rejected_quantity')
    def _compute_total_graded_quantity(self):
        """Compute total graded quantity"""
        for record in self:
            record.total_graded_quantity = (
                    record.grade_a_quantity +
                    record.grade_b_quantity +
                    record.grade_c_quantity +
                    record.rejected_quantity
            )
    @api.depends('actual_quantity', 'total_graded_quantity')
    def _compute_quantity_difference(self):
        """Compute difference between actual and graded quantities"""
        for record in self:
            record.quantity_difference = record.actual_quantity - record.total_graded_quantity
    @api.depends('actual_quantity', 'estimated_quantity')
    def _compute_yield_efficiency(self):
        """Compute yield efficiency percentage"""
        for record in self:
            if record.estimated_quantity > 0:
                record.yield_efficiency = (record.actual_quantity / record.estimated_quantity) * 100
            else:
                record.yield_efficiency = 0.0
    @api.depends('rejected_quantity', 'actual_quantity')
    def _compute_waste_percentage(self):
        """Compute waste percentage"""
        for record in self:
            if record.actual_quantity > 0:
                record.waste_percentage = (record.rejected_quantity / record.actual_quantity) * 100
            else:
                record.waste_percentage = 0.0
    def action_process(self):
        """Process the harvest - create stock and accounting entries"""
        for record in self:
            # Validate graded quantities
            record.write({'state': 'processing'})
            record.message_post(body=_("Processing harvest..."))
            try:
                # REMOVED INCORRECT LOT GENERATION - lots are generated automatically in _create_stock_move_for_grade
                # The following line was incorrect and has been removed:
                # if record.generate_lots:
                #     record._generate_lot_name(self.crop_id)

                # Create stock movements - produce and damaged items
                record._create_harvest_stock_movements()

                # Create accounting entries based on farm accounts
                # Uncomment when ready:
                # record._create_harvest_accounting_entries()

                record.message_post(
                    body=_("Processing completed successfully."),
                    subject=_("Harvest Processed")
                )
            except Exception as e:
                _logger.error("Error processing harvest %s: %s", record.name, str(e))
                record.message_post(
                    body=_("Error during processing: %s") % str(e),
                    subject=_("Processing Error")
                )
                raise
    def _create_goods_movements(self):
        """Create stock movements for harvested goods"""
        self.ensure_one()

        moves = self.env['stock.move']

        # Create picking
        picking = self._create_stock_picking()

        if not picking:
            return moves

        # Create moves for each grade - FIXED ORDER OF ARGUMENTS
        if self.grade_a_quantity > 0:
            moves |= self._create_stock_move_for_grade(
                picking,
                'a',  # grade (string)
                self.grade_a_quantity  # quantity (float)
            )

        if self.grade_b_quantity > 0:
            moves |= self._create_stock_move_for_grade(
                picking,
                'b',  # grade (string)
                self.grade_b_quantity  # quantity (float)
            )

        if self.grade_c_quantity > 0:
            moves |= self._create_stock_move_for_grade(
                picking,
                'c',  # grade (string)
                self.grade_c_quantity  # quantity (float)
            )

        # Confirm moves
        if moves:
            moves._action_confirm()
            picking.action_assign()

        return moves
    def _create_stock_move_for_grade(self, picking, grade, quantity):
        """Create stock move for a specific grade

        Args:
            picking: stock.picking record
            grade: str - Quality grade ('a', 'b', 'c', etc.)
            quantity: float - Quantity to move
        """
        self.ensure_one()

        # Validate inputs
        if not isinstance(grade, str):
            raise UserError(_("Grade must be a string (a, b, c, etc.), got %s") % type(grade))

        # Get or create product variant for grade
        product = self._get_product_for_grade(grade)

        # Generate lot if product requires tracking
        lot_id = False
        if product.tracking != 'none':
            lot_id = self._generate_single_lot(product, grade, quantity)

        move_vals = {
            'name': self.name,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'product_uom': product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name,
            'harvest_schedule_id': self.id,
            'state': 'draft',
        }

        move = self.env['stock.move'].create(move_vals)

        # Create move line with lot if tracking is required
        if product.tracking != 'none' and lot_id:
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'quantity': quantity,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.destination_location_id.id,
                'lot_id': lot_id.id,
            })

        return move
    def _generate_single_lot(self, product, grade='b', quantity=0):
        """Generate a unique lot/serial number for the product

        Args:
            product: product.product record
            grade: str - Quality grade ('a', 'b', 'c', etc.)
            quantity: float - Quantity (optional)

        Returns:
            stock.lot record
        """
        self.ensure_one()

        # Validate inputs
        if not product or not isinstance(product, type(self.env['product.product'])):
            raise UserError(_("Invalid product passed to _generate_single_lot"))

        if not isinstance(grade, str):
            raise UserError(_("Grade must be a string, got %s") % type(grade))

        # Generate lot name
        lot_name = self._generate_lot_name(product, grade)

        # Prepare lot values with agricultural data
        lot_vals = {
            'name': lot_name,
            'product_id': product.id,
            'harvest_schedule_id': self.id,
            'quality_grade': grade,
            'growing_method': self.growing_method if hasattr(self, 'growing_method') else False,
            'processing_method': 'fresh',
            'production_date': fields.Date.today(),
            'harvest_date': self.scheduled_date,
            'ref': self.name,  # Reference to harvest schedule
        }

        # Add cost if available
        if hasattr(self, 'unit_cost') and self.unit_cost:
            lot_vals['unit_cost'] = self.unit_cost

        # Create lot
        lot = self.env['stock.lot'].create(lot_vals)

        self.message_post(
            body=_("Lot %s generated for product %s (Grade: %s)") % (
                lot.name,
                product.display_name,
                dict(lot._fields['quality_grade'].selection).get(grade, grade)
            )
        )

        return lot
    def _generate_lot_name(self, product, grade='b'):
        """Generate unique lot name

        Args:
            product: product.product record
            grade: str - Quality grade

        Returns:
            str - Generated lot name
        """
        self.ensure_one()

        # Validate grade is a string
        if not isinstance(grade, str):
            raise UserError(_("Grade must be a string for lot name generation, got %s") % type(grade))

        # Format: LOT-FARM-DATE-GRADE-PRODUCT-SEQ
        farm_code = self.farm_id.code[:3].upper() if self.farm_id and self.farm_id.code else 'FRM'
        date_str = fields.Date.today().strftime('%Y%m%d')
        grade_code = grade.upper()
        product_code = product.default_code[:10] if product.default_code else str(product.id)

        # Get sequence
        sequence = self.env['ir.sequence'].next_by_code('harvest.lot') or '001'

        return f"LOT-{farm_code}-{date_str}-{grade_code}-{product_code}-{sequence}"
    def _get_product_for_grade(self, grade):
        """Get or create product variant for specific grade

        Args:
            grade: str - Quality grade ('a', 'b', 'c', 'rejected')

        Returns:
            product.product record
        """
        self.ensure_one()

        # Validate grade
        if not isinstance(grade, str):
            raise UserError(_("Grade must be a string"))

        if grade not in ['a', 'b', 'c', 'rejected']:
            raise UserError(_("Invalid grade: %s. Must be 'a', 'b', 'c', or 'rejected'") % grade)

        # For now, return the main crop product
        # TODO: Implement product variant creation based on grade
        return self.crop_id
    @api.depends('lot_ids')
    def _compute_lot_count(self):
        for record in self:
            record.lot_count = len(record.lot_ids)
    def _generate_lots_for_grades(self):
        """Generate lots for all quality grades"""
        self.ensure_one()

        lots = self.env['stock.lot']

        # Define grade quantities (you may have these as fields)
        grade_quantities = {
            'a': self.grade_a_quantity if hasattr(self, 'grade_a_quantity') else 0,
            'b': self.grade_b_quantity if hasattr(self, 'grade_b_quantity') else 0,
            'c': self.grade_c_quantity if hasattr(self, 'grade_c_quantity') else 0,
        }

        product = self._get_product_for_grade('b')  # Base product

        for grade, quantity in grade_quantities.items():
            if quantity > 0:
                grade_product = self._get_product_for_grade(grade)
                lot = self._generate_single_lot(grade_product, grade, quantity)
                lots |= lot

        return lots
    def action_view_lots(self):
        """View generated lots"""
        self.ensure_one()
        return {
            'name': _('Generated Lots'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('harvest_schedule_id', '=', self.id)],
            'context': {
                'default_harvest_schedule_id': self.id,
                'default_product_id': self.crop_id.id,
            }
        }
    def _create_harvest_stock_movements(self):
        """Create stock movements for all harvested goods and damaged items"""
        # Create movements for quality produce
        self._create_goods_movements()
        # Create movement for damaged items
        self._create_scrap_movement()
    def _create_scrap_movement(self):
        """Create scrap movement for rejected items"""
        if self.rejected_quantity > 0 and self.scrap_location_id:
            scrap_vals = {
                'product_id': self.crop_id.id,
                'scrap_qty': self.rejected_quantity,
                'uom_id': self.uom_id.id,
                'location_id': self.source_location_id.id,
                'scrap_location_id': self.scrap_location_id.id,
                'origin': self.name,
                'harvest_schedule_id': self.id,
            }
            scrap = self.env['stock.scrap'].create(scrap_vals)
            scrap.action_validate()
    def _create_harvest_accounting_entries(self):
        """Create journal entries for the harvest"""
        # Get farm-specific accounts
        journal = self.env['account.journal'].search([
            ('code', '=', 'HARV'),
        ], limit=1) or self.env.ref('account.expense_journal')

        # Prepare journal item values
        move_lines = [
            # Debit: Inventory Account (Farm's asset account)
            (0, 0, {
                'name': _('Harvested Produce: %s') % self.name,
                'account_id': self.farm_id.asset_account_id.id,
                'debit': self.total_cost,
                'credit': 0,
            }),
            # Credit: Harvest Expense Account (Farm's expense account)
            (0, 0, {
                'name': _('Harvest Expenses: %s') % self.name,
                'account_id': self.farm_id.expense_account_id.id,
                'debit': 0,
                'credit': self.total_cost,
            })
        ]

        # Create account move
        move_vals = {
            'date': fields.Date.today(),
            'ref': self.name,
            'journal_id': journal.id,
            'line_ids': move_lines,
            'harvest_schedule_id': self.id,
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        # Link to harvest schedule
        self.account_move_ids = [(4, move.id)]
    def action_plan_batches(self):
        """Transition to batch planning phase"""
        for record in self:
            record.state = 'batch_planning'
            record.message_post(
                body=_("Batch planning initiated. Please create harvest batches."),
                subject=_("Batch Planning Started")
            )
    def action_start_sorting(self):
        """Transition harvest to sorting stage"""
        for record in self:
            if not record.harvest_batch_ids:
                raise UserError(_("Create harvest batches before starting sorting."))
            record.state = 'sorting'
            record.message_post(
                body=_("Harvest sorting initiated."),
                subject=_("Sorting Started")
            )
    def action_complete_sorting(self):
        """Complete sorting and move to quality check"""
        for record in self:
            if not record.sorting_line_ids:
                raise UserError(_("Sort harvest batches before completing sorting."))

            record.state = 'quality_check'
            record._create_quality_checks()
            record.message_post(
                body=_("Sorting completed. Quality checks initiated."),
                subject=_("Sorting Completed")
            )
    def _compute_harvest_totals(self):
        for record in self:
            harvested = sum(record.harvest_batch_ids.mapped('total_weight'))
            sorted = sum(record.sorting_line_ids.mapped('final_weight_kg'))

            record.update({
                'total_harvested_qty': harvested,
                'total_sorted_qty': sorted,
                'total_waste_qty': harvested - sorted,
                'sorting_completion': (sorted / harvested * 100) if harvested > 0 else 0
            })
    @api.depends('name')
    def _compute_display_name(self):
        """Enhanced display name computation"""
        for record in self:
            if record.name:
                record.display_name = f"{record.name}"
            else:
                record.display_name = "Without Name"
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('agricultural.harvest.schedule') or _('New')
        # Auto-calculate scheduled date from planting
        if vals.get('schedule_type') == 'auto_planting' and vals.get('planting_date') and vals.get('growth_cycle_days'):
            planting_date = fields.Date.from_string(vals['planting_date'])
            vals['scheduled_date'] = planting_date + timedelta(days=vals['growth_cycle_days'])
        harvest = super(AgriculturalHarvestSchedule, self).create(vals)

        # Create recurring schedule if needed
        if harvest.schedule_type == 'recurring' and harvest.state == 'completed':
            harvest._create_next_recurring_schedule()
        return harvest
    def write(self, vals):
        # Track state changes
        if 'state' in vals:
            for record in self:
                old_state = record.state
                new_state = vals['state']
                record.message_post(
                    body=_("State changed from %s to %s") % (
                        dict(record._fields['state'].selection).get(old_state),
                        dict(record._fields['state'].selection).get(new_state)
                    )
                )
        return super(AgriculturalHarvestSchedule, self).write(vals)
    def unlink(self):
        for record in self:
            if record.state not in ('draft', 'cancelled'):
                raise UserError(_("You cannot delete a harvest schedule that is not in draft or cancelled state."))
    def action_confirm(self):
        """Confirm the harvest schedule"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft schedules can be confirmed."))
            # Validate required fields
            if not record.source_location_id:
                raise UserError(_("Please set the harvest location."))
            if not record.destination_location_id:
                raise UserError(_("Please set the destination location."))
            if not record.warehouse_id:
                raise UserError(_("Please set the warehouse."))
            record.write({'state': 'scheduled'})
            # Create activity for supervisor
            if record.supervisor_id and record.supervisor_id.user_id:
                record.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Harvest Scheduled: %s') % record.name,
                    note=_('Harvest scheduled for %s. Estimated quantity: %s %s') % (
                        record.scheduled_date,
                        record.estimated_quantity,
                        record.uom_id.name
                    ),
                    user_id=record.supervisor_id.user_id.id,
                    date_deadline=record.scheduled_date
                )

            record.message_post(
                body=_("Harvest schedule confirmed for %s") % record.scheduled_date,
                subject=_("Harvest Confirmed")
            )
    def action_set_ready(self):
        """Mark harvest as ready to start"""
        for record in self:
            if record.state != 'scheduled':
                raise UserError(_("Only scheduled harvests can be set to ready."))
            record.write({'state': 'ready'})
            record.message_post(body=_("Harvest is ready to start"))
            # Notify workers
    def action_start_harvest(self):
        """Start the harvest process"""
        for record in self:
            if record.state not in ('scheduled', 'ready'):
                raise UserError(_("Only scheduled or ready harvests can be started."))
            record.write({
                'state': 'in_progress',
                'actual_start_date': fields.Datetime.now()
            })
            # Create work orders or timesheets if needed
    def action_complete(self):
        """Complete the harvest"""
        for record in self:
            if record.state != 'processing':
                raise UserError(_("Only processed harvests can be completed."))
            # Validate all stock moves are done
            if any(move.state != 'done' for move in record.move_ids):
                raise UserError(_("All stock moves must be completed before marking harvest as done."))
            record.write({'state': 'completed'})
            record.message_post(
                body=_("Harvest completed successfully. Total quantity: %s %s, Yield efficiency: %.2f%%") % (
                    record.actual_quantity,
                    record.uom_id.name,
                    record.yield_efficiency
                ),
                subject=_("Harvest Completed")
            )

            # Create next recurring schedule
            if record.schedule_type == 'recurring':
                record._create_next_recurring_schedule()

            # Close activities
            record.activity_ids.action_done()

            # Send completion report
            record._send_completion_report()
    def action_delay(self):
        """Mark harvest as delayed"""
        for record in self:
            if record.state not in ('scheduled', 'ready'):
                raise UserError(_("Only scheduled or ready harvests can be delayed."))

            return {
                'name': _('Delay Harvest'),
                'type': 'ir.actions.act_window',
                'res_model': 'agricultural.harvest.delay.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_harvest_id': record.id,
                }
            }
    def action_cancel(self):
        """Cancel the harvest"""
        for record in self:
            if record.state in ('completed', 'cancelled'):
                raise UserError(_("Completed or cancelled harvests cannot be cancelled."))

            # Check for linked stock moves
            if record.move_ids.filtered(lambda m: m.state == 'done'):
                raise UserError(_("Cannot cancel harvest with completed stock moves."))

            return {
                'name': _('Cancel Harvest'),
                'type': 'ir.actions.act_window',
                'res_model': 'agricultural.harvest.cancel.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_harvest_id': record.id,
                }
            }
    def action_reset_to_draft(self):
        """Reset to draft"""
        for record in self:
            if record.state not in ('cancelled', 'scheduled'):
                raise UserError(_("Only cancelled or scheduled harvests can be reset to draft."))

            if record.picking_ids or record.account_move_ids:
                raise UserError(_("Cannot reset harvest with stock pickings or journal entries."))

            record.write({
                'state': 'draft',
                'actual_start_date': False,
                'actual_end_date': False,
                'actual_quantity': 0
            })

            record.message_post(body=_("Harvest reset to draft"))
    def _create_stock_picking(self):
        """Create stock picking and moves for harvested products"""
        self.ensure_one()

        if not self.actual_quantity:
            raise UserError(_("No quantity to transfer."))

        # Get or create picking type
        picking_type = self.picking_type_id or self._get_default_picking_type()

        # Create main picking for good quality products
        picking_vals = {
            'partner_id':self.project_id.partner_id.id,
            'agricultural_project_id': self.project_id.id,
            'picking_type_id': picking_type.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name,
            'harvest_schedule_id': self.id,
            'scheduled_date': fields.Datetime.now(),
            'company_id': self.company_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)
        moves = self.env['stock.move']
        if self:
            moves |= self._create_stock_move_for_grade(
                picking, 'a', self.estimated_quantity
            )


        # Create separate picking for rejected items
        if self.rejected_quantity > 0 and self.scrap_location_id:
            self._create_scrap_picking()

        return picking
    def _create_scrap_picking(self):
        """Create picking for rejected/scrap items"""
        self.ensure_one()

        scrap_vals = {
            'product_id': self.crop_id.id,
            'uom_id': self.uom_id.id,
            'scrap_qty': self.rejected_quantity,
            'location_id': self.source_location_id.id,
            'scrap_location_id': self.scrap_location_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
        }

        scrap = self.env['stock.scrap'].create(scrap_vals)
        scrap.action_validate()

        self.message_post(
            body=_("Scrap order created for rejected quantity: %s %s") % (
                self.rejected_quantity,
                self.uom_id.name
            )
        )

        return scrap
    def _get_default_picking_type(self):
        """Get default internal picking type"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', self.warehouse_id.id),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not picking_type:
            raise UserError(_("No internal picking type found for warehouse %s") % self.warehouse_id.name)

        return picking_type
    def _create_accounting_entries(self):
        """Create journal entries for harvest costs"""
        self.ensure_one()

        if not self.total_cost or self.total_cost <= 0:
            return

        # Get accounts
        harvest_account = self.harvest_account_id or self._get_default_harvest_account()
        inventory_account = self.inventory_account_id or self._get_default_inventory_account()

        if not harvest_account or not inventory_account:
            raise UserError(_("Please configure harvest and inventory accounts."))
        # Get journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not journal:
            raise UserError(_("No general journal found."))

        # Prepare move lines
        line_vals = []

        # Debit: Inventory Account (Asset increase)
        line_vals.append((0, 0, {
            'name': _('Harvest: %s') % self.name,
            'account_id': inventory_account.id,
            'debit': self.total_cost,
            'credit': 0.0,
            'partner_id': False,
            'product_id': self.crop_id.id,
            'quantity': self.estimated_quantity,
            'uom_id': self.uom_id.id,
        }))
        # Credit: Harvest Expense Account
        line_vals.append((0, 0, {
            'name': _('Harvest Cost: %s') % self.name,
            'account_id': harvest_account.id,
            'debit': 0.0,
            'credit': self.total_cost,
            'partner_id': False,
        }))
        # Create account move
        move_vals = {
            'ref': self.name,
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'harvest_schedule_id': self.id,
            'line_ids': line_vals,
            'company_id': self.company_id.id,
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.message_post(
            body=_("Journal entry %s created for harvest cost: %s") % (
                move.name,
                self.total_cost
            )
        )

        return move
    def _get_default_harvest_account(self):
        """Get default harvest expense account"""
        # Try to get from company settings or use a default
        account = self.env['account.account'].search([
            ('code', '=like', '6%'),  # Expense account
            ('deprecated', '=', False),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        return account
    def _get_default_inventory_account(self):
        """Get default inventory account"""
        # Get from product category or company settings
        if self.crop_id.categ_id.property_stock_valuation_account_id:
            return self.crop_id.categ_id.property_stock_valuation_account_id

        account = self.env['account.account'].search([
            ('code', '=like', '1%'),  # Asset account
            ('deprecated', '=', False),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        return account
    def _update_inventory_valuation(self):
        """Update inventory valuation after harvest"""
        self.ensure_one()

        if not self.estimated_quantity or not self.total_cost:
            return

        # Update product standard price if needed
        if self.cost_per_unit > 0:
            # This is a simplified approach
            # In production, you'd use proper inventory valuation methods
            self.crop_id.standard_price = self.cost_per_unit
    def _send_completion_report(self):
        """Send completion report to stakeholders"""
        self.ensure_one()

        # Prepare report data
        report_data = {
            'harvest_name': self.name,
            'crop': self.crop_id.name,
            'scheduled_date': self.scheduled_date,
            'actual_date': self.actual_end_date,
            'estimated_qty': self.estimated_quantity,
            'actual_qty': self.actual_quantity,
            'yield_efficiency': self.yield_efficiency,
            'quality_grade': dict(self._fields['quality_grade'].selection).get(self.quality_grade),
            'total_cost': self.total_cost,
        }

        # Send email using template
        template = self.env.ref('agricultural_management.email_template_harvest_completion', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    def action_print_harvest_report(self):
        """Print harvest completion report"""
        self.ensure_one()
        return self.env.ref('agricultural_management.action_report_harvest_schedule').report_action(self)
    def action_view_stock_pickings(self):
        """View related stock pickings"""
        self.ensure_one()
        action = self.env.ref('stock.action_picking_list_all').read()[0]
        action['domain'] = [('harvest_schedule_id', '=', self.id)]
        action['context'] = {'default_harvest_schedule_id': self.id}
        return action
    def action_view_stock_moves(self):
        """View related stock moves"""
        self.ensure_one()
        action = self.env.ref('stock.stock_move_action').read()[0]
        action['domain'] = [('harvest_schedule_id', '=', self.id)]
        action['context'] = {'default_harvest_schedule_id': self.id}
        return action
    def action_view_account_moves(self):
        """View related journal entries"""
        self.ensure_one()
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('harvest_schedule_id', '=', self.id)]
        action['context'] = {'default_harvest_schedule_id': self.id}
        return action
    def action_view_quality_report(self):
        """View quality report"""
        self.ensure_one()
        return {
            'name': _('Quality Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.harvest.quality.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_harvest_id': self.id}
        }
    @api.model
    def cron_check_due_harvests(self):
        """Cron job to check for due harvests"""
        today = fields.Date.today()
        # Find scheduled harvests that are due
        due_harvests = self.search([
            ('scheduled_date', '<=', today),
            ('state', '=', 'scheduled')
        ])
        for harvest in due_harvests:
            harvest.write({'state': 'ready'})
            # Send notification
            if harvest.supervisor_id and harvest.supervisor_id.user_id:
                harvest.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Harvest Due: %s') % harvest.name,
                    note=_('Harvest %s is due today. Please prepare the team and equipment.') % harvest.name,
                    user_id=harvest.supervisor_id.user_id.id
                )

        _logger.info("Checked due harvests: %s harvests are now ready", len(due_harvests))
    @api.model
    def cron_check_delayed_harvests(self):
        """Check for delayed harvests"""
        today = fields.Date.today()

        delayed_harvests = self.search([
            ('scheduled_date', '<', today),
            ('state', 'in', ['scheduled', 'ready']),
            ('state', '!=', 'delayed')
        ])

        for harvest in delayed_harvests:
            harvest.write({
                'state': 'delayed',
                'priority': '3',  # Very High
            })

            harvest.message_post(
                body=_("Harvest is delayed. Scheduled date was %s") % harvest.scheduled_date,
                subject=_("Harvest Delayed"),
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
    @api.model
    def cron_auto_create_schedules(self):
        """Auto-create harvest schedules based on planting dates"""
        # Find planting records that need harvest schedules
        # This would integrate with your planting module
        pass
    def _get_duration_display(self):
        """Get human-readable duration"""
        self.ensure_one()
        if self.duration_hours:
            hours = int(self.duration_hours)
            minutes = int((self.duration_hours - hours) * 60)
            return _("%s hours %s minutes") % (hours, minutes)
        return _("Not started")
    def get_harvest_summary(self):
        """Get harvest summary for dashboard"""
        self.ensure_one()
        return {
            'name': self.name,
            'crop': self.crop_id.name,
            'state': self.state,
            'scheduled_date': self.scheduled_date,
            'actual_quantity': self.actual_quantity,
            'estimated_quantity': self.estimated_quantity,
            'yield_efficiency': self.yield_efficiency,
            'total_cost': self.total_cost,
        }
    @api.model
    def get_harvest_statistics(self, date_from=None, date_to=None):
        """Get harvest statistics for dashboard"""
        domain = []

        if date_from:
            domain.append(('scheduled_date', '>=', date_from))
        if date_to:
            domain.append(('scheduled_date', '<=', date_to))

        harvests = self.search(domain)

        return {
            'total_harvests': len(harvests),
            'completed': len(harvests.filtered(lambda h: h.state == 'completed')),
            'in_progress': len(harvests.filtered(lambda h: h.state == 'in_progress')),
            'scheduled': len(harvests.filtered(lambda h: h.state == 'scheduled')),
            'total_quantity': sum(harvests.mapped('actual_quantity')),
            'total_cost': sum(harvests.mapped('total_cost')),
            'avg_yield_efficiency': sum(harvests.mapped('yield_efficiency')) / len(harvests) if harvests else 0,
        }
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    harvest_schedule_id = fields.Many2one('agricultural.harvest.schedule', 'Harvest Schedule')
class StockMove(models.Model):
    _inherit = 'stock.move'

    harvest_schedule_id = fields.Many2one('agricultural.harvest.schedule', 'Harvest Schedule')
class AccountMove(models.Model):
    _inherit = 'account.move'

    harvest_schedule_id = fields.Many2one('agricultural.harvest.schedule', 'Harvest Schedule')
class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    harvest_schedule_id = fields.Many2one('agricultural.harvest.schedule', 'Harvest Schedule')
class StockMoveLine(models.Model):
    _inherit = "stock.move.line"


    is_expired = fields.Float('is expired')


