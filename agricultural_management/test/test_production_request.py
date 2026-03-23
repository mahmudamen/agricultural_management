# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestProductionRequest(TransactionCase):
    """Test cases for agricultural.production.request model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProductionRequest = cls.env['agricultural.production.request']
        cls.Farm = cls.env['agricultural.farm']

        # Create test farm
        cls.farm = cls.Farm.create({
            'name': 'Production Test Farm',
            'code': 'PTF001',
            'location': 'Test Location',
            'level': 'farm',
        })

        # Get a test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Fertilizer',
            'type': 'product',
            'list_price': 50.0,
            'standard_price': 30.0,
        })

    def test_production_request_creation(self):
        """Test basic production request creation."""
        request = self.ProductionRequest.create({
            'farm_id': self.farm.id,
        })
        self.assertTrue(request.id)
        self.assertEqual(request.farm_id, self.farm)

    def test_production_request_default_state(self):
        """Test that new production requests start in draft state."""
        request = self.ProductionRequest.create({
            'farm_id': self.farm.id,
        })
        self.assertEqual(request.state, 'draft')

    def test_production_request_sequence(self):
        """Test that production requests get a sequence number."""
        request = self.ProductionRequest.create({
            'farm_id': self.farm.id,
        })
        # Should have a name/sequence assigned (not 'New' or False)
        self.assertTrue(request.name)


class TestProductionRequestLine(TransactionCase):
    """Test cases for agricultural.production.request.line model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.RequestLine = cls.env['agricultural.production.request.line']
        cls.Farm = cls.env['agricultural.farm']

        cls.farm = cls.Farm.create({
            'name': 'Line Test Farm',
            'code': 'LTF001',
            'location': 'Test Location',
            'level': 'farm',
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Test Seeds',
            'type': 'product',
            'list_price': 25.0,
            'standard_price': 15.0,
            'uom_id': cls.env.ref('uom.product_uom_kgm').id,
        })

        cls.request = cls.env['agricultural.production.request'].create({
            'farm_id': cls.farm.id,
        })

    def test_request_line_creation(self):
        """Test creating a production request line."""
        line = self.RequestLine.create({
            'request_id': self.request.id,
            'product_id': self.product.id,
            'product_uom_qty': 100.0,
        })
        self.assertTrue(line.id)
        self.assertEqual(line.product_id, self.product)
        self.assertEqual(line.product_uom_qty, 100.0)
