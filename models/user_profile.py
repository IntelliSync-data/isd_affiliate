# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# The create-order API passes the referral through the context
REF_KEY = 'isd_affiliate_ref'
SOURCE_KEY = 'isd_affiliate_source'


class UserProfile(models.Model):
    """A Profile Management order. When its package has a product, the order
    also lives as a Sale Order: quotation sent when ordered, sales order once
    fully paid."""
    _inherit = 'user.profile'

    affiliate_id = fields.Many2one(
        'res.partner', string='Affiliate', index=True, tracking=True, copy=False,
        domain=[('is_affiliate', '=', True)], ondelete='restrict')
    affiliate_source_id = fields.Many2one(
        'isd.affiliate.source', string='Affiliate Source', copy=False, ondelete='restrict')
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order', copy=False, readonly=True, ondelete='set null')
    package_has_product = fields.Boolean(compute='_compute_package_has_product')

    def _compute_package_has_product(self):
        for order in self:
            order.package_has_product = bool(order.profile_id.product_id)

    # ---------------------------------------------------------- referral
    @api.model
    def _referral_from_context(self, partner_id):
        """(affiliate, source) for the ref= and ssm= the API received.

        A wrong, unapproved or missing code is ignored: the customer's order
        must go through whatever the link said. So is a customer referring
        themselves.
        """
        Partner = self.env['res.partner']
        affiliate = Partner._find_affiliate(self.env.context.get(REF_KEY))
        if not affiliate:
            return Partner.browse(), self.env['isd.affiliate.source'].browse()
        buyer = Partner.sudo().browse(partner_id).exists()
        if buyer and (buyer == affiliate or (
                buyer.email and affiliate.email
                and buyer.email.strip().lower() == affiliate.email.strip().lower())):
            _logger.info('isd_affiliate: order by %s ignored as a self-referral', affiliate.affiliate_code)
            return Partner.browse(), self.env['isd.affiliate.source'].browse()
        source = self.env['isd.affiliate.source']._by_key(self.env.context.get(SOURCE_KEY))
        if not source:
            # Link chung không có ssm=, hoặc ssm sai/không active: coi như đến
            # từ website thay vì bỏ trống nguồn.
            source = self.env['isd.affiliate.source']._by_key('website')
        return affiliate, source

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get(REF_KEY):
            for vals in vals_list:
                if not vals.get('affiliate_id'):
                    affiliate, source = self._referral_from_context(vals.get('partner_id'))
                    if affiliate:
                        vals['affiliate_id'] = affiliate.id
                        vals['affiliate_source_id'] = source.id or False
        orders = super().create(vals_list)
        orders._create_sale_orders()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('isd_affiliate_syncing'):
            return res
        if {'payment_status', 'locked_cost', 'state', 'affiliate_id', 'affiliate_source_id'} & set(vals):
            self._sync_sale_orders()
        return res

    # -------------------------------------------------------- sale order
    def _sale_order_values(self):
        self.ensure_one()
        product = self.profile_id.product_id
        return {
            'partner_id': self.partner_id.id,
            'origin': self.order_code,
            'affiliate_id': self.affiliate_id.id or False,
            'affiliate_source_id': self.affiliate_source_id.id or False,
            'profile_order_id': self.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': self.profile_id.name or product.display_name,
                'product_uom_qty': 1,
                'price_unit': self.total_cost,
                # The order price is what the customer pays: no tax on top
                'tax_id': [(5, 0, 0)],
            })],
        }

    def _create_sale_orders(self):
        """A Sale Order, marked Quotation Sent, for each order of a package with a product.

        A failure here is logged and leaves the order itself untouched: the
        customer's purchase must never fail because of the sales side.
        """
        for order in self:
            if order.sale_order_id or not order.profile_id.product_id or not order.partner_id:
                continue
            try:
                with self.env.cr.savepoint():
                    sale = self.env['sale.order'].sudo().create(order._sale_order_values())
                    # Mark as sent without emailing the customer
                    sale.action_quotation_sent()
                    order.with_context(isd_affiliate_syncing=True).sudo().write({'sale_order_id': sale.id})
                    if order.payment_status == 'paid':
                        sale.action_confirm()
            except Exception:
                _logger.exception('isd_affiliate: could not create the Sale Order of order %s', order.order_code)

    def _sync_sale_orders(self):
        """Carry the order's price, referral and status over to its Sale Order."""
        for order in self.filtered('sale_order_id'):
            sale = order.sale_order_id.sudo()
            try:
                with self.env.cr.savepoint():
                    if order.state == 'cancelled':
                        if sale.state != 'cancel':
                            sale._action_cancel()
                        continue
                    if sale.state not in ('draft', 'sent'):
                        continue
                    referral = {'affiliate_id': order.affiliate_id.id or False,
                                'affiliate_source_id': order.affiliate_source_id.id or False}
                    if (sale.affiliate_id.id or False, sale.affiliate_source_id.id or False) != (
                            referral['affiliate_id'], referral['affiliate_source_id']):
                        sale.write(referral)
                    line = sale.order_line.filtered(
                        lambda l: l.product_id == order.profile_id.product_id)[:1]
                    if line and line.price_unit != order.total_cost:
                        line.price_unit = order.total_cost
                    # Half paid is not paid: the sale waits for the rest of the money
                    if order.payment_status == 'paid':
                        sale.action_confirm()
            except Exception:
                _logger.exception('isd_affiliate: could not update the Sale Order of order %s', order.order_code)

    def action_create_sale_order(self):
        self.ensure_one()
        if self.sale_order_id:
            raise UserError(_('This order already has a Sale Order.'))
        if not self.profile_id.product_id:
            raise UserError(_('Link a product to the package first.'))
        self._create_sale_orders()
        if not self.sale_order_id:
            raise UserError(_('The Sale Order could not be created. The server log has the details.'))
        return self.action_view_sale_order()

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }
