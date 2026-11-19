# -*- coding: utf-8 -*-
import logging
import re
import time
from collections import defaultdict, deque

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD = 8
# Sign-ups per address per hour, per server process
RATE_LIMIT, RATE_WINDOW = 5, 3600
_attempts = defaultdict(deque)


def _rate_ok():
    ip = request.httprequest.remote_addr or 'unknown'
    now = time.time()
    hits = _attempts[ip]
    while hits and now - hits[0] > RATE_WINDOW:
        hits.popleft()
    if len(hits) >= RATE_LIMIT:
        return False
    hits.append(now)
    return True


class AffiliateSignup(http.Controller):

    def _render(self, values):
        return request.render('isd_affiliate.signup', values)

    @http.route('/affiliate/register', type='http', auth='public', sitemap=False)
    def register_old_address(self, **kw):
        # Links shared before the page moved keep working
        return request.redirect('/register-affiliate', code=301)

    @http.route('/register-affiliate', type='http', auth='public', methods=['GET', 'POST'],
                sitemap=False, website=True)
    def register(self, **post):
        Partner = request.env['res.partner']
        if not Partner._affiliate_signup_enabled():
            return self._render({'closed': True})
        if not request.env.user._is_public():
            return request.redirect('/my-affiliate')
        if request.httprequest.method == 'GET':
            return self._render({})

        values = {k: (post.get(k) or '').strip() for k in ('name', 'email', 'phone')}
        error = self._validate(post, values)
        if not error and not _rate_ok():
            error = _('Too many sign-ups from this address. Please try again later.')
        if error:
            return self._render(dict(values, error=error))
        try:
            login = self._create_affiliate(values, post['password'])
        except Exception:
            _logger.exception('isd_affiliate: sign-up failed for %s', values['email'])
            request.env.cr.rollback()
            return self._render(dict(values, error=_('Could not create your account. Please try again.')))
        # authenticate() opens its own cursor, so the new user must be committed first
        request.env.cr.commit()
        request.session.authenticate(request.db, {
            'login': login, 'password': post['password'], 'type': 'password'})
        return request.redirect('/my-affiliate')

    def _validate(self, post, values):
        if not values['name']:
            return _('Please enter your name.')
        if not EMAIL_RE.match(values['email']):
            return _('Please enter a valid email address.')
        if len(post.get('password') or '') < MIN_PASSWORD:
            return _('The password needs at least %s characters.', MIN_PASSWORD)
        if post.get('password') != post.get('confirm_password'):
            return _('The two passwords do not match.')
        if not post.get('terms'):
            return _('Please accept the terms to continue.')
        Users = request.env['res.users'].sudo().with_context(active_test=False)
        if Users.search_count(['|', ('login', '=ilike', values['email']), ('email', '=ilike', values['email'])]):
            return _('An account already exists for this email. Log in instead.')
        return None

    def _create_affiliate(self, values, password):
        """A portal user from Odoo's portal template, plus the Affiliate group.

        The default user template used by ordinary sign-ups is not touched.
        A contact that already has this email (a past customer) is reused
        rather than duplicated.
        """
        env = request.env
        Partner = env['res.partner'].sudo()
        partner = Partner.search([('email', '=ilike', values['email']), ('user_ids', '=', False)], limit=1)
        if not partner:
            partner = Partner.create({'name': values['name'], 'email': values['email']})
        approval = env['ir.config_parameter'].sudo().get_param('isd_affiliate.require_approval') == 'True'
        partner.write({
            'phone': values['phone'] or partner.phone,
            'is_affiliate': True,
            'is_company': False,
            'affiliate_state': 'pending' if approval else 'approved',
        })
        user = env['res.users'].sudo()._create_user_from_template({
            'login': values['email'],
            'partner_id': partner.id,
            'password': password,
        })
        user.write({'groups_id': [(4, env.ref('isd_affiliate.group_affiliate_portal').id)]})
        return user.login
