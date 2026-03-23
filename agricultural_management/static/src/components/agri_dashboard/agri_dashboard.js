/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class AgriDashboard extends Component {
    static template = "agricultural_management.AgriDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.profitChartRef = useRef("profitChart");
        this.costChartRef = useRef("costChart");
        this.yieldChartRef = useRef("yieldChart");

        this.state = useState({
            loading: true,
            period: "year",
            kpis: {
                total_farms: 0,
                total_area: 0,
                total_revenue: 0,
                total_cost: 0,
                net_profit: 0,
                profit_margin: 0,
                active_projects: 0,
                pending_requests: 0,
                harvest_count: 0,
                yield_efficiency: 0,
            },
            farms: [],
            cost_breakdown: { materials: 0, labor: 0, equipment: 0, overhead: 0 },
        });

        this._charts = {};

        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js");
            await this._loadData();
        });

        onMounted(() => this._renderAllCharts());
    }

    async _loadData() {
        try {
            const data = await this.orm.call("agricultural.farm", "get_dashboard_data", []);
            this.state.kpis = data.kpis || this.state.kpis;
            this.state.farms = data.farms || [];
            this.state.cost_breakdown = data.cost_breakdown || this.state.cost_breakdown;
        } catch {
            console.warn("AgriDashboard: get_dashboard_data not available, using defaults");
        }
        this.state.loading = false;
    }

    async onRefresh() {
        this.state.loading = true;
        await this._loadData();
        this._destroyCharts();
        this._renderAllCharts();
    }

    _destroyCharts() {
        Object.values(this._charts).forEach((c) => c && c.destroy());
        this._charts = {};
    }

    _renderAllCharts() {
        this._renderProfitChart();
        this._renderCostChart();
        this._renderYieldChart();
    }

    _renderProfitChart() {
        const el = this.profitChartRef.el;
        if (!el || typeof Chart === "undefined") return;

        const farms = this.state.farms.slice(0, 8);
        this._charts.profit = new Chart(el, {
            type: "bar",
            data: {
                labels: farms.map((f) => f.name),
                datasets: [
                    {
                        label: "Revenue",
                        data: farms.map((f) => f.revenue || 0),
                        backgroundColor: "rgba(46, 125, 50, 0.75)",
                        borderRadius: 6,
                        barPercentage: 0.6,
                    },
                    {
                        label: "Cost",
                        data: farms.map((f) => f.cost || 0),
                        backgroundColor: "rgba(198, 40, 40, 0.75)",
                        borderRadius: 6,
                        barPercentage: 0.6,
                    },
                    {
                        label: "Profit",
                        data: farms.map((f) => f.profit || 0),
                        backgroundColor: "rgba(21, 101, 192, 0.75)",
                        borderRadius: 6,
                        barPercentage: 0.6,
                    },
                ],
            },
            options: this._chartOptions("Revenue vs Cost vs Profit"),
        });
    }

    _renderCostChart() {
        const el = this.costChartRef.el;
        if (!el || typeof Chart === "undefined") return;

        const bd = this.state.cost_breakdown;
        this._charts.cost = new Chart(el, {
            type: "doughnut",
            data: {
                labels: ["Materials", "Labor", "Equipment", "Overhead"],
                datasets: [
                    {
                        data: [bd.materials || 35, bd.labor || 30, bd.equipment || 20, bd.overhead || 15],
                        backgroundColor: [
                            "rgba(52, 152, 219, 0.85)",
                            "rgba(46, 204, 113, 0.85)",
                            "rgba(241, 196, 15, 0.85)",
                            "rgba(155, 89, 182, 0.85)",
                        ],
                        borderWidth: 0,
                        hoverOffset: 8,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "68%",
                plugins: {
                    legend: { position: "bottom", labels: { padding: 16, usePointStyle: true } },
                },
            },
        });
    }

    _renderYieldChart() {
        const el = this.yieldChartRef.el;
        if (!el || typeof Chart === "undefined") return;

        const farms = this.state.farms.slice(0, 8);
        this._charts.yield = new Chart(el, {
            type: "line",
            data: {
                labels: farms.map((f) => f.name),
                datasets: [
                    {
                        label: "Revenue per m\u00B2",
                        data: farms.map((f) => (f.area > 0 ? +(f.revenue / f.area).toFixed(2) : 0)),
                        borderColor: "rgba(46, 125, 50, 1)",
                        backgroundColor: "rgba(46, 125, 50, 0.1)",
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointBackgroundColor: "rgba(46, 125, 50, 1)",
                    },
                    {
                        label: "Cost per m\u00B2",
                        data: farms.map((f) => (f.area > 0 ? +(f.cost / f.area).toFixed(2) : 0)),
                        borderColor: "rgba(198, 40, 40, 1)",
                        backgroundColor: "rgba(198, 40, 40, 0.1)",
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointBackgroundColor: "rgba(198, 40, 40, 1)",
                    },
                ],
            },
            options: this._chartOptions("Yield Efficiency (per m\u00B2)"),
        });
    }

    _chartOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { position: "top", labels: { padding: 12, usePointStyle: true } },
            },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.06)" } },
            },
        };
    }

    // Navigation
    openFarms() {
        this.actionService.doAction("agricultural_management.action_agricultural_farm");
    }
    openProjects() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Agricultural Projects",
            res_model: "agricultural.project",
            view_mode: "list,form",
        });
    }
    openRequests() {
        this.actionService.doAction("agricultural_management.action_agricultural_production_request");
    }
    openHarvest() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Harvest Schedules",
            res_model: "agricultural.harvest.schedule",
            view_mode: "list,form",
        });
    }

    _fmt(num) {
        if (!num) return "0";
        if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
        if (num >= 1000) return (num / 1000).toFixed(1) + "K";
        return num.toLocaleString();
    }
}

registry.category("actions").add("agricultural_dashboard", AgriDashboard);