odoo.define('hr_contract_management.relational_fields', function (require) {
    "use strict";

    let FieldReference = require('web.relational_fields').FieldReference;
    let FieldRegistry = require('web.field_registry');
    let core = require('web.core');

    let _t = core._t;

    let HrPayrollContractReference = FieldReference.extend({

        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            this._setDynamicRelation();
        },
        /**
         * Executes a name_search and process its result.
         *
         * @private
         * @param {string} search_val
         * @returns {Promise}
         */
        _search: function (search_val) {
            var self = this;
            var def = new Promise(function (resolve, reject) {
                var context = self.record.getContext(self.recordParams);
                var domain = self.record.getDomain(self.recordParams);

                // Add the additionalContext
                _.extend(context, self.additionalContext);

                var blacklisted_ids = self._getSearchBlacklist();
                if (blacklisted_ids.length > 0) {
                    domain.push(['id', 'not in', blacklisted_ids]);
                }
                console.log(self)

                self._rpc({
                    model: 'contract.management.line',
                    method: "get_reference_name",
                    args: [self.res_id, self.recordData.company_int],
                    kwargs: {
                        model_relation: self.field.relation,
                        name: search_val,
                        operator: "ilike",
                        limit: self.limit + 1,
                        args: domain,
                        context: context,
                    }
                }).then(function (datas) {
                    // possible selections for the m2o

                    let result = datas.names
                    let new_domain = datas.domain

                    var values = _.map(result, function (x) {
                        x[1] = self._getDisplayName(x[1]);
                        return {
                            label: _.str.escapeHTML(x[1].trim()) || data.noDisplayContent,
                            value: x[1],
                            name: x[1],
                            id: x[0],
                        };
                    });

                    // search more... if more results than limit
                    if (values.length > self.limit) {
                        values = self._manageSearchMore(values, search_val, new_domain, context);
                    }
                    var create_enabled = self.can_create && !self.nodeOptions.no_create;
                    // quick create
                    var raw_result = _.map(result, function (x) {
                        return x[1];
                    });
                    if (create_enabled && !self.nodeOptions.no_quick_create &&
                        search_val.length > 0 && !_.contains(raw_result, search_val)) {
                        values.push({
                            label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                                $('<span />').text(search_val).html()),
                            action: self._quickCreate.bind(self, search_val),
                            classname: 'o_m2o_dropdown_option'
                        });
                    }
                    // create and edit ...
                    if (create_enabled && !self.nodeOptions.no_create_edit) {
                        var createAndEditAction = function () {
                            // Clear the value in case the user clicks on discard
                            self.$('input').val('');
                            return self._searchCreatePopup("form", false, self._createContext(search_val));
                        };
                        values.push({
                            label: _t("Create and Edit..."),
                            action: createAndEditAction,
                            classname: 'o_m2o_dropdown_option',
                        });
                    } else if (values.length === 0) {
                        values.push({
                            label: _t("No results to show..."),
                        });
                    }

                    resolve(values);
                });
            });
            this.orderer.add(def);
            return def;
        },
        /**
         * @private
         * @param {Object} values
         * @param {string} search_val
         * @param {Object} domain
         * @param {Object} context
         * @returns {Object}
         */
        _manageSearchMore: function (values, search_val, domain, context) {
            var self = this;
            values = values.slice(0, this.limit);
            values.push({
                label: _t("Search More..."),
                action: function () {
                    var prom;
                    console.log(search_val !== '')

                    prom = self._rpc({
                        model: self.field.relation,
                        method: 'name_search',
                        kwargs: {
                            name: search_val,
                            args: domain,
                            operator: "ilike",
                            limit: self.SEARCH_MORE_LIMIT,
                            context: context,
                        },
                    });

                    Promise.resolve(prom).then(function (results) {
                        var dynamicFilters;
                        console.log(results)
                        if (results) {
                            var ids = _.map(results, function (x) {
                                return x[0];
                            });
                            dynamicFilters = [{
                                description: _.str.sprintf(_t('Quick search: %s'), search_val),
                                domain: [['id', 'in', ids]],
                            }];
                        }
                        self._searchCreatePopup("search", false, {}, dynamicFilters);
                    });
                },
                classname: 'o_m2o_dropdown_option',
            });
            return values;
        },
        /**
         * Set `relation` key in field properties IF RELATION IS EMPTY.
         *
         * @private
         */
        _setDynamicRelation: function () {
            let value
            if (this.value){value = this.value.model;}
            else{
                value = undefined
            }
            this.field.relation = value || this.record.data.model_relation;
        },

    });
    FieldRegistry.add('payroll_contract_reference', HrPayrollContractReference);

});
