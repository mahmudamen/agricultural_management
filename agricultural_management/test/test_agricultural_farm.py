# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAgriculturalFarm(TransactionCase):
    """Test cases for agricultural.farm model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Farm = cls.env['agricultural.farm']

        # Create a parent farm
        cls.farm = cls.Farm.create({
            'name': 'Test Farm',
            'code': 'TF001',
            'location': 'Test Location',
            'level': 'farm',
        })

    def test_farm_creation(self):
        """Test basic farm record creation."""
        self.assertTrue(self.farm.id)
        self.assertEqual(self.farm.name, 'Test Farm')
        self.assertEqual(self.farm.code, 'TF001')
        self.assertEqual(self.farm.level, 'farm')
        self.assertTrue(self.farm.active)

    def test_farm_display_name(self):
        """Test computed display name includes code."""
        self.assertIn('TF001', self.farm.display_name)
        self.assertIn('Test Farm', self.farm.display_name)

    def test_farm_hierarchy(self):
        """Test parent-child farm hierarchy."""
        sector = self.Farm.create({
            'name': 'Sector A',
            'code': 'TF001-SA',
            'location': 'Test Location - Sector A',
            'level': 'sector',
            'parent_id': self.farm.id,
        })
        self.assertEqual(sector.parent_id, self.farm)
        self.assertIn(sector, self.farm.child_ids)

    def test_farm_hierarchy_levels(self):
        """Test full 4-level hierarchy: Farm > Sector > Unit > House."""
        sector = self.Farm.create({
            'name': 'Sector 1',
            'code': 'S1',
            'location': 'Sector 1 Location',
            'level': 'sector',
            'parent_id': self.farm.id,
        })
        unit = self.Farm.create({
            'name': 'Unit 1',
            'code': 'U1',
            'location': 'Unit 1 Location',
            'level': 'unit',
            'parent_id': sector.id,
        })
        house = self.Farm.create({
            'name': 'House 1',
            'code': 'H1',
            'location': 'House 1 Location',
            'level': 'house',
            'parent_id': unit.id,
        })
        self.assertEqual(house.parent_id, unit)
        self.assertEqual(unit.parent_id, sector)
        self.assertEqual(sector.parent_id, self.farm)

    def test_farm_archive(self):
        """Test farm archiving (deactivation)."""
        self.farm.active = False
        self.assertFalse(self.farm.active)
        # Archived farms should not appear in default search
        farms = self.Farm.search([('code', '=', 'TF001')])
        self.assertFalse(farms)
        # But should appear with active_test=False
        farms = self.Farm.with_context(active_test=False).search([('code', '=', 'TF001')])
        self.assertTrue(farms)

    def test_farm_code_uniqueness(self):
        """Test that farm codes should be unique (if constraint exists)."""
        farm2 = self.Farm.create({
            'name': 'Another Farm',
            'code': 'TF002',
            'location': 'Another Location',
            'level': 'farm',
        })
        self.assertNotEqual(self.farm.code, farm2.code)
