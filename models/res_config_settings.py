# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # The module's own base URL: web.base.url stays as it is
    isd_affiliate_base_url = fields.Char(
        string='Referral Link Base URL', config_parameter='isd_affiliate.base_url',
        help='Where referral links point, e.g. https://bloompod.vn. Each link adds ?ref=<code>&ssm=<source>.')
    isd_affiliate_signup_enabled = fields.Boolean(
        string='Open Sign-up', config_parameter='isd_affiliate.signup_enabled',
        help='Lets anyone register as an affiliate on /affiliate/register')
    isd_affiliate_require_approval = fields.Boolean(
        string='Approve New Affiliates', config_parameter='isd_affiliate.require_approval',
        help='New affiliates wait for a manager: until then they have no link and their referrals are not counted')
