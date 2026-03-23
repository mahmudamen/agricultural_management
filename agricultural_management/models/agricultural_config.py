from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ==================== Pre-existing Accounts ====================
    cash_receivable_acc = fields.Many2one(
        'account.account',
        readonly=False,
        string="Cash Customers"
    )
    cash_receivable_partner = fields.Many2one(
        'res.partner',
        readonly=False,
        string="Cash Customers"
    )
    main_cash_journal = fields.Many2one(
        'account.journal',
        readonly=False,
        domain=[('type', '=', 'cash')],
        string="Main Cash Journal"
    )
    main_cash = fields.Many2one(
        'account.account',
        readonly=False,
        string="Main Cash Account"
    )
    service_exp_account = fields.Many2one(
        'account.account',
        readonly=False,
        string="Administrative Expense Account"
    )
    reception_journal = fields.Many2one(
        'account.journal',
        readonly=False,
        domain=[('type', '=', 'general')],
        string="General Journal"
    )
    engineer_expense_account = fields.Many2one(
        'account.account',
        readonly=False,
        string="Engineer Account"
    )
    inventory_valuation_method = fields.Selection([
        ('average', 'Weighted Average'),
    ],
        string="Inventory Valuation Method",
        readonly=False,
        default='average',
        help="Inventory cost calculation method:\n"
             "- FIFO: First In, First Out\n"
             "- Weighted Average: Average cost calculation\n"
             "- Standard Cost: Pre-defined fixed cost"
    )
    # ==================== 📁 Accounting Journals ====================
    stock_journal = fields.Many2one(
        'account.journal',
        domain=[('type', '=', 'general')],
        string="Stock Movement Journal",
        help="Journal used to record all stock movements (purchase, issue, transfer)"
    )
    stock_valuation_journal = fields.Many2one(
        'account.journal',
        readonly=False,
        domain=[('type', '=', 'general')],
        string="Stock Valuation Journal",
        help="Journal for stock valuation and inventory adjustment entries"
    )
    internal_transfer_journal = fields.Many2one(
        'account.journal',
        readonly=False,
        domain=[('type', '=', 'general')],
        string="Internal Transfer Journal",
        help="Journal for inter-warehouse transfer operations"
    )
    # ==================== 🏢 Stock Accounts - Main Warehouse ====================
    stock_fertilizers_main = fields.Many2one(
        'account.account',
        readonly=False,
        string="Fertilizer Stock - Main Warehouse",
        help="Fertilizer stock account in main warehouse"
    )
    stock_pesticides_main = fields.Many2one(
        'account.account',
        readonly=False,
        string="Pesticide Stock - Main Warehouse",
        help="Pesticide stock account in main warehouse"
    )
    stock_seeds_main = fields.Many2one(
        'account.account',
        string="Seed Stock - Main Warehouse",
        help="Seed stock account in main warehouse"
    )
    stock_fertilizers_branch = fields.Many2one(
        'account.account',
        string="Oils & Fuel Stock",
        help="Fertilizer stock account in branch warehouses"
    )
    stock_pesticides_branch = fields.Many2one(
        'account.account',
        string="Pesticide Stock - Branch Warehouses",
        help="Pesticide stock account in branch warehouses"
    )
    stock_seeds_branch = fields.Many2one(
        'account.account',
        string="Seed Stock - Branch Warehouses",
        help="Seed stock account in branch warehouses"
    )
    # ==================== 💰 Cost of Goods Sold/Used Accounts ====================
    cogs_fertilizers = fields.Many2one(
        'account.account',
        string="Fertilizer Cost Used",
        help="Cost account for sold or used fertilizers"
    )
    cogs_pesticides = fields.Many2one(
        'account.account',
        readonly=False,
        string="Pesticide Cost Used",
        help="Cost account for sold or used pesticides"
    )
    cogs_seeds = fields.Many2one(
        'account.account',
        readonly=False,
        string="Seed Cost Used",
        help="Cost account for sold or used seeds"
    )
    # ==================== 🛒 Purchase Accounts ====================
    purchases_account = fields.Many2one(
        'account.account',
        readonly=False,
        string="General Purchases Account",
        help="General purchases account (used when perpetual inventory is not enabled)"
    )
    suppliers_payable = fields.Many2one(
        'account.account',
        readonly=False,
        string="Suppliers Payable Account",
        help="Main account for suppliers"
    )
    # ==================== 📦 Internal Transfer Accounts ====================
    goods_in_transit = fields.Many2one(
        'account.account',
        readonly=False,
        string="Goods in Transit",
        help="Temporary account for goods during inter-warehouse transfer"
    )
    transfer_clearing = fields.Many2one(
        'account.account',
        readonly=False,
        string="Internal Transfer Clearing",
        help="Intermediary account for internal transfer clearing"
    )
    # ==================== 📉 Inventory Adjustment Accounts ====================
    inventory_gain = fields.Many2one(
        'account.account',
        readonly=False,
        string="Inventory Gain",
        help="Account for gains from physical stock exceeding book stock"
    )
    inventory_loss = fields.Many2one(
        'account.account',
        readonly=False,
        string="Inventory Loss",
        help="Account for losses from physical stock below book stock"
    )
    inventory_adjustment = fields.Many2one(
        'account.account',
        string="Inventory Adjustment",
        help="General account for inventory adjustments"
    )
    # ==================== 📊 Stock Valuation Accounts ====================
    stock_valuation_diff = fields.Many2one(
        'account.account',
        string="Stock Valuation Difference",
        help="Account for stock revaluation differences"
    )
    stock_interim = fields.Many2one(
        'account.account',
        string="Interim Stock Account",
        help="Intermediary stock account"
    )
    # ==================== ⚙️ Additional Settings ====================
    auto_post_stock_entries = fields.Boolean(
        string="Auto-Post Stock Entries",
        readonly=False,
        default=True,
        help="If enabled, stock entries will be auto-posted upon confirmation"
    )
    stock_accounting_active = fields.Boolean(
        string="Enable Automatic Stock Accounting",
        readonly=False,
        default=True,
        help="Enable perpetual inventory system and automatic entries"
    )


