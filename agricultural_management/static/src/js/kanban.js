/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";

export class SectionsKanbanController extends KanbanController {
    setup() {
        super.setup();
        this._setupThemeDetection();
        this._injectCustomStyles(); // Add this line
    }

    _setupThemeDetection() {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
        this._setThemeClass(prefersDark.matches);
        prefersDark.addEventListener('change', (e) => {
            this._setThemeClass(e.matches);
        });
    }

    _setThemeClass(isDark) {
        document.body.classList.remove('light-mode', 'dark-mode');
        document.body.classList.add(isDark ? 'dark-mode' : 'light-mode');
    }

    _injectCustomStyles() {
        // Check if styles already exist to avoid duplicates
        if (!document.getElementById('sections-kanban-custom-styles')) {
            const style = document.createElement('style');
            style.id = 'sections-kanban-custom-styles';
            style.innerHTML = `
                /* Increase text size for all kanban cards */
                .o_kanban_view .o_kanban_record {
                    font-size: 16px !important;
                }

                /* Card headers */
                .o_kanban_view .o_kanban_card_header {
                    font-size: 20px !important;
                    font-weight: bold;
                }

 /* Primary text ( etc.) */
                .o_kanban_view .o_primary {
                    font-size: 22px !important;
                    font-weight: bold;
                }

                /* Status section text */
                .o_kanban_view .status-section {
                    font-size: 18px !important;
                }

                /* Card content */
                .o_kanban_view .o_kanban_card_content {
                    font-size: 16px !important;
                }

                /* Buttons in cards */
                .o_kanban_view .btn {
                    font-size: 16px !important;
                }

                /* Specific for Arabic text */
                .o_kanban_view .o_kanban_record [lang="ar"],
                .o_kanban_view .o_kanban_record:lang(ar) {
                    font-size: 18px !important;
                    line-height: 1.6;
                }

                /* Make sure nested elements inherit the font size */
                .o_kanban_view .oe_kanban_card * {
                    font-size: inherit;
                }

                /* Specific styles for different section types */
                .o_kanban_card_header[data-type="ProductionOperationsManagement"] .o_primary {
                    font-size: 24px !important;
                }

                .o_kanban_card_header[data-type="CostCenter"] .o_primary {
                    font-size: 24px !important;
                }

                .o_kanban_card_header[data-type="Accounting"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="FinishedGoodsWarehouses"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="SortingAndPackingArea"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="RawMaterialsWarehouses"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="AgriculturalWorkers"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="PreSaleWarehouses"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="Rfq"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="Harvest"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="CarWorkshops"] .o_primary {
                    font-size: 24px !important;
                }
                .o_kanban_card_header[data-type="MaintenanceWorkshops"] .o_primary {
                    font-size: 24px !important;
                }

            `;
            document.head.appendChild(style);
        }
    }

    _setupSectionTypes() {
        const headers = this.el.querySelectorAll('.o_kanban_card_header');
        headers.forEach(header => {
            const type = this._getSectionType(header);
            if (type) {
                header.setAttribute('data-type', type);
            }
        });
    }

    _getSectionType(header) {
        const titleText = header.querySelector('.o_primary')?.textContent?.toLowerCase() || '';
 if (titleText.includes('')) return'ProductionOperationsManagement';
 if (titleText.includes('')) return'CostCenter';
 if (titleText.includes('')) return'Accounting';
 if (titleText.includes('')) return'FinishedGoodsWarehouses';
 if (titleText.includes('')) return'RawMaterialsWarehouses';
 if (titleText.includes('')) return'AgriculturalWorkers';
 if (titleText.includes('')) return'PreSaleWarehouses';

 if (titleText.includes('')) return'Rfq';
 if (titleText.includes('')) return'Harvest';
 if (titleText.includes('')) return'CarWorkshops';
 if (titleText.includes('')) return'MaintenanceWorkshops';
        return 'other';
    }

    mounted() {
        super.mounted();
        this._setupSectionTypes();
        // Apply custom font sizes to dynamically loaded content
        this._applyCustomFontSizes();
    }

    _applyCustomFontSizes() {
        // Additional runtime styling if needed
        const cards = this.el.querySelectorAll('.o_kanban_record');
        cards.forEach(card => {
            // You can add inline styles or classes here if needed
            card.style.fontSize = '16px';
        });
    }

    // Override renderer to ensure styles persist on updates
    async onWillUpdateProps() {
        await super.onWillUpdateProps(...arguments);
        this._applyCustomFontSizes();
    }
}

registry.category("views").add("sections_kanban", {
    ...kanbanView,
    Controller: SectionsKanbanController,
});