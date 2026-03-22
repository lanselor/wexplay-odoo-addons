/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class KnowledgeBaseClientAction extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState(this.getInitialState());
        this.initializeFromContext();
        onWillStart(async () => {
            await this.load();
        });
    }

    initializeFromContext() {}

    getInitialState() {
        return {
            loading: true,
            data: {},
            filters: {},
        };
    }

    async load() {}

    async openArticle(ev) {
        const articleId = Number(ev.currentTarget.dataset.articleId);
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "wex.knowledge.article",
            res_id: articleId,
            views: [[false, "form"]],
            target: "current",
            context: {
                wex_kb_explorer_payload: { ...this.state.filters },
            },
        });
    }

    async openNewArticle() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "wex.knowledge.article",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_state: "draft",
                wex_kb_explorer_payload: this.state.filters ? { ...this.state.filters } : {},
            },
        });
    }

    async executeActionXmlId(ev) {
        const xmlId = ev.currentTarget.dataset.actionXmlid;
        const additionalContext = {};
        if (ev.currentTarget.dataset.favoritesOnly === "1") {
            additionalContext.explorer_favorites_only = true;
        }
        if (ev.currentTarget.dataset.categoryId) {
            additionalContext.explorer_category_id = Number(ev.currentTarget.dataset.categoryId);
        }
        if (ev.currentTarget.dataset.search) {
            additionalContext.wex_kb_explorer_payload = { search: ev.currentTarget.dataset.search };
        }
        await this.action.doAction(xmlId, { additionalContext });
    }

    humanStateLabel(state) {
        return {
            draft: "Borrador",
            published: "Publicado",
            archived: "Archivado",
            obsolete: "Obsoleto",
        }[state] || state;
    }

    humanVisibilityLabel(visibility) {
        return {
            private: "Privado",
            internal: "Interno",
            by_group: "Por grupo",
        }[visibility] || visibility;
    }
}

class KnowledgeDashboard extends KnowledgeBaseClientAction {
    getInitialState() {
        return {
            loading: true,
            data: {},
            filters: {},
            dashboardSearch: "",
        };
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("wex.knowledge.article", "get_dashboard_data", []);
        this.state.loading = false;
    }

    onDashboardSearchInput(ev) {
        this.state.dashboardSearch = ev.target.value;
    }

    async submitDashboardSearch() {
        await this.action.doAction("wex_knowledge.action_knowledge_explorer", {
            additionalContext: {
                wex_kb_explorer_payload: {
                    search: (this.state.dashboardSearch || "").trim(),
                },
            },
        });
    }

    async openDashboardCategory(ev) {
        await this.action.doAction("wex_knowledge.action_knowledge_explorer", {
            additionalContext: {
                explorer_category_id: Number(ev.currentTarget.dataset.categoryId),
            },
        });
    }
}

KnowledgeDashboard.template = "wex_knowledge.KnowledgeDashboard";

class KnowledgeExplorer extends KnowledgeBaseClientAction {
    initializeFromContext() {
        const context = this.props.action?.context || {};
        if (context.wex_kb_explorer_payload) {
            Object.assign(this.state.filters, context.wex_kb_explorer_payload);
        }
        if (context.explorer_favorites_only) {
            this.state.filters.favorites_only = true;
        }
        if (context.explorer_category_id) {
            this.state.filters.category_id = context.explorer_category_id;
        }
        if (context.wex_kb_view_mode) {
            this.state.viewMode = context.wex_kb_view_mode;
        }
    }

    getInitialState() {
        return {
            loading: true,
            data: {
                articles: [],
                sidebar: {
                    category_article_tree: [],
                    categories: [],
                    tags: [],
                    authors: [],
                    owners: [],
                    collaborators: [],
                    companies: [],
                },
            },
            expandedNodes: {},
            expandedCategoryNodes: {},
            viewMode: "grid",
            filters: {
                search: "",
                category_id: null,
                tag_id: null,
                author_id: null,
                owner_id: null,
                collaborator_id: null,
                state: "",
                visibility: "",
                favorites_only: false,
                company_id: null,
                article_branch_id: null,
            },
        };
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("wex.knowledge.article", "get_explorer_data", [this.state.filters]);
        this.syncExpandedNodes();
        this.syncExpandedCategoryNodes();
        this.state.loading = false;
    }

    async refreshWithFilter(key, value) {
        this.state.filters[key] = value;
        await this.load();
    }

    async toggleScalarFilter(key, value, emptyValue = null) {
        this.state.filters[key] = this.state.filters[key] === value ? emptyValue : value;
        await this.load();
    }

    syncExpandedNodes() {
        const nextExpanded = { ...this.state.expandedNodes };
        const walk = (nodes, forceOpen = false) => {
            for (const node of nodes || []) {
                if (nextExpanded[node.id] === undefined) {
                    nextExpanded[node.id] = forceOpen || !!node.is_in_selected_path;
                } else if (node.is_in_selected_path) {
                    nextExpanded[node.id] = true;
                }
                walk(node.children || [], false);
            }
        };
        const walkCategories = (categories) => {
            for (const category of categories || []) {
                walk(category.articles || [], false);
                walkCategories(category.children || []);
            }
        };
        walkCategories(this.state.data.sidebar.category_article_tree || []);
        Object.assign(this.state.expandedNodes, nextExpanded);
    }

    syncExpandedCategoryNodes() {
        const nextExpanded = { ...this.state.expandedCategoryNodes };
        const walk = (nodes) => {
            for (const node of nodes || []) {
                if (nextExpanded[node.id] === undefined) {
                    nextExpanded[node.id] = !!node.is_selected;
                }
                if (node.is_selected || (node.children || []).some((child) => child.is_selected)) {
                    nextExpanded[node.id] = true;
                }
                walk(node.children || []);
            }
        };
        walk(this.state.data.sidebar.category_article_tree || []);
        Object.assign(this.state.expandedCategoryNodes, nextExpanded);
    }

    isNodeExpanded(node) {
        return !!this.state.expandedNodes[node.id];
    }

    isCategoryExpanded(node) {
        return !!this.state.expandedCategoryNodes[node.id];
    }

    toggleTreeNode(ev) {
        ev.stopPropagation();
        const nodeId = Number(ev.currentTarget.dataset.nodeId);
        this.state.expandedNodes[nodeId] = !this.state.expandedNodes[nodeId];
    }

    toggleCategoryNode(ev) {
        ev.stopPropagation();
        const nodeId = Number(ev.currentTarget.dataset.nodeId);
        this.state.expandedCategoryNodes[nodeId] = !this.state.expandedCategoryNodes[nodeId];
    }

    async filterByBranch(ev) {
        const nodeId = Number(ev.currentTarget.dataset.nodeId);
        this.state.filters.article_branch_id = this.state.filters.article_branch_id === nodeId ? null : nodeId;
        if (this.state.filters.article_branch_id) {
            this.state.expandedNodes[nodeId] = true;
        }
        await this.load();
    }

    async filterByCategoryNode(ev) {
        const categoryId = Number(ev.currentTarget.dataset.categoryId);
        this.state.filters.category_id = this.state.filters.category_id === categoryId ? null : categoryId;
        if (this.state.filters.category_id) {
            this.state.expandedCategoryNodes[categoryId] = true;
        }
        await this.load();
    }

    get selectedBranchNode() {
        const selectedId = this.state.filters.article_branch_id;
        if (!selectedId) {
            return null;
        }
        const walk = (nodes) => {
            for (const node of nodes || []) {
                if (node.id === selectedId) {
                    return node;
                }
                const childResult = walk(node.children || []);
                if (childResult) {
                    return childResult;
                }
            }
            return null;
        };
        const walkCategories = (categories) => {
            for (const category of categories || []) {
                const ownMatch = walk(category.articles || []);
                if (ownMatch) {
                    return ownMatch;
                }
                const childMatch = walkCategories(category.children || []);
                if (childMatch) {
                    return childMatch;
                }
            }
            return null;
        };
        return walkCategories(this.state.data.sidebar.category_article_tree || []);
    }

    async clearBranchFilter() {
        this.state.filters.article_branch_id = null;
        await this.load();
    }

    get activeFilterChips() {
        const chips = [];
        const sidebar = this.state.data.sidebar || {};
        const pushMappedChip = (key, list, label) => {
            const selectedId = this.state.filters[key];
            if (!selectedId) {
                return;
            }
            const item = (list || []).find((entry) => entry.id === selectedId);
            if (item) {
                chips.push({ key, label, value: item.name, variant: key });
            }
        };

        if (this.state.filters.search) {
            chips.push({ key: "search", label: "Búsqueda", value: this.state.filters.search, variant: "search" });
        }
        if (this.selectedBranchNode) {
            chips.push({ key: "article_branch_id", label: "Rama", value: this.selectedBranchNode.name, variant: "branch" });
        }
        pushMappedChip("category_id", sidebar.categories, "Categoría");
        pushMappedChip("tag_id", sidebar.tags, "Etiqueta");
        pushMappedChip("author_id", sidebar.authors, "Autor");
        if (this.state.filters.state) {
            chips.push({ key: "state", label: "Estado", value: this.humanStateLabel(this.state.filters.state), variant: "state" });
        }
        if (this.state.filters.favorites_only) {
            chips.push({ key: "favorites_only", label: "Vista", value: "Solo favoritos", variant: "favorite" });
        }
        return chips;
    }

    async clearSingleFilter(ev) {
        const key = ev.currentTarget.dataset.filterKey;
        if (!key) {
            return;
        }
        if (key === "favorites_only") {
            this.state.filters.favorites_only = false;
        } else if (key === "search") {
            this.state.filters.search = "";
        } else if (key === "state") {
            this.state.filters.state = "";
        } else {
            this.state.filters[key] = null;
        }
        await this.load();
    }

    onSearchInput(ev) {
        this.state.filters.search = ev.target.value;
    }

    async submitSearch() {
        await this.load();
    }

    async clearFilters() {
        Object.assign(this.state.filters, this.getInitialState().filters);
        await this.load();
    }

    async toggleFavorites() {
        this.state.filters.favorites_only = !this.state.filters.favorites_only;
        await this.load();
    }

    setViewMode(ev) {
        this.state.viewMode = ev.currentTarget.dataset.viewMode;
    }
}

KnowledgeExplorer.template = "wex_knowledge.KnowledgeExplorer";

registry.category("actions").add("wex_knowledge_dashboard", KnowledgeDashboard);
registry.category("actions").add("wex_knowledge_explorer", KnowledgeExplorer);
