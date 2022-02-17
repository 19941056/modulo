odoo.define('cits_timeline.TimelineModel', function (require) {
    'use strict';
    var AbstractModel = require('web.AbstractModel');
    var Context = require('web.Context');
    var core = require('web.core');
    var fieldUtils = require('web.field_utils');
    var session = require('web.session');
    var time = require('web.time');
    var _t = core._t;
    var defaultScale = 'month';
    var scales = [
        'day',
        'week',
        'month',
        'year'
    ];

    function dateToServer(date) {
        return date.clone().utc().locale('en').format('YYYY-MM-DD HH:mm:ss');
    }

    function rangeExclude(a, b) {
        var start;
        var end;
        if (b.start.diff(a.start) > 0) {
            start = a.end.clone();
        } else {
            start = b.start.clone();
        }
        if (b.end.diff(a.end) > 0) {
            end = b.end.clone();
        } else {
            end = a.start.clone();
        }
        if (end.diff(start) < 0) {
            return null;
        }
        return {
            start: start,
            end: end
        };
    }

    function rangeMerge(a, b) {
        var start;
        var end;
        if (b.start.diff(a.start) > 0) {
            start = a.start.clone();
        } else {
            start = b.start.clone();
        }
        if (b.end.diff(a.end) > 0) {
            end = b.end.clone();
        } else {
            end = a.end.clone();
        }
        return {
            start: start,
            end: end
        };
    }

    return AbstractModel.extend({
        init: function () {
            this._super.apply(this, arguments);
            this.end_date = null;
            this.color_map = {};
        },
        timelineItemToRecord: function (item) {
            var self = this;
            var start = moment(item.start);
            var end = item.end && moment(item.end);
            var record = {};
            if (this.canUpdateGroup()) {
                _.extend(record, this.parseGroupId(item.group));
            }
            if (!end || end.diff(start) < 0) {
                end = start.clone();
            }
            record[this.mapping.date_start] = start;
            if (this.mapping.date_end) {
                record[this.mapping.date_end] = end;
            }
            if (this.mapping.date_delay) {
                record[this.mapping.date_delay] = (end.diff(start) <= 0 ? end.endOf('day').diff(start) : end.diff(start)) / 1000 / 3600;
            }
            return record;
        },
        get: function () {
            return _.extend({}, this.data, {
                fields: this.fields
            });
        },
        load: function (params) {
            var self = this;
            this.modelName = params.modelName;
            this.fields = params.fields;
            this.fieldNames = params.fieldNames;
            this.fieldsInfo = params.fieldsInfo;
            this.mapping = params.mapping;
            this.scales = params.scales || scales;
            this.tooltip = params.tooltip;
            this.editable = params.editable;
            this.creatable = params.creatable;
            this.eventLimit = params.eventLimit;
            this.groupPreloadCount = 4;
            this.fieldColor = params.fieldColor;
            if (!this.preload_def) {
                this.preload_def = $.Deferred();
                $.when(this._rpc({
                    model: this.modelName,
                    method: 'check_access_rights',
                    args: [
                        'write',
                        false
                    ]
                }), this._rpc({
                    model: this.modelName,
                    method: 'check_access_rights',
                    args: [
                        'create',
                        false
                    ]
                })).then(function (write, create) {
                    self.write_right = write;
                    self.create_right = create;
                    self.preload_def.resolve();
                });
            }
            this.data = {
                domain: params.domain,
                context: params.context,
                groupBy: params.groupedBy,
                scale: params.scale || defaultScale,
                visibleGroups: []
            };
            this.setDate(params.initialDate);
            return this.preload_def.then(function () {
                return self._loadTimeline();
            });
        },
        getTitle: function () {
            var title = '';
            switch (this.data.scale) {
                case 'year':
                    title = this.data.target_date.format('YYYY');
                    break;
                case 'month':
                    title = this.data.target_date.format('MMM YYYY');
                    break;
                case 'week':
                    title = _t('Week') + ' ' + this.data.target_date.format('w - YYYY');
                    break;
                default:
                    title = this.data.target_date.format('MMM D YYYY');
            }
            return title;
        },
        next: function () {
            this.setDate(this.data.target_date.clone().add(1, this.data.scale));
        },
        prev: function () {
            this.setDate(this.data.target_date.clone().add(-1, this.data.scale));
        },
        reload: function (_handle, params) {
            if (params.domain || params.groupBy) {
                if (_.isEqual(params.domain, this.data.domain) && _.isEqual(params.groupBy, this.data.groupBy)) {
                    this.data.loadedRange = undefined;
                    return this._loadRange({
                        start: this.data.start_date,
                        end: this.data.end_date
                    });
                } else {
                    if (params.domain) {
                        this.data.domain = params.domain;
                    }
                    if (params.groupBy) {
                        this.data.groupBy = params.groupBy;
                    }
                    return this._loadTimeline();
                }
            } else if (params.updateId) {
                var item = this.data.items.get(params.updateId);
                var group = item.group && this.data.groups.get(item.group) || undefined;
                return this._loadItems([['id',
                    '=',
                    params.updateId]], group);
            } else {
                return this._loadRange({
                    start: this.data.start_date,
                    end: this.data.end_date
                });
            }
        },
        setDate: function (date) {
            this.setRange(date.clone().startOf(this.data.scale), date.clone().add(1, this.data.scale).startOf(this.data.scale), date);
        },
        setRange: function (start_date, end_date, target_date) {
            this.data.start_date = start_date.clone();
            this.data.end_date = end_date.clone();
            if (target_date === undefined) {
                target_date = start_date.clone().add(end_date.diff(start_date, 'hours') / 2, 'hours');
            }
            this.data.target_date = target_date.clone();
            if (end_date.diff(start_date, 'days') < 7) {
                this.data.scale = 'day';
            } else if (end_date.diff(start_date, 'months') < 1) {
                this.data.scale = 'week';
            } else if (end_date.diff(start_date, 'years') < 1) {
                this.data.scale = 'month';
            } else {
                this.data.scale = 'year';
            }
            this.data.focus_start_date = target_date.clone().startOf(this.data.scale);
            this.data.focus_end_date = target_date.clone().endOf(this.data.scale);
        },
        setVisibleGroups: function (visibleGroups) {
            this.data.visibleGroups = visibleGroups;
        },
        setScale: function (scale) {
            if (!_.contains(scales, scale)) {
                throw new Error('Invalid scale ' + scale);
            }
            this.data.scale = scale;
            this.setDate(this.data.target_date);
        },
        today: function () {
            this.setDate(moment(new Date()));
        },
        updateItem: function (item) {
            var record = _.omit(this.timelineItemToRecord(item), 'name');
            for (var k in record) {
                if (record[k] && record[k]._isAMomentObject) {
                    record[k] = dateToServer(record[k]);
                }
            }
            var context = new Context(this.data.context, {
                from_ui: true
            });
            return this._rpc({
                model: this.modelName,
                method: 'write',
                args: [
                    [item.id],
                    record
                ],
                context: context
            });
        },
        _getTimelineOptions: function () {
            return {
                editable: {
                    add: false,
                    updateTime: this.editable,
                    updateGroup: this.canUpdateGroup(),
                    remove: false,
                    overrideItems: false
                },
                start: this.data.start_date.toDate(),
                end: this.data.end_date.toDate(),
                min: new moment({
                    year: 1960
                }).toDate(),
                max: new moment({
                    year: 4000
                }).toDate()
            };
        },
        canUpdateGroup: function () {
            var self = this;
            return !_.isEmpty(this.data.groupBy) && _.filter(this.data.groupBy, function (group) {
                return self.fields[self._parseGroupByField(group)].type === 'many2one';
            }).length === this.data.groupBy.length;
        },
        _getRangeDomain: function (range) {
            var domain = [
                [this.mapping.date_start,
                    '<=',
                    dateToServer(range.end)]
            ];
            if (this.mapping.date_end) {
                domain.push([this.mapping.date_end,
                    '>=',
                    dateToServer(range.start)]);
            } else if (!this.mapping.date_delay) {
                domain.push([this.mapping.date_start,
                    '>=',
                    dateToServer(range.start)]);
            }
            return domain;
        },
        _getGroupId: function (record, lastGroup) {
            var groupId = [];
            for (var i = 0; i <= this.data.groupBy.indexOf(lastGroup); i++) {
                var group = this.data.groupBy[i];
                var groupValue = record[group];
                if (this.fields[this._parseGroupByField(group)].type === 'many2one' && groupValue !== false) {
                    groupValue = groupValue[0];
                }
                groupId.push(groupValue);
            }
            return groupId.join('--');
        },
        _parseGroupByField: function (group) {
            var field = group;
            if (field.indexOf(':') !== -1) {
                field = field.split(':') [0];
            }
            return field;
        },
        _parseGroupByFields: function (groupBy) {
            return _.map(groupBy, this._parseGroupByField.bind(this));
        },
        parseGroupId: function (groupId) {
            var self = this;
            var groupValues = groupId.split('--');
            var values = {};
            _.each(this.data.groupBy, function (group, i) {
                values[group] = parseInt(groupValues[i]);
            });
            return values;
        },
        _loadGroups: function (groupBy) {
            var self = this;
            return self._rpc({
                model: self.modelName,
                method: 'read_group',
                context: self.data.context,
                fields: _.uniq(self.fieldNames.concat(self._parseGroupByFields(groupBy))),
                domain: self.data.domain,
                groupBy: groupBy,
                lazy: false
            }).then(function (records) {
                var ids = [];
                _.each(records, function (record) {
                    _.each(self.fieldNames, function (fieldName) {
                        record[fieldName] = self._parseServerValue(self.fields[fieldName], record[fieldName]);
                    });
                    var parentGroup;
                    _.each(self.data.groupBy, function (group) {
                        var groupId = self._getGroupId(record, group);
                        if (self.data.groups.get(groupId) === null) {
                            self.data.groups.add({
                                id: groupId,
                                displayField: group,
                                record: record,
                                order: ids.length
                            });
                        }
                        ids.push(groupId);
                        var group = self.data.groups.get(groupId);
                        if (parentGroup !== undefined) {
                            if (parentGroup.nestedGroups === undefined) {
                                parentGroup.nestedGroups = [];
                            }
                            parentGroup.nestedGroups.push(group.id);
                            self.data.groups.update(parentGroup);
                        }
                        parentGroup = group;
                    });
                });
                return ids;
            });
        },
        _loadItems: function (domain, group) {
            var self = this;
            return self._rpc({
                model: self.modelName,
                method: 'search_read',
                context: self.data.context,
                fields: self.fieldNames,
                domain: domain
            }).then(function (records) {
                var ids = [];
                _.each(records, function (record) {
                    _.each(self.fieldNames, function (fieldName) {
                        record[fieldName] = self._parseServerValue(self.fields[fieldName], record[fieldName]);
                    });
                    var className = '';
                    if (self.fieldColor) {
                        var colorValue = record[self.fieldColor];
                        className = 'o_timeline_color_' + self._getColor(_.isArray(colorValue) ? colorValue[0] : colorValue);
                    }
                    var tooltip = self._getTooltip(record);
                    if (self.data.items.get(record.id) === null) {
                        self.data.items.add(_.extend(self._getRecordRange(record), {
                            id: record.id,
                            group: group && group.id || undefined,
                            content: record.id.toString(),
                            record: record,
                            title: tooltip,
                            className: className
                        }));
                    } else {
                        self.data.items.update(_.extend(self.data.items.get(record.id), self._getRecordRange(record), {
                            id: record.id,
                            group: group && group.id || undefined,
                            record: record,
                            title: tooltip,
                            className: className
                        }));
                    }
                    ids.push(record.id);
                });
                return ids;
            });
        },
        _loadRange: function (range) {
            var self = this;
            var domain = self._getRangeDomain(range);
            var defs = [];
            if (this.data.loadedRange === undefined) {
                this.data.loadedRange = {};
                if (!_.isEmpty(this.data.groupBy)) {
                    this.data.groups.forEach(function (group) {
                        if (group.nestedGroups === undefined) {
                            if (self.data.visibleGroups.length < self.groupPreloadCount) {
                                self.data.visibleGroups.push(group.id);
                            }
                            self.data.loadedRange[group.id] = [];
                        }
                    });
                }
            }
            if (!_.isEmpty(self.data.groupBy)) {
                _.each(self.data.loadedRange, function (loadedRange, groupId) {
                    if (self.data.visibleGroups.indexOf(groupId) !== -1) {
                        var missingRange = _.isEmpty(loadedRange) ? range : rangeExclude(loadedRange, range);
                        if (missingRange !== null) {
                            var group = self.data.groups.get(groupId);
                            var domain = group.record.__domain.concat(self._getRangeDomain(missingRange));
                            defs.push(self._loadItems(domain, group).then(function (items) {
                                self.data.loadedRange[groupId] = _.isEmpty(loadedRange) ? range : rangeMerge(loadedRange, range);
                                return {
                                    items: items,
                                    range: missingRange
                                };
                            }));
                        }
                    }
                });
            } else {
                var missingRange = _.isEmpty(self.data.loadedRange) ? range : rangeExclude(self.data.loadedRange, range);
                if (missingRange !== null) {
                    defs.push(self._loadItems(self.data.domain.concat(self._getRangeDomain(missingRange))).then(function (items) {
                        self.data.loadedRange = _.isEmpty(self.data.loadedRange) ? range : rangeMerge(self.data.loadedRange, range);
                        return {
                            items: items,
                            range: missingRange
                        };
                    }));
                }
            }
            return $.when.apply($, defs);
        },
        _loadTimeline: function () {
            var self = this;
            var def = $.Deferred();
            this.data.timeline_options = this._getTimelineOptions();
            this.data.items = new vis.DataSet();
            this.data.visibleGroups = [];
            this.data.loadedRange = undefined;
            if (!_.isEmpty(self.data.groupBy)) {
                this.data.groups = new vis.DataSet();
                def = this._loadGroups(self.data.groupBy);
            } else {
                this.data.groups = null;
                def.resolve();
            }
            return def.then(function () {
                return self._loadRange({
                    start: self.data.start_date,
                    end: self.data.end_date
                }).then(function () {
                });
            });
        },
        _getTooltip: function (record) {
            var tooltip = this.tooltip;
            if (tooltip) {
                _.each(this.fieldNames, function (fieldName) {
                    var value = record[fieldName];
                    if (value instanceof Array) {
                        value = value[1];
                    }
                    tooltip = tooltip.replace('[' + fieldName + ']', value || _t('Undefined'));
                });
            }
            return tooltip;
        },
        _getColor: function (key) {
            if (!key) {
                return;
            }
            if (this.color_map[key]) {
                return this.color_map[key];
            }
            if (typeof key === 'string' && key.match(/^((#[A-F0-9]{3})|(#[A-F0-9]{6})|((hsl|rgb)a?\(\s*(?:(\s*\d{1,3}%?\s*),?){3}(\s*,[0-9.]{1,4})?\))|)$/i)) {
                return this.color_map[key] = key;
            }
            var index = (((_.keys(this.color_map).length + 1) * 5) % 24) + 1;
            this.color_map[key] = index;
            return index;
        },
        _getRecordRange: function (record) {
            var date_start;
            var date_end;
            var date_delay = record[this.mapping.date_delay] || 1;
            date_start = record[this.mapping.date_start].clone();
            date_end = this.mapping.date_end ? record[this.mapping.date_end].clone() : null;
            if (!date_end && date_delay) {
                date_end = date_start.clone().add(date_delay, 'hours');
            }
            date_start.add(this.getSession().getTZOffset(date_start), 'minutes');
            date_end.add(this.getSession().getTZOffset(date_end), 'minutes');
            return {
                'start': date_start.toDate(),
                'end': date_end.toDate()
            };
        }
    });
})