# -*- coding: utf-8 -*-
#mahmudamen
#xamltech.com
#Agriculture
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
import logging

_logger = logging.getLogger(__name__)


class StockLotQuarantineWizard(models.TransientModel):
    _name = 'stock.lot.quarantine.wizard'
    _description = 'Quarantine Lot Wizard'

    lot_id = fields.Many2one('stock.lot', string='Lot', required=True, ondelete='cascade')
    reason = fields.Text(string='Reason', required=True)
    release_date = fields.Date(string='Planned Release Date')

    def action_confirm_quarantine(self):
        """Apply quarantine: Set a flag or use a specific location?"""
        self.ensure_one()
        # You can:
        # 1. Move to quarantine location
        # 2. Add a boolean field like `is_quarantined` on stock.lot
        # Example: just log it for now
        self.lot_id.sudo().write({
            'company_id': self.env.company.id,
            'quarantine_reason': self.reason,
            'quarantine_release_date': self.release_date,
            'is_quarantined': True,
        })
        return {'type': 'ir.actions.act_window_close'}
class StockLotQualityTestWizard(models.TransientModel):
    _name = 'stock.lot.quality.test.wizard'
    _description = 'Quality Test for Lot'

    lot_id = fields.Many2one('stock.lot', string='Lot', required=True, ondelete='cascade')
    test_date = fields.Datetime(string='Test Date', default=fields.Datetime.now)
    inspector_id = fields.Many2one('res.users', string='Inspector', default=lambda self: self.env.user)
    quality_grade = fields.Selection([
        ('a', 'Grade A (Premium)'),
        ('b', 'Grade B (Standard)'),
        ('c', 'Grade C (Low)'),
        ('fail', 'Fail'),
    ], string='Quality Grade', required=True)
    pesticide_level = fields.Float(string='Pesticide Residue (ppm)')
    heavy_metal_tested = fields.Boolean(string='Heavy Metal Tested')
    microbial_tested = fields.Boolean(string='Microbial Tested')
    test_results = fields.Html(string='Test Results & Observations')

    def action_confirm_test(self):
        self.ensure_one()
        # Create or update quality test record
        quality_test = self.env['stock.lot.quality.test'].create({
            'lot_id': self.lot_id.id,
            'test_date': self.test_date,
            'inspector_id': self.inspector_id.id,
            'quality_grade': self.quality_grade,
            'pesticide_level': self.pesticide_level,
            'heavy_metal_tested': self.heavy_metal_tested,
            'microbial_tested': self.microbial_tested,
            'test_results': self.test_results,
            'company_id': self.env.company.id,
        })
        # Optionally update lot's current grade
        self.lot_id.quality_grade = self.quality_grade
        return {'type': 'ir.actions.act_window_close'}
class StockLotSplitWizard(models.TransientModel):
    _name = 'stock.lot.split.wizard'
    _description = 'Split Lot Wizard'

    lot_id = fields.Many2one('stock.lot', string='Original Lot', required=True, ondelete='cascade')
    total_quantity = fields.Float(string='Total Quantity', readonly=True)
    num_splits = fields.Integer(string='Number of Splits', default=2, required=True)
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining_quantity')
    split_line_ids = fields.One2many(
        'stock.lot.split.line', 'wizard_id', string='Split Details')
    product_qty = fields.Float(string="product qty")

    @api.onchange('num_splits')
    def _onchange_num_splits(self):
        if self.num_splits > 0:
            existing_lines = self.split_line_ids
            new_lines = [(5, 0, 0)]  # clear
            quantity_per_split = self.total_quantity / self.num_splits
            for i in range(self.num_splits):
                new_lines.append((0, 0, {
                    'sequence': i + 1,
                    'new_lot_name': f"{self.lot_id.name}-SPL{i+1}",
                    'quantity': round(quantity_per_split, 2),
                    'quality_grade': self.lot_id.quality_grade,
                }))
            new_lines.append((0, 0, {
                'sequence': self.num_splits + 1,
                'new_lot_name': False,
                'quantity': 0.0,
                'quality_grade': self.lot_id.quality_grade,
            }))
            self.split_line_ids = new_lines

    @api.depends('split_line_ids.quantity', 'total_quantity')
    def _compute_remaining_quantity(self):
        for wizard in self:
            distributed = sum(line.quantity for line in wizard.split_line_ids)
            wizard.remaining_quantity = wizard.total_quantity - distributed

    def action_split_lot(self):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if float_compare(self.remaining_quantity, 0.0, precision_digits=precision) != 0:
            raise UserError(_("Total split quantities must equal the original quantity."))

        move_lines_to_update = self.env['stock.move.line']
        quants = self.env['stock.quant'].search([('lot_id', '=', self.lot_id.id), ('quantity', '>', 0)])
        total_available = sum(quants.mapped('quantity'))

        distributed = 0.0
        new_lots = self.env['stock.lot']

        for line in self.split_line_ids.filtered(lambda l: l.quantity > 0):
            # Create new lot
            new_lot = self.env['stock.lot'].create({
                'name': line.new_lot_name,
                'product_id': self.lot_id.product_id.id,
                'company_id': self.lot_id.company_id.id,
                'quality_grade': line.quality_grade,
            })
            new_lots |= new_lot

            # Reserve quantity from existing stock
            qty_to_reserve = line.quantity
            remaining = qty_to_reserve
            for quant in quants:
                if remaining <= 0:
                    break
                take = min(remaining, quant.quantity)
                # We'll update move lines linked to this lot
                move_lines = self.env['stock.move.line'].search([
                    ('lot_id', '=', self.lot_id.id),
                    ('qty_done', '>', 0),
                    ('state', 'not in', ['done', 'cancel']),
                ])
                for ml in move_lines:
                    if remaining <= 0:
                        break
                    deduct = min(ml.qty_done, remaining)
                    ml.qty_done -= deduct
                    remaining -= deduct

                    # Create a new move line for the new lot
                    new_ml_vals = ml.copy_data()[0]
                    new_ml_vals.update({
                        'lot_id': new_lot.id,
                        'qty_done': deduct,
                        'reference': f"{ml.reference} (split)",
                    })
                    self.env['stock.move.line'].create(new_ml_vals)

                quant.quantity -= take
                distributed += take

        # Final check
        if float_compare(distributed, total_available, precision_digits=precision) != 0:
            raise UserError(_("Error splitting lot: quantity mismatch."))

        self.lot_id.invalidate_recordset()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Split Completed'),
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('id', 'in', new_lots.ids)],
            'target': 'current',
        }
class StockLotSplitLine(models.TransientModel):
    _name = 'stock.lot.split.line'
    _description = 'Split Lot Line'
    _order = 'sequence'

    wizard_id = fields.Many2one('stock.lot.split.wizard', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence')
    new_lot_name = fields.Char(string='New Lot Name', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    quality_grade = fields.Selection([
        ('a', 'Grade A'), ('b', 'Grade B'), ('c', 'Grade C'), ('fail', 'Fail')
    ], string='Quality Grade')
class StockLotMergeWizard(models.TransientModel):
    _name = 'stock.lot.merge.wizard'
    _description = 'Merge Lots Wizard'

    product_id = fields.Many2one('product.product', string='Product', compute='_compute_product')
    new_lot_name = fields.Char(string='New Merged Lot Name', required=True)
    merge_strategy = fields.Selection([
        ('average', 'Average Quality'),
        ('worst', 'Use Worst Grade'),
        ('best', 'Use Best Grade'),
        ('manual', 'Manually Assign Grade')
    ], string='Merge Strategy', required=True, default='average')
    manual_grade = fields.Selection([
        ('a', 'Grade A'), ('b', 'Grade B'), ('c', 'Grade C'), ('fail', 'Fail')
    ], string='Manual Grade')
    lot_ids = fields.Many2many('stock.lot', string='Lots to Merge', domain="[('product_id', '=', product_id)]")
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_totals', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom', store=True)
    resulting_grade = fields.Selection([
        ('a', 'Grade A'), ('b', 'Grade B'), ('c', 'Grade C'), ('fail', 'Fail')
    ], string='Resulting Grade', compute='_compute_resulting_grade', readonly=True)

    @api.depends('lot_ids.product_uom_id')
    def _compute_uom(self):
        for wizard in self:
            wizard.uom_id = wizard.lot_ids[:1].product_uom_id

    @api.depends('lot_ids')
    def _compute_product(self):
        for wizard in self:
            wizard.product_id = wizard.lot_ids[:1].product_id if wizard.lot_ids else False

    @api.depends('lot_ids')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_quantity = sum(lot.product_qty for lot in wizard.lot_ids)

    @api.depends('merge_strategy', 'manual_grade', 'lot_ids.quality_grade')
    def _compute_resulting_grade(self):
        grade_rank = {'a': 3, 'b': 2, 'c': 1, 'fail': 0}
        rank_to_grade = {v: k for k, v in grade_rank.items()}
        for wizard in self:
            if not wizard.lot_ids:
                wizard.resulting_grade = False
                continue
            grades = [grade_rank.get(lot.quality_grade, 0) for lot in wizard.lot_ids]
            if wizard.merge_strategy == 'worst':
                rank = min(grades)
            elif wizard.merge_strategy == 'best':
                rank = max(grades)
            elif wizard.merge_strategy == 'manual':
                wizard.resulting_grade = wizard.manual_grade
                continue
            else:  # average
                avg = sum(grades) / len(grades)
                rank = round(avg)
            wizard.resulting_grade = rank_to_grade.get(rank, 'c')

    def action_merge_lots(self):
        self.ensure_one()
        if len(self.lot_ids) < 2:
            raise UserError(_("You must select at least two lots to merge."))

        # Create new lot
        new_lot = self.env['stock.lot'].create({
            'name': self.new_lot_name,
            'product_id': self.product_id.id,
            'company_id': self.env.company.id,
            'quality_grade': self.resulting_grade,
        })

        # Transfer all stock from old lots to new lot
        quants = self.env['stock.quant'].search([('lot_id', 'in', self.lot_ids.ids), ('quantity', '>', 0)])
        for quant in quants:
            self.env['stock.quant'].create({
                'product_id': quant.product_id.id,
                'location_id': quant.location_id.id,
                'lot_id': new_lot.id,
                'quantity': quant.quantity,
                'reserved_quantity': quant.reserved_quantity,
                'company_id': quant.company_id.id,
            })
            # Zero out original
            quant.quantity = 0

        # Optionally archive old lots
        self.lot_ids.write({'active': False})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Merged Lot'),
            'res_model': 'stock.lot',
            'res_id': new_lot.id,
            'view_mode': 'form',
            'target': 'current',
        }
class StockLotTraceabilityWizard(models.TransientModel):
    _name = 'stock.lot.traceability.wizard'
    _description = 'Generate Lot Traceability Report'

    lot_id = fields.Many2one('stock.lot', string='Lot', required=True)
    include_movements = fields.Boolean(string='Include Stock Movements', default=True)
    include_quality = fields.Boolean(string='Include Quality Tests')
    include_certifications = fields.Boolean(string='Include Certifications')
    include_financials = fields.Boolean(string='Include Financial Info')
    report_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('html', 'Web Report'),
    ], string='Report Format', default='html')

    def action_generate_report(self):
        self.ensure_one()
        # This would normally open a report
        data = {
            'lot_id': self.lot_id.id,
            'options': self.read()[0],
        }
        return self._show_report(report_name='stock_lot_operations.report_lot_traceability', report_type='qweb-html', data=data)

    def action_export_pdf(self):
        self.ensure_one()
        data = {
            'lot_id': self.lot_id.id,
            'options': self.read()[0],
        }
        return self._show_report(report_name='stock_lot_operations.report_lot_traceability_pdf', report_type='qweb-pdf', data=data)

    def _show_report(self, report_name, report_type, data):
        return {
            'type': 'ir.actions.report',
            'report_name': report_name,
            'report_type': report_type,
            'data': data,
            'context': {'active_model': 'stock.lot.traceability.wizard'},
        }
class StockLotQualityTest(models.Model):
    _name = 'stock.lot.quality.test'
    _description = 'Lot Quality Test'
    _order = 'test_date desc'

    lot_id = fields.Many2one('stock.lot', string='Lot', required=True, ondelete='cascade')
    test_date = fields.Datetime(string='Test Date')
    inspector_id = fields.Many2one('res.users', string='Inspector')
    quality_grade = fields.Selection([
        ('a', 'Grade A'), ('b', 'Grade B'), ('c', 'Grade C'), ('fail', 'Fail')
    ], string='Grade')
    pesticide_level = fields.Float(string='Pesticide (ppm)')
    heavy_metal_tested = fields.Boolean(string='Heavy Metals')
    microbial_tested = fields.Boolean(string='Microbial')
    test_results = fields.Html(string='Details')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
