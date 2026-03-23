# __manifest__.py
{
    'name': 'Advanced Agricultural Management',
    'version': '19.0.1.0.0',
    'category': 'Agriculture',
    'summary': 'Complete Farm, Crop, Harvest & Production Management with Full Odoo ERP Integration',
    'description': '''
        Advanced Agricultural Management System
        ========================================

        A comprehensive agricultural management solution for Odoo that covers
        the full farm-to-warehouse lifecycle.

        Key Features:
        * Farm & Location Management - hierarchical farm/sector/unit/house structure
        * Crop Management - crop lifecycle tracking with yield analytics
        * Harvest Scheduling - plan, track, and manage harvest operations
        * Harvest Sorting & Grading - quality-based sorting with batch tracking
        * Production Requests - agricultural production orders with approval workflow
        * Cost Allocation - multi-level cost center tracking with analytic accounts
        * Warehouse Integration - multi-warehouse management with lot/batch tracking
        * Accounting Integration - automated journal entries with budget compliance
        * Agricultural Projects - project-based farm management with cost/profit analysis
        * Section Management - department-based operations dashboard
        * Worker Management - agricultural worker assignment and tracking
        * Mobile Responsive - works on tablets and phones for field use
        * Complete Audit Trail - full tracking on all operations
        * Role-based Security - granular access control (Manager/User/Readonly)
        * Email Notifications - automated alerts for task assignments
        * Arabic RTL Support - full Arabic language support
    ''',
    'author': 'xamltech',
    'website': 'https://xamltech.com/',
    'license': 'LGPL-3',
    "currency": 'USD',
    'price': 850.00,
    'company': 'xamltech',
    'maintainer': 'Mahmudamen',
    'depends': [
        'base',
        'product',
        'sale',
        'stock',
        'account',
        'hr',
        'project',
        'mail',
        'contacts',
        'stock_account',
        'sale_stock',
        'analytic',
        'purchase',
    ],
    'data': [
        # Security
        'security/agricultural_security.xml',
        'security/res_sections_security.xml',
        'security/groups.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        # Core Views
        'views/production_request_views.xml',
        'views/res_company.xml',
        'views/res_users_views.xml',
        'views/menu_views.xml',
        'views/agricultural_harvest_schedule.xml',
        'views/agricultural_farm_views.xml',
        'views/sections.xml',
        'views/reception_new.xml',
        'views/agricultural_farm.xml',
        'views/agricultural_project_cost_profit_views.xml',
        'views/agricultural_project.xml',
        # Menu Integration
        'views/product_menu.xml',
        'views/account_menu.xml',
        'views/stock_menu.xml',
        'views/purchase_menu.xml',
        'views/inventory_menu.xml',
        'views/accountant_menu.xml',
        # Configuration
        'views/stock_view_warehouse.xml',
        'views/view_production_request_template.xml',
        'views/agricultural_cost_allocation_views.xml',
        # Wizards
        'wizard/request_production_template_wizard.xml',
        'wizard/harvest_sorting_wizard_views.xml',
        # Settings & Extra Views
        'views/farms_config.xml',
        'views/view_location_form.xml',
        'views/product_category_form_view.xml',
        'views/harvest_sorting_line_views.xml',
        'views/agricultural_harvest_batch.xml',
        'views/agricultural_project_sections_views.xml',
        'views/stock_production_lot.xml',
        'views/household_harvest_views.xml',
        'views/product.xml',
        # Data
        'data/sequences.xml',
        'data/base_data.xml',
        'data/email_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # JS
            'agricultural_management/static/src/js/kanban.js',
            'agricultural_management/static/src/js/sections_kanban.js',
            'agricultural_management/static/src/js/farm_services_kanban.js',
            # OWL Dashboard
            'agricultural_management/static/src/components/agri_dashboard/agri_dashboard.js',
            'agricultural_management/static/src/components/agri_dashboard/agri_dashboard.xml',
            'agricultural_management/static/src/components/agri_dashboard/agri_dashboard.scss',
            # SCSS
            'agricultural_management/static/src/css/schedule_gantt.scss',
            'agricultural_management/static/src/scss/sections_kanban.scss',
            'agricultural_management/static/src/css/sections_dashboard.scss',
            'agricultural_management/static/src/css/kanban.css',
            'agricultural_management/static/src/scss/farm_services_kanban.scss',
            'agricultural_management/static/src/scss/agricultural_farm.scss',
            'agricultural_management/static/src/scss/production_form.scss',
            'agricultural_management/static/src/scss/production_form_extended.scss',
            'agricultural_management/static/src/scss/agricultural_kanban_requested.scss',
        ],
        'web.report_assets_common': [
            'agricultural_management/static/src/fonts/Tajawal-Regular.ttf',
            'agricultural_management/static/src/fonts/Tajawal-Bold.ttf',
        ],
    },
    'demo': [

        'data/agricultural_demo_data.xml',
        'data/demo_master.xml',
        'data/base_data.xml',
        'data/demo_projects.xml',
        #'data/cost.xml',
        'data/demo_dashboards.xml',
        #'data/demo_production.xml',

        #'data/demo_financial.xml',
        #'data/demo_inventory.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
