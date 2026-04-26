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

    getExplorerPayloadContext() {
        return { ...this.state.filters };
    }

    getArticleAction(articleId = false, extraContext = {}) {
        return {
            type: "ir.actions.act_window",
            res_model: "wex.knowledge.article",
            res_id: articleId || false,
            views: [[false, articleId ? "form" : "form"]],
            target: "current",
            context: {
                ...extraContext,
                wex_kb_explorer_payload: this.getExplorerPayloadContext(),
            },
        };
    }

    async openArticle(ev) {
        const articleId = Number(ev.currentTarget.dataset.articleId);
        await this.action.doAction(this.getArticleAction(articleId));
    }

    async openNewArticle() {
        await this.action.doAction(
            this.getArticleAction(false, {
                default_state: "draft",
            })
        );
    }

    getXmlActionAdditionalContext(ev) {
        const context = {};
        if (ev.currentTarget.dataset.favoritesOnly === "1") {
            context.explorer_favorites_only = true;
        }
        if (ev.currentTarget.dataset.categoryId) {
            context.explorer_category_id = Number(ev.currentTarget.dataset.categoryId);
        }
        if (ev.currentTarget.dataset.search) {
            context.wex_kb_explorer_payload = { search: ev.currentTarget.dataset.search };
        }
        return context;
    }

    async executeActionXmlId(ev) {
        const xmlId = ev.currentTarget.dataset.actionXmlid;
        await this.action.doAction(xmlId, {
            additionalContext: this.getXmlActionAdditionalContext(ev),
        });
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

    stateBadgeClass(state) {
        return {
            draft: "wex_kb_badge is-draft",
            published: "wex_kb_badge is-published",
            archived: "wex_kb_badge is-archived",
            obsolete: "wex_kb_badge is-obsolete",
        }[state] || "wex_kb_badge";
    }

    visibilityBadgeClass(visibility) {
        return {
            private: "wex_kb_badge is-visibility-private",
            internal: "wex_kb_badge is-visibility-internal",
            by_group: "wex_kb_badge is-visibility-group",
        }[visibility] || "wex_kb_badge is-muted";
    }

    externalChannelLabel(article) {
        if (article.public_link_enabled) {
            return "Enlace público";
        }
        if (article.portal_visible) {
            return "Portal";
        }
        return "";
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

    getDashboardSearchPayload() {
        return {
            search: (this.state.dashboardSearch || "").trim(),
        };
    }

    async submitDashboardSearch() {
        await this.action.doAction("wex_knowledge.action_knowledge_explorer", {
            additionalContext: {
                wex_kb_explorer_payload: this.getDashboardSearchPayload(),
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
    getDefaultSidebarData() {
        return {
            category_article_tree: [],
            categories: [],
            tags: [],
            authors: [],
            owners: [],
            collaborators: [],
            companies: [],
        };
    }

    getDefaultFilters() {
        return {
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
        };
    }

    getInitialState() {
        return {
            loading: true,
            data: {
                articles: [],
                sidebar: this.getDefaultSidebarData(),
            },
            expandedNodes: {},
            expandedCategoryNodes: {},
            viewMode: "grid",
            filters: this.getDefaultFilters(),
        };
    }

    initializeFromContext() {
        const context = this.props.action?.context || {};
        this.applyContextFilters(context);
        if (context.wex_kb_view_mode) {
            this.state.viewMode = context.wex_kb_view_mode;
        }
    }

    applyContextFilters(context) {
        if (context.wex_kb_explorer_payload) {
            Object.assign(this.state.filters, context.wex_kb_explorer_payload);
        }
        if (context.explorer_favorites_only) {
            this.state.filters.favorites_only = true;
        }
        if (context.explorer_category_id) {
            this.state.filters.category_id = context.explorer_category_id;
        }
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("wex.knowledge.article", "get_explorer_data", [this.state.filters]);
        this.syncExpandedNodes();
        this.syncExpandedCategoryNodes();
        this.state.loading = false;
    }

    async setFilterAndReload(key, value) {
        this.state.filters[key] = value;
        await this.load();
    }

    async refreshWithFilter(key, value) {
        await this.setFilterAndReload(key, value);
    }

    async toggleScalarFilter(key, value, emptyValue = null) {
        const nextValue = this.state.filters[key] === value ? emptyValue : value;
        await this.setFilterAndReload(key, nextValue);
    }

    getExpandedArticleTreeState() {
        const nextExpanded = { ...this.state.expandedNodes };
        const walkArticles = (nodes, forceOpen = false) => {
            for (const node of nodes || []) {
                if (nextExpanded[node.id] === undefined) {
                    nextExpanded[node.id] = forceOpen || !!node.is_in_selected_path;
                } else if (node.is_in_selected_path) {
                    nextExpanded[node.id] = true;
                }
                walkArticles(node.children || [], false);
            }
        };
        const walkCategories = (categories) => {
            for (const category of categories || []) {
                walkArticles(category.articles || []);
                walkCategories(category.children || []);
            }
        };
        walkCategories(this.state.data.sidebar.category_article_tree || []);
        return nextExpanded;
    }

    syncExpandedNodes() {
        Object.assign(this.state.expandedNodes, this.getExpandedArticleTreeState());
    }

    getExpandedCategoryTreeState() {
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
        return nextExpanded;
    }

    syncExpandedCategoryNodes() {
        Object.assign(this.state.expandedCategoryNodes, this.getExpandedCategoryTreeState());
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
        const nextBranchId = this.state.filters.article_branch_id === nodeId ? null : nodeId;
        this.state.filters.article_branch_id = nextBranchId;
        if (nextBranchId) {
            this.state.expandedNodes[nodeId] = true;
        }
        await this.load();
    }

    async filterByCategoryNode(ev) {
        const categoryId = Number(ev.currentTarget.dataset.categoryId);
        const nextCategoryId = this.state.filters.category_id === categoryId ? null : categoryId;
        this.state.filters.category_id = nextCategoryId;
        if (nextCategoryId) {
            this.state.expandedCategoryNodes[categoryId] = true;
        }
        await this.load();
    }

    findArticleNode(nodes, selectedId) {
        for (const node of nodes || []) {
            if (node.id === selectedId) {
                return node;
            }
            const childResult = this.findArticleNode(node.children || [], selectedId);
            if (childResult) {
                return childResult;
            }
        }
        return null;
    }

    findArticleNodeInCategories(categories, selectedId) {
        for (const category of categories || []) {
            const ownMatch = this.findArticleNode(category.articles || [], selectedId);
            if (ownMatch) {
                return ownMatch;
            }
            const childMatch = this.findArticleNodeInCategories(category.children || [], selectedId);
            if (childMatch) {
                return childMatch;
            }
        }
        return null;
    }

    get selectedBranchNode() {
        const selectedId = this.state.filters.article_branch_id;
        if (!selectedId) {
            return null;
        }
        return this.findArticleNodeInCategories(this.state.data.sidebar.category_article_tree || [], selectedId);
    }

    async clearBranchFilter() {
        await this.setFilterAndReload("article_branch_id", null);
    }

    addMappedFilterChip(chips, key, list, label) {
        const selectedId = this.state.filters[key];
        if (!selectedId) {
            return;
        }
        const item = (list || []).find((entry) => entry.id === selectedId);
        if (item) {
            chips.push({ key, label, value: item.name, variant: key });
        }
    }

    get activeFilterChips() {
        const chips = [];
        const sidebar = this.state.data.sidebar || {};

        if (this.state.filters.search) {
            chips.push({ key: "search", label: "B?squeda", value: this.state.filters.search, variant: "search" });
        }
        if (this.selectedBranchNode) {
            chips.push({ key: "article_branch_id", label: "Rama", value: this.selectedBranchNode.name, variant: "branch" });
        }

        this.addMappedFilterChip(chips, "category_id", sidebar.categories, "Categor?a");
        this.addMappedFilterChip(chips, "tag_id", sidebar.tags, "Etiqueta");
        this.addMappedFilterChip(chips, "author_id", sidebar.authors, "Autor");

        if (this.state.filters.state) {
            chips.push({
                key: "state",
                label: "Estado",
                value: this.humanStateLabel(this.state.filters.state),
                variant: "state",
            });
        }
        if (this.state.filters.favorites_only) {
            chips.push({ key: "favorites_only", label: "Vista", value: "Solo favoritos", variant: "favorite" });
        }
        return chips;
    }

    getClearedFilterValue(key) {
        if (key === "favorites_only") {
            return false;
        }
        if (key === "search" || key === "state") {
            return "";
        }
        return null;
    }

    async clearSingleFilter(ev) {
        const key = ev.currentTarget.dataset.filterKey;
        if (!key) {
            return;
        }
        await this.setFilterAndReload(key, this.getClearedFilterValue(key));
    }

    onSearchInput(ev) {
        this.state.filters.search = ev.target.value;
    }

    async submitSearch() {
        await this.load();
    }

    async clearFilters() {
        Object.assign(this.state.filters, this.getDefaultFilters());
        await this.load();
    }

    async toggleFavorites() {
        await this.setFilterAndReload("favorites_only", !this.state.filters.favorites_only);
    }

    setViewMode(ev) {
        this.state.viewMode = ev.currentTarget.dataset.viewMode;
    }
}

KnowledgeExplorer.template = "wex_knowledge.KnowledgeExplorer";

registry.category("actions").add("wex_knowledge_dashboard", KnowledgeDashboard);
registry.category("actions").add("wex_knowledge_explorer", KnowledgeExplorer);
