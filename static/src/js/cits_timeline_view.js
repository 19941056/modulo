odoo.define('cits_timeline.TimelineView', function (require) {
    'use strict';
    var ajax = require('web.ajax');
    var AbstractView = require('web.AbstractView');
    var view_registry = require('web.view_registry');
    var core = require('web.core');
    var utils = require('web.utils');
    var TimelineModel = require('cits_timeline.TimelineModel');
    var TimelineController = require('cits_timeline.TimelineController');
    var TimelineRenderer = require('cits_timeline.TimelineRenderer');
    var _lt = core._lt;
    var fieldsToGather = [
        'date_start',
        'date_delay',
        'date_end'
    ];
    var TimelineView = AbstractView.extend({
        display_name: _lt('Timeline'),
        icon: 'fa-clock-o',
        jsLibs: [
            '/citas/static/lib/js/vis.js'
        ],
        config: {
            Model: TimelineModel,
            Controller: TimelineController,
            Renderer: TimelineRenderer
        },
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
            var arch = this.arch;
            var fields = this.fields;
            var attrs = arch.attrs;
            if (!attrs.date_start) {
                throw new Error(_lt('Timeline view has not defined \'date_start\' attribute.'));
            }
            var mapping = {};
            var fieldNames = [];
            var displayFields = {};
            _.each(fieldsToGather, function (field) {
                if (arch.attrs[field]) {
                    var fieldName = attrs[field];
                    mapping[field] = fieldName;
                    fieldNames.push(fieldName);
                }
            });
            _.each(arch.children, function (child) {
                if (child.tag !== 'field') return;
                var fieldName = child.attrs.name;
                fieldNames.push(fieldName);
                if (!child.attrs.invisible) {
                    displayFields[fieldName] = child.attrs;
                }
            });
            if (attrs.color) {
                var fieldName = attrs.color;
                fieldNames.push(fieldName);
            }
            this.controllerParams.quickAddPop = (!('quick_add' in attrs) || utils.toBoolElse(attrs.quick_add + '', true));
            this.controllerParams.disableQuickCreate = params.disable_quick_create || !this.controllerParams.quickAddPop;
            this.controllerParams.formViewId = !attrs.form_view_id || !utils.toBoolElse(attrs.form_view_id, true) ? false : attrs.form_view_id;
            this.controllerParams.readonlyFormViewId = !attrs.readonly_form_view_id || !utils.toBoolElse(attrs.readonly_form_view_id, true) ? false : attrs.readonly_form_view_id;
            this.controllerParams.eventOpenPopup = utils.toBoolElse(attrs.event_open_popup || '', false);
            this.controllerParams.mapping = mapping;
            this.controllerParams.context = params.context || {};
            this.controllerParams.displayName = params.action && params.action.name;

            this.rendererParams.displayFields = displayFields;
            this.rendererParams.itemTemplate = _.findWhere(arch.children, {'tag': 'templates'});
            this.rendererParams.model = viewInfo.model;

            this.loadParams.fieldNames = _.uniq(fieldNames);
            this.loadParams.mapping = mapping;
            this.loadParams.fields = fields;
            this.loadParams.fieldsInfo = viewInfo.fieldsInfo;
            this.loadParams.editable = !fields[mapping.date_start].readonly;
            this.loadParams.creatable = true;
            this.loadParams.fieldColor = attrs.color;
            this.loadParams.tooltip = attrs.tooltip;
            this.loadParams.mode = attrs.mode;
            this.loadParams.initialDate = moment(params.initialDate || new Date());
        },
        getController: function (parent) {
            var self = this;
            return ajax.loadLibs(this).then(function () {
                return self._loadData(parent);
            }).then(function () {
                var model = self.getModel();
                var state = model.get(arguments[-1]);
                var renderer = self.getRenderer(parent, state);
                var Controller = self.Controller || self.config.Controller;
                var controllerParams = _.extend({
                    initialState: state
                }, self.controllerParams);
                var controller = new Controller(parent, model, renderer, controllerParams);
                renderer.setParent(controller);
                if (!self.model) {
                    model.setParent(controller);
                }
                return controller;
            });
        }
    });
    view_registry.add('cits_timeline', TimelineView);
    return TimelineView;
})