# -*- coding: utf-8 -*-

import re

from odoo import _, api, models
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    @api.model
    def _sanitize_sat_dms_name(self, name, fallback="ITEM"):
        sanitized = (name or "").strip()
        if not sanitized:
            sanitized = fallback
        sanitized = re.sub(r'[<>:"/\\|?*]+', "-", sanitized)
        sanitized = re.sub(r"[\x00-\x1f]", "", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
        if not sanitized:
            sanitized = fallback
        return sanitized[:120]

    def _get_sat_dms_safe_name(self):
        self.ensure_one()
        return self._sanitize_sat_dms_name(
            self.name,
            fallback="REPAIR-%s" % self.id,
        )

    def _get_sat_dms_storage(self):
        self.ensure_one()
        storage = self.company_id.x_wex_consent_dms_storage_id
        if not storage:
            raise UserError(_("Configura primero el almacenamiento DMS SAT en Ajustes."))
        return storage

    def _get_or_create_sat_root_directory(self):
        self.ensure_one()
        company = self.company_id
        root_directory = company.x_wex_consent_dms_root_directory_id
        if root_directory and root_directory.exists():
            return root_directory

        storage = self._get_sat_dms_storage()
        root_directory = self.env["dms.directory"].search(
            [
                ("is_root_directory", "=", True),
                ("storage_id", "=", storage.id),
                ("name", "=", "SAT"),
            ],
            limit=1,
        )
        if not root_directory:
            root_directory = self.env["dms.directory"].create(
                {
                    "name": "SAT",
                    "is_root_directory": True,
                    "storage_id": storage.id,
                }
            )
        company.x_wex_consent_dms_root_directory_id = root_directory
        return root_directory

    def _get_or_create_sat_child_directory(self, parent_directory, name):
        self.ensure_one()
        directory = self.env["dms.directory"].search(
            [
                ("parent_id", "=", parent_directory.id),
                ("name", "=", name),
            ],
            limit=1,
        )
        if not directory:
            directory = self.env["dms.directory"].create(
                {
                    "name": name,
                    "parent_id": parent_directory.id,
                }
            )
        return directory

    def _get_or_create_sat_repair_directory(self):
        self.ensure_one()
        root = self._get_or_create_sat_root_directory()
        return self._get_or_create_sat_child_directory(root, self._get_sat_dms_safe_name())

    def _get_or_create_sat_directory(self, folder_name, create_defaults=False):
        self.ensure_one()
        repair_directory = self._get_or_create_sat_repair_directory()
        if create_defaults:
            for default_name in ("IMAGES", "DOCUMENTS", "SIGNATURES"):
                self._get_or_create_sat_child_directory(repair_directory, default_name)
        return self._get_or_create_sat_child_directory(repair_directory, folder_name)
