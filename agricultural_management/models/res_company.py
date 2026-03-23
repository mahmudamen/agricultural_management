from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cash_receivable_acc = fields.Many2one('account.account',string="Customer Cash Account",
                                          domain="[('account_type', '=', 'asset_receivable'),"
                                                 " ('deprecated', '=', False)]")
    cash_receivable_partner = fields.Many2one('res.partner',string="Company Account",
                                              readonly=False, )
    main_cash_journal = fields.Many2one('account.journal',string="Main Cash Journal",
                                          
                                        domain=[('type', '=', 'cash')])
    main_cash = fields.Many2one('account.account',string="Main Cash Account",
                                  
                                domain="[('account_type', '=', 'asset_cash'), "
                                       "('deprecated', '=', False)]")
    service_exp_account = fields.Many2one('account.account',string="Service Expense Account",
                                            
                                          domain="[('account_type', '=', 'income_other'), ('deprecated', '=', False)]")
    service_tax_account = fields.Many2one('account.account',string="Service Tax Account",
                                            
                                          domain="[('account_type', '=', 'income_other'), ('deprecated', '=', False)]")
    reception_journal = fields.Many2one('account.journal',string="Reception Journal",
                                          
                                        domain=[('type', '=', 'general')])
    engineer_expense_account = fields.Many2one('account.account',string="Engineer Expense Account",
                                           
                                         domain="[('account_type', '=', 'expense'), ('deprecated', '=', False)]")
    engineer_discount_account = fields.Many2one('account.account',string="Engineer Discount Account" )
    operations_journal = fields.Many2one('account.journal',   readonly=False,domain=[('type', '=', 'general')])
    input_deposit_account = fields.Many2one('account.account' ,
                                        readonly=False,string="Input Deposit Account ",
                                        domain="[('account_type', '=', 'liability_payable'),"
                                               " ('deprecated', '=', False)]")
    output_deposit_account = fields.Many2one('account.account' ,string="Output Deposit Account",
                                         readonly=False, domain="[('account_type', '=', 'liability_payable'),"
                                                                " ('deprecated', '=', False)]")
    contract_journal = fields.Many2one('account.journal',
                                       domain=[('type', '=', 'sale')], string="Contracts Journal")

    # Perpetual Inventory System
    inventory_valuation_method = fields.Selection([
        ('average', 'Weighted Average'),
    ], string="Inventory Valuation Method", default='average')

    # Journals
    stock_journal = fields.Many2one('account.journal' )
    stock_valuation_journal = fields.Many2one('account.journal' )
    internal_transfer_journal = fields.Many2one('account.journal' )

    # Stock Accounts - Main Warehouse
    stock_fertilizers_main = fields.Many2one('account.account')
    stock_pesticides_main = fields.Many2one('account.account' )
    stock_seeds_main = fields.Many2one('account.account' )

    # Stock Accounts - Branch Warehouses
    stock_fertilizers_branch = fields.Many2one('account.account' )
    stock_pesticides_branch = fields.Many2one('account.account' )
    stock_seeds_branch = fields.Many2one('account.account' )

    # Cost of Goods Accounts
    cogs_fertilizers = fields.Many2one('account.account' )
    cogs_pesticides = fields.Many2one('account.account' )
    cogs_seeds = fields.Many2one('account.account' )

    # Purchase & Supplier Accounts
    purchases_account = fields.Many2one('account.account' )
    suppliers_payable = fields.Many2one('account.account' )

    # Internal Transfer Accounts
    goods_in_transit = fields.Many2one('account.account' )
    transfer_clearing = fields.Many2one('account.account' )

    # Inventory Adjustment Accounts
    inventory_gain = fields.Many2one('account.account' )
    inventory_loss = fields.Many2one('account.account' )
    inventory_adjustment = fields.Many2one('account.account' )

    # Valuation Accounts
    stock_valuation_diff = fields.Many2one('account.account' )
    stock_interim = fields.Many2one('account.account' )

    # Additional Settings
    auto_post_stock_entries = fields.Boolean(string="Auto-Post Stock Entries", default=True)
    stock_accounting_active = fields.Boolean(string="Enable Automatic Stock Accounting", default=True)


