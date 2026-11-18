# -*- coding: utf-8 -*-
import re
import unicodedata

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

KEY_RE = re.compile(r'^[a-z0-9_-]+$')


def slugify(name):
    """'TikTok' -> 'tiktok', 'Facebook Ads' -> 'facebook-ads', 'Zalo Đà Nẵng' -> 'zalo-da-nang'."""
    text = (name or '').replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')


class AffiliateSource(models.Model):
    """A place an affiliate shares their link: TikTok, Facebook... Its key is
    the ssm= of the link, so an order can say where the customer came from."""
    _name = 'isd.affiliate.source'
    _description = 'Affiliate Source'
    _order = 'sequence, name, id'

    name = fields.Char(required=True, translate=True)
    description = fields.Text()
    key = fields.Char(required=True, copy=False,
                      help='Goes into the link as ssm=<key>. Lowercase letters, digits, - and _ only.')
    icon = fields.Image(max_width=256, max_height=256)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')],
                              default='active', required=True,
                              help='Only active sources can be picked for a link')
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('key_unique', 'unique(key)', 'Another source already uses this key.'),
    ]

    @api.constrains('key')
    def _check_key(self):
        for source in self:
            if not KEY_RE.match(source.key or ''):
                raise ValidationError(_(
                    'The key "%s" can only hold lowercase letters, digits, - and _, '
                    'because it goes into a web address.', source.key))

    @api.onchange('name')
    def _onchange_name(self):
        # Follow the name while the key is still the one made from it, so a
        # key typed by hand is never overwritten
        for source in self:
            if not source.key or source.key == slugify(source._origin.name):
                source.key = slugify(source.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('key') and vals.get('name'):
                vals['key'] = slugify(vals['name'])
            elif vals.get('key'):
                vals['key'] = vals['key'].strip().lower()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('key'):
            vals['key'] = vals['key'].strip().lower()
        return super().write(vals)

    @api.model
    def _by_key(self, key):
        """The active source with this key, or an empty recordset."""
        key = (key or '').strip().lower()
        if not key:
            return self.browse()
        return self.sudo().search([('key', '=', key), ('status', '=', 'active')], limit=1)
