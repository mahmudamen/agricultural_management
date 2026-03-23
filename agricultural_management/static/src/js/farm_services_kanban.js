/** @odoo-module **/

import { KanbanRecord } from '@web/views/kanban/kanban_record';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, onPatched } from "@odoo/owl";

export class FarmServiceKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.state = useState({
            isExpanded: false,
            showDetails: false,
            isAnimating: false,
        });

        onMounted(() => {
            this.initializeCard();
        });

        onPatched(() => {
            this.updateProgressBars();
        });
    }

    initializeCard() {
        const card = this.el.querySelector('.fs_kanban_card');
        if (!card) return;

        // Add stagger animation delay
        const cards = document.querySelectorAll('.fs_kanban_card');
        const index = Array.from(cards).indexOf(card);
        card.style.animationDelay = `${index * 0.1}s`;

        // Initialize progress bar animation
        this.animateProgressBar();

        // Add entrance animation class
        setTimeout(() => {
            card.classList.add('ds_card_loaded');
        }, 100);
    }

    animateProgressBar() {
        const progressFill = this.el.querySelector('.ds_progress_fill');
        if (!progressFill) return;

        const percentage = progressFill.getAttribute('data-percentage') ||
                          progressFill.style.width.replace('%', '');

        // Reset and animate
        progressFill.style.width = '0%';
        progressFill.style.opacity = '0';

        setTimeout(() => {
            progressFill.style.transition = 'width 1.5s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.8s ease';
            progressFill.style.width = `${percentage}%`;
            progressFill.style.opacity = '1';
        }, 200);
    }

    updateProgressBars() {
        // Update progress bars when data changes
        const progressFill = this.el.querySelector('.ds_progress_fill');
        if (progressFill && !this.state.isAnimating) {
            this.animateProgressBar();
        }
    }

    onGlobalClick(ev) {
        // Create ripple effect on click
        this.createDSRipple(ev);

        // Add click feedback
        const card = this.el.querySelector('.fs_kanban_card');
        if (card) {
            card.style.transform = 'translateY(-8px) scale(0.98)';
            setTimeout(() => {
                card.style.transform = '';
            }, 150);
        }

        super.onGlobalClick(ev);
    }

    createDSRipple(event) {
        const card = event.currentTarget;
        const rect = card.getBoundingClientRect();
        const ripple = document.createElement('div');
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ds_ripple');

        card.style.position = 'relative';
        card.appendChild(ripple);

        setTimeout(() => {
            if (ripple.parentNode) {
                ripple.remove();
            }
        }, 600);
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
        this.state.isExpanded = !this.state.isExpanded;

        const card = this.el.querySelector('.fs_kanban_card');
        if (card) {
            card.classList.toggle('ds_expanded', this.state.isExpanded);
        }

        if (this.state.showDetails) {
 this.notification.add("", {
                type: "info",
                duration: 2000,
            });
        }
    }

    getDoctorPercentage() {
        const record = this.props.record;
        const amount = record.data.amount || 0;
        const engineerAmount = record.data.engineer_amount || 0;

        if (amount > 0) {
            return Math.round((engineerAmount / amount) * 100);
        }
        return 0;
    }

    getFinancialSummary() {
        const record = this.props.record;
        return {
            amount: record.data.amount || 0,
            engineerAmount: record.data.engineer_amount || 0,
            expAmount: record.data.exp_amount || 0,
            taxAmount: record.data.tax_amount || 0,
            totalAmount: record.data.total_amount || 0,
            percentage: this.getDoctorPercentage(),
        };
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('ar-EG', {
            style: 'currency',
            currency: 'EGP',
            minimumFractionDigits: 2,
        }).format(amount);
    }

    onAmountHover(ev) {
        const item = ev.currentTarget;
        const icon = item.querySelector('.ds_amount_icon');
        if (icon) {
            icon.style.transform = 'rotate(360deg) scale(1.1)';
            setTimeout(() => {
                icon.style.transform = '';
            }, 500);
        }
    }

    onBadgeClick(ev) {
        ev.stopPropagation();
        const badge = ev.currentTarget;
        const type = badge.textContent.trim();

 this.notification.add(` : ${type}`, {
            type: "info",
            duration: 1500,
        });

        // Add click animation
        badge.style.transform = 'scale(0.95)';
        setTimeout(() => {
            badge.style.transform = '';
        }, 100);
    }
}

export class FarmServiceKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    onRecordClick(record, ev) {
        // Enhanced record click handling
 const serviceName = record.data.service_id ? record.data.service_id[1] :'';
 const engineerName = record.data.engineer_id ? record.data.engineer_id[1] :'';
        const amount = record.data.total_amount || 0;

 this.notification.add(` : ${serviceName} - : ${engineerName} - : ${amount} .`, {
            type: "success",
            duration: 3000,
        });

        // Add visual feedback
        const cardElement = ev.target.closest('.fs_kanban_card');
        if (cardElement) {
            cardElement.classList.add('ds_selected');
            setTimeout(() => {
                cardElement.classList.remove('ds_selected');
            }, 1000);
        }
    }

    onGroupClick(group) {
 const engineerName = group.name ||'';
 this.notification.add(` : ${engineerName}`, {
            type: "info",
            duration: 2000,
        });
    }

    async refreshView() {
        // Custom refresh with animation
        const cards = document.querySelectorAll('.fs_kanban_card');
        cards.forEach((card, index) => {
            card.style.animation = `ds_fadeOut 0.3s ease-out forwards`;
            setTimeout(() => {
                card.style.animation = '';
            }, 300 + (index * 50));
        });

        await super.reload();

 this.notification.add("", {
            type: "success",
            duration: 2000,
        });
    }
}

// Register the custom components
registry.category("views").add("farm_service_kanban", {
    type: "kanban",
    display_name: "Doctor Service Kanban",
    icon: "fa fa-th-large",
    multiEdit: false,
    Controller: FarmServiceKanbanController,
    Record: FarmServiceKanbanRecord,
});

// Utility functions for farm service kanban
const DSKanbanUtils = {
    // Format percentage with Arabic numerals
    formatPercentage(value) {
 const arabicNumerals ='';
        const englishNumerals = '0123456789';
        let result = Math.round(value).toString();

        for (let i = 0; i < englishNumerals.length; i++) {
            result = result.replace(new RegExp(englishNumerals[i], 'g'), arabicNumerals[i]);
        }

        return result + '%';
    },

    // Get status color based on account type
    getStatusColor(accountType) {
        const colors = {
            'cash': '#48bb78',
            'contract': '#4299e1',
            'default': '#718096'
        };
        return colors[accountType] || colors.default;
    },

    // Calculate financial metrics
    calculateMetrics(record) {
        const amount = record.amount || 0;
        const engineerAmount = record.engineer_amount || 0;
        const expAmount = record.exp_amount || 0;
        const taxAmount = record.tax_amount || 0;

        return {
            engineerPercentage: amount > 0 ? (engineerAmount / amount) * 100 : 0,
            profitMargin: amount > 0 ? ((amount - engineerAmount - expAmount - taxAmount) / amount) * 100 : 0,
            totalCosts: engineerAmount + expAmount + taxAmount,
            netProfit: amount - engineerAmount - expAmount - taxAmount
        };
    },

    // Animate card entrance
    animateCardEntrance(card, delay = 0) {
        if (!card) return;

        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';

        setTimeout(() => {
            card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, delay);
    },

    // Create notification for financial alerts
    createFinancialAlert(record, notificationService) {
        const metrics = this.calculateMetrics(record.data);

        if (metrics.engineerPercentage > 80) {
 notificationService.add(":", {
                type: "warning",
                duration: 4000,
            });
        }

        if (metrics.netProfit < 0) {
 notificationService.add(":", {
                type: "danger",
                duration: 4000,
            });
        }
    }
};

// Enhanced styling and animations
const dsKanbanStyle = document.createElement('style');
dsKanbanStyle.textContent = `
    /* Additional animations for farm service cards */
    @keyframes ds_fadeOut {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-20px);
        }
    }

    .ds_selected {
        transform: translateY(-8px) scale(1.05) !important;
        box-shadow: 0 16px 40px rgba(102, 126, 234, 0.4) !important;
        z-index: 10;
    }

    .ds_card_loaded {
        animation: ds_cardBounce 0.6s ease-out;
    }

    @keyframes ds_cardBounce {
        0% {
            transform: scale(0.8);
            opacity: 0;
        }
        60% {
            transform: scale(1.05);
            opacity: 0.9;
        }
        100% {
            transform: scale(1);
            opacity: 1;
        }
    }

    /* Progress bar enhanced animations */
    .ds_progress_fill[data-percentage="100"] {
        background: linear-gradient(90deg, #48bb78 0%, #38a169 100%);
        animation: ds_successPulse 2s ease-in-out infinite;
    }

    @keyframes ds_successPulse {
        0%, 100% {
            box-shadow: 0 2px 8px rgba(72, 187, 120, 0.4);
        }
        50% {
            box-shadow: 0 2px 16px rgba(72, 187, 120, 0.6);
        }
    }

    /* Warning states */
    .fs_kanban_card[data-warning="high-percentage"] .ds_progress_fill {
        background: linear-gradient(90deg, #ed8936 0%, #dd6b20 100%);
    }

    .fs_kanban_card[data-warning="negative-profit"] {
        border-left: 4px solid #e53e3e;
    }

    /* Hover enhancements */
    .ds_amount_item:hover .ds_amount_icon {
        animation: ds_iconRotate 0.5s ease-in-out;
    }

    @keyframes ds_iconRotate {
        0% { transform: rotate(0deg) scale(1); }
        50% { transform: rotate(360deg) scale(1.1); }
        100% { transform: rotate(360deg) scale(1); }
    }

    /* Loading states */
    .fs_kanban_card.ds_loading {
        opacity: 0.7;
        pointer-events: none;
    }

    .fs_kanban_card.ds_loading::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        animation: ds_loadingShimmer 1.5s infinite;
    }

    @keyframes ds_loadingShimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
`;

document.head.appendChild(dsKanbanStyle);

// Initialize enhanced features when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Add intersection observer for card animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting && entry.target.classList.contains('fs_kanban_card')) {
                const delay = Array.from(entry.target.parentElement.children).indexOf(entry.target) * 100;
                DSKanbanUtils.animateCardEntrance(entry.target, delay);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '50px'
    });

    // Observe all farm service cards
    const observeCards = () => {
        document.querySelectorAll('.fs_kanban_card').forEach(card => {
            observer.observe(card);
        });
    };

    // Initial observation
    observeCards();

    // Re-observe on dynamic content changes
    const mutationObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                observeCards();
            }
        });
    });

    const kanbanContainer = document.querySelector('.fs_kanban_view');
    if (kanbanContainer) {
        mutationObserver.observe(kanbanContainer, {
            childList: true,
            subtree: true
        });
    }
});

// Export everything for module use
export {
    FarmServiceKanbanRecord,
    FarmServiceKanbanController,
    DSKanbanUtils
};