/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

console.log("WEXPLAY: asset cargado (expand button)");

const originalSetup = ListController.prototype.setup;

patch(ListController.prototype, {
  setup() {
    // llama al setup original de forma segura
    if (originalSetup) {
      originalSetup.call(this, ...arguments);
    }

    // solo para repair.order
    if (this.props?.resModel === "repair.order") {
      window._wex_last_list_controller = this;
      console.log("WEXPLAY: ListController capturado en window._wex_last_list_controller", this);
    }
  },
});
