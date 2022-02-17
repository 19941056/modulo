odoo.define('cits_timeline.TimelineController', function (require) {
    'use strict';
    var AbstractController = require('web.AbstractController');
    var dialogs = require('web.view_dialogs');
    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var _t = core._t;
    var QWeb = core.qweb;
    return AbstractController.extend({
        custom_events: _.extend({}, AbstractController.prototype.custom_events, {
            openCreate: '_onOpenCreate',
            openItem: '_onOpenItem',
            dropItem: '_onDropItem',
            updateItem: '_onUpdateItem',
            changeRange: '_onChangeRange',
            updateView: '_onUpdateView'
        }),
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.current_start = null;
            this.displayName = params.displayName;
            this.eventOpenPopup = params.eventOpenPopup;
            this.formViewId = params.formViewId;
            this.readonlyFormViewId = params.readonlyFormViewId;
            this.mapping = params.mapping;
            this.context = params.context;
        },
        renderButtons: function ($node) {
            var self = this;
            this.$buttons = $(QWeb.render('TimelineView.buttons', {
                'widget': this
            }));
            this.$buttons.on('click', 'button.o_timeline_button_new', function () {
                self.trigger_up('switch_view', {
                    view_type: 'form'
                });
            });
            _.each(['prev', 'today', 'next'], function (action) {
                self.$buttons.on('click', '.o_timeline_button_' + action, function () {
                    self.model[action]();
                    self.reload();
                });
            });
            _.each(this.model.scales, function (scale) {
                self.$buttons.on('click', '.o_timeline_button_' + scale, function () {
                    self.model.setScale(scale);
                    self.reload();
                });
            });
            if ($node) {
                this.$buttons.appendTo($node);
            } else {
                this.$('.o_timeline_buttons').replaceWith(this.$buttons);
            }
            this._updateView();
        },
        _updateItem: function (item) {
            var self = this;
            return this.model.updateItem(item).then(function () {
                self.model.reload(undefined, {
                    updateId: item.id
                });
            });
        },
        _updateView: function () {
            if (this.$buttons) {
                this.$buttons.find('.active').removeClass('active');
                this.$buttons.find('.o_timeline_button_' + this.model.data.scale).addClass('active');
            }
            this.set({
                title: this.displayName + ' (' + this.model.getTitle() + ')'
            });
        },
        _onUpdateView: function (event) {
            this._updateView();
            if (!_.isEqual(event.data.visibleGroups, this.model.data.visibleGroups)) {
                this.model.setVisibleGroups(event.data.visibleGroups);
                this.reload();
            }
        },
        _onChangeRange: function (event) {
            this.model.setRange(event.data.start, event.data.end);
            this.reload();
        },
        _onDropItem: function (event) {
            this._updateItem(event.data);
        },
        _onOpenCreate: function (event) {
            var self = this;
            var context = _.extend({}, this.context, event.options && event.options.context);
            context['default_' + this.mapping.date_start] = moment(event.data.snappedTime);
            if (this.mapping.date_delay) {
                var durationScale = this.model.scales[Math.max(this.model.scales.indexOf(this.model.data.scale) - 1, 0)];
                context['default_' + this.mapping.date_delay] = moment.duration(1, durationScale + 's').asHours();
            }
            if (this.model.canUpdateGroup() && event.data.group) {
                _.each(self.model.parseGroupId(event.data.group), function (value, key) {
                    context['default_' + key] = value;
                });
            }
            for (var k in context) {
                if (context[k] && context[k]._isAMomentObject) {
                    context[k] = context[k].clone().utc().format('YYYY-MM-DD HH:mm:ss');
                }
            }
            var options = _.extend({}, this.options, event.options, {
                context: context
            });
            var title = _t('Create');
            if (this.renderer.arch.attrs.string) {
                title += ': ' + this.renderer.arch.attrs.string;
            }
            if (this.eventOpenPopup) {
                new dialogs.FormViewDialog(self, {
                    res_model: this.modelName,
                    context: context,
                    title: title,
                    disable_multiple_selection: true,
                    on_saved: function () {
                        self.reload();
                    }
                }).open();
            } else {
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: this.modelName,
                    views: [
                        [this.formViewId || false,
                            'form']
                    ],
                    target: 'current',
                    context: context
                });
            }
        },
        _onOpenItem: function (event) {
            var self = this;
            var id = event.data.id;
            id = id && parseInt(id).toString() === id ? parseInt(id) : id;
            if (this.eventOpenPopup) {
                var open_dialog = function (readonly) {
                    var options = {
                        res_model: self.modelName,
                        res_id: id || null,
                        context: event.context || self.context,
                        readonly: readonly,
                        title: _t('Open: ') + event.data.title,
                        on_saved: function () {
                            self.reload();
                        }
                    };
                    if (readonly) {
                        if (self.readonlyFormViewId) {
                            options.view_id = parseInt(self.readonlyFormViewId);
                        }
                        options.buttons = [
                            {
                                text: _t('Edit'),
                                classes: 'btn-primary',
                                close: true,
                                click: function () {
                                    open_dialog(false);
                                }
                            },
                            {
                                text: _t('Delete'),
                                click: function () {
                                    Dialog.confirm(this, _t('Are you sure you want to delete this record ?'), {
                                        confirm_callback: function () {
                                            self.model.deleteRecords([id], self.modelName).then(function () {
                                                self.dialog.destroy();
                                                self.reload();
                                            });
                                        }
                                    });
                                }
                            },
                            {
                                text: _t('Close'),
                                close: true
                            }
                        ];
                    } else if (self.formViewId) {
                        options.view_id = parseInt(self.formViewId);
                    }
                    self.dialog = new dialogs.FormViewDialog(self, options).open();
                };
                open_dialog(true);
            } else {
                this._rpc({
                    model: self.modelName,
                    method: 'get_formview_id',
                    args: [
                        [id],
                        event.context || self.context
                    ]
                }).then(function (viewId) {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_id: id,
                        res_model: self.modelName,
                        views: [
                            [viewId || false,
                                'form']
                        ],
                        target: 'current',
                        context: event.context || self.context
                    });
                });
            }
        },
        _onUpdateItem: function (event) {
            this._updateItem(event.data);
        }
    });
})