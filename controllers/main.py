import functools
import json
import logging
import re

from odoo import http
from odoo.addons.contact_rest_api.common import (extract_arguments, invalid_response,
                                        valid_response)
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


def validate_token(func):
    """."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """."""
        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            return invalid_response("access_token_not_found", "missing access token in request header", 401)
        access_token_data = (
            request.env["contact.access.token"].sudo().search([("token", "=", access_token)], order="id DESC", limit=1)
        )

        if access_token_data.find_one_or_create_token(company_id=access_token_data.company_id.id) != access_token:
            return invalid_response("access_token", "token seems to have expired or invalid", 401)

        # request.session.uid = access_token_data.user_id.id
        # request.uid = access_token_data.user_id.id
        return func(self, *args, **kwargs)

    return wrap

class APIController(http.Controller):
    """."""

    def __init__(self):
        self._model = "ir.model"

    # @validate_token
    @http.route("/contact/api/get_detail", methods=["GET"], type="http", auth="none", csrf=False)
    def get_phone_detail(self, phone_number=None,**kwargs):
        data = request.env['contacts.partner'].sudo().search([('phone_number', '=', phone_number)], limit=1)
        if data:
            response_data = dict()
            response_data['name'] = data.name
            response_data['identity_card'] = data.identity_card or None
            response_data['gender'] = data.gender or None
            response_data['phone_number'] = data.phone_number
            response_data['company'] = data.company or None
            response_data['facebook'] = data.facebook or None
            response_data['facebook_name'] = data.facebook_name or None
            response_data['address'] = data.address or None
            response_data['fax_number'] = data.fax_number or None
            response_data['website'] = data.website or None
            response_data['note'] = data.note or None
            return valid_response(response_data)
        return invalid_response("Not found!", message="Phone number: %s not found!"%phone_number, status=404)
    
    # @validate_token
    @http.route("/contact/api/detail", methods=["POST"], type="http", auth="none", csrf=False)
    def post_phone_detail(self, phone_number = None, **kwargs):
        try:
            params = ["name", "identity_card", "gender", "company", "facebook", 'facebook_name', 'address', 'fax_number', 'website', 'note']
            request_data = {key: kwargs.get(key) for key in params if kwargs.get(key)}
            if not phone_number:
                return invalid_response(
                        "missing error", "either of the following are missing [phone_number]", 400
                    )
            record = request.env['contacts.partner'].sudo().search([('phone_number', '=', phone_number)], limit=1)
            if record:
                record.sudo().write(request_data)
                _logger.info("Update infomation %s successfully!"%phone_number)
                return valid_response("Update infomation %s successfully!"%phone_number)
            return invalid_response("Not found!", message="Phone number: %s not found!"%phone_number, status=404)
        except Exception as e:
            _logger.error(e.__str__())
            return invalid_response("Error!", e.__str__(), status=400)


