# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase


def make_package(env, product=True, cost=1000.0):
    step = env['profile.step'].create({'name': 'Step 1', 'cost': 0.0})
    package = env['profile.management'].create({
        'name': 'Gói Test', 'state': 'active', 'package_cost': cost, 'step_ids': [(6, 0, step.ids)]})
    if product:
        package.action_create_product()
    return package


class AffiliateCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('isd_affiliate.base_url', 'https://bloompod.vn')
        cls.tiktok = cls.env.ref('isd_affiliate.source_tiktok')
        cls.website = cls.env.ref('isd_affiliate.source_website')
        cls.affiliate = cls.env['res.partner'].create({
            'name': 'Lan Affiliate', 'email': 'lan@affiliate.test', 'is_affiliate': True})

    @classmethod
    def _package(cls, product=True, cost=1000.0):
        return make_package(cls.env, product, cost)
