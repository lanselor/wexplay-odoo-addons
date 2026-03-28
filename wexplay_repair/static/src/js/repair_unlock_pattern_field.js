/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useEffect, useRef, useState } from "@odoo/owl";

const PATTERN_POINTS = [
    { id: 7, row: 0, col: 0 },
    { id: 8, row: 0, col: 1 },
    { id: 9, row: 0, col: 2 },
    { id: 4, row: 1, col: 0 },
    { id: 5, row: 1, col: 1 },
    { id: 6, row: 1, col: 2 },
    { id: 1, row: 2, col: 0 },
    { id: 2, row: 2, col: 1 },
    { id: 3, row: 2, col: 2 },
];

const POINTS_BY_ID = Object.fromEntries(PATTERN_POINTS.map((point) => [point.id, point]));
const COORDS_TO_ID = Object.fromEntries(
    PATTERN_POINTS.map((point) => [`${point.row},${point.col}`, point.id])
);

class RepairUnlockTypePickerField extends Component {
    static template = "wexplay_repair.RepairUnlockTypePickerField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.boardRef = useRef("board");
        this.state = useState({
            isOpen: false,
            draftPath: this.parseValue(this.patternValue),
            pointer: null,
            error: "",
            isDrawing: false,
        });

        this.onPointerMove = this.onPointerMove.bind(this);
        this.onPointerUp = this.onPointerUp.bind(this);

        useEffect(
            () => {
                if (this.state.isDrawing) {
                    window.addEventListener("pointermove", this.onPointerMove);
                    window.addEventListener("pointerup", this.onPointerUp);
                    window.addEventListener("pointercancel", this.onPointerUp);
                    return () => {
                        window.removeEventListener("pointermove", this.onPointerMove);
                        window.removeEventListener("pointerup", this.onPointerUp);
                        window.removeEventListener("pointercancel", this.onPointerUp);
                    };
                }
            },
            () => [this.state.isDrawing]
        );

        useEffect(
            () => {
                const nextValue = this.patternValue;
                if (!this.state.isDrawing && !this.state.isOpen) {
                    this.state.draftPath = this.parseValue(nextValue);
                }
            },
            () => [this.patternValue, this.state.isDrawing, this.state.isOpen]
        );
    }

    get value() {
        return this.props.record.data[this.props.name] || false;
    }

    get patternValue() {
        return this.props.record.data.x_unlock_pattern || "";
    }

    get options() {
        return this.props.record.fields[this.props.name]?.selection || [];
    }

    get points() {
        return PATTERN_POINTS.map((point) => ({
            ...point,
            style: this.pointStyle(point),
        }));
    }

    get currentSequence() {
        return this.state.draftPath.join("");
    }

    get helperText() {
        if (this.state.error) {
            return this.state.error;
        }
        return "Minimo 4 puntos. Respeta reglas Android y completa saltos intermedios.";
    }

    get hasValidPattern() {
        return this.state.draftPath.length >= 4;
    }

    get segments() {
        const path = this.state.draftPath;
        const segments = [];
        for (let index = 0; index < path.length - 1; index++) {
            const from = POINTS_BY_ID[path[index]];
            const to = POINTS_BY_ID[path[index + 1]];
            if (!from || !to) {
                continue;
            }
            segments.push({
                key: `${from.id}-${to.id}-${index}`,
                x1: this.percentForCol(from.col),
                y1: this.percentForRow(from.row),
                x2: this.percentForCol(to.col),
                y2: this.percentForRow(to.row),
            });
        }
        if (this.state.isDrawing && this.state.pointer && path.length) {
            const last = POINTS_BY_ID[path[path.length - 1]];
            segments.push({
                key: "pointer-segment",
                x1: this.percentForCol(last.col),
                y1: this.percentForRow(last.row),
                x2: this.state.pointer.x,
                y2: this.state.pointer.y,
            });
        }
        return segments;
    }

    parseValue(value) {
        return (value || "")
            .split("")
            .map((char) => parseInt(char, 10))
            .filter((number) => POINTS_BY_ID[number]);
    }

    pointStyle(point) {
        return `left: ${this.percentForCol(point.col)}%; top: ${this.percentForRow(point.row)}%;`;
    }

    percentForCol(col) {
        return 16.6667 + col * 33.3333;
    }

    percentForRow(row) {
        return 16.6667 + row * 33.3333;
    }

    isSelected(pointId) {
        return this.state.draftPath.includes(pointId);
    }

    selectedIndex(pointId) {
        return this.state.draftPath.indexOf(pointId) + 1;
    }

    async selectOption(optionValue) {
        if (this.props.readonly) {
            return;
        }
        const updates = { [this.props.name]: optionValue };
        if (optionValue !== "pattern") {
            this.state.isOpen = false;
            this.state.error = "";
            this.state.draftPath = this.parseValue(this.patternValue);
        } else {
            this.state.isOpen = true;
            this.state.error = "";
            this.state.draftPath = this.parseValue(this.patternValue);
        }
        await this.props.record.update(updates);
    }

    clearPattern() {
        if (this.props.readonly) {
            return;
        }
        this.state.draftPath = [];
        this.state.pointer = null;
        this.state.error = "";
    }

    async applyPattern() {
        if (this.props.readonly) {
            return;
        }
        if (!this.state.draftPath.length) {
            this.state.error = "";
            await this.props.record.update({ x_unlock_pattern: false });
            this.state.isOpen = false;
            return;
        }
        if (!this.hasValidPattern) {
            this.state.error = "El patron debe tener al menos 4 puntos.";
            return;
        }
        this.state.error = "";
        await this.props.record.update({ x_unlock_pattern: this.currentSequence });
        this.state.isOpen = false;
    }

    startFromPoint(pointId, ev) {
        if (this.props.readonly) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.state.error = "";
        this.state.isDrawing = true;
        this.state.draftPath = [];
        this.state.pointer = this.eventToBoardPercent(ev);
        this.extendPath(pointId);
    }

    onPointerMove(ev) {
        if (!this.state.isDrawing) {
            return;
        }
        this.state.pointer = this.eventToBoardPercent(ev);
        const pointId = this.findPointFromEvent(ev);
        if (pointId) {
            this.extendPath(pointId);
        }
    }

    onPointerUp(ev) {
        if (!this.state.isDrawing) {
            return;
        }
        const pointId = this.findPointFromEvent(ev);
        if (pointId) {
            this.extendPath(pointId);
        }
        this.state.isDrawing = false;
        this.state.pointer = null;
    }

    extendPath(pointId) {
        const path = [...this.state.draftPath];
        const lastPointId = path[path.length - 1];
        if (lastPointId === pointId || path.includes(pointId)) {
            return;
        }
        if (lastPointId) {
            const bridgeId = this.bridgePoint(lastPointId, pointId);
            if (bridgeId && !path.includes(bridgeId)) {
                path.push(bridgeId);
            }
        }
        path.push(pointId);
        this.state.draftPath = path;
    }

    bridgePoint(fromId, toId) {
        const from = POINTS_BY_ID[fromId];
        const to = POINTS_BY_ID[toId];
        if (!from || !to) {
            return null;
        }
        const middleRow = (from.row + to.row) / 2;
        const middleCol = (from.col + to.col) / 2;
        if (!Number.isInteger(middleRow) || !Number.isInteger(middleCol)) {
            return null;
        }
        if (Math.abs(from.row - to.row) < 2 && Math.abs(from.col - to.col) < 2) {
            return null;
        }
        const middleId = COORDS_TO_ID[`${middleRow},${middleCol}`];
        return middleId && middleId !== fromId && middleId !== toId ? middleId : null;
    }

    eventToBoardPercent(ev) {
        const board = this.boardRef.el;
        if (!board) {
            return { x: 0, y: 0 };
        }
        const rect = board.getBoundingClientRect();
        const x = ((ev.clientX - rect.left) / rect.width) * 100;
        const y = ((ev.clientY - rect.top) / rect.height) * 100;
        return {
            x: Math.max(0, Math.min(100, x)),
            y: Math.max(0, Math.min(100, y)),
        };
    }

    findPointFromEvent(ev) {
        const board = this.boardRef.el;
        if (!board) {
            return null;
        }
        const rect = board.getBoundingClientRect();
        const x = ev.clientX - rect.left;
        const y = ev.clientY - rect.top;
        if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
            return null;
        }

        let closestPointId = null;
        let minDistance = Number.POSITIVE_INFINITY;
        const threshold = Math.min(rect.width, rect.height) * 0.14;
        for (const point of PATTERN_POINTS) {
            const pointX = (this.percentForCol(point.col) / 100) * rect.width;
            const pointY = (this.percentForRow(point.row) / 100) * rect.height;
            const distance = Math.hypot(x - pointX, y - pointY);
            if (distance < threshold && distance < minDistance) {
                minDistance = distance;
                closestPointId = point.id;
            }
        }
        return closestPointId;
    }
}

export const repairUnlockTypePickerField = {
    component: RepairUnlockTypePickerField,
    displayName: "Repair Unlock Type Picker",
    supportedTypes: ["selection"],
};

registry.category("fields").add("wex_repair_unlock_type_picker", repairUnlockTypePickerField);
