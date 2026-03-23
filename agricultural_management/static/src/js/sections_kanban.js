/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Agricultural Sections Enhanced Kanban Controller
 */
class AgriculturalSectionsKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.state = useState({
            isDarkMode: false,
            isLoading: false,
            filterType: 'all',
            sortBy: 'sequence',
            searchQuery: '',
            isGridView: false,
        });

        this.notification = useService("notification");
        this.user = useService("user");
        this.orm = useService("orm");

        this.kanbanRef = useRef("kanban");

        onMounted(() => {
            this.initializeTheme();
            this.initializeAnimations();
            this.setupEventListeners();
            this.loadUserPreferences();
        });

        onWillUnmount(() => {
            this.cleanupEventListeners();
        });
    }

    /**
     * Initialize theme based on user preference or system
     */
    initializeTheme() {
        try {
            const savedTheme = localStorage.getItem('agricultural-kanban-theme');
            const systemDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

            const isDark = savedTheme === 'dark' || (!savedTheme && systemDarkMode);
            this.toggleTheme(isDark);

            // Listen for system theme changes
            if (window.matchMedia) {
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                    if (!localStorage.getItem('agricultural-kanban-theme')) {
                        this.toggleTheme(e.matches);
                    }
                });
            }
        } catch (error) {
            console.warn('Error initializing theme:', error);
        }
    }

    /**
     * Toggle between light and dark themes
     */
    toggleTheme(forceDark = null) {
        try {
            const isDark = forceDark !== null ? forceDark : !this.state.isDarkMode;
            this.state.isDarkMode = isDark;

            document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
            localStorage.setItem('agricultural-kanban-theme', isDark ? 'dark' : 'light');

            if (this.notification) {
                this.notification.add(
 isDark ?'' :'',
                    { type: 'info', sticky: false }
                );
            }
        } catch (error) {
            console.warn('Error toggling theme:', error);
        }
    }

    /**
     * Initialize entrance animations for cards
     */
    initializeAnimations() {
        try {
            if (typeof IntersectionObserver !== 'undefined') {
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach((entry, index) => {
                        if (entry.isIntersecting) {
                            setTimeout(() => {
                                if (entry.target && entry.target.classList) {
                                    entry.target.classList.add('fade-in');
                                }
                            }, index * 100);
                        }
                    });
                }, { threshold: 0.1 });

                // Observe all kanban cards with a delay
                setTimeout(() => {
                    const cards = document.querySelectorAll('.o_agricultural_section_card');
                    cards.forEach(card => {
                        if (card) observer.observe(card);
                    });
                }, 100);
            }
        } catch (error) {
            console.warn('Error initializing animations:', error);
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        try {
            // Keyboard shortcuts
            this.keydownHandler = this.handleKeyboardShortcuts.bind(this);
            document.addEventListener('keydown', this.keydownHandler);

            // Window resize handler
            this.resizeHandler = this.handleResize.bind(this);
            window.addEventListener('resize', this.resizeHandler);

            // Theme toggle on Alt + T
            this.themeToggleListener = (e) => {
                if (e.altKey && e.key === 't') {
                    e.preventDefault();
                    this.toggleTheme();
                }
            };
            document.addEventListener('keydown', this.themeToggleListener);
        } catch (error) {
            console.warn('Error setting up event listeners:', error);
        }
    }

    /**
     * Cleanup event listeners
     */
    cleanupEventListeners() {
        try {
            if (this.keydownHandler) {
                document.removeEventListener('keydown', this.keydownHandler);
            }
            if (this.themeToggleListener) {
                document.removeEventListener('keydown', this.themeToggleListener);
            }
            if (this.resizeHandler) {
                window.removeEventListener('resize', this.resizeHandler);
            }
        } catch (error) {
            console.warn('Error cleaning up event listeners:', error);
        }
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(event) {
        try {
            // Ctrl + F for search focus
            if (event.ctrlKey && event.key === 'f') {
                event.preventDefault();
                const searchInput = document.querySelector('.o_searchview_input');
                if (searchInput && searchInput.focus) searchInput.focus();
            }

            // Escape to clear search
            if (event.key === 'Escape') {
                this.clearSearch();
            }

            // Arrow keys for card navigation
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
                this.handleCardNavigation(event);
            }
        } catch (error) {
            console.warn('Error handling keyboard shortcuts:', error);
        }
    }

    /**
     * Handle window resize
     */
    handleResize() {
        try {
            clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(() => {
                this.adjustLayoutForViewport();
            }, 250);
        } catch (error) {
            console.warn('Error handling resize:', error);
        }
    }

    /**
     * Adjust layout based on viewport size
     */
    adjustLayoutForViewport() {
        try {
            const viewport = window.innerWidth;
            const cards = document.querySelectorAll('.o_agricultural_section_card');

            cards.forEach(card => {
                if (card && card.classList) {
                    if (viewport < 768) {
                        card.classList.add('mobile-layout');
                    } else {
                        card.classList.remove('mobile-layout');
                    }
                }
            });
        } catch (error) {
            console.warn('Error adjusting layout:', error);
        }
    }

    /**
     * Load user preferences
     */
    async loadUserPreferences() {
        try {
            if (this.orm && this.user) {
                const preferences = await this.orm.call(
                    'res.users',
                    'get_kanban_preferences',
                    [this.user.userId]
                );

                if (preferences) {
                    this.state.sortBy = preferences.sort_by || 'sequence';
                    this.state.filterType = preferences.filter_type || 'all';
                    this.state.isGridView = preferences.is_grid_view || false;
                }
            }
        } catch (error) {
            console.warn('Could not load user preferences:', error);
        }
    }

    /**
     * Save user preferences
     */
    async saveUserPreferences() {
        try {
            if (this.orm && this.user) {
                await this.orm.call('res.users', 'save_kanban_preferences', [this.user.userId], {
                    sort_by: this.state.sortBy,
                    filter_type: this.state.filterType,
                    is_grid_view: this.state.isGridView,
                });
            }
        } catch (error) {
            console.warn('Could not save user preferences:', error);
        }
    }

    /**
     * Handle card navigation with keyboard
     */
    handleCardNavigation(event) {
        try {
            const cards = Array.from(document.querySelectorAll('.o_agricultural_section_card'));
            const activeCard = document.activeElement && document.activeElement.closest
                ? document.activeElement.closest('.o_agricultural_section_card')
                : null;

            if (!activeCard || cards.length === 0) return;

            const currentIndex = cards.indexOf(activeCard);
            let nextIndex = currentIndex;

            switch (event.key) {
                case 'ArrowUp':
                    nextIndex = Math.max(0, currentIndex - 3);
                    break;
                case 'ArrowDown':
                    nextIndex = Math.min(cards.length - 1, currentIndex + 3);
                    break;
                case 'ArrowLeft':
                    nextIndex = Math.max(0, currentIndex - 1);
                    break;
                case 'ArrowRight':
                    nextIndex = Math.min(cards.length - 1, currentIndex + 1);
                    break;
            }

            if (nextIndex !== currentIndex && cards[nextIndex]) {
                event.preventDefault();
                if (cards[nextIndex].focus) cards[nextIndex].focus();
                if (cards[nextIndex].scrollIntoView) {
                    cards[nextIndex].scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                }
            }
        } catch (error) {
            console.warn('Error handling card navigation:', error);
        }
    }

    /**
     * Clear search
     */
    clearSearch() {
        try {
            this.state.searchQuery = '';
            const searchInput = document.querySelector('.o_searchview_input');
            if (searchInput) {
                searchInput.value = '';
                if (searchInput.dispatchEvent) {
                    searchInput.dispatchEvent(new Event('input'));
                }
            }
        } catch (error) {
            console.warn('Error clearing search:', error);
        }
    }
}

/**
 * Enhanced Kanban Renderer with custom features
 */
class AgriculturalSectionsKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.state = useState({
            hoveredCard: null,
            expandedCards: new Set(),
        });
    }

    /**
     * Handle card hover
     */
    onCardHover(recordId, isHovering) {
        try {
            this.state.hoveredCard = isHovering ? recordId : null;

            const card = document.querySelector(`[data-id="${recordId}"]`);
            if (card && card.classList) {
                if (isHovering) {
                    card.classList.add('card-hover');
                    // Add subtle animation to buttons
                    const buttons = card.querySelectorAll('.btn');
                    buttons.forEach((btn, index) => {
                        setTimeout(() => {
                            if (btn && btn.classList) {
                                btn.classList.add('slide-in');
                            }
                        }, index * 50);
                    });
                } else {
                    card.classList.remove('card-hover');
                    const buttons = card.querySelectorAll('.btn');
                    buttons.forEach(btn => {
                        if (btn && btn.classList) {
                            btn.classList.remove('slide-in');
                        }
                    });
                }
            }
        } catch (error) {
            console.warn('Error handling card hover:', error);
        }
    }

    /**
     * Toggle card expansion
     */
    toggleCardExpansion(recordId) {
        try {
            if (this.state.expandedCards.has(recordId)) {
                this.state.expandedCards.delete(recordId);
            } else {
                this.state.expandedCards.add(recordId);
            }

            const card = document.querySelector(`[data-id="${recordId}"]`);
            if (card && card.classList) {
                card.classList.toggle('expanded', this.state.expandedCards.has(recordId));
            }
        } catch (error) {
            console.warn('Error toggling card expansion:', error);
        }
    }
}

/**
 * Custom Kanban View Registration
 */
export const agriculturalSectionsKanbanView = {
    ...kanbanView,
    Controller: AgriculturalSectionsKanbanController,
    Renderer: AgriculturalSectionsKanbanRenderer,
};

registry.category("views").add("agricultural_sections_kanban", agriculturalSectionsKanbanView);

/**
 * Theme Toggle Component for toolbar
 */
class ThemeToggle extends Component {
    static template = "agricultural_management.ThemeToggle";

    setup() {
        this.state = useState({
            isDarkMode: document.documentElement.getAttribute('data-theme') === 'dark'
        });
    }

    toggleTheme() {
        try {
            this.state.isDarkMode = !this.state.isDarkMode;
            document.documentElement.setAttribute('data-theme', this.state.isDarkMode ? 'dark' : 'light');
            localStorage.setItem('agricultural-kanban-theme', this.state.isDarkMode ? 'dark' : 'light');
        } catch (error) {
            console.warn('Error toggling theme:', error);
        }
    }
}

ThemeToggle.template = `
    <button class="btn btn-sm btn-outline-secondary theme-toggle"
            t-on-click="toggleTheme"
 title="/">
        <i t-if="state.isDarkMode" class="fa fa-sun"/>
        <i t-else="" class="fa fa-moon"/>
    </button>
`;

/**
 * Utility Functions
 */
export const KanbanUtils = {

    /**
     * Animate card entrance
     */
    animateCardEntrance(element, delay = 0) {
        try {
            if (!element || !element.style) return;

            setTimeout(() => {
                element.style.opacity = '0';
                element.style.transform = 'translateY(20px)';
                element.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';

                requestAnimationFrame(() => {
                    element.style.opacity = '1';
                    element.style.transform = 'translateY(0)';
                });
            }, delay);
        } catch (error) {
            console.warn('Error animating card entrance:', error);
        }
    },

    /**
     * Create ripple effect on button click - Fixed version
     */
    createRippleEffect(event) {
        try {
            // Ensure we have a valid event and target
            if (!event || !event.currentTarget) {
                console.warn('Invalid event or target for ripple effect');
                return;
            }

            const button = event.currentTarget;

            // Check if button is a valid DOM element
            if (!button || typeof button.getBoundingClientRect !== 'function') {
                console.warn('Invalid button element for ripple effect');
                return;
            }

            const rect = button.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = event.clientX - rect.left - size / 2;
            const y = event.clientY - rect.top - size / 2;

            const ripple = document.createElement('span');
            if (!ripple) return;

            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.5);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
                z-index: 1;
            `;

            // Ensure button has proper positioning
            const buttonStyle = window.getComputedStyle(button);
            if (buttonStyle.position === 'static') {
                button.style.position = 'relative';
            }
            button.style.overflow = 'hidden';

            // Add ripple to button
            button.appendChild(ripple);

            // Remove ripple after animation completes
            setTimeout(() => {
                if (ripple && ripple.parentNode) {
                    ripple.parentNode.removeChild(ripple);
                }
            }, 600);

        } catch (error) {
            console.warn('Error creating ripple effect:', error);
        }
    },

    /**
     * Format numbers with Arabic numerals
     */
    formatArabicNumber(number) {
        try {
 const arabicNumerals ='';
            return number.toString().replace(/\d/g, (digit) => arabicNumerals[digit]);
        } catch (error) {
            console.warn('Error formatting Arabic number:', error);
            return number.toString();
        }
    },

    /**
     * Get section type display name in Arabic
     */
    getSectionTypeDisplayName(type) {
        try {
            const typeMap = {
'ProductionOperationsManagement':'',
'CostCenter':'',
'AgriculturalWorkers':'',
'PreSaleWarehouses':'',
'RawMaterialsWarehouses':'',
'FinishedGoodsWarehouses':'',
'Rfq':'',
'SortingAndPackingArea':'',
'Harvest':'',
'CarWorkshops':'',
'MaintenanceWorkshops':'',
'Accounting':''
            };

            return typeMap[type] || type;
        } catch (error) {
            console.warn('Error getting section type display name:', error);
            return type;
        }
    },

    /**
     * Get priority badge class
     */
    getPriorityBadgeClass(priority) {
        try {
            const priorityClasses = {
                '3': 'badge-danger',
                '2': 'badge-warning',
                '1': 'badge-info',
                '0': 'badge-secondary'
            };

            return priorityClasses[priority] || 'badge-secondary';
        } catch (error) {
            console.warn('Error getting priority badge class:', error);
            return 'badge-secondary';
        }
    },

    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            try {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            } catch (error) {
                console.warn('Error in debounced function:', error);
            }
        };
    },

    /**
     * Throttle function
     */
    throttle(func, limit) {
        let inThrottle;
        return function() {
            try {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            } catch (error) {
                console.warn('Error in throttled function:', error);
            }
        };
    },

    /**
     * Safe DOM query selector
     */
    safeQuerySelector(selector) {
        try {
            return document.querySelector(selector);
        } catch (error) {
            console.warn('Error in querySelector:', error);
            return null;
        }
    },

    /**
     * Safe DOM query selector all
     */
    safeQuerySelectorAll(selector) {
        try {
            return document.querySelectorAll(selector);
        } catch (error) {
            console.warn('Error in querySelectorAll:', error);
            return [];
        }
    }
};

/**
 * Performance Monitor for Kanban
 */
export class KanbanPerformanceMonitor {
    constructor() {
        this.metrics = {
            renderTime: 0,
            buttonClicks: 0,
            cardHovers: 0,
            themeToggles: 0,
            errors: 0
        };
        this.startTime = performance.now();
    }

    recordRenderTime() {
        try {
            this.metrics.renderTime = performance.now() - this.startTime;
        } catch (error) {
            console.warn('Error recording render time:', error);
        }
    }

    recordButtonClick() {
        try {
            this.metrics.buttonClicks++;
        } catch (error) {
            console.warn('Error recording button click:', error);
        }
    }

    recordCardHover() {
        try {
            this.metrics.cardHovers++;
        } catch (error) {
            console.warn('Error recording card hover:', error);
        }
    }

    recordThemeToggle() {
        try {
            this.metrics.themeToggles++;
        } catch (error) {
            console.warn('Error recording theme toggle:', error);
        }
    }

    recordError() {
        try {
            this.metrics.errors++;
        } catch (error) {
            console.warn('Error recording error metric:', error);
        }
    }

    getMetrics() {
        try {
            return {
                ...this.metrics,
                totalTime: performance.now() - this.startTime
            };
        } catch (error) {
            console.warn('Error getting metrics:', error);
            return this.metrics;
        }
    }

    logMetrics() {
        try {
            console.group('🌾 Agricultural Kanban Performance Metrics');
            console.log('⏱️ Render Time:', `${this.metrics.renderTime.toFixed(2)}ms`);
            console.log('🖱️ Button Clicks:', this.metrics.buttonClicks);
            console.log('👆 Card Hovers:', this.metrics.cardHovers);
            console.log('🌙 Theme Toggles:', this.metrics.themeToggles);
            console.log('❌ Errors:', this.metrics.errors);
            console.log('⏰ Total Session Time:', `${((performance.now() - this.startTime) / 1000).toFixed(2)}s`);
            console.groupEnd();
        } catch (error) {
            console.warn('Error logging metrics:', error);
        }
    }
}

/**
 * Accessibility Enhancements
 */
export const KanbanAccessibility = {

    /**
     * Add ARIA labels and roles
     */
    enhanceAccessibility() {
        try {
            // Add roles and labels to cards
            const cards = KanbanUtils.safeQuerySelectorAll('.o_agricultural_section_card');
            cards.forEach((card, index) => {
                if (card && card.setAttribute) {
                    card.setAttribute('role', 'article');
                    card.setAttribute('tabindex', '0');
 card.setAttribute('aria-label', ` ${index + 1}`);
                }
            });

            // Add labels to buttons
            const buttons = KanbanUtils.safeQuerySelectorAll('.action-buttons .btn');
            buttons.forEach(button => {
                if (button && button.setAttribute) {
                    const icon = button.querySelector('i');
                    const text = button.textContent ? button.textContent.trim() : '';
                    if (icon && text) {
                        button.setAttribute('aria-label', text);
                    }
                }
            });

            // Add keyboard navigation hints
            const helpText = document.createElement('div');
            if (helpText) {
                helpText.id = 'keyboard-help';
                helpText.className = 'sr-only';
 helpText.textContent =' Enter';
                document.body.appendChild(helpText);
            }
        } catch (error) {
            console.warn('Error enhancing accessibility:', error);
        }
    },

    /**
     * Handle keyboard navigation
     */
    setupKeyboardNavigation() {
        try {
            const keydownHandler = (event) => {
                try {
                    if (event.target && event.target.classList && event.target.classList.contains('o_agricultural_section_card')) {
                        switch (event.key) {
                            case 'Enter':
                            case ' ':
                                event.preventDefault();
                                const firstButton = event.target.querySelector('.btn');
                                if (firstButton && firstButton.click) firstButton.click();
                                break;
                            case 'Tab':
                                // Let default tab behavior handle focus
                                break;
                        }
                    }
                } catch (error) {
                    console.warn('Error in keyboard navigation handler:', error);
                }
            };

            document.addEventListener('keydown', keydownHandler);
        } catch (error) {
            console.warn('Error setting up keyboard navigation:', error);
        }
    },

    /**
     * Add high contrast mode support
     */
    setupHighContrast() {
        try {
            if (window.matchMedia) {
                const mediaQuery = window.matchMedia('(prefers-contrast: high)');

                const handleContrastChange = (e) => {
                    try {
                        if (e.matches) {
                            document.body.classList.add('high-contrast');
                        } else {
                            document.body.classList.remove('high-contrast');
                        }
                    } catch (error) {
                        console.warn('Error handling contrast change:', error);
                    }
                };

                mediaQuery.addEventListener('change', handleContrastChange);
                handleContrastChange(mediaQuery);
            }
        } catch (error) {
            console.warn('Error setting up high contrast:', error);
        }
    }
};

/**
 * Safe DOM Ready Handler
 */
function safeDocumentReady(callback) {
    try {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback);
        } else {
            callback();
        }
    } catch (error) {
        console.warn('Error in document ready handler:', error);
        // Fallback: try to execute callback anyway
        try {
            callback();
        } catch (callbackError) {
            console.warn('Error executing callback:', callbackError);
        }
    }
}

/**
 * Initialize all enhancements when DOM is ready
 */
safeDocumentReady(() => {
    try {
        // Initialize accessibility features
        KanbanAccessibility.enhanceAccessibility();
        KanbanAccessibility.setupKeyboardNavigation();
        KanbanAccessibility.setupHighContrast();

        // Initialize performance monitoring
        const performanceMonitor = new KanbanPerformanceMonitor();

        // Log performance metrics after 5 seconds
        setTimeout(() => {
            performanceMonitor.logMetrics();
        }, 5000);

        // Add ripple effect to all buttons with error handling
        const clickHandler = (event) => {
            try {
                if (event.target && event.target.classList && event.target.classList.contains('btn')) {
                    KanbanUtils.createRippleEffect(event);
                    performanceMonitor.recordButtonClick();
                }
            } catch (error) {
                console.warn('Error in click handler:', error);
                performanceMonitor.recordError();
            }
        };

        document.addEventListener('click', clickHandler);

        // Track card hovers with error handling
        const mouseenterHandler = (event) => {
            try {
                if (event.target && event.target.classList && event.target.classList.contains('o_agricultural_section_card')) {
                    performanceMonitor.recordCardHover();
                }
            } catch (error) {
                console.warn('Error in mouseenter handler:', error);
                performanceMonitor.recordError();
            }
        };

        document.addEventListener('mouseenter', mouseenterHandler, true);

        console.log('🌾 Agricultural Sections Kanban Enhanced - Ready!');

        // Make performance monitor available globally for debugging
        window.KanbanPerformanceMonitor = performanceMonitor;

    } catch (error) {
        console.error('Error initializing kanban enhancements:', error);
    }
});

// Global error handler for unhandled errors
window.addEventListener('error', (event) => {
    console.warn('Global error caught:', event.error);
    if (window.KanbanPerformanceMonitor && window.KanbanPerformanceMonitor.recordError) {
        window.KanbanPerformanceMonitor.recordError();
    }
});

// Global error handler for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.warn('Unhandled promise rejection caught:', event.reason);
    if (window.KanbanPerformanceMonitor && window.KanbanPerformanceMonitor.recordError) {
        window.KanbanPerformanceMonitor.recordError();
    }
});