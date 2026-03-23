# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Product(models.Model):
    _inherit = 'product.template'

    request_type = fields.Selection([
        ('seeds', 'Seeds Request'),
        ('fertilizers', 'Fertilizers Request'),
        ('pesticides', 'Pesticides Request'),
        ('equipment', 'Equipment Request'),
        ('labor', 'Labor Request'),
        ('mixed', 'Mixed Request')
    ], required=False, default='mixed')
    agricultural_product_type = fields.Selection([
        ('Product', 'Finished Product'),
        ('RawMaterials', 'Raw Materials'),
        ('seeds', 'Seeds'),
        ('Pesticides', 'Pesticides'),
        ('SpareParts', 'Spare Parts'),
        ('FillingPackaging', 'Packaging'),
        ('Assets', 'Assets'),
    ], string="Product Type", tracking=True)
    available_in = fields.Selection(selection=[
            ('ProductionOperationsManagement', 'Production & Operations Management'),
            ('CostCenter', 'Cost Centers'),
            ('Accounting', 'General Accounting'),
            ('FinishedGoodsWarehouses', 'Finished Goods Warehouses'),
            ('SortingAndPackingArea', 'Sorting & Packing Area'),
            ('RawMaterialsWarehouses', 'Warehouse Management'),
            ('AgriculturalWorkers', 'Agricultural Workers'),
            ('PreSaleWarehouses', 'Pre-Sale Warehouses'),
            ('Rfq', 'Purchase Requests'),
            ('Harvest', 'Harvest'),
            ('CarWorkshops', 'Vehicle Workshop'),
            ('MaintenanceWorkshops', 'Maintenance Workshop')
        ],required=False,string="Available In", tracking=True
    )
    harvest_schedule_ids = fields.One2many('agricultural.harvest.schedule','crop_id',string='Inventory Stages',copy=False)