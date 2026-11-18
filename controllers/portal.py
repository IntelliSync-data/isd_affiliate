# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

ORDER_LIMIT = 50


class AffiliatePortal(http.Controller):

    @http.route('/my/affiliate', type='http', auth='user', website=True, sitemap=False)
    def my_affiliate(self, **kw):
        partner = request.env.user.partner_id
        if not partner.is_affiliate:
            return request.redirect('/my')
        partner = partner.sudo()
        sources = request.env['isd.affiliate.source'].sudo().search([('status', '=', 'active')])
        links = [{'id': s.id, 'name': s.name, 'icon': bool(s.icon), 'url': partner._affiliate_link_for(s)}
                 for s in sources]
        Sale = request.env['sale.order'].sudo()
        orders = Sale.search([('affiliate_id', '=', partner.id)], order='date_order desc', limit=ORDER_LIMIT)
        state_labels = dict(Sale._fields['state']._description_selection(request.env))
        # Only what the affiliate needs: never who the buyer is
        rows = [{
            'date': order.date_order,
            'product': ', '.join(order.order_line.mapped('product_id.display_name')),
            'amount': order.amount_total,
            'currency': order.currency_id,
            'state': order.state,
            'state_label': state_labels.get(order.state, order.state),
            'source': order.affiliate_source_id.name or '',
        } for order in orders]
        counted = Sale.search([('affiliate_id', '=', partner.id), ('state', '!=', 'cancel')])
        paid = counted.filtered(lambda o: o.state == 'sale')
        return request.render('isd_affiliate.portal_my_affiliate', {
            'affiliate': partner,
            'links': links,
            'default_link': partner._affiliate_link_for(),
            'orders': rows,
            'order_count': len(counted),
            'paid_total': sum(paid.mapped('amount_total')),
            'currency': request.env.company.currency_id,
            'page_name': 'affiliate',
        })

    @http.route('/affiliate/source-icon/<int:source_id>', type='http', auth='public', sitemap=False)
    def source_icon(self, source_id, **kw):
        """A source's icon for the affiliate page: portal users cannot read sources themselves."""
        source = request.env['isd.affiliate.source'].sudo().browse(source_id).exists()
        if not source or not source.icon or source.status != 'active':
            return request.not_found()
        stream = request.env['ir.binary']._get_image_stream_from(source, 'icon')
        return stream.get_response(max_age=3600)
