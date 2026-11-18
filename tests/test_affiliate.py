# -*- coding: utf-8 -*-
import re

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from ..models.affiliate_source import slugify
from .common import AffiliateCase

CODE_RE = re.compile(r'^\d{4}-\d{4}-\d{4}$')


@tagged('post_install', '-at_install')
class TestAffiliate(AffiliateCase):

    def test_code_format_and_uniqueness(self):
        partners = self.env['res.partner'].create([
            {'name': 'A%s' % i, 'is_affiliate': True} for i in range(30)])
        codes = partners.mapped('affiliate_code')
        self.assertTrue(all(CODE_RE.match(c) for c in codes), codes)
        self.assertEqual(len(set(codes)), len(codes))
        with self.assertRaises(Exception), self.cr.savepoint():
            partners[1].affiliate_code = partners[0].affiliate_code
            partners.flush_recordset()

    def test_contact_type_affiliate(self):
        person = self.env['res.partner'].create({'name': 'Chi'})
        self.assertEqual(person.company_type, 'person')
        self.assertFalse(person.affiliate_code)
        person.company_type = 'affiliate'
        self.assertTrue(person.is_affiliate)
        self.assertFalse(person.is_company)
        self.assertTrue(CODE_RE.match(person.affiliate_code))
        code = person.affiliate_code
        # Back to individual: the code stays, so past orders keep their link
        person.company_type = 'person'
        self.assertFalse(person.is_affiliate)
        self.assertEqual(person.affiliate_code, code)
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({'name': 'Co', 'is_company': True, 'is_affiliate': True})

    def test_links(self):
        code = self.affiliate.affiliate_code
        self.assertEqual(self.affiliate._affiliate_link_for(self.tiktok),
                         'https://bloompod.vn?ref=%s&ssm=tiktok' % code)
        self.assertEqual(self.affiliate._affiliate_link_for(), 'https://bloompod.vn?ref=%s' % code)
        self.affiliate.affiliate_source_id = self.tiktok
        self.assertIn('ssm=tiktok', self.affiliate.affiliate_link)
        # A base that already has a query string
        self.env['ir.config_parameter'].sudo().set_param('isd_affiliate.base_url', 'https://shop.vn/landing?lang=vi')
        self.assertEqual(self.affiliate._affiliate_link_for(self.tiktok),
                         'https://shop.vn/landing?lang=vi&ref=%s&ssm=tiktok' % code)
        # No link while waiting for approval, or without a base URL
        self.affiliate.affiliate_state = 'pending'
        self.assertFalse(self.affiliate._affiliate_link_for(self.tiktok))
        self.affiliate.affiliate_state = 'approved'
        self.env['ir.config_parameter'].sudo().set_param('isd_affiliate.base_url', '')
        self.assertFalse(self.affiliate._affiliate_link_for(self.tiktok))

    def test_find_affiliate_only_approved(self):
        Partner = self.env['res.partner']
        self.assertEqual(Partner._find_affiliate(self.affiliate.affiliate_code), self.affiliate)
        self.assertFalse(Partner._find_affiliate('0000-0000-0000'))
        self.assertFalse(Partner._find_affiliate(''))
        self.affiliate.action_affiliate_reject()
        self.assertFalse(Partner._find_affiliate(self.affiliate.affiliate_code))

    def test_source_keys(self):
        self.assertEqual(slugify('TikTok'), 'tiktok')
        self.assertEqual(slugify('Facebook Ads'), 'facebook-ads')
        self.assertEqual(slugify('Zalo Đà Nẵng'), 'zalo-da-nang')
        Source = self.env['isd.affiliate.source']
        source = Source.create({'name': 'Threads Việt'})
        self.assertEqual(source.key, 'threads-viet')
        with self.assertRaises(ValidationError):
            Source.create({'name': 'Bad', 'key': 'has space'})
        with self.assertRaises(Exception), self.cr.savepoint():
            Source.create({'name': 'Other TikTok', 'key': 'tiktok'})
            Source.flush_model()
        self.assertEqual(Source._by_key('TikTok'), self.tiktok)
        self.tiktok.status = 'inactive'
        self.assertFalse(Source._by_key('tiktok'))

    def test_list_shows_affiliates_only_even_without_filters(self):
        self.env['res.partner'].create({'name': 'Plain Customer'})
        action = self.env['ir.actions.act_window']._for_xml_id('isd_affiliate.action_affiliate')
        from odoo.tools.safe_eval import safe_eval
        found = self.env['res.partner'].search(safe_eval(action['domain']))
        self.assertIn(self.affiliate, found)
        self.assertTrue(all(found.mapped('is_affiliate')))
