odoo.define('om_hr_payroll.action_call', function (require){
    "use strict";

    var ajax = require('web.ajax');
    var ListController = require('web.ListController');

    ListController.include({
        renderButtons: function($node) {
            this._super.apply(this, arguments);
            var self = this;
            if (this.$buttons) {
                $(this.$buttons).find('.oe_action_button').on('click', function() {
                    self.do_action('om_hr_payroll.generate_payroll_period_action', {
                        additional_context: {},
                    });
                });
            }
        },
    });

});