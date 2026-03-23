# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestResSections(TransactionCase):
    """Test cases for res.sections model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Section = cls.env['res.sections']

        cls.section = cls.Section.create({
            'name': 'Test Production Section',
            'type': 'ProductionOperationsManagement',
            'code': 'SEC-PROD',
        })

    def test_section_creation(self):
        """Test basic section creation."""
        self.assertTrue(self.section.id)
        self.assertEqual(self.section.name, 'Test Production Section')
        self.assertEqual(self.section.type, 'ProductionOperationsManagement')
        self.assertTrue(self.section.active)

    def test_section_types(self):
        """Test all section types can be created."""
        types = [
            'ProductionOperationsManagement',
            'CostCenter',
            'Accounting',
            'FinishedGoodsWarehouses',
            'SortingAndPackingArea',
            'RawMaterialsWarehouses',
            'AgriculturalWorkers',
            'PreSaleWarehouses',
            'Rfq',
            'Harvest',
            'CarWorkshops',
            'MaintenanceWorkshops',
        ]
        for i, section_type in enumerate(types):
            section = self.Section.create({
                'name': f'Test Section {section_type}',
                'type': section_type,
                'code': f'SEC-{i:03d}',
            })
            self.assertEqual(section.type, section_type)

    def test_section_manager_assignment(self):
        """Test assigning a manager to a section."""
        user = self.env.ref('base.user_admin')
        self.section.manager_id = user.id
        self.assertEqual(self.section.manager_id, user)

    def test_section_user_assignment(self):
        """Test assigning users to a section."""
        user = self.env.ref('base.user_admin')
        self.section.assigned_user_ids = [(4, user.id)]
        self.assertIn(user, self.section.assigned_user_ids)

    def test_section_color_computation(self):
        """Test that section color is computed based on type."""
        # Color should be computed and stored
        self.assertIsInstance(self.section.color, int)

    def test_section_priority(self):
        """Test section priority values."""
        self.section.priority = '0'
        self.assertEqual(self.section.priority, '0')
        self.section.priority = '3'
        self.assertEqual(self.section.priority, '3')

    def test_section_states(self):
        """Test section state transitions."""
        self.section.state = 'draft'
        self.assertEqual(self.section.state, 'draft')

    def test_section_archive(self):
        """Test section archiving."""
        self.section.active = False
        self.assertFalse(self.section.active)
        sections = self.Section.search([('code', '=', 'SEC-PROD')])
        self.assertFalse(sections)

    def test_public_section(self):
        """Test public section flag."""
        self.section.is_public = True
        self.assertTrue(self.section.is_public)


class TestSectionAccess(TransactionCase):
    """Test section-based access control."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Section = cls.env['res.sections']

    def test_section_with_no_users(self):
        """Test section created without assigned users."""
        section = self.Section.create({
            'name': 'Empty Section',
            'type': 'Accounting',
            'code': 'SEC-EMPTY',
        })
        self.assertEqual(len(section.assigned_user_ids), 0)

    def test_section_user_count(self):
        """Test user count computation."""
        section = self.Section.create({
            'name': 'Count Section',
            'type': 'CostCenter',
            'code': 'SEC-COUNT',
        })
        user = self.env.ref('base.user_admin')
        section.assigned_user_ids = [(4, user.id)]
        self.assertEqual(section.user_count, 1)
