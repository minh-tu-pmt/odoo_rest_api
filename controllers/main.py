import ast
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

    @http.route("/contact/api/")
    def get_phone_detail(self):
        pass
    
    @http.route()
    def post_phone_detail(self):
        pass

    @validate_token
    @http.route('/switchboard/api/send_message', type="json", auth="none", methods=["POST"], csrf=False)
    def post_send_message(self, **payload):
        """Send a new message for multi phone number.
        Basic sage:
        import requests

        headers = {
            'content-type': 'application/json',
            'charset': 'utf-8',
            'access-token': 'access_token'
        }
        data = {
            'Phone': [0941xxxxxx, 0981xxxxxx],
            'Content': 'Cam on quy khach da su dung dich vu cua chung toi. Chuc quy khach mot ngay tot lanh!'
        }
        req = requests.post('/switchboard/api/send_message', headers=headers, data=data)

        """
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)
        
        phone, content = (
            payload.get("phone"),
            payload.get("content"),
        )
        
        _payload_includes_in_body = all([phone, content])
        if not _payload_includes_in_body:
                return invalid_response(
                    "missing error", "either of the following are missing [phone, content]", 400,
                )
    
        try:
            message = {'Phone': phone, 'Content': content}
            response = request.env['sms.api']._send_sms_batch(message)
            return valid_response(response)
        except Exception as e:
            return invalid_response("Error", e)

    @validate_token
    @http.route('/switchboard/api/send_autocall', type="json", auth="none", methods=["POST"], csrf=False)
    def post_send_autocall(self, **payload):
        """
        speed:
            Tốc độ đọc, Giá trị từ  -3 - 3 : Mặc định là 0
            - 3 : Cực kì chậm
            -2 : Rất chậm
            -1 : Chậm
            0 : Bình thường
            1 : Nhanh
            ...
        voice:
            Giọng đọc, có thể một trong các giá trị sau
            banmai : Giọng nữ miền Bắc
            leminh : Giọng nam miền Bắc
            lannhi : Giọng nữ miền Nam
        cid:
            Đầu số dùng để gọi tự động. 
            Nếu không truyền, mặc định ưu tiên gọi nội mạng
        name: Tên của phiên gọi tự động
        
        template_dialplans: array
            Cấu trúc phiên gọi tự động theo loại. 
            1. Phiên gọi tự động với file ghi âm
            [{
            "target_type" : "Recording",
            "target":"5ed0c6dffb7b390007e111"
            }]
            target: Là Id của file ghi âm được lấy từ  chức năng
            Cấu hình >> Tổng đài >> File ghi âm

            2. Phiên gọi tự động  với Text To Speech
            [{
            "target_type":"Text_variable"
            }]

            3. Phiên gọi tự động với file ghi âm và Text To Speech. Thực thi theo thứ tự 
            [{ 
            "target_type":"Text_variable" 
            }, 
            { 
                "target_type":"Recording",   
                "target":"5ed0c6dffb7b390007e5211" 
            }]
        variables: Mảng giá trị cho Text To Speech 
            [ 
            "Đơn hàng của bạn là ",
            "CKHDKD00203",
            "Số tiền",
            "900000",
            "Đã được bàn giao cho đối tác vận chuyển"
            ]
        phone_number_list* Array Danh sách số điện thoại cần gọi
        num_retry Integer Số lần gọi lại khi không nghe máy. Mặc định là 0
        num_per_call Integer Số cuộc gọi mỗi lần. Mặc định là 15 
        distance_per_call Integer Khoảng cách thời gian , giữa các lần gọi. Mặc định là 30s
        distance_retry Integer Khoảng cách giữa các lần gọi lại . Mặc định là 0
        
        {
            "name":"Thông báo đơn hàng",
            "template_dialplans":[
                {"target_type":"Text_variable"},
                {"target_type":"Text_variable"},
                {"target_type":"Text_variable"},
                {"target_type":"Text_variable"}
            ],
            "variables":[
                "Đơn hàng của bạn là",
                "HHKKK",
                "Tổng giá trị",
                "90000"
            ],
            }
        """
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)
        
        name, speed, voice, phone_number_list, num_retry, num_per_call, distance_per_call, distance_retry, template_dialplans, variables = (
            payload.get("name"),
            payload.get("speed"),
            payload.get("voice"),
            payload.get("phone_number_list"),
            payload.get("num_retry"),
            payload.get("num_per_call"),
            payload.get("distance_per_call"),
            payload.get("distance_retry"),
            payload.get("template_dialplans"),
            payload.get("variables")
        )
        
        _payload_includes_in_body = all([name, speed, voice, phone_number_list, num_retry, num_per_call, distance_per_call, distance_retry, template_dialplans, variables])
        if not _payload_includes_in_body:
            return invalid_response(
                    "missing error", "either of the following are missing [name, speed, voice, phone_number_list, num_retry, num_per_call, distance_per_call, distance_retry, template_dialplans, variables]", 403,
                )
        
        try:
            response = request.env['actech.omicall.api']._send_auto_call(params=[], payload=payload)
            return valid_response(response)
        except Exception as e:
            return invalid_response("exception", e)

