# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "HRMS Transition Module Odoo 18",
    "summary": """HRMS Transition Module Odoo 18""",
    # "icon":"hris_test_module.static/src/description/icon.jpg",
    "version": "1.0.1",
    "sequence": 2,
    # "license": "AGPL-3",
    "category": "Productivity",
    "author": "Marc Roda",
    "website": "",
    "depends": ["base", "mail", "utm", "website", 'hr', 'hrms_employee_module'],
    # 'qweb': [
    #     'static/src/hris_style.scss',
    # ],
    "data": [
        "data/hrms_transition_groups.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        # "views/rule.xml",
        "views/actions.xml",
        "views/menus.xml",
        "views/kanban_views.xml",
        "views/list_views.xml",
        "views/search_filters.xml",
        "views/form_views.xml",                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
        
    ],
    "application": True,
    "auto_install": False,
    "installable": True,
}
