# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # A real link to the affiliate, not free text like Customer Reference, so
    # orders can be filtered, grouped and counted per affiliate
    affiliate_id = fields.Many2one(
        'res.partner', string='Affiliate', index=True, tracking=True, copy=False,
        domain=[('is_affiliate', '=', True)], ondelete='restrict')
    affiliate_source_id = fields.Many2one(
        'isd.affiliate.source', string='Affiliate Source', copy=False, ondelete='restrict')
    profile_order_id = fields.Many2one(
        'user.profile', string='Profile Order', copy=False, readonly=True, ondelete='set null')
