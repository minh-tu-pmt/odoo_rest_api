# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import hashlib
import os
import uuid
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

expires_in = "contact_rest_api.contact_access_token_expires_in"


def nonce(length=40, prefix="access_token"):
    rbytes = os.urandom(length)
    return "{}_{}".format(prefix, str(hashlib.sha1(rbytes).hexdigest()))

class ContactUser(models.Model):
    _name = 'contact.user'
    _description = 'Contact User'

    phone_number = fields.Char(string="Phone", required = True, index=True)
    password = fields.Char(string="Password")
    name = fields.Char(string="Name")
    otp = fields.Char(string="OTP")
    otp_expired_at = fields.Datetime(string="OTP expired")
    code = fields.Char(string="Code")
    # active = fields.Boolean(string="Active")
    expired_at = fields.Datetime(string="Date expired")
    access_tokens = fields.One2many('contact.access.token', 'user_id', string="access tokens")

class AccessToken(models.Model):
    _name = 'contact.access.token'
    _description = 'Contact access token'
    
    token = fields.Char("Access Token", required=True)
    expires = fields.Datetime(string="Expires", required=True)
    scope = fields.Char(string="Scope")
    user_id = fields.Many2one('contact.user', string="")
    
    def find_one_or_create_token(self, user_id=None, create=False):
        if not user_id:
            _logger.error('User is not found!')
            raise Exception('User is not found!')
        access_token = self.env["contact.access.token"].sudo().search([("user_id", "=", user_id)], order="id DESC", limit=1)
        if access_token:
            access_token = access_token[0]
            if access_token.has_expired():
                access_token = None
        if not access_token and create:
            expires = datetime.now() + timedelta(seconds=int(self.env.ref(expires_in).sudo().value))
            vals = {
                "user_id": user_id,
                "scope": "userinfo",
                "expires": expires.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                "token": nonce(),
            }
            access_token = self.env["contact.access.token"].sudo().create(vals)
        if not access_token:
            return None
        return access_token.token
    
    def is_valid(self, scopes=None):
        """
        Checks if the access token is valid.

        :param scopes: An iterable containing the scopes to check or None
        """
        self.ensure_one()
        return not self.has_expired() and self._allow_scopes(scopes)

    def has_expired(self):
        self.ensure_one()
        return datetime.now() > fields.Datetime.from_string(self.expires)

    def _allow_scopes(self, scopes):
        self.ensure_one()
        if not scopes:
            return True

        provided_scopes = set(self.scope.split())
        resource_scopes = set(scopes)

        return resource_scopes.issubset(provided_scopes)
