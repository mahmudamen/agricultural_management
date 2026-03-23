# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ResSections(models.Model):
    _name = 'res.sections'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'
    _description = 'Agricultural Farm Sections'

    name = fields.Char(required=True, translate=True, string="Name", tracking=True)
    sequence = fields.Integer(default=10, string="Sequence", tracking=True)
    type = fields.Selection(
        selection=[
            ('ProductionOperationsManagement', 'Production & Operations Management'),
            ('CostCenter', 'Cost Centers'),
            ('Accounting', 'General Accounting'),
            ('FinishedGoodsWarehouses', 'Finished Goods Warehouses'),
            ('SortingAndPackingArea','Sorting & Packing Area'),
            ('RawMaterialsWarehouses', 'Warehouse Management'),
            ('AgriculturalWorkers', 'Agricultural Workers'),
            ('PreSaleWarehouses', 'Pre-Sale Warehouses'),
            ('Rfq', 'Purchase Requests'),
            ('Harvest','Harvest'),
            ('CarWorkshops','Vehicle Workshop'),
            ('MaintenanceWorkshops','Maintenance Workshop')
        ],
        required=False,
        string="Section Type",
        tracking=True
    )
    active = fields.Boolean(default=True, string="Active", tracking=True)
    color = fields.Integer(string="Color", compute='_compute_color', store=True)
    description = fields.Text(string="Description", tracking=True)
    assigned_user_ids = fields.Many2many(
        'res.users',
        'section_user_rel',
        'section_id',
        'user_id',
        string="Assigned Users",
        help="Users who have access to this section",
        tracking=True
    )
    manager_id = fields.Many2one(
        'res.users',
        string="Section Manager",
        help="Main section manager",
        tracking=True
    )
    is_public = fields.Boolean(
        string="Public Section",
        default=False,
        help="If enabled, all users can see this section",
        tracking=True
    )
    user_has_access = fields.Boolean(
        string="Has Access",
        compute='_compute_user_has_access'
    )
    assigned_users_count = fields.Integer(
        string="User Count",
        compute='_compute_assigned_users_count'
    )
    code = fields.Char(
        string="Section Code",
        required=True,
        help="Unique code for the section",
        tracking=True
    )
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Urgent'),
        ('3', 'Critical')
    ], string="Priority", default='0', tracking=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived')
    ], string="Status", default='draft', tracking=True)
    rating = fields.Selection([
        ('1', '⭐'),
        ('2', '⭐⭐'),
        ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'),
        ('5', '⭐⭐⭐⭐⭐')
    ], string="Rating")

    # Is critical
    is_critical = fields.Boolean(
        string="Critical Section",
        help="Critical section requiring special follow-up"
    )
    total_requests_count = fields.Integer(
        string="Total Requests",
        compute='_compute_statistics'
    )
    pending_requests_count = fields.Integer(
        string="Pending Requests",
        compute='_compute_statistics'
    )
    completed_requests_count = fields.Integer(
        string="Completed Requests",
        compute='_compute_statistics'
    )

    active_projects_count = fields.Integer(
        string="Active Projects",
        compute='_compute_statistics'
    )
    # Add computed fields for cost center statistics
    total_cost_calculations = fields.Integer(
        string="Total Cost Calculations",
        compute='_compute_cost_center_stats',
        store=False
    )

    total_cost_allocations = fields.Integer(
        string="Total Cost Allocations",
        compute='_compute_cost_center_stats',
        store=False
    )

    monthly_cost_amount = fields.Monetary(
        string="Monthly Cost Amount",
        compute='_compute_cost_center_stats',
        currency_field='currency_id',
        store=False
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )


    def action_cost_center_dashboard(self):
        """Open cost center dashboard"""
        self.ensure_one()
        if self.type != 'CostCenter':
            raise UserError(_("This action is only available for Cost Centers"))

        return {
            'type': 'ir.actions.client',
            'name': _('Cost Center Dashboard - %s') % self.name,
            'tag': 'cost_center_dashboard',
            'target': 'current',
            'context': {
                'section_id': self.id,
                'section_name': self.name,
                'default_cost_center_id': self.id,
            }
        }
    def action_cost_calculations(self):
        """View cost calculations for this cost center"""
        self.ensure_one()
        return {
            'name': _('Cost Calculations - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.calculation',
            'view_mode': 'list,form',
            'domain': [('cost_center_id', '=', self.id)],
            'context': {
                'default_cost_center_id': self.id,
                'search_default_cost_center_id': self.id,
            },
            'target': 'current',
        }
    def action_create_cost_calculation(self):
        """Create new cost calculation for this cost center"""
        self.ensure_one()
        return {
            'name': _('New Cost Calculation'),
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.calculation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cost_center_id': self.id,
                'default_name': _('Cost Calculation - %s') % self.name,
            }
        }
    def action_cost_allocations(self):
        """View cost allocations for this cost center"""
        self.ensure_one()
        return {
            'name': _('Cost Allocations - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form',
            'domain': [('cost_center_id', '=', self.id)],
            'context': {
                'default_cost_center_id': self.id,
                'search_default_cost_center_id': self.id,
            },
            'target': 'current',
        }
    def action_create_cost_allocation(self):
        """Create new cost allocation for this cost center"""
        self.ensure_one()
        return {
            'name': _('New Cost Allocation'),
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cost_center_id': self.id,
                'default_name': _('Cost Allocation - %s') % self.name,
            }
        }
    def action_cost_reports(self):
        """Generate cost reports for this cost center"""
        self.ensure_one()
        return {
            'name': _('Cost Reports - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'cost.center.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cost_center_id': self.id,
                'default_section_name': self.name,
            }
        }
    def action_budget_planning(self):
        """Open budget planning for this cost center"""
        self.ensure_one()
        return {
            'name': _('Budget Planning - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'cost.center.budget',
            'view_mode': 'list,form',
            'domain': [('cost_center_id', '=', self.id)],
            'context': {
                'default_cost_center_id': self.id,
                'search_default_current_year': 1,
            },
            'target': 'current',
        }
    def action_cost_analysis(self):
        """Open cost analysis for this cost center"""
        self.ensure_one()
        return {
            'name': _('Cost Analysis - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'cost.center.analysis',
            'view_mode': 'pivot,graph,list',
            'domain': [('cost_center_id', '=', self.id)],
            'context': {
                'search_default_cost_center_id': self.id,
                'search_default_this_month': 1,
            },
            'target': 'current',
        }
    def get_cost_center_summary(self):
        """Get cost center summary data"""
        self.ensure_one()

        # Calculate current month totals
        today = fields.Date.today()
        first_day = today.replace(day=1)

        cost_calculations = self.env['agri.cost.calculation'].search([
            ('cost_center_id', '=', self.id),
            ('date', '>=', first_day),
            ('date', '<=', today),
            ('state', '=', 'confirmed')
        ])

        cost_allocations = self.env['agri.cost.allocation'].search([
            ('cost_center_id', '=', self.id),
            ('date', '>=', first_day),
            ('date', '<=', today),
            ('state', '=', 'confirmed')
        ])

        return {
            'total_calculations': len(cost_calculations),
            'total_allocations': len(cost_allocations),
            'total_cost_amount': sum(cost_calculations.mapped('total_cost')),
            'total_allocation_amount': sum(cost_allocations.mapped('total_amount')),
            'pending_calculations': len(cost_calculations.filtered(lambda x: x.state == 'draft')),
            'pending_allocations': len(cost_allocations.filtered(lambda x: x.state == 'draft')),
        }
    @api.depends('type')
    def _compute_cost_center_stats(self):
        for record in self:
            if record.type == 'CostCenter':
                summary = record.get_cost_center_summary()
                record.total_cost_calculations = summary['total_calculations']
                record.total_cost_allocations = summary['total_allocations']
                record.monthly_cost_amount = summary['total_cost_amount']
            else:
                record.total_cost_calculations = 0
                record.total_cost_allocations = 0
                record.monthly_cost_amount = 0
    @api.depends('type')
    def _compute_color(self):
        """Compute color based on section type"""
        color_map = {
            'ProductionOperationsManagement': 1,
            'CostCenter': 2,
            'Accounting': 3,
            'FinishedGoodsWarehouses': 4,
            'RawMaterialsWarehouses': 5,
            'AgriculturalWorkers': 6,
            'PreSaleWarehouses': 7,
            'SortingAndPackingArea':8,
            'Rfq':9,
            'Harvest':10,
            'CarWorkshops':11,
            'MaintenanceWorkshops':12,
        }
        for record in self:
            record.color = color_map.get(record.type, 7)
    @api.depends('assigned_user_ids')
    def _compute_assigned_users_count(self):
        """Compute count of assigned users"""
        for record in self:
            record.assigned_users_count = len(record.assigned_user_ids)
    @api.depends('assigned_user_ids', 'manager_id', 'is_public')
    def _compute_user_has_access(self):
        """Check if current user has access to this section"""
        current_user = self.env.user
        for record in self:
            has_access = False

            # Admin always has access
            if current_user.has_group('base.group_system'):
                has_access = True
            # Public sections are accessible to all
            elif record.is_public:
                has_access = True
            # Manager has access
            elif record.manager_id == current_user:
                has_access = True
            # Assigned users have access
            elif current_user in record.assigned_user_ids:
                has_access = True

            record.user_has_access = has_access
    def assign_user(self, user_id):
        """Assign user to section"""
        self.ensure_one()
        user = self.env['res.users'].browse(user_id)
        if user and user not in self.assigned_user_ids:
            self.assigned_user_ids = [(4, user_id)]
            self.message_post(
                body=_("User has been assigned to %s the section") % user.name,
                message_type='notification',
            )
            return True
        return False
    def remove_user(self, user_id):
        """Remove user from section"""
        self.ensure_one()
        user = self.env['res.users'].browse(user_id)
        if user and user in self.assigned_user_ids:
            self.assigned_user_ids = [(3, user_id)]
            self.message_post(
                body=_("User has been unassigned from %s from the section") % user.name,
                message_type='notification',
            )
            return True
        return False
    def check_user_access(self, user_id=None):
        """Check if user has access to this section"""
        self.ensure_one()
        if not user_id:
            user_id = self.env.uid

        user = self.env['res.users'].browse(user_id)

        # Admin always has access
        if user.has_group('base.group_system'):
            return True

        # Public sections
        if self.is_public:
            return True

        # Manager has access
        if self.manager_id and self.manager_id.id == user_id:
            return True

        # Assigned users have access
        if user in self.assigned_user_ids:
            return True

        return False
    @api.model
    def get_user_accessible_sections(self, user_id=None):
        """Get sections accessible to user"""
        if not user_id:
            user_id = self.env.uid

        user = self.env['res.users'].browse(user_id)

        # Admin sees all sections
        if user.has_group('base.group_system'):
            return self.search([])

        # Regular users see their assigned sections + public sections
        return self.search([
            '|',
            '|',
            ('is_public', '=', True),
            ('assigned_user_ids', 'in', [user_id]),
            ('manager_id', '=', user_id)
        ])
    def get_section_action(self):
        """Open section-specific views based on type"""
        self.ensure_one()

        # Check access
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        # Define actions for each section type
        action_map = {
            'ProductionOperationsManagement': 'agricultural_management.action_agricultural_production_request',
            'CostCenter': 'agricultural_management.action_cost_centers',
            'Accounting': 'agricultural_management.action_accounting',
            'FinishedGoodsWarehouses': 'agricultural_management.action_finished_goods',
            'RawMaterialsWarehouses': 'agricultural_management.action_raw_materials',
            'AgriculturalWorkers': 'agricultural_management.action_workers',
            'PreSaleWarehouses': 'agricultural_management.action_presale_warehouses',
            'Rfq': 'agricultural_management.action_purchase_rfq',
        }

        action_name = action_map.get(self.type)

        if action_name:
            action = self.env.ref(action_name, raise_if_not_found=False)
            if action:
                return action.read()[0]

        # Default action - show a list view of the section
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.sections',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
    def get_engineers_action(self):
        # Check access
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Farm List"),
            'res_model': 'agricultural.farm',
            'view_mode': 'list',
            'views': [[self.env.ref('agricultural_management.engineer_list_farm').id, "list"]],
            'target': 'new',
            'context': {'create': False},
            'flags': {
                'action_buttons': True,
                'sidebar': False,
            }
        }
    def get_rfq_needed_action(self):
        # Check access
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("New Purchase Requests"),
            'res_model': 'agricultural.production.request.line',
            'view_mode': 'list',
            'views': [[self.env.ref('agricultural_management.production_request_line_list_farm').id, "list"]],
            'target': 'new',
            'domain': [('state', '=', 'rfq_needed')],
            'context': {'create': False},
            'flags': {
                'action_buttons': True,
                'sidebar': False,
            }
        }
    def get_rfq_pending_action(self):
        # Check access
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("In Progress"),
            'res_model': 'agricultural.production.request.line',
            'view_mode': 'list',
            'views': [[self.env.ref('agricultural_management.production_request_line_list_farm').id, "list"]],
            'target': 'new',
            'domain': [('state', '=', 'rfq_pending')],
            'context': {'create': False},
            'flags': {
                'action_buttons': True,
                'sidebar': False,
            }
        }
    def get_rfq_purchase_approved_action(self):
        # Check access
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchases"),
            'res_model': 'agricultural.production.request.line',
            'view_mode': 'list',
            'views': [[self.env.ref('agricultural_management.production_request_line_list_farm').id, "list"]],
            'target': 'new',
            'domain': [('state', '=', 'purchase_approved')],
            'context': {'create': False},
            'flags': {
                'action_buttons': True,
                'sidebar': False,
            }
        }
    def agricultural_production_request_view(self):
        """Create production request action with all views"""
        self.ensure_one()

        # Check access
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("🔥 Production Requests - %s") % self.name,
            'res_model': 'agricultural.production.request',
            'view_mode': 'list,form,kanban,calendar,graph,pivot',
            'views': [
                [self.env.ref('agricultural_management.view_agricultural_production_request_list').id, "list"],
                [self.env.ref('agricultural_management.view_agricultural_production_request_form').id, "form"],
                [self.env.ref('agricultural_management.view_agricultural_production_request_kanban').id, "kanban"],

                [self.env.ref('agricultural_management.view_agricultural_production_request_graph').id, "graph"],
                [self.env.ref('agricultural_management.view_agricultural_production_request_pivot').id, "pivot"]
            ],
            'target': 'current',
            #'domain': [('section_id', '=', self.id)],  # Filter by current section
            'context': {
            #    'default_section_id': self.id,  # Set default section
                'create': True
            },
            'help': '''
                <p class="o_view_nocontent_smiling_face">
                    Create your first production request for %s!
                </p>
                <p>
                    Production requests help you manage and track agricultural inputs and operations.
                </p>
            ''' % self.name
        }
    def toggle_active(self):
        """Toggle active status"""
        for record in self:
            # Check access
            if not record.check_user_access():
                raise UserError(_("You do not have permission to edit this section"))
            record.active = not record.active
    @api.model
    def create(self, vals):
        """Override create to handle sequence"""
        if 'sequence' not in vals:
            # Get max sequence for the same type
            max_sequence = self.search([
                ('type', '=', vals.get('type', 'other'))
            ], order='sequence desc', limit=1)
            vals['sequence'] = max_sequence.sequence + 10 if max_sequence else 10

        # Auto-assign creator as manager if not specified
        if 'manager_id' not in vals:
            vals['manager_id'] = self.env.uid

        # Log activity
        section = super(ResSections, self).create(vals)
        section.message_post(
            body=_("New section created: %s") % section.name,
            message_type='notification',
        )
        return section
    def write(self, vals):
        """Override write to track changes"""
        for record in self:
            # Check access for non-admin users
            if not self.env.user.has_group('base.group_system') and not record.check_user_access():
                raise UserError(_("You do not have permission to edit this section"))

            old_values = {}
            if 'active' in vals:
                old_values['active'] = record.active
            if 'type' in vals:
                old_values['type'] = record.type
            if 'assigned_user_ids' in vals:
                old_values['assigned_user_ids'] = record.assigned_user_ids.ids

            result = super(ResSections, record).write(vals)

            # Log important changes
            if 'active' in vals and old_values.get('active') != vals['active']:
                status = 'Activated' if vals['active'] else 'Deactivated'
                record.message_post(
                    body=_("%s Section") % status,
                    message_type='notification',
                )

            # Log user assignment changes
            if 'assigned_user_ids' in vals:
                old_user_ids = set(old_values.get('assigned_user_ids', []))
                new_user_ids = set(record.assigned_user_ids.ids)

                # New assignments
                added_users = new_user_ids - old_user_ids
                if added_users:
                    users = self.env['res.users'].browse(list(added_users))
                    record.message_post(
                        body=_("User has been assigned to: %s") % ', '.join(users.mapped('name')),
                        message_type='notification',
                    )

                # Removed assignments
                removed_users = old_user_ids - new_user_ids
                if removed_users:
                    users = self.env['res.users'].browse(list(removed_users))
                    record.message_post(
                        body=_("User has been unassigned from: %s") % ', '.join(users.mapped('name')),
                        message_type='notification',
                    )

        return result
    @api.constrains('sequence')
    def _check_sequence(self):
        """Check sequence is positive"""
        for record in self:
            if record.sequence < 0:
                raise ValidationError(_("Sequence Must be a positive number"))
    @api.constrains('manager_id', 'assigned_user_ids')
    def _check_manager_in_assigned_users(self):
        """Ensure manager is in assigned users"""
        for record in self:
            if record.manager_id and record.manager_id not in record.assigned_user_ids:
                record.assigned_user_ids = [(4, record.manager_id.id)]
    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            # Get Arabic type name
            type_names = dict(self._fields['type'].selection)
            type_name = type_names.get(record.type, '')
            name = f"[{type_name}] {record.name}"

            # Add access indicator for current user
            if hasattr(record, 'user_has_access') and not record.user_has_access:
                name = f"🔒 {name}"

            result.append((record.id, name))
        return result
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search"""
        args = args or []
        if name:
            # Search by name or type
            type_dict = dict(self._fields['type'].selection)
            matching_types = [k for k, v in type_dict.items() if name.lower() in v.lower()]

            if matching_types:
                args = ['|', ('name', operator, name), ('type', 'in', matching_types)] + args
            else:
                args = [('name', operator, name)] + args

        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
    @api.constrains('sequence')
    def _check_sequence(self):
        """Check sequence is positive"""
        for record in self:
            if record.sequence < 0:
                raise ValidationError(_("Sequence Must be a positive number"))
    def action_create_production_request(self):
        """Create a new production request"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("New Production Request"),
            'res_model': 'agricultural.production.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_section_id': self.id,
                'default_request_type': 'mixed',
                'default_requested_by': self.env.user.employee_id.id,
            }
        }
    def action_view_projects(self):
        """View agricultural projects"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Projects Agricultural"),
            'res_model': 'agricultural.project',
            'view_mode': 'list,form,kanban,graph',
            'target': 'current',
            'domain': [('state', '!=', 'cancelled')],
            'context': {'create': True}
        }
    def action_view_harvest_schedule(self):
        """View harvest scheduling"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Scheduling Harvest"),
            'res_model': 'agricultural.harvest.schedule',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'create': True}
        }

    def action_create_purchase_request(self):
        """Create a new purchase request"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("New Purchase Request"),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_origin': f'Section: {self.name}',
                'default_user_id': self.env.uid,
            }
        }
    def action_view_vendors(self):
        """View vendor management"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Vendor Management"),
            'res_model': 'res.partner',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('supplier_rank', '>', 0), ('category_id.name', 'ilike', 'Agricultural')],
            'context': {'create': True}
        }
    def action_purchase_analytics(self):
        """View purchase analytics"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Analytics Purchases"),
            'res_model': 'purchase.report',
            'view_mode': 'graph,pivot',
            'target': 'current',
            'context': {'create': False}
        }
    def action_purchase_reports(self):
        """View purchase reports"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.report',
            'report_name': 'purchase.report_purchaseorder',
            'report_type': 'qweb-pdf',
        }
    def action_material_request(self):
        """Create material request"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Issued to Subsidiary Company"),
            'res_model': 'res.partner',
            'view_mode': 'list',
            'views': [[self.env.ref('agricultural_management.res_partner_list_farm').id, "list"]],
            'target': 'new',
            'flags': {
                'action_buttons': True,
                'sidebar': False,
            }
        }
    def action_project_request(self):
        """Create material request"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Projects Agricultural"),
            'res_model': 'agricultural.project',
            'view_mode': 'list',
            'views': [[self.env.ref('agricultural_management.agricultural_project_list_sections_cost_view').id, "list"]],
            'target': 'new',
            'flags': {
                'action_buttons': True,
                'sidebar': False,
            }
        }
    def action_stock_levels(self):
        """View current stock levels"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Stock Levels"),
            'res_model': 'stock.quant',
            'view_mode': 'list,graph',
            'target': 'current',
            'domain': [('location_id.usage', '=', 'internal')],
            'context': {'create': False}
        }
    def action_stock_moves(self):
        """View stock movements"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Stock Movements"),
            'res_model': 'stock.move',
            'view_mode': 'list,form,graph',
            'target': 'current',
            'domain': [('state', '!=', 'cancel')],
            'context': {'create': False}
        }
    def action_inventory_valuation(self):
        """View inventory valuation"""
        self.ensure_one()
        pass

    def action_stock_alerts(self):
        """View stock alerts and low stock items"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("AlertStock Operations"),
            'res_model': 'stock.warehouse.orderpoint',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'create': True}
        }
    def action_warehouse_reports(self):
        """View warehouse reports"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Stock Reports"),
            'res_model': 'stock.report',
            'view_mode': 'graph,pivot',
            'target': 'current',
            'context': {'create': False}
        }
    def action_journal_entries(self):
        """View journal entries"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Journal Entries"),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('move_type', '=', 'entry')],
            'context': {'create': True, 'default_move_type': 'entry'}
        }
    def action_invoices(self):
        """View invoices"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Invoices"),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('move_type', 'in', ['out_invoice', 'in_invoice'])],
            'context': {'create': True}
        }
    def action_payments(self):
        """View payments"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Payments"),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'create': True}
        }
    def action_analytic_accounts(self):
        """View analytic accounts"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Accounts Analytic"),
            'res_model': 'account.analytic.account',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'create': True}
        }
    def action_cost_centers(self):
        """View cost centers"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Cost Centers"),
            'res_model': 'account.analytic.account',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('plan_id.name', 'ilike', 'Cost Center')],
            'context': {'create': True}
        }
    def action_budget_analysis(self):
        """View budget analysis"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Budget Analysis"),
            'res_model': 'crossovered.budget',
            'view_mode': 'list,form,graph',
            'target': 'current',
            'context': {'create': True}
        }
    def action_financial_reports(self):
        """View financial reports"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.client',
            'tag': 'account_report',
            'name': _("Financial Reports"),
            'context': {'create': False}
        }
    def action_create_cost_center(self):
        """Create new cost center"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("New Cost Center"),
            'res_model': 'account.analytic.account',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_name': f'Cost Center - {self.name}'}
        }
    def action_cost_allocation(self):
        """Manage cost allocation"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Cost Distribution"),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form,graph',
            'target': 'current',
            'context': {'create': True}
        }
    def action_cost_tracking(self):
        """Track costs"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Cost Tracking"),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,graph,pivot',
            'target': 'current',
            'context': {'create': False}
        }
    def action_budget_vs_actual(self):
        """Compare budget vs actual"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Budget vs Actual"),
            'res_model': 'crossovered.budget.lines',
            'view_mode': 'list,graph,pivot',
            'target': 'current',
            'context': {'create': False}
        }
    def action_profitability_analysis(self):
        """Analyze profitability"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Profitability Analysis"),
            'res_model': 'account.analytic.account',
            'view_mode': 'list,graph,pivot',
            'target': 'current',
            'context': {'create': False, 'group_by': ['partner_id', 'date']}
        }
    def action_finished_goods_receipt(self):
        """Receive finished goods"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Reception fromFinished Products"),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('picking_type_code', '=', 'incoming'), ('state', '!=', 'cancel')],
            'context': {'create': True}
        }

    def action_packaging_operations(self):
        """Manage packaging operations"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Packaging Operations"),
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('location_dest_id.name', 'ilike', 'Packaging'), ('state', '!=', 'cancel')],
            'context': {'create': True}
        }
    def action_dispatch_orders(self):
        """Manage dispatch orders"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Shipping Orders"),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('picking_type_code', '=', 'outgoing'), ('state', '!=', 'cancel')],
            'context': {'create': True}
        }
    def action_inventory_tracking(self):
        """Track finished goods inventory"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Stock Tracking fromFinished Products"),
            'res_model': 'stock.quant',
            'view_mode': 'list,graph,pivot',
            'target': 'current',
            'domain': [('location_id.name', 'ilike', 'Finished Goods')],
            'context': {'create': False}
        }
    def action_expiry_management(self):
        """Manage product expiry dates"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Expiry Management Permission"),
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'create': False}
        }
    def action_sorting_operations(self):
        """Manage sorting operations"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Sorting Operations"),
            'res_model': 'agricultural.sorting.operation',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'context': {'create': True, 'default_section_id': self.id}
        }
    def action_packing_operations(self):
        """Manage packing operations"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Packaging Operations"),
            'res_model': 'agricultural.packing.operation',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'context': {'create': True, 'default_section_id': self.id}
        }
    def action_quality_grades(self):
        """Manage quality grades"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Quality Grades"),
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('categ_id.name', 'ilike', 'Agricultural'), ('default_code', '!=', False)],
            'context': {'create': True}
        }
    def action_labeling(self):
        """Manage product labeling"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Labeling"),
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'create': True}
        }
    def action_batch_tracking(self):
        """Track product batches"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Batch Tracking"),
            'res_model': 'stock.lot',
            'view_mode': 'list,form,graph',
            'target': 'current',
            'context': {'create': False}
        }
    def action_packing_reports(self):
        """View packing reports"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Packaging Reports"),
            'res_model': 'agricultural.packing.report',
            'view_mode': 'list,graph,pivot',
            'target': 'current',
            'context': {'create': False}
        }
    def action_loading_operations(self):
        """Manage loading operations"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Loading Operations"),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('picking_type_code', '=', 'outgoing'), ('state', 'in', ['confirmed', 'assigned'])],
            'context': {'create': True}
        }
    def action_delivery_schedule(self):
        """Manage delivery scheduling"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Delivery Scheduling"),
            'res_model': 'agricultural.delivery.schedule',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'context': {'create': True, 'default_section_id': self.id}
        }
    def action_transport_management(self):
        """Manage transportation"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Transport Management"),
            'res_model': 'fleet.vehicle',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('vehicle_type', 'ilike', 'truck')],
            'context': {'create': True}
        }
    def action_delivery_tracking(self):
        """Track deliveries"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Delivery Tracking"),
            'res_model': 'stock.picking',
            'view_mode': 'list,form,map',
            'target': 'current',
            'domain': [('picking_type_code', '=', 'outgoing'), ('state', 'in', ['done', 'assigned'])],
            'context': {'create': False}
        }
    def action_customer_orders(self):
        """View customer orders"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Customer Orders"),
            'res_model': 'sale.order',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('state', 'not in', ['cancel', 'draft'])],
            'context': {'create': True}
        }
    def action_shipping_documents(self):
        """Manage shipping documents"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Shipping Documents"),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('picking_type_code', '=', 'outgoing')],
            'context': {'create': False}
        }
    def action_worker_management(self):
        """Manage agricultural workers"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Worker Management Agricultural"),
            'res_model': 'hr.employee',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('department_id.name', 'ilike', 'Agricultural')],
            'context': {'create': True}
        }
    def action_work_assignments(self):
        """Assign work tasks"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Task Assignment"),
            'res_model': 'project.task',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('project_id.name', 'ilike', 'Agricultural')],
            'context': {'create': True}
        }
    def action_attendance_tracking(self):
        """Track worker attendance"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Attendance Tracking"),
            'res_model': 'hr.attendance',
            'view_mode': 'list,form,graph',
            'target': 'current',
            'domain': [('employee_id.department_id.name', 'ilike', 'Agricultural')],
            'context': {'create': True}
        }
    def action_payroll_management(self):
        """Manage worker payroll"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Payroll Management"),
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('employee_id.department_id.name', 'ilike', 'Agricultural')],
            'context': {'create': True}
        }
    def action_skills_training(self):
        """Manage skills and training"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Training & Skills"),
            'res_model': 'hr.employee.skill',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('employee_id.department_id.name', 'ilike', 'Agricultural')],
            'context': {'create': True}
        }
    def action_safety_compliance(self):
        """Manage safety compliance"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Occupational Safety"),
            'res_model': 'agricultural.safety.record',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'context': {'create': True, 'default_section_id': self.id}
        }
    def action_performance_reports(self):
        """View worker performance reports"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Worker Performance Reports"),
            'res_model': 'hr.employee',
            'view_mode': 'graph,pivot',
            'target': 'current',
            'domain': [('department_id.name', 'ilike', 'Agricultural')],
            'context': {'create': False}
        }
    def action_harvest_planning(self):
        """Plan harvest activities"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Planning Harvest"),
            'res_model': 'agricultural.harvest.schedule',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'context': {'create': True, 'default_section_id': self.id}
        }
    def action_harvest_operations(self):
        """Manage harvest operations"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Operations Harvest"),
            'res_model': 'agricultural.harvest.operation',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'context': {'create': True, 'default_section_id': self.id}
        }
    def action_yield_tracking(self):
        """Track harvest yield"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Productivity Tracking"),
            'res_model': 'agricultural.yield.record',
            'view_mode': 'list,form,graph',
            'target': 'current',
            'context': {'create': True, 'default_section_id': self.id}
        }

    def action_post_harvest(self):
        """Manage post-harvest operations"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Operations what after Harvest"),
            'res_model': 'agricultural.post.harvest.operation',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'context': {'create': True, 'default_section_id': self.id}
        }
    def action_harvest_reports(self):
        """View harvest reports"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Reports Harvest"),
            'res_model': 'agricultural.harvest.report',
            'view_mode': 'list,graph,pivot',
            'target': 'current',
            'context': {'create': False}
        }
    def action_vehicle_maintenance(self):
        """Manage vehicle maintenance"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Maintenance Vehicles"),
            'res_model': 'fleet.vehicle.log.services',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'context': {'create': True}
        }
    def action_service_requests(self):
        """Manage service requests"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Requests Service"),
            'res_model': 'fleet.vehicle.log.services',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('state', '=', 'new')],
            'context': {'create': True}
        }
    def action_parts_inventory(self):
        """Manage spare parts inventory"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Stock Parts Spare"),
            'res_model': 'product.template',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('categ_id.name', 'ilike', 'Spare Parts')],
            'context': {'create': True}
        }
    def action_maintenance_schedule(self):
        """Schedule maintenance activities"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Scheduling Maintenance"),
            'res_model': 'fleet.vehicle.log.services',
            'view_mode': 'calendar,list,form',
            'target': 'current',
            'context': {'create': True}
        }
    def action_fuel_management(self):
        """Manage fuel consumption"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Management Fuel"),
            'res_model': 'fleet.vehicle.log.fuel',
            'view_mode': 'list,form,graph',
            'target': 'current',
            'context': {'create': True}
        }
    def action_maintenance_costs(self):
        """Track maintenance costs"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Costs Maintenance"),
            'res_model': 'fleet.vehicle.cost',
            'view_mode': 'list,form,graph',
            'target': 'current',
            'context': {'create': False}
        }
    def action_equipment_maintenance(self):
        """Manage equipment maintenance"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Maintenance Equipment"),
            'res_model': 'maintenance.request',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'domain': [('equipment_id.category_id.name', 'ilike', 'Agricultural')],
            'context': {'create': True}
        }
    def action_preventive_maintenance(self):
        """Manage preventive maintenance"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Maintenance Preventive"),
            'res_model': 'maintenance.request',
            'view_mode': 'list,form,calendar',
            'target': 'current',
            'domain': [('maintenance_type', '=', 'preventive')],
            'context': {'create': True, 'default_maintenance_type': 'preventive'}
        }
    def action_repair_orders(self):
        """Manage repair orders"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Orders Repair"),
            'res_model': 'maintenance.request',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('maintenance_type', '=', 'corrective')],
            'context': {'create': True, 'default_maintenance_type': 'corrective'}
        }
    def action_asset_management(self):
        """Manage assets"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Management Assets"),
            'res_model': 'maintenance.equipment',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('category_id.name', 'ilike', 'Agricultural')],
            'context': {'create': True}
        }
    def action_work_orders(self):
        """Manage work orders"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Orders Work"),
            'res_model': 'maintenance.request',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('stage_id.name', 'not in', ['Done', 'Cancelled'])],
            'context': {'create': True}
        }
    def action_emergency_repairs(self):
        """Handle emergency repairs"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Repairs Emergency"),
            'res_model': 'maintenance.request',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('priority', '=', '3'), ('maintenance_type', '=', 'corrective')],
            'context': {
                'create': True,
                'default_priority': '3',
                'default_maintenance_type': 'corrective'
            }
        }
    def action_maintenance_analytics(self):
        """View maintenance analytics"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Analytics Maintenance"),
            'res_model': 'maintenance.request',
            'view_mode': 'graph,pivot',
            'target': 'current',
            'context': {
                'create': False,
                'group_by': ['equipment_id', 'maintenance_type', 'stage_id']
            }
        }
    def action_section_dashboard(self):
        """Open section dashboard"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.client',
            'name': _("Dashboard Control Section - %s") % self.name,
            'tag': 'agricultural_section_dashboard',
            'target': 'current',
            'context': {
                'section_id': self.id,
                'section_type': self.type,
                'section_name': self.name
            }
        }
    def action_section_reports(self):
        """Generate section reports"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Reports Section - %s") % self.name,
            'res_model': 'agricultural.section.report',
            'view_mode': 'list,graph,pivot',
            'target': 'current',
            'domain': [('section_id', '=', self.id)],
            'context': {'create': False, 'default_section_id': self.id}
        }
    def action_quick_create(self):
        """Quick create based on section type"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        quick_create_map = {
            'ProductionOperationsManagement': self.action_create_production_request,
            'Rfq': self.action_create_purchase_request,
            'RawMaterialsWarehouses': self.action_material_request,
            'Accounting': self.action_journal_entries,
            'CostCenter': self.action_create_cost_center,
            'FinishedGoodsWarehouses': self.action_finished_goods_receipt,
            'SortingAndPackingArea': self.action_sorting_operations,
            'PreSaleWarehouses': self.action_loading_operations,
            'AgriculturalWorkers': self.action_work_assignments,
            'Harvest': self.action_harvest_planning,
            'CarWorkshops': self.action_vehicle_maintenance,
            'MaintenanceWorkshops': self.action_equipment_maintenance,
        }

        action_method = quick_create_map.get(self.type)
        if action_method:
            return action_method()
        else:
            return self.action_section_dashboard()
    def action_section_settings(self):
        """Open section settings"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Settings Section"),
            'res_model': 'res.sections',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'create': False}
        }
    def action_user_management(self):
        """Manage section users"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Management Users of Section"),
            'res_model': 'res.users',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', self.assigned_user_ids.ids)],
            'context': {'create': False}
        }
    def action_activity_log(self):
        """View section activity log"""
        self.ensure_one()
        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Active Section Log"),
            'res_model': 'mail.message',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('res_id', '=', self.id), ('model', '=', 'res.sections')],
            'context': {'create': False}
        }
    @api.depends('type', 'active')
    def _compute_statistics(self):
        """Compute section statistics"""
        for record in self:
            # Initialize counters
            record.total_requests_count = 0
            record.pending_requests_count = 0
            record.completed_requests_count = 0
            record.total_operations_count = 0
            record.active_projects_count = 0

            # Production requests statistics
            if record.type == 'ProductionOperationsManagement':
                production_requests = self.env['agricultural.production.request'].search_count([
                    ('section_id', '=', record.id)
                ])
                pending_requests = self.env['agricultural.production.request'].search_count([
                    ('section_id', '=', record.id),
                    ('state', 'in', ['draft', 'submitted', 'approved'])
                ])
                completed_requests = self.env['agricultural.production.request'].search_count([
                    ('section_id', '=', record.id),
                    ('state', '=', 'completed')
                ])

                record.total_requests_count = production_requests
                record.pending_requests_count = pending_requests
                record.completed_requests_count = completed_requests

            # Purchase requests statistics
            elif record.type == 'Rfq':
                purchase_orders = self.env['purchase.order'].search_count([
                    ('origin', 'ilike', f'Section: {record.name}')
                ])
                pending_orders = self.env['purchase.order'].search_count([
                    ('origin', 'ilike', f'Section: {record.name}'),
                    ('state', 'in', ['draft', 'sent', 'to approve'])
                ])

                record.total_requests_count = purchase_orders
                record.pending_requests_count = pending_orders

            # Warehouse statistics
            elif record.type in ['RawMaterialsWarehouses', 'FinishedGoodsWarehouses']:
                stock_moves = self.env['stock.move'].search_count([
                    ('location_id.name', 'ilike', record.name.split()[0])
                ])
                record.total_operations_count = stock_moves

            # Projects statistics
            active_projects = self.env['agricultural.project'].search_count([
                ('state', '=', 'active')
            ])
            record.active_projects_count = active_projects
    @api.model
    def get_section_quick_actions(self, section_type):
        """Get quick actions for section type"""
        quick_actions = {
            'ProductionOperationsManagement': [
                {'name': _('Request Production'), 'method': 'action_create_production_request', 'icon': 'fa-plus'},
                {'name': _('Projects'), 'method': 'action_view_projects', 'icon': 'fa-project-diagram'},
                {'name': _('Operations'), 'method': 'action_view_operations', 'icon': 'fa-cogs'},
            ],
            'CostCenter': [  # Add this section
                {'name': _('Account Cost'), 'method': 'action_create_cost_calculation', 'icon': 'fa-calculator'},
                {'name': _('Distribution Cost'), 'method': 'action_create_cost_allocation', 'icon': 'fa-share-alt'},
                {'name': _('Reports'), 'method': 'action_cost_reports', 'icon': 'fa-chart-bar'},
                {'name': _('Budget'), 'method': 'action_budget_planning', 'icon': 'fa-money-bill'},
                {'name': _('Analysis'), 'method': 'action_cost_analysis', 'icon': 'fa-analytics'},
                {'name': _('Dashboard Control'), 'method': 'action_cost_center_dashboard', 'icon': 'fa-tachometer-alt'},
            ],
            'Rfq': [
                {'name': _('Request Purchase'), 'method': 'action_create_purchase_request', 'icon': 'fa-shopping-cart'},
                {'name': _('Suppliers'), 'method': 'action_view_vendors', 'icon': 'fa-handshake'},
                {'name': _('Reports'), 'method': 'action_purchase_reports', 'icon': 'fa-chart-bar'},
            ],
            'RawMaterialsWarehouses': [
                {'name': _('Request Materials'), 'method': 'action_material_request', 'icon': 'fa-plus'},
                {'name': _('Stock'), 'method': 'action_stock_levels', 'icon': 'fa-boxes'},
                {'name': _('Movements'), 'method': 'action_stock_moves', 'icon': 'fa-exchange-alt'},
            ],
            # Add more section types as needed...
        }
        return quick_actions.get(section_type, [])
    def get_section_color_class(self):
        """Get CSS color class for section"""
        color_classes = {
            'ProductionOperationsManagement': 'section-production',
            'CostCenter': 'section-cost-center',
            'Accounting': 'section-accounting',
            'FinishedGoodsWarehouses': 'section-finished-goods',
            'SortingAndPackingArea': 'section-sorting',
            'RawMaterialsWarehouses': 'section-raw-materials',
            'AgriculturalWorkers': 'section-workers',
            'PreSaleWarehouses': 'section-pre-sale',
            'Rfq': 'section-rfq',
            'Harvest': 'section-harvest',
            'CarWorkshops': 'section-car-workshop',
            'MaintenanceWorkshops': 'section-maintenance',
        }
        return color_classes.get(self.type, 'section-default')
    def get_section_icon(self):
        """Get FontAwesome icon for section"""
        icons = {
            'ProductionOperationsManagement': 'fa-industry',
            'CostCenter': 'fa-building',
            'Accounting': 'fa-calculator',
            'FinishedGoodsWarehouses': 'fa-box',
            'SortingAndPackingArea': 'fa-sort',
            'RawMaterialsWarehouses': 'fa-warehouse',
            'AgriculturalWorkers': 'fa-users',
            'PreSaleWarehouses': 'fa-truck-loading',
            'Rfq': 'fa-shopping-cart',
            'Harvest': 'fa-leaf',
            'CarWorkshops': 'fa-car',
            'MaintenanceWorkshops': 'fa-hammer',
        }
        return icons.get(self.type, 'fa-folder')
    def action_bulk_operations(self):
        """Handle bulk operations for multiple sections"""
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError(_("not done select any Sections"))

        return {
            'type': 'ir.actions.act_window',
            'name': _("Operations Multiple on Sections"),
            'res_model': 'agricultural.section.bulk.operation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_section_ids': [(6, 0, active_ids)],
                'active_ids': active_ids
            }
        }
    @api.model
    def create_default_sections(self):
        """Create default agricultural sections"""
        default_sections = [
            {
                'name': 'Management Production Main',
                'code': 'PROD-MAIN',
                'type': 'ProductionOperationsManagement',
                'sequence': 10,
                'is_public': True,
                'status': 'active',
                'priority': '2',
                'description': 'Management & Coordination All Operations Production Agricultural'
            },
            {
                'name': 'Section Purchases',
                'code': 'PUR-001',
                'type': 'Rfq',
                'sequence': 20,
                'status': 'active',
                'priority': '2',
                'description': 'Management All Operations Purchase & Requests Prices'
            },
            {
                'name': 'Warehouse Materials Raw Main',
                'code': 'RAW-001',
                'type': 'RawMaterialsWarehouses',
                'sequence': 30,
                'status': 'active',
                'priority': '3',
                'is_critical': True,
                'description': 'Warehouse Storage All Materials Raw for Production'
            },
            {
                'name': 'Warehouse fromFinished Products',
                'code': 'FIN-001',
                'type': 'FinishedGoodsWarehouses',
                'sequence': 40,
                'status': 'active',
                'priority': '2',
                'description': 'Warehouse fromProducts Ready for delivery'
            },
            {
                'name': 'Section Accountant General',
                'code': 'ACC-001',
                'type': 'Accounting',
                'sequence': 50,
                'status': 'active',
                'priority': '2',
                'description': 'Management Accounts & Entries Accountant'
            },
            {
                'name': 'Cost Center Main',
                'code': 'COST-001',
                'type': 'CostCenter',
                'sequence': 60,
                'status': 'active',
                'priority': '1',
                'description': 'Monitoring & Tracking Costs Operations'
            },
            {
                'name': 'fromArea Sorting & Packaging',
                'code': 'SORT-001',
                'type': 'SortingAndPackingArea',
                'sequence': 70,
                'status': 'active',
                'priority': '2',
                'description': 'Sort & Pack fromProducts by Quality'
            },
            {
                'name': 'Warehouse Loading Main',
                'code': 'LOAD-001',
                'type': 'PreSaleWarehouses',
                'sequence': 80,
                'status': 'active',
                'priority': '2',
                'description': 'Preparation & Loading fromProducts for delivery'
            },
            {
                'name': 'Section Agricultural Workers',
                'code': 'WORK-001',
                'type': 'AgriculturalWorkers',
                'sequence': 90,
                'status': 'active',
                'priority': '1',
                'description': 'Management Workers & Tasks Agricultural'
            },
            {
                'name': 'Section Harvest',
                'code': 'HARV-001',
                'type': 'Harvest',
                'sequence': 100,
                'status': 'active',
                'priority': '3',
                'is_critical': True,
                'description': 'Planning & Execution Operations Harvest'
            },
            {
                'name': 'Workshop Maintenance Vehicles',
                'code': 'CAR-001',
                'type': 'CarWorkshops',
                'sequence': 110,
                'status': 'active',
                'priority': '1',
                'description': 'Maintenance & Repair Vehicles Agricultural'
            },
            {
                'name': 'Maintenance Workshop General',
                'code': 'MAIN-001',
                'type': 'MaintenanceWorkshops',
                'sequence': 120,
                'status': 'active',
                'priority': '1',
                'description': 'Maintenance Equipment & Machinery Agricultural'
            }
        ]

        created_sections = []
        for section_data in default_sections:
            existing = self.search([('code', '=', section_data['code'])], limit=1)
            if not existing:
                section = self.create(section_data)
                created_sections.append(section)
                # Log creation
                section.message_post(
                    body=_("has been Create Section Automatically as part of from Setup Default"),
                    message_type='notification'
                )

        # Create analytic accounts for cost centers
        self._create_default_analytic_accounts(created_sections)

        # Assign default users if admin is running this
        self._assign_default_users(created_sections)

        return created_sections
    def _create_default_analytic_accounts(self, sections):
        """Create default analytic accounts for sections"""
        analytic_account_obj = self.env['account.analytic.account']

        for section in sections:
            if section.type in ['CostCenter', 'ProductionOperationsManagement', 'Accounting']:
                # Check if analytic account exists
                existing_account = analytic_account_obj.search([
                    ('name', '=', f"Analytic - {section.name}")
                ], limit=1)

                if not existing_account:
                    analytic_account = analytic_account_obj.create({
                        'name': f"Analytic - {section.name}",
                        'code': f"AN-{section.code}",
                        'plan_id': self._get_default_analytic_plan().id,
                    })
                    section.message_post(
                        body=_("has been Create Account Analytic: %s") % analytic_account.name,
                        message_type='notification'
                    )
    def _assign_default_users(self, sections):
        """Assign default users to sections"""
        admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
        current_user = self.env.user

        for section in sections:
            # Assign current user as manager
            section.manager_id = current_user.employee_id.id if current_user.employee_id else False

            # Add current user to assigned users
            if current_user not in section.assigned_user_ids:
                section.assigned_user_ids = [(4, current_user.id)]

            # Add admin user if available and different from current user
            if admin_user and admin_user != current_user:
                section.assigned_user_ids = [(4, admin_user.id)]
    def _get_default_analytic_plan(self):
        """Get or create default analytic plan"""
        plan_obj = self.env['account.analytic.plan']
        plan = plan_obj.search([('name', '=', 'Agricultural Sections')], limit=1)

        if not plan:
            plan = plan_obj.create({
                'name': 'Agricultural Sections',
                'description': 'Analytic plan for agricultural sections cost tracking'
            })

        return plan
    @api.model
    def setup_section_security(self):
        """Setup security groups for sections"""
        groups_to_create = [
            {
                'name': 'Agricultural Section Manager',
                'category_id': self.env.ref('base.module_category_hidden').id,
                'users': [self.env.ref('base.user_admin').id]
            },
            {
                'name': 'Agricultural Section User',
                'category_id': self.env.ref('base.module_category_hidden').id,
            },
            {
                'name': 'Agricultural Section Viewer',
                'category_id': self.env.ref('base.module_category_hidden').id,
            }
        ]

        created_groups = []
        for group_data in groups_to_create:
            existing = self.env['res.groups'].search([
                ('name', '=', group_data['name'])
            ], limit=1)

            if not existing:
                group = self.env['res.groups'].create(group_data)
                created_groups.append(group)

        return created_groups
    @api.model
    def migrate_existing_data(self):
        """Migrate existing data to section structure"""
        # This method can be used to migrate existing production requests, etc.
        # to be associated with appropriate sections

        # Example: Associate existing production requests with sections
        production_requests = self.env['agricultural.production.request'].search([
            ('section_id', '=', False)
        ])

        for request in production_requests:
            # Auto-assign to production management section
            prod_section = self.search([
                ('type', '=', 'ProductionOperationsManagement')
            ], limit=1)

            if prod_section:
                request.section_id = prod_section.id

        return True
    @api.model
    def cleanup_inactive_sections(self):
        """Clean up inactive sections and their data"""
        inactive_sections = self.search([
            ('active', '=', False),
            ('status', '=', 'archived'),
            ('create_date', '<', fields.Datetime.now() - timedelta(days=365))
        ])

        for section in inactive_sections:
            # Archive related data instead of deleting
            self._archive_section_data(section)

        return len(inactive_sections)
    def _archive_section_data(self, section):
        """Archive data related to a section"""
        # Archive production requests
        production_requests = self.env['agricultural.production.request'].search([
            ('section_id', '=', section.id)
        ])
        production_requests.write({'active': False})

        # Log archival
        section.message_post(
            body=_("has been Archive Data Related Section"),
            message_type='notification'
        )
    @api.model
    def get_sections_performance_data(self):
        """Get performance data for all sections"""
        sections = self.search([('active', '=', True)])
        performance_data = []

        for section in sections:
            data = {
                'section_id': section.id,
                'section_name': section.name,
                'section_type': section.type,
                'total_requests': section.total_requests_count,
                'pending_requests': section.pending_requests_count,
                'completed_requests': section.completed_requests_count,
                'completion_rate': (
                    (section.completed_requests_count / section.total_requests_count * 100)
                    if section.total_requests_count > 0 else 0
                ),
                'assigned_users': len(section.assigned_user_ids),
                'last_activity': section.message_ids[0].date if section.message_ids else False
            }
            performance_data.append(data)

        return performance_data
    def generate_section_report(self):
        """Generate comprehensive section report"""
        self.ensure_one()

        report_data = {
            'section': self,
            'statistics': {
                'total_requests': self.total_requests_count,
                'pending_requests': self.pending_requests_count,
                'completed_requests': self.completed_requests_count,
                'active_projects': self.active_projects_count,
                'assigned_users': len(self.assigned_user_ids)
            },
            'recent_activities': self.message_ids.filtered(
                lambda m: m.date >= fields.Datetime.now() - timedelta(days=30)
            ),
            'performance_metrics': self._calculate_performance_metrics()
        }

        return {
            'type': 'ir.actions.report',
            'report_name': 'agricultural_management.section_performance_report',
            'report_type': 'qweb-pdf',
            'data': report_data,
            'context': self.env.context
        }
    def _calculate_performance_metrics(self):
        """Calculate performance metrics for the section"""
        metrics = {
            'efficiency': 0.0,
            'user_satisfaction': 0.0,
            'cost_effectiveness': 0.0,
            'response_time': 0.0
        }

        # Calculate efficiency based on completion rate
        if self.total_requests_count > 0:
            metrics['efficiency'] = (self.completed_requests_count / self.total_requests_count) * 100

        # Add more metric calculations based on your business logic

        return metrics
    def notify_section_update(self, update_type='general'):
        """Notify external systems about section updates"""
        notification_data = {
            'section_id': self.id,
            'section_name': self.name,
            'section_type': self.type,
            'update_type': update_type,
            'timestamp': fields.Datetime.now().isoformat(),
            'updated_by': self.env.user.name
        }

        # Here you can add webhook calls, email notifications, etc.
        self.message_post(
            body=_("has been Notification Systems External Update: %s") % update_type,
            message_type='notification'
        )

        return notification_data
    @api.model
    def sync_with_external_system(self):
        """Synchronize sections data with external systems"""
        sections = self.search([('active', '=', True)])
        sync_results = []

        for section in sections:
            try:
                # Add your external system sync logic here
                result = {
                    'section_id': section.id,
                    'status': 'success',
                    'message': 'Synchronized successfully'
                }
                sync_results.append(result)
            except Exception as e:
                result = {
                    'section_id': section.id,
                    'status': 'error',
                    'message': str(e)
                }
                sync_results.append(result)

        return sync_results
    @api.model
    def daily_section_maintenance(self):
        """Daily maintenance tasks for sections"""
        # Update statistics
        sections = self.search([('active', '=', True)])
        for section in sections:
            section._compute_statistics()

        # Clean up old messages
        old_messages = self.env['mail.message'].search([
            ('model', '=', 'res.sections'),
            ('date', '<', fields.Datetime.now() - timedelta(days=90))
        ])
        old_messages.unlink()

        # Generate performance alerts
        self._generate_performance_alerts()

        return True
    def _generate_performance_alerts(self):
        """Generate alerts for poor performing sections"""
        sections = self.search([('active', '=', True)])

        for section in sections:
            # Check for sections with low completion rates
            if (section.total_requests_count > 10 and
                    section.completed_requests_count / section.total_requests_count < 0.7):
                section.activity_schedule(
                    'mail.mail_activity_data_warning',
                    summary=_("Warning Performance Section"),
                    note=_("Rate Achievement Low in Section: %s") % section.name,
                    user_id=section.manager_id.user_id.id if section.manager_id else self.env.uid
                )
    def action_view_projects_cost_management(self):
        """View projects list with cost management buttons"""
        self.ensure_one()

        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        # Get projects based on section type
        domain = self._get_project_domain()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Management Costs Projects"),
            'res_model': 'agricultural.project',
            'view_mode': 'list,form',
            'views': [
                [self.env.ref('agricultural_management.agricultural_project_list_sections_cost_view').id, "list"]],
            'target': 'current',
            'domain': domain,
            'context': {
                'default_section_id': self.id,
                'section_name': self.name,
                'section_type': self.type,
                'search_default_filter_active': 1,
            },
            'flags': {
                'action_buttons': True,
                'sidebar': True,
            }
        }
    def action_view_direct_expenses_all_projects(self):
        """View direct expenses for all projects in this section"""
        self.ensure_one()

        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        projects = self.env['agricultural.project'].search(self._get_project_domain())

        if not projects:
            raise UserError(_("No projects in this Section"))

        direct_categories = ['direct_material', 'seeds', 'fertilizers',
                             'pesticides', 'direct_labor', 'machinery',
                             'utilities', 'fuel']

        return {
            'name': _("Expenses Direct - %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [
                ('project_id', 'in', projects.ids),
                ('cost_category', 'in', direct_categories),
                ('allocation_method', '=', 'direct_assignment')
            ],
            'context': {
                'search_default_group_by_project': 1,
                'search_default_group_by_category': 1,
            }
        }
    def action_view_indirect_expenses_all_projects(self):
        """View indirect expenses for all projects in this section"""
        self.ensure_one()

        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        projects = self.env['agricultural.project'].search(self._get_project_domain())

        if not projects:
            raise UserError(_("No projects in this Section"))

        indirect_categories = ['maintenance', 'overhead']

        return {
            'name': _("Expenses Not Direct - %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation',
            'view_mode': 'list,form,pivot,graph',
            'domain': [
                ('project_id', 'in', projects.ids),
                ('cost_category', 'in', indirect_categories)
            ],
            'context': {
                'search_default_group_by_project': 1,
                'search_default_group_by_category': 1,
            }
        }
    def action_view_cost_summary_dashboard(self):
        """View cost summary dashboard for all section projects"""
        self.ensure_one()

        if not self.check_user_access():
            raise UserError(_("You do not have access to this section"))

        projects = self.env['agricultural.project'].search(self._get_project_domain())

        if not projects:
            raise UserError(_("No projects in this Section"))

        return {
            'name': _("Summary Costs - %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agri.cost.allocation.line',
            'view_mode': 'pivot,graph,list',
            'domain': [('project_id', 'in', projects.ids)],
            'context': {
                'pivot_measures': ['amount', 'cost_per_m2', 'cost_per_plant'],
                'pivot_column_groupby': ['project_id'],
                'pivot_row_groupby': ['cost_category'],
                'graph_type': 'bar',
                'graph_measure': 'amount',
                'graph_groupbys': ['project_id', 'cost_category'],
            },
            'views': [
                (False, 'pivot'),
                (False, 'graph'),
                (False, 'list'),
            ]
        }
    def _get_project_domain(self):
        """Get domain for projects based on section type"""
        self.ensure_one()

        domain = [('state', '!=', 'cancelled')]

        # Add specific domain based on section type
        if self.type == 'ProductionOperationsManagement':
            domain.append(('state', 'in', ['active', 'planned']))
        elif self.type == 'CostCenter':
            # All projects with cost allocations
            domain.append(('allocation_count', '>', 0))
        elif self.type == 'Accounting':
            # Projects with accounting entries
            domain.append(('analytic_account_id', '!=', False))

        return domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Add a field to store the partner's destination location (if not exists)
    property_stock_dest = fields.Many2one(
        'stock.location',
        string='Destination Location',
        company_dependent=True,
        domain="[('usage', '=', 'internal')]",
        help="Stock location for the subsidiary company"
    )

    def create_stock_picking(self):
        """Create stock picking for partner with company_type contract"""
        self.ensure_one()

        # Validate partner has company_type = contract
        if self.company_type != 'company':
            raise UserError(_("Partner type must be 'Subsidiary Company'"))

        # Get source location (main stock location)
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not warehouse:
            raise UserError(_("not done find on Warehouse"))

        location_src_id = warehouse.lot_stock_id.id

        # Get destination location from partner or use customer location
        location_dest_id = self.property_stock_dest.id if self.property_stock_dest else \
            self.property_stock_customer.id

        if not location_dest_id:
            raise UserError(_("not done select Destination Location for company subsidiary"))

        # Get internal picking type
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', warehouse.id)
        ], limit=1)

        if not picking_type:
            # Fallback to outgoing if internal not found
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id', '=', warehouse.id)
            ], limit=1)

        if not picking_type:
            raise UserError(_("not done find on Type Operation"))

        # Create stock picking
        picking_vals = {
            'partner_id': self.id,
            'picking_type_id': picking_type.id,
            'location_id': location_src_id,
            'location_dest_id': location_dest_id,
            'origin': f'Issued to - {self.name}',
            'company_id': self.env.company.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        # Return form view of created picking
        return {
            'type': 'ir.actions.act_window',
            'name': _('Issue Materials for company subsidiary'),
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'view_id': self.env.ref('stock.view_picking_form').id,
            'target': 'current',
            'context': {
                'default_partner_id': self.id,
                'default_location_id': location_src_id,
                'default_location_dest_id': location_dest_id,
                'default_picking_type_id': picking_type.id,
            }
        }

    def create_invoice(self):
        """Create invoice for partner with company_type contract"""
        self.ensure_one()

        # Validate partner has company_type = contract
        if self.company_type != 'company':
            raise UserError(_("Partner type must be 'Subsidiary Company'"))

        # Validate partner is a customer
        if not self.customer_rank and not self.supplier_rank:
            raise UserError(_("Must that be Partner customer or vendor"))

        # Get journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not journal:
            raise UserError(_("not done find on Ledger Journal Sales"))

        # Prepare invoice values
        invoice_vals = {
            'partner_id': self.id,
            'move_type': 'out_invoice',  # Customer invoice
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': f'Invoice for {self.name}',
            'company_id': self.env.company.id,
            'currency_id': self.env.company.currency_id.id,
        }

        # Create invoice
        invoice = self.env['account.move'].create(invoice_vals)

        # Return form view of created invoice
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice for company subsidiary'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'context': {
                'default_move_type': 'out_invoice',
                'default_partner_id': self.id,
            }
        }

    def create_customer_invoice(self):
        """Create customer invoice"""
        return self._create_invoice_common('out_invoice', 'sale')

    def create_vendor_bill(self):
        """Create vendor bill"""
        return self._create_invoice_common('in_invoice', 'purchase')

    def create_credit_note(self):
        """Create credit note"""
        return self._create_invoice_common('out_refund', 'sale')

    def _create_invoice_common(self, move_type, journal_type):
        """Common method to create invoices"""
        self.ensure_one()

        if self.company_type != 'company':
            raise UserError(_("Partner type must be 'Subsidiary Company'"))

        # Get appropriate journal
        journal = self.env['account.journal'].search([
            ('type', '=', journal_type),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not journal:
            raise UserError(_("not done find on Ledger Journal fromappropriate"))

        # Create invoice
        invoice_vals = {
            'partner_id': self.id,
            'move_type': move_type,
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': f'{self._get_invoice_type_name(move_type)} for {self.name}',
            'company_id': self.env.company.id,
        }

        invoice = self.env['account.move'].create(invoice_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': self._get_invoice_type_name(move_type),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_invoice_type_name(self, move_type):
        """Get invoice type display name"""
        names = {
            'out_invoice': _('Invoice Customer'),
            'out_refund': _('Notification Creditor'),
            'in_invoice': _('Invoice Vendor'),
            'in_refund': _('Return Vendor'),
        }
        return names.get(move_type, _('Invoice'))