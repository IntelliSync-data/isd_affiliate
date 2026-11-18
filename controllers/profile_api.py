# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from odoo.addons.isd_profile_management.controllers.external_api import ExternalProfileAPIController

from ..models.user_profile import REF_KEY, SOURCE_KEY


class AffiliateProfileAPI(ExternalProfileAPIController):

    @http.route()
    def create_profile_package(self, **kwargs):
        """Accept affiliate_ref and affiliate_source alongside the existing payload.

        They travel to the order through the context; the order decides
        whether the code counts (approved, not the buyer's own).
        """
        ref = kwargs.pop('affiliate_ref', None)
        source = kwargs.pop('affiliate_source', None)
        if ref:
            request.update_context(**{REF_KEY: str(ref).strip(), SOURCE_KEY: str(source or '').strip()})
        return super().create_profile_package(**kwargs)

    @http.route()
    def get_order_info(self, **kwargs):
        result = super().get_order_info(**kwargs)
        order_data = isinstance(result, dict) and result.get('success') and result.get('order')
        if order_data and order_data.get('id'):
            order = request.env['user.profile'].sudo().browse(order_data['id']).exists()
            affiliate = order.affiliate_id
            # The code and a display name only: never the affiliate's contact details
            order_data['affiliate'] = {
                'code': affiliate.affiliate_code,
                'name': affiliate.name,
                'source': order.affiliate_source_id.key or None,
            } if affiliate else None
        return result
