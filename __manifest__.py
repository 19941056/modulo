# -*- coding: utf-8 -*-
{
    'name': "Citas Massay",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Fidenet",
    'website': "http://www.fidenet.net",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'web', 'hr'],
    # 'qweb': ['static/src/xml/cits_timeline.xml'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/citas_mgmt_view.xml',
        'views/citas_config_settings_view.xml',
        'views/cits_mgmt_menu_view.xml',
        'views/cits_specialist_schedule.xml',
        'data/cits_config_data.xml',
        'data/cit_mgmt_cits_seq.xml',
        'email/mail_to_customer_on_aprove_cits.xml',
        'email/reminder_mail_to_customer.xml',
        'wizard/citas_cancel_reason_wizard_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    "pre_init_hook": "pre_init_check",
}
