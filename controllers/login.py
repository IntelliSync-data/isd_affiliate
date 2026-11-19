# -*- coding: utf-8 -*-
import time
from collections import defaultdict, deque

from odoo import _, http
from odoo.exceptions import AccessDenied
from odoo.http import request

from odoo.addons.portal.controllers.web import Home

# Failed sign-ins per address, per server process
FAIL_LIMIT, FAIL_WINDOW = 10, 900
_failures = defaultdict(deque)


def _too_many_failures(ip):
    now = time.time()
    hits = _failures[ip]
    while hits and now - hits[0] > FAIL_WINDOW:
        hits.popleft()
    return len(hits) >= FAIL_LIMIT


class AffiliateLogin(http.Controller):

    def _render(self, values):
        return request.render('isd_affiliate.login', values)

    @http.route('/login-affiliate', type='http', auth='public', methods=['GET', 'POST'],
                sitemap=False, website=True)
    def login(self, **post):
        user = request.env.user
        if not user._is_public() and user.partner_id.is_affiliate:
            return request.redirect('/my-affiliate')
        values = {'login': (post.get('login') or '').strip(),
                  'signup_enabled': request.env['res.partner'].sudo()._affiliate_signup_enabled()}
        if request.httprequest.method != 'POST':
            return self._render(values)

        ip = request.httprequest.remote_addr or 'unknown'
        if _too_many_failures(ip):
            return self._render(dict(values, error=_('Too many failed sign-ins. Please wait a few minutes.')))
        try:
            request.session.authenticate(request.db, {
                'login': values['login'], 'password': post.get('password') or '', 'type': 'password'})
        except AccessDenied:
            _failures[ip].append(time.time())
            return self._render(dict(values, error=_('Wrong email or password.')))
        if not request.session.uid:
            # Two-factor authentication: Odoo's own page asks for the code
            return request.redirect('/web/login/totp?redirect=/my-affiliate')
        signed_in = request.env['res.users'].sudo().browse(request.session.uid)
        if not signed_in.partner_id.is_affiliate:
            request.session.logout(keep_db=True)
            return self._render(dict(values, error=_(
                'This is not an affiliate account. Please use the regular sign-in page.')))
        return request.redirect('/my-affiliate')


class AffiliateHome(Home):

    def _login_redirect(self, uid, redirect=None):
        """An affiliate signing in on /web/login lands on their own page, not /my."""
        if not redirect:
            user = request.env['res.users'].sudo().browse(uid)
            if user.share and user.partner_id.is_affiliate:
                redirect = '/my-affiliate'
        return super()._login_redirect(uid, redirect=redirect)
