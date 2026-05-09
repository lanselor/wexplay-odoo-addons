/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class KnowledgeCategoryTree extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            tree: [],
            expandedNodes: {},
            draggingId: null,
            dropTargetId: null,
            dropPosition: null,
        });
        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        this.state.loading = true;
        const tree = await this.orm.call(
            "wex.knowledge.category",
            "get_category_tree_data",
            []
        );
        this.state.tree = tree;
        // Auto-expand root nodes that have children
        for (const node of tree) {
            if (node.children && node.children.length) {
                this.state.expandedNodes[node.id] = true;
            }
        }
        this.state.loading = false;
    }

    // ── Flat tree for rendering ────────────────────────────────────────────

    get flatNodes() {
        if (!this.state.tree || !this.state.tree.length) {
            return [];
        }
        const result = [];
        const walk = (nodes, depth) => {
            for (const node of nodes) {
                const isExpanded = !!this.state.expandedNodes[node.id];
                result.push({ ...node, depth, isExpanded });
                if (isExpanded && node.children && node.children.length) {
                    walk(node.children, depth + 1);
                }
            }
        };
        walk(this.state.tree, 0);
        return result;
    }

    getRowClass(node) {
        let cls = "wex_kb_cat_tree_row";
        if (node.id === this.state.draggingId) {
            cls += " is-dragging";
        }
        if (this.state.dropTargetId === node.id) {
            cls += ` is-drop-${this.state.dropPosition}`;
        }
        return cls;
    }

    // ── Node expand / collapse ─────────────────────────────────────────────

    toggleNode(ev) {
        const nodeId = Number(ev.currentTarget.dataset.nodeId);
        this.state.expandedNodes[nodeId] = !this.state.expandedNodes[nodeId];
    }

    // ── Navigation actions ─────────────────────────────────────────────────

    async openNew() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "wex.knowledge.category",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openEdit(ev) {
        const nodeId = Number(ev.currentTarget.dataset.nodeId);
        if (!nodeId) {
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "wex.knowledge.category",
            res_id: nodeId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ── Drag & Drop ────────────────────────────────────────────────────────

    onDragStart(ev) {
        const nodeId = Number(ev.currentTarget.dataset.nodeId);
        this.state.draggingId = nodeId;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", String(nodeId));
    }

    onDragEnd() {
        this.state.draggingId = null;
        this.state.dropTargetId = null;
        this.state.dropPosition = null;
    }

    onDragOver(ev) {
        const nodeId = Number(ev.currentTarget.dataset.nodeId);
        if (nodeId === this.state.draggingId) {
            return;
        }
        // Prevent dropping onto own descendant
        if (this._isDescendant(this.state.tree, this.state.draggingId, nodeId)) {
            return;
        }
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";

        const rect = ev.currentTarget.getBoundingClientRect();
        const relY = ev.clientY - rect.top;
        const zone = rect.height * 0.28;

        let position;
        if (relY < zone) {
            position = "before";
        } else if (relY > rect.height - zone) {
            position = "after";
        } else {
            position = "inside";
        }

        this.state.dropTargetId = nodeId;
        this.state.dropPosition = position;
    }

    onDragLeave(ev) {
        // Only clear if leaving the row itself, not moving into a child element
        if (ev.currentTarget.contains(ev.relatedTarget)) {
            return;
        }
        const nodeId = Number(ev.currentTarget.dataset.nodeId);
        if (this.state.dropTargetId === nodeId) {
            this.state.dropTargetId = null;
            this.state.dropPosition = null;
        }
    }

    async onDrop(ev) {
        ev.preventDefault();
        const draggedId = this.state.draggingId;
        const targetId = this.state.dropTargetId;
        const position = this.state.dropPosition;

        // Always reset drag state immediately
        this.state.draggingId = null;
        this.state.dropTargetId = null;
        this.state.dropPosition = null;

        if (!draggedId || !targetId || draggedId === targetId) {
            return;
        }
        if (this._isDescendant(this.state.tree, draggedId, targetId)) {
            return;
        }

        const targetNode = this._findNode(this.state.tree, targetId);
        if (!targetNode) {
            return;
        }

        let newParentId;
        let newSequence;

        if (position === "inside") {
            newParentId = targetId;
            const children = targetNode.children || [];
            newSequence = children.length
                ? Math.max(...children.map((c) => c.sequence)) + 10
                : 10;
            this.state.expandedNodes[targetId] = true;
        } else {
            newParentId = targetNode.parent_id || false;
            newSequence =
                position === "before"
                    ? Math.max(0, targetNode.sequence - 1)
                    : targetNode.sequence + 1;
        }

        try {
            await this.orm.write("wex.knowledge.category", [draggedId], {
                parent_id: newParentId || false,
                sequence: newSequence,
            });
        } catch (error) {
            const msg =
                error?.data?.message ||
                error?.message ||
                "No se pudo mover la categoría.";
            this.notification.add(msg, { type: "danger" });
        }
        // Reload regardless — restores state on success or error
        await this.load();
    }

    // ── Helpers ────────────────────────────────────────────────────────────

    _findNode(nodes, id) {
        for (const node of nodes || []) {
            if (node.id === id) {
                return node;
            }
            const found = this._findNode(node.children, id);
            if (found) {
                return found;
            }
        }
        return null;
    }

    _isDescendant(tree, ancestorId, nodeId) {
        const ancestor = this._findNode(tree, ancestorId);
        if (!ancestor) {
            return false;
        }
        const walk = (nodes) => {
            for (const n of nodes || []) {
                if (n.id === nodeId) {
                    return true;
                }
                if (walk(n.children)) {
                    return true;
                }
            }
            return false;
        };
        return walk(ancestor.children);
    }
}

KnowledgeCategoryTree.template = "wex_knowledge.KnowledgeCategoryTree";

registry.category("actions").add("wex_knowledge_category_tree", KnowledgeCategoryTree);
