# Advanced Agricultural Management for Odoo 18

[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-blueviolet.svg)](https://www.odoo.com)

A comprehensive agricultural management solution for Odoo that covers the full farm-to-warehouse lifecycle.

**Developed by [XAMLTech](https://xamltech.com)**

## Features

### Farm & Location Management
- Hierarchical farm structure: Farm → Sector → Unit → House
- GPS location tracking and area management
- Capacity planning and utilization tracking
- Parent-child navigation with tree and kanban views

### Crop Management
- Full crop lifecycle from planting to harvest
- Crop types, varieties, and growth stage tracking
- Yield analytics per location and season
- Historical crop data and rotation planning

### Harvest Operations
- **Harvest Scheduling** — Plan and manage harvest with Gantt visualization
- **Harvest Sorting & Grading** — Quality-based classification with batch processing
- **Batch Tracking** — Full lot traceability from field to warehouse

### Production Requests
- Agricultural production orders with multi-level approval workflow
- Electronic signatures and authorization tracking
- Template system for recurring operations
- Budget compliance checking

### Cost Allocation
- Multi-level cost center tracking
- Analytic account integration
- Automated cost distribution across farms and projects
- Profit/loss analysis by farm section

### Section-Based Operations Dashboard
- Kanban views for: Production, Cost Centers, Accounting, Warehouses, Workers, Purchasing, Harvest, and Maintenance
- Department-level KPIs and action shortcuts

### Full Odoo ERP Integration
- **Accounting** — Automated journal entries, budget tracking, P&L by farm
- **Inventory** — Multi-warehouse management, lot tracking, stock valuation
- **Purchasing** — RFQs, vendor management, purchase orders
- **HR** — Worker assignment, task tracking
- **Projects** — Project-based farm management with cost tracking
- **Sales** — Customer orders and delivery management

## Dependencies

```
base, product, sale, stock, account, hr, project, mail,
contacts, stock_account, sale_stock, analytic, purchase
```

All dependencies are standard Odoo Community modules — no Enterprise-only requirements.

## Installation

1. Clone this repository into your Odoo addons directory:
   ```bash
   git clone https://github.com/xamltech/agricultural_management.git
   ```

2. Update the module list in Odoo:
   - Go to **Apps** → **Update Apps List**

3. Install the module:
   - Search for "Agricultural Management" in the Apps menu
   - Click **Install**

4. Configure your farm:
   - Go to **Agriculture** → **Configuration** → **Settings**
   - Set up your accounting accounts, journals, and warehouse defaults

## Configuration

### Required Setup
1. **Farm Locations** — Create your farm hierarchy under Agriculture → Farms
2. **Sections** — Define operational sections (Production, Warehouses, etc.)
3. **Security Groups** — Assign users to Agricultural Manager/User/Readonly groups
4. **Accounting** — Configure farm-specific journals and accounts in Settings

### Optional
- Enable email notifications for task assignments
- Configure analytic accounts for cost center tracking
- Set up production request templates for recurring operations

## Support

- **Website**: [https://xamltech.com](https://xamltech.com)
- **Email**: support@xamltech.com
- **Issues**: Report bugs via the repository issue tracker

## License

This module is licensed under [LGPL-3](https://www.gnu.org/licenses/lgpl-3.0).

## Credits

Developed and maintained by **XAMLTech** — Odoo ERP specialists for agriculture and manufacturing.
