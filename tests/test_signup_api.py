# -*- coding: utf-8 -*-
import json
import re

from odoo.tests import HttpCase, tagged

from .common import make_package

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


@tagged('post_install', '-at_install')
class TestSignupAndApi(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('isd_affiliate.base_url', 'https://bloompod.vn')
        # Every sign-up below comes from the same address
        from ..controllers import signup
        signup._attempts.clear()

    def _register(self, **values):
        page = self.url_open('/affiliate/register')
        self.assertEqual(page.status_code, 200)
        data = {'name': 'Mai Affiliate', 'email': 'mai@affiliate.test', 'phone': '0901234567',
                'password': 'secret-123', 'confirm_password': 'secret-123', 'terms': '1',
                'csrf_token': CSRF_RE.search(page.text).group(1)}
        data.update(values)
        return self.url_open('/affiliate/register', data=data)

    def test_signup_makes_a_portal_affiliate(self):
        template_before = self.env['ir.config_parameter'].sudo().get_param('base.template_portal_user_id')
        response = self._register()
        self.assertTrue(response.url.endswith('/my/affiliate'), response.url)
        user = self.env['res.users'].search([('login', '=', 'mai@affiliate.test')])
        self.assertTrue(user.share, 'a portal user')
        self.assertFalse(user.has_group('base.group_user'), 'never in the back office')
        self.assertTrue(user.has_group('isd_affiliate.group_affiliate_portal'))
        partner = user.partner_id
        self.assertTrue(partner.is_affiliate)
        self.assertEqual(partner.affiliate_state, 'approved')
        self.assertEqual(partner.phone, '0901234567')
        self.assertRegex(partner.affiliate_code, r'^\d{4}-\d{4}-\d{4}$')
        # The ordinary sign-up template is untouched
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('base.template_portal_user_id'),
                         template_before)
        # Their page, with their code and link, behind the login just made
        self.assertIn(partner.affiliate_code, response.text)
        self.assertIn('https://bloompod.vn?ref=%s' % partner.affiliate_code, response.text)
        # And no way into /odoo: Odoo sends a portal user to /my
        self.assertTrue(self.url_open('/odoo').url.split('?')[0].endswith('/my'))

    def test_signup_waits_for_approval_when_asked(self):
        self.env['ir.config_parameter'].sudo().set_param('isd_affiliate.require_approval', 'True')
        response = self._register(email='wait@affiliate.test')
        partner = self.env['res.users'].search([('login', '=', 'wait@affiliate.test')]).partner_id
        self.assertEqual(partner.affiliate_state, 'pending')
        self.assertIn('waiting for approval', response.text)
        self.assertNotIn('ref=%s' % partner.affiliate_code, response.text)

    def test_signup_errors_and_reuse(self):
        self._register(email='dup@affiliate.test')
        self.url_open('/web/session/logout')
        response = self._register(email='DUP@affiliate.test')
        self.assertIn('already exists', response.text)
        self.assertIn('do not match', self._register(email='x@affiliate.test', confirm_password='other-123').text)
        # A past customer's contact is reused, not duplicated
        customer = self.env['res.partner'].create({'name': 'Old Customer', 'email': 'old@customer.test'})
        self._register(email='old@customer.test')
        self.assertTrue(customer.is_affiliate)
        self.assertEqual(self.env['res.partner'].search_count([('email', '=', 'old@customer.test')]), 1)

    def test_closed_signup(self):
        self.env['ir.config_parameter'].sudo().set_param('isd_affiliate.signup_enabled', 'False')
        self.assertIn('closed', self.url_open('/affiliate/register').text)

    def test_create_order_api_reads_the_ref(self):
        affiliate = self.env['res.partner'].create({'name': 'Lan', 'email': 'lan@affiliate.test', 'is_affiliate': True})
        package = make_package(self.env)
        payload = {'package_id': package.id, 'email': 'buyer@customer.test', 'name': 'Buyer',
                   'affiliate_ref': affiliate.affiliate_code, 'affiliate_source': 'tiktok'}
        result = self.url_open('/api/profile/create', data=json.dumps({'jsonrpc': '2.0', 'params': payload}),
                               headers={'Content-Type': 'application/json'}).json()['result']
        self.assertTrue(result.get('success'), result)
        order = self.env['user.profile'].browse(result['user_profile_id'])
        self.assertEqual(order.affiliate_id, affiliate)
        self.assertEqual(order.affiliate_source_id.key, 'tiktok')
        self.assertEqual(order.sale_order_id.state, 'sent')
        self.assertEqual(order.sale_order_id.affiliate_id, affiliate)

        info = self.url_open('/api/profile/order-info', data=json.dumps({'jsonrpc': '2.0', 'params': {
            'user_profile_id': order.id}}), headers={'Content-Type': 'application/json'}).json()['result']
        self.assertEqual(info['order']['affiliate'], {
            'code': affiliate.affiliate_code, 'name': 'Lan', 'source': 'tiktok'})

        # A wrong code never stops the order
        payload['affiliate_ref'] = 'not-a-code'
        payload['email'] = 'other@customer.test'
        result = self.url_open('/api/profile/create', data=json.dumps({'jsonrpc': '2.0', 'params': payload}),
                               headers={'Content-Type': 'application/json'}).json()['result']
        self.assertTrue(result.get('success'), result)
        self.assertFalse(self.env['user.profile'].browse(result['user_profile_id']).affiliate_id)
