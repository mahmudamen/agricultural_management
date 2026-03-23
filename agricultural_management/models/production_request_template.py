from odoo import fields, models, api, _

class ProductionRequestTemplate(models.Model):
    _name = 'production.request.template'
    _description = 'Production Request Template'
    _order = 'usage_count desc, sequence, name'

    name = fields.Char('Template Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)

    # Template lines
    template_line_ids = fields.One2many(
        'request.template.line',
        'template_id',
        string='Template Lines'
    )

    # Statistics
    line_count = fields.Integer('Lines Count', compute='_compute_line_count')
    total_estimated_cost = fields.Float('Total Estimated Cost', compute='_compute_total_cost')

    # Usage Tracking
    usage_count = fields.Integer('Usage Count', default=0, readonly=True)
    last_used_date = fields.Datetime('Last Used', readonly=True)
    last_used_by = fields.Many2one('res.users', 'Last Used By', readonly=True)

    @api.depends('template_line_ids')
    def _compute_line_count(self):
        for template in self:
            template.line_count = len(template.template_line_ids)

    @api.depends('template_line_ids.estimated_cost')
    def _compute_total_cost(self):
        for template in self:
            template.total_estimated_cost = sum(template.template_line_ids.mapped('estimated_cost'))

    def increment_usage(self):
        """Increment usage count and update last used info"""
        self.write({
            'usage_count': self.usage_count + 1,
            'last_used_date': fields.Datetime.now(),
            'last_used_by': self.env.user.id,
        })

    def action_view_usage_history(self):
        """View requests that used this template"""
        request_lines = self.env['agricultural.production.request.line'].search([
            ('template_id', '=', self.id)
        ])
        request_ids = request_lines.mapped('request_id').ids

        return {
            'name': _('Usage History'),
            'type': 'ir.actions.act_window',
            'res_model': 'agricultural.production.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', request_ids)],
            'context': {'search_default_template_filter': True}
        }
class ProductionRequestTemplateLine(models.Model):
    _name = 'request.template.line'
    _description = 'Production Request Template Line'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'production.request.template',
        'Template',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer('Sequence', default=10)

    # Product Information
    product_id = fields.Many2one('product.product', 'Product', required=True)
    description = fields.Text('Description')
    quantity = fields.Float('Quantity', required=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True)

    # Cost Information
    cost_center_type = fields.Selection([
        ('direct', 'Direct Material'),
        ('indirect', 'Indirect Material')
    ], 'Cost Center Type', required=True, default='direct')

    unit_price = fields.Float('Unit Price', digits='Product Price')
    estimated_cost = fields.Float('Estimated Cost', compute='_compute_estimated_cost', store=True)

    # Account Linking
    expense_account = fields.Many2one('account.account', 'Expense Account')
    provision_account = fields.Many2one('account.account', 'Provision Account')

    # Notes
    notes = fields.Text('Notes')

    @api.depends('quantity', 'unit_price')
    def _compute_estimated_cost(self):
        for line in self:
            line.estimated_cost = line.quantity * line.unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.unit_price = self.product_id.standard_price
            self.description = self.product_id.name

            # Set default accounts based on product category
            if self.product_id.categ_id:
                self.expense_account = self.product_id.categ_id.property_account_expense_categ_id
# Update ProductionRequestLine to track template usage
class ProductionRequestLine(models.Model):
    _inherit = 'agricultural.production.request.line'

    # Add template tracking
    template_id = fields.Many2one(
        'production.request.template',
        'Source Template',
        readonly=True,
        help='Template used to create this line'
    )
class ProductionRequest(models.Model):
    _inherit = 'agricultural.production.request'

    def action_select_templates(self):
        """Open wizard to select templates"""
        return {
            'name': _('Select Templates'),
            'type': 'ir.actions.act_window',
            'res_model': 'request.template.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
            }
        }

    def action_clear_lines(self):
        """Clear all production request lines"""
        self.line_ids.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('All production lines have been cleared.'),
                'type': 'success',
                'sticky': False,
            }
        }


