from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)

class TemplateWizard(models.TransientModel):
    _name = 'request.template.wizard'
    _description = 'Select Production Request Templates'

    request_id = fields.Many2one('agricultural.production.request', 'Production Request', required=True)
    template_ids = fields.Many2many(
        'production.request.template',
        string='Select Templates',
        domain=[('active', '=', True)]
    )
    merge_mode = fields.Selection([
        ('replace', 'Replace Existing Lines'),
        ('append', 'Add to Existing Lines')
    ], string='Mode', default='append', required=True)

    # Show current request info
    current_line_count = fields.Integer(
        'Current Lines',
        related='request_id.line_count',
        readonly=True
    )
    farm_id = fields.Many2one(
        'agricultural.farm',
        related='request_id.farm_id',
        readonly=True
    )

    @api.onchange('template_ids')
    def _onchange_template_ids(self):
        """Show preview of what will be added"""
        if self.template_ids:
            total_lines = sum(self.template_ids.mapped('line_count'))
            total_cost = sum(self.template_ids.mapped('total_estimated_cost'))
            return {
                'warning': {
                    'title': _('Template Preview'),
                    'message': _('This will add %d lines with estimated cost of %.2f')
                }
            }
    def action_apply_templates(self):
        """Apply selected templates to production request"""
        if not self.template_ids:
            raise ValidationError(_('Please select at least one template.'))

        # Count lines before
        lines_before = len(self.request_id.line_ids)

        # Clear existing lines if replace mode
        if self.merge_mode == 'replace':
            self.request_id.line_ids.unlink()

        # Get current max sequence
        max_sequence = 0
        if self.request_id.line_ids:
            max_sequence = max(self.request_id.line_ids.mapped('sequence'))

        # Apply templates and track usage
        lines_added = 0
        for template in self.template_ids:
            # Increment usage count
            template.increment_usage()

            for template_line in template.template_line_ids:
                max_sequence += 10
                self.request_id.line_ids.create({
                    'request_id': self.request_id.id,
                    'sequence': max_sequence,
                    'product_id': template_line.product_id.id,
                    'description': template_line.description,
                    'quantity': template_line.quantity,
                    'uom_id': template_line.uom_id.id,
                    'cost_center_type': template_line.cost_center_type,
                    'unit_price': template_line.unit_price,
                    'expense_account': template_line.expense_account.id,
                    'provision_account': template_line.provision_account.id,
                    'warehouse_notes': template_line.notes,
                    'template_id': template.id,
                })
                lines_added += 1

        # Return to the form with success message
        return {
            'name': _('Production Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.production.request',
            'res_id': self.request_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'form_view_initial_mode': 'edit',
            },
            'params': {
                'message': _('%d templates applied, %d lines added successfully.') % (len(self.template_ids),
                                                                                      lines_added),
                'type': 'success',
            }
        }
    def action_preview_templates(self):
        """Preview what lines will be added"""
        if not self.template_ids:
            raise ValidationError(_('Please select templates to preview.'))

        # Collect all lines that would be added
        preview_lines = []
        for template in self.template_ids:
            for line in template.template_line_ids:
                preview_lines.append({
                    'template_name': template.name,
                    'product_name': line.product_id.name,
                    'quantity': line.quantity,
                    'uom': line.uom_id.name,
                    'unit_price': line.unit_price,
                    'estimated_cost': line.estimated_cost,
                })

        # Create temporary preview records or show in a report
        return {
            'name': _('Template Preview'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.production.request.template.preview',
            'view_mode': 'list',
            'target': 'new',
            'context': {
                'preview_data': preview_lines,
                'wizard_id': self.id,
            }
        }
