from crypt import methods
import json
import logging

import werkzeug.wrappers

from odoo import http
from odoo.addons.contact_rest_api.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


class AccessToken(http.Controller):
    """."""

    def __init__(self):

        self._token = request.env["switchboard.access.token"]

    @http.route("/contact/api/register", methods=["POST"], type="http", auth="none", csrf=False)
    def register(self):
        pass
    @http.route("/switchboard/api/auth/token", methods=["POST"], type="http", auth="none", csrf=False)
    def token(self, **post):
        """
            params: SDT + password
        """
        _token = request.env["switchboard.access.token"]

        # payload = request.httprequest.data.decode()
        # payload = json.loads(payload)
        
        params = ["company_name", "secret_key"]
        params = {key: post.get(key) for key in params if post.get(key)}
        company_name, secret_key = (
            post.get("company_name"),
            post.get("secret_key"),
        )
        # company_name, secret_key = (
        #     payload.get("company_name"),
        #     payload.get("secret_key"),
        # )
        _credentials_includes_in_body = all([company_name, secret_key])
        if not _credentials_includes_in_body:
            # The request post body is empty the credetials maybe passed via the headers.
            headers = request.httprequest.headers
            company_name = headers.get("company_name")
            secret_key = headers.get("secret_key")
            _credentials_includes_in_headers = all([company_name, secret_key])
            if not _credentials_includes_in_headers:
                return invalid_response(
                    "missing error", "either of the following are missing [company_name, secret_key]", 403,
                )
        try:
            company = request.env['switchboard.partner.company'].sudo().search([('name', '=', company_name),('secret_key', '=', secret_key)], order="id DESC", limit=1)
            if not company:
                raise Exception('Invalid company_name or secret_key!')
        except Exception as e:
            # Invalid database:
            info = "Authenticate false: {}".format((e))
            error = "invalid_company_and_secret_key"
            _logger.error(info)
            return invalid_response("Authenticate false!", error, 403)

        # Generate tokens
        access_token = _token.find_one_or_create_token(company_id=company.id, create=True)
        # Successful response:
        return valid_response({
                    "company_id": company.id,
                    "company_name": company_name,
                    "access_token": access_token,
                })

    @http.route("/switchboard/api/auth/token", methods=["DELETE"], type="http", auth="none", csrf=False)
    def delete(self, **post):
        """Delete a given token"""
        limit = 1
        token = request.env["switchboard.access.token"]
        access_token = post.get("access_token")
        access_token = token.search([("token", "=", access_token)], limit)
        if not access_token:
            error = "Access token is missing in the request header or invalid token was provided"
            return invalid_response(400, error)
        for token in access_token:
            token.unlink()
        # Successful response:
        return valid_response([{"message": "access token %s successfully deleted" % (access_token,), "delete": True}])
