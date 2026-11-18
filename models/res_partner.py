# -*- coding: utf-8 -*-
import random
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_random = random.SystemRandom()


def new_code_candidate():
    """XXXX-XXXX-XXXX in digits. Random, not a sequence, so no one can guess
    the next affiliate's code and try it on someone else's order."""
    digits = ''.join(_random.choice('0123456789') for _i in range(12))
    return '%s-%s-%s' % (digits[:4], digits[4:8], digits[8:])


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # The third choice beside Individual and Company. An affiliate is a person
    # (is_company stays False) who is also flagged as an affiliate.
    company_type = fields.Selection(selection_add=[('affiliate', 'Affiliate')])
    is_affiliate = fields.Boolean(string='Is an Affiliate', index=True, copy=False)
    affiliate_code = fields.Char(string='Affiliate Code', readonly=True, copy=False, index=True)
    affiliate_state = fields.Selection([
        ('pending', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Affiliate Status', default='approved', copy=False,
        help='Only an approved affiliate has links, and only their referrals are counted')
    affiliate_source_id = fields.Many2one(
        'isd.affiliate.source', string='Link Source', domain=[('status', '=', 'active')],
        ondelete='set null', help='The network the link below is made for')
    affiliate_link = fields.Char(string='Referral Link', compute='_compute_affiliate_link')
    affiliate_sale_count = fields.Integer(string='Referred Orders', compute='_compute_affiliate_sales')

    _sql_constraints = [
        ('affiliate_code_unique', 'unique(affiliate_code)', 'This affiliate code is already used.'),
    ]

    # ------------------------------------------------------------ type
    @api.depends('is_company', 'is_affiliate')
    def _compute_company_type(self):
        super()._compute_company_type()
        for partner in self:
            if partner.is_affiliate and not partner.is_company:
                partner.company_type = 'affiliate'

    def _write_company_type(self):
        for partner in self:
            partner.is_affiliate = partner.company_type == 'affiliate'
        super()._write_company_type()

    @api.onchange('company_type')
    def onchange_company_type(self):
        super().onchange_company_type()
        self.is_affiliate = self.company_type == 'affiliate'

    @api.constrains('is_affiliate', 'is_company')
    def _check_affiliate_is_a_person(self):
        if any(p.is_affiliate and p.is_company for p in self):
            raise ValidationError(_('An affiliate is a person, not a company.'))

    # ------------------------------------------------------------ code
    @api.model
    def _new_affiliate_code(self):
        Partner = self.sudo().with_context(active_test=False)
        for _attempt in range(50):
            code = new_code_candidate()
            if not Partner.search_count([('affiliate_code', '=', code)]):
                return code
        raise ValidationError(_('Could not find a free affiliate code, please try again.'))

    def _ensure_affiliate_code(self):
        for partner in self.filtered(lambda p: p.is_affiliate and not p.affiliate_code):
            partner.affiliate_code = self._new_affiliate_code()

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._ensure_affiliate_code()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_affiliate') or vals.get('company_type') == 'affiliate':
            self._ensure_affiliate_code()
        return res

    # ------------------------------------------------------------ links
    @api.model
    def _affiliate_base_url(self):
        return (self.env['ir.config_parameter'].sudo().get_param('isd_affiliate.base_url') or '').strip()

    def _affiliate_link_for(self, source=None):
        """The referral link for one source, or False while there is none to give."""
        self.ensure_one()
        base = self._affiliate_base_url()
        if not (base and self.is_affiliate and self.affiliate_code and self.affiliate_state == 'approved'):
            return False
        params = {'ref': self.affiliate_code}
        if source:
            params['ssm'] = source.key
        # The base may already carry a query string of its own
        separator = '' if base.endswith(('?', '&')) else ('&' if '?' in base else '?')
        return base + separator + urlencode(params)

    @api.depends('affiliate_code', 'affiliate_state', 'affiliate_source_id.key', 'is_affiliate')
    def _compute_affiliate_link(self):
        for partner in self:
            partner.affiliate_link = partner._affiliate_link_for(partner.affiliate_source_id)

    # ------------------------------------------------------- approval
    def action_affiliate_approve(self):
        self.write({'affiliate_state': 'approved'})

    def action_affiliate_reject(self):
        self.write({'affiliate_state': 'rejected'})

    @api.model
    def _find_affiliate(self, code):
        """The approved affiliate behind a ref= code, or an empty recordset."""
        code = (code or '').strip()
        if not code:
            return self.browse()
        return self.sudo().search([
            ('affiliate_code', '=', code), ('is_affiliate', '=', True),
            ('affiliate_state', '=', 'approved')], limit=1)

    # ---------------------------------------------------- referred sales
    def _compute_affiliate_sales(self):
        counts = {}
        affiliates = self.filtered('is_affiliate')
        if affiliates:
            groups = self.env['sale.order'].sudo()._read_group(
                [('affiliate_id', 'in', affiliates.ids), ('state', '!=', 'cancel')],
                ['affiliate_id'], ['__count'])
            counts = {partner.id: count for partner, count in groups}
        for partner in self:
            partner.affiliate_sale_count = counts.get(partner.id, 0)

    def action_view_affiliate_sales(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Referred Orders'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('affiliate_id', '=', self.id)],
            'context': {'default_affiliate_id': self.id, 'create': False},
        }

    @api.model
    def _affiliate_signup_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param('isd_affiliate.signup_enabled') == 'True'
