# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import tagged

from ..models.user_profile import REF_KEY, SOURCE_KEY
from .common import AffiliateCase


@tagged('post_install', '-at_install')
class TestSaleSync(AffiliateCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.package = cls._package()
        cls.buyer = cls.env['res.partner'].create({'name': 'Khach Mua', 'email': 'buyer@customer.test'})

    def _order(self, ref=None, source=None, partner=None, package=None):
        ctx = {REF_KEY: ref, SOURCE_KEY: source} if ref else {}
        return self.env['user.profile'].with_context(**ctx).create({
            'partner_id': (partner or self.buyer).id,
            'profile_id': (package or self.package).id,
            'locked_cost': 1000.0,
        })

    def test_referred_order_becomes_a_sent_quotation(self):
        order = self._order(self.affiliate.affiliate_code, 'tiktok')
        self.assertEqual(order.affiliate_id, self.affiliate)
        self.assertEqual(order.affiliate_source_id, self.tiktok)
        sale = order.sale_order_id
        self.assertTrue(sale)
        self.assertEqual(sale.state, 'sent')
        self.assertEqual(sale.affiliate_id, self.affiliate)
        self.assertEqual(sale.affiliate_source_id, self.tiktok)
        self.assertEqual(sale.partner_id, self.buyer)
        self.assertEqual(sale.order_line.product_id, self.package.product_id)
        self.assertEqual(sale.amount_total, 1000.0, 'the order price is what was paid, no tax on top')
        self.assertEqual(self.affiliate.affiliate_sale_count, 1)

    def test_payment_flow(self):
        order = self._order(self.affiliate.affiliate_code)
        sale = order.sale_order_id
        # A price change before payment follows to the sale
        order.locked_cost = 1200.0
        self.assertEqual(sale.amount_total, 1200.0)
        # Half paid is not paid
        order.payment_status = 'half_paid'
        self.assertEqual(sale.state, 'sent')
        order.payment_status = 'paid'
        self.assertEqual(sale.state, 'sale')

    def test_cancelled_order_cancels_the_sale(self):
        order = self._order()
        order.state = 'cancelled'
        self.assertEqual(order.sale_order_id.state, 'cancel')

    def test_referrals_that_do_not_count(self):
        self.assertFalse(self._order('9999-9999-9999').affiliate_id, 'unknown code')
        pending = self.env['res.partner'].create({'name': 'P', 'is_affiliate': True, 'affiliate_state': 'pending'})
        self.assertFalse(self._order(pending.affiliate_code).affiliate_id, 'not approved yet')
        self.assertFalse(self._order(self.affiliate.affiliate_code, partner=self.affiliate).affiliate_id, 'self')
        same_email = self.env['res.partner'].create({'name': 'Lan again', 'email': 'LAN@affiliate.test'})
        self.assertFalse(self._order(self.affiliate.affiliate_code, partner=same_email).affiliate_id, 'self by email')
        # An unknown source key still keeps the affiliate, source falls back to website
        order = self._order(self.affiliate.affiliate_code, 'nope')
        self.assertEqual(order.affiliate_id, self.affiliate)
        self.assertEqual(order.affiliate_source_id, self.website)

    def test_missing_source_defaults_to_website(self):
        # The shared link has no ssm= at all (ref= only)
        order = self._order(self.affiliate.affiliate_code)
        self.assertEqual(order.affiliate_id, self.affiliate)
        self.assertEqual(order.affiliate_source_id, self.website)

    def test_package_without_product_has_no_sale(self):
        order = self._order(package=self._package(product=False))
        self.assertFalse(order.sale_order_id)

    def test_a_failing_sale_never_blocks_the_order(self):
        with patch.object(type(self.env['sale.order']), 'create', side_effect=RuntimeError('boom')):
            order = self._order(self.affiliate.affiliate_code)
        self.assertTrue(order.exists())
        self.assertFalse(order.sale_order_id)
        # It can be made again from the order
        order.action_create_sale_order()
        self.assertEqual(order.sale_order_id.state, 'sent')
