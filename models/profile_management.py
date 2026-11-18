# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class ProfileManagement(models.Model):
    _inherit = 'profile.management'

    product_id = fields.Many2one(
        'product.product', string='Product', ondelete='set null', tracking=True,
        help='Orders of this package also become Sale Orders of this product')

    def action_create_product(self):
        """A service product with the package's name and price, linked right away."""
        self.ensure_one()
        if self.product_id:
            raise UserError(_('This package already has a product.'))
        self.product_id = self.env['product.product'].create({
            'name': self.name,
            'type': 'service',
            'list_price': self.total_cost,
            'sale_ok': True,
            'purchase_ok': False,
            # The order price is what the customer pays, taxes included
            'taxes_id': [(5, 0, 0)],
        })
        return True
