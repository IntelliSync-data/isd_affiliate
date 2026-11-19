# -*- coding: utf-8 -*-
{
    'name': 'Affiliate (by ISD)',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Affiliates who sign up themselves, member codes, referral links by '
               'social network, and referred orders tracked to the right affiliate',
    'description': """
Affiliate marketing for Profile Management packages.

* A third contact type, Affiliate, with a member code XXXX-XXXX-XXXX
* Referral links per social network source (?ref=...&ssm=...)
* Public sign-up page; affiliates are portal users with their own page
* Optional manual approval before an affiliate's link counts
* Packages linked to a product: their orders become Sale Orders, quotation
  sent when ordered, sales order once fully paid
* Affiliate and source on every Sale Order, read from the create-order API
    """,
    'author': 'IntelliSyncData',
    'website': 'https://intellisyncdata.com',
    'license': 'LGPL-3',
    'depends': ['contacts', 'portal', 'auth_signup', 'sales_team', 'sale', 'isd_profile_management'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'data/source_data.xml',
        'views/affiliate_source_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/profile_management_views.xml',
        'views/user_profile_views.xml',
        'views/portal_templates.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'isd_affiliate/static/src/js/affiliate_portal.js',
            'isd_affiliate/static/src/scss/affiliate_portal.scss',
        ],
    },
    'installable': True,
    'application': True,
}
