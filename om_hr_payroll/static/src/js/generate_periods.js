odoo.define('om_hr_payroll.generate_periods', function (require) {
"use strict";
var ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');
var TreeButton = ListController.extend({
   buttons_template: 'payroll_period.buttons',
   events: _.extend({}, ListController.prototype.events, {
       'click .generate_period_action': '_OpenWizard',
   }),
   _OpenWizard: function () {
       var self = this;
        this.do_action({
           type: 'ir.actions.act_window',
           res_model: 'generate.payroll.period',
           name :'Generate Payroll Period',
           view_mode: 'form',
           view_type: 'form',
           view_id: 'om_hr_payroll.generate_payroll_period',
           views: [[false, 'form']],
           target: 'new',
           res_id: false,
       });
   }
});
var PayrollPeriodListView = ListView.extend({
   config: _.extend({}, ListView.prototype.config, {
       Controller: TreeButton,
   }),
});
viewRegistry.add('button_in_tree', PayrollPeriodListView);
});