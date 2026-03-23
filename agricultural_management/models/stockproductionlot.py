import logging
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class StockProductionLot(models.Model):
    _inherit = 'stock.lot'

    # ========== AGRICULTURAL FIELDS ==========

    # Currency for monetary fields
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    # Quarantine Management
    quarantine = fields.Boolean(
        string='Quarantine',
        default=False,
        tracking=True,
        copy=False,
        index=True,
        help="If checked, this lot is under quarantine and cannot be used"
    )
    quarantine_reason = fields.Text('Quarantine Reason', tracking=True)
    quarantine_date = fields.Date('Quarantine Date', tracking=True)
    quarantine_release_date = fields.Date('Expected Release Date', tracking=True)

    # Agricultural Relationships
    harvest_schedule_id = fields.Many2one(
        'agricultural.harvest.schedule',
        string='Harvest Schedule',
        ondelete='set null',
        tracking=True,
        index=True,
        help="Harvest schedule that generated this lot"
    )
    farm_id = fields.Many2one(
        'agricultural.farm',
        'Farm',
        compute='_compute_agricultural_fields',
        store=True,
        readonly=True
    )
    project_id = fields.Many2one(
        'agricultural.project',
        'Project',
        compute='_compute_agricultural_fields',
        store=True,
        readonly=True
    )

    # Date Fields
    harvest_date = fields.Date(
        'Harvest Date',
        compute='_compute_agricultural_fields',
        store=True,
        tracking=True
    )
    production_date = fields.Date(
        'Production/Processing Date',
        default=fields.Date.today,
        tracking=True
    )

    # Quality Fields
    quality_grade = fields.Selection([
        ('a', 'Grade A - Premium'),
        ('b', 'Grade B - Standard'),
        ('c', 'Grade C - Economy'),
        ('rejected', 'Rejected'),
    ], string='Quality Grade', default='b', tracking=True)

    quality_score = fields.Float(
        'Quality Score (0-100)',
        digits=(5, 2),
        compute='_compute_quality_score',
        store=True,
        help="Overall quality score based on multiple factors"
    )

    # Growing & Processing
    growing_method = fields.Selection([
        ('soil', 'Soil'),
        ('hydroponic', 'Hydroponic'),
        ('aeroponic', 'Aeroponic'),
        ('aquaponic', 'Aquaponic')
    ], string='Growing Method', tracking=True)

    processing_method = fields.Selection([
        ('fresh', 'Fresh'),
        ('washed', 'Washed'),
        ('cut', 'Cut & Prepared'),
        ('packaged', 'Packaged')
    ], string='Processing Method', default='fresh')

    # Certification & Compliance
    organic_certification = fields.Char('Organic Certification', tracking=True)
    organic_certified = fields.Boolean(
        'Organic Certified',
        compute='_compute_certifications',
        store=True
    )
    food_safety_certification = fields.Selection([
        ('gmp', 'GMP - Good Manufacturing Practice'),
        ('haccp', 'HACCP - Hazard Analysis'),
        ('iso22000', 'ISO 22000 - Food Safety'),
        ('brc', 'BRC - British Retail Consortium'),
        ('sqf', 'SQF - Safe Quality Food')
    ], string='Food Safety Certification', tracking=True)

    pesticide_residue_level = fields.Float(
        'Pesticide Residue (ppm)',
        digits=(5, 4),
        tracking=True,
        help="Parts per million"
    )
    pesticide_compliant = fields.Boolean(
        'Pesticide Compliant',
        compute='_compute_compliance',
        store=True,
        help="Within acceptable pesticide residue limits"
    )
    heavy_metal_tested = fields.Boolean('Heavy Metal Tested', tracking=True)
    microbial_tested = fields.Boolean('Microbial Tested', tracking=True)

    # Cost & Pricing
    unit_cost = fields.Monetary(
        'Unit Cost',
        currency_field='currency_id',
        tracking=True,
        help="Cost per unit of measure"
    )
    total_cost = fields.Monetary(
        'Total Cost',
        compute='_compute_financials',
        store=True,
        currency_field='currency_id'
    )
    unit_price = fields.Monetary(
        'Unit Price',
        currency_field='currency_id',
        tracking=True,
        help="Selling price per unit"
    )
    total_value = fields.Monetary(
        'Total Value',
        compute='_compute_financials',
        store=True,
        currency_field='currency_id'
    )

    # Warehouse (already exists but we might want to compute it)
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Warehouse',
        compute='_compute_agricultural_fields',
        store=True,
        readonly=False
    )

    # ========== COMPUTE METHODS ==========

    @api.depends('harvest_schedule_id', 'harvest_schedule_id.farm_id',
                 'harvest_schedule_id.project_id', 'harvest_schedule_id.scheduled_date',
                 'harvest_schedule_id.warehouse_id')
    def _compute_agricultural_fields(self):
        """Compute fields from harvest schedule"""
        for lot in self:
            if lot.harvest_schedule_id:
                lot.farm_id = lot.harvest_schedule_id.farm_id
                lot.project_id = lot.harvest_schedule_id.project_id
                lot.harvest_date = lot.harvest_schedule_id.scheduled_date
                lot.warehouse_id = lot.harvest_schedule_id.warehouse_id
            else:
                if not lot.farm_id:
                    lot.farm_id = False
                if not lot.project_id:
                    lot.project_id = False
                if not lot.harvest_date:
                    lot.harvest_date = False
                if not lot.warehouse_id:
                    lot.warehouse_id = False

    @api.depends('quality_grade')
    def _compute_quality_score(self):
        """Compute quality score based on grade"""
        grade_scores = {
            'a': 95.0,
            'b': 80.0,
            'c': 65.0,
            'rejected': 0.0
        }
        for lot in self:
            lot.quality_score = grade_scores.get(lot.quality_grade, 80.0)

    @api.depends('organic_certification')
    def _compute_certifications(self):
        """Compute certification status"""
        for lot in self:
            lot.organic_certified = bool(lot.organic_certification)

    @api.depends('pesticide_residue_level')
    def _compute_compliance(self):
        """Compute compliance status"""
        MAX_PESTICIDE_LEVEL = 0.5  # ppm
        for lot in self:
            lot.pesticide_compliant = lot.pesticide_residue_level <= MAX_PESTICIDE_LEVEL if lot.pesticide_residue_level else True

    @api.depends('unit_cost', 'unit_price', 'product_qty')
    def _compute_financials(self):
        """Compute financial totals"""
        for lot in self:
            lot.total_cost = lot.unit_cost * lot.product_qty
            lot.total_value = lot.unit_price * lot.product_qty

    # ========== ACTION METHODS ==========

    def action_quarantine(self):
        """Put lot in quarantine"""
        return {
            'name': _('Quarantine Lot'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot.quarantine.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lot_id': self.id,
            }
        }

    def action_release_quarantine(self):
        """Release lot from quarantine"""
        self.ensure_one()
        self.write({
            'quarantine': False,
            'quarantine_reason': False,
            'quarantine_release_date': False,
        })
        self.message_post(
            body=_("Lot released from quarantine"),
            subject=_("Quarantine Released")
        )
        return True

    def action_open_harvest(self):
        """Open related harvest schedule"""
        self.ensure_one()
        if not self.harvest_schedule_id:
            raise UserError(_("This lot is not linked to any harvest schedule."))

        return {
            'name': _('Harvest Schedule'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.harvest.schedule',
            'view_mode': 'form',
            'res_id': self.harvest_schedule_id.id,
        }

    def action_view_farm(self):
        """Open related farm"""
        self.ensure_one()
        if not self.farm_id:
            raise UserError(_("This lot is not linked to any farm."))

        return {
            'name': _('Farm'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.farm',
            'view_mode': 'form',
            'res_id': self.farm_id.id,
        }

    def action_view_project(self):
        """Open related project"""
        self.ensure_one()
        if not self.project_id:
            raise UserError(_("This lot is not linked to any project."))

        return {
            'name': _('Project'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.project',
            'view_mode': 'form',
            'res_id': self.project_id.id,
        }

    def action_print_certificate(self):
        """Print quality certificate"""
        self.ensure_one()
        return self.env.ref('agricultural_management.report_lot_quality_certificate').report_action(self)

    def action_print_label(self):
        """Print lot label"""
        self.ensure_one()
        return self.env.ref('agricultural_management.report_lot_label').report_action(self)

    def action_generate_traceability_report(self):
        """Generate traceability report"""
        self.ensure_one()
        return self.env.ref('agricultural_management.report_lot_traceability').report_action(self)

    # ========== CRUD OVERRIDES ==========

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to add agricultural data"""
        lots = super(StockProductionLot, self).create(vals_list)

        # Post message for harvest-related lots
        for lot in lots.filtered('harvest_schedule_id'):
            lot.message_post(
                body=_("Lot created from harvest schedule: %s") % lot.harvest_schedule_id.name,
                subject=_("Lot Created")
            )

        return lots

    def write(self, vals):
        """Override write to track quarantine changes"""
        # Track quarantine status
        if 'quarantine' in vals and vals['quarantine']:
            for lot in self:
                if not lot.quarantine:
                    lot.message_post(
                        body=_("Lot put in quarantine. Reason: %s") % vals.get('quarantine_reason', 'Not specified'),
                        subject=_("Quarantine Alert")
                    )

        return super(StockProductionLot, self).write(vals)