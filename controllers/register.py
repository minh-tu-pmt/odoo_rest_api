import functools
import json
import logging
import random
import string
import hashlib
import re
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from odoo import http
from odoo.addons.contact_rest_api.common import (extract_arguments, invalid_response,
                                                 valid_response)
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


class RegisterController(http.Controller):
    @http.route("/contact/api/register", methods=["POST"], type="http", auth="none", csrf=False)
    def post_register_phone(self, phone_number=None, otp=None, **kwargs):
        try:
            print("AA")
            print(phone_number)
            if not phone_number:
                return invalid_response("Missing phone_number")
            data = request.env['contact.user'].sudo().search([('phone_number', '=', phone_number)], limit=1)
            if data:
                return invalid_response("This number have already exists")
            else:
                otp = ""
                otp = random.randint(1000, 9999)
                date_start = datetime.today()
                notice_interval = timedelta(minutes=5)
                otp_expired_at = date_start + notice_interval
                request.env['contact.user'].sudo().create(
                    {'phone_number': phone_number, 'otp': str(otp), 'otp_expired_at': otp_expired_at})
                # response_data = dict()
                # response_data['otp'] = data.otp
                # response_data['phone_number'] = data.phone_number

                """api send sms otp"""
                # sent_sms_otp = request.env['sms.api'].sudo()._send_sms_batch({
                #     'Phone': phone_number,
                #     'Content': str(otp)
                # })
                print(otp)
                print(otp_expired_at)
                return valid_response("OK")
            # query = f"""INSERT INTO contact_user (otp) VALUES {str(otp)}"""
            # self.env.cr.execute(query)
            # request.env['contact.user'].sudo().create({'otp': otp})

        except Exception as e:
            print(e)
            return invalid_response(e.__str__())

    @http.route("/contact/api/CheckOtp", methods=["POST"], type="http", auth="none", csrf=False)
    def check_register_phone(self, phone_number, otp, code=None, **kwargs):
        try:
            print(phone_number)
            data_check = request.env['contact.user'].sudo().search([('phone_number', '=', phone_number)], limit=1)
            # data_check = f"SELECT * FROM contact_user WHERE phone_number = '{phone_number}'"
            # data_check = request.env['contact.user'].sudo().search([])
            print(type(data_check))
            if data_check['otp'] == otp and data_check['otp_expired_at'] > datetime.today():
                characters = string.ascii_letters + string.digits
                expired_at = datetime.today() + timedelta(minutes=15)
                code = ''.join(random.choice(characters) for i in range(8))
                data_check['code'] = code
                data_check['expired_at'] = expired_at
                return valid_response("Done")
            else:
                if data_check['otp_expired_at'] < datetime.today():
                    query = f"DELETE FROM contact_user WHERE phone_number ='{phone_number}'"
                    request.env.cr.execute(query)
                    print(query)
                    return invalid_response(" Otp is over date")
                return invalid_response("Wrong Otp")
        except Exception as e:
            print(e)
            return invalid_response(e.__str__())

    @http.route("/contact/api/checkpass", methods=["POST"], type="http", auth="none", csrf=False)
    def check_pass_phone(self, phone_number, password, code, **kwargs):
        try:
            print(phone_number)
            data_check = request.env['contact.user'].sudo().search([('phone_number', '=', phone_number)], limit=1)
            print(data_check)
            textpass = password.encode("utf-8")
            hashpass = hashlib.md5(textpass)
            passwords = hashpass.hexdigest()
            if data_check['code'] == code and data_check['expired_at'] > datetime.today():
                data_check['password'] = passwords
                data_check['code'] = None
                data_check['expired_at'] = None
                return valid_response("Done")
            else:
                return invalid_response("Wrong code")
        except Exception as e:
            print(e)
            return invalid_response(e.__str__())
