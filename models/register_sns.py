import logging
import threading

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)

class RegisterSms(models.Model):
    _inherit = 'sms.sms'

    IAP_TO_SMS_STATE = {
        'success': 'sent',
        'insufficient_credit': 'sms_credit',
        'wrong_number_format': 'sms_number_format',
        'server_error': 'sms_server',
        'unregistered': 'sms_acc'
    }

    RESULT_CODE = {
        '100': 'success',
        '99': 'server_error',
        '101': 'unregistered',
        '102': 'unregistered',
        '103': 'insufficient_credit',
        '104': 'unregistered',
        '118': 'server_error',
        '119': 'server_error',
        '131': 'server_error',
        '132': 'server_error',
        '145': 'server_error',
        '146': 'server_error',
        '159': 'server_error',
        '177': 'server_error',
    }

    def send(self, unlink_failed=False, unlink_sent=True, auto_commit=False, raise_exception=False):
        """ Main API method to send SMS.
        """
        sms_dict = dict()
        for record in self:
            mailing_id = record.mailing_id.id
            value = sms_dict.get(mailing_id, False)
            if not value:
                sms_dict[mailing_id] = self.filtered(lambda sms: sms.mailing_id.id == mailing_id)

        for key in sms_dict:
            for batch_ids in sms_dict[key]._split_batch():
                self.browse(batch_ids)._send(unlink_failed=unlink_failed, unlink_sent=unlink_sent,
                                             raise_exception=raise_exception)
                # auto-commit if asked except in testing mode
                if auto_commit is True and not getattr(threading.currentThread(), 'testing', False):
                    self._cr.commit()

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        list_phone = [record.number for record in self]
        list_phone = ','.join(list_phone)
        msg_data = {
            'Phone': list_phone,
            'Content': self.mailing_id.body_plaintext
        }

        try:
            iap_results = self.env['sms.api']._send_sms_batch(msg_data)
        except Exception as e:
            _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(self.ids), self.ids, e)
            if raise_exception:
                raise
            self._postprocess_iap_sent_sms(
                [{'res_id': sms.id, 'state': 'server_error'} for sms in self],
                unlink_failed=unlink_failed, unlink_sent=unlink_sent)
        else:
            state = self.RESULT_CODE.get(iap_results['CodeResult'], 'server_error')
            _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, iap_results)

            if state == 'success':
                msg_result = [{'res_id': sms.id, 'state': self.IAP_TO_SMS_STATE['server_error'], 'number': sms.number}
                              for sms in self]
                params = {'RefId': iap_results['SMSID']}
                sent_results = self.env['sms.api']._get_sms_sent_detail(params)
                if sent_results.get('CodeResult', False) != '100':
                    _logger.warning('Get Sent SMS: %s: failed with exception %s', iap_results['SMSID'],
                                    sent_results.get('ErrorMessage', 'server_error'))
                else:
                    receivers = sent_results.get('ReceiverList', [])
                    for result in receivers:
                        if result.get('IsSent', False) and result.get('SentResult', False):
                            for msg in msg_result:
                                if msg.get('number', '') == result.get('Phone', ''):
                                    msg['state'] = 'success'
                                    _logger.info('Sent SMS: %s to phone number: %s successfully', msg.get('res_id'),
                                                 msg.get('number'))

                    self._postprocess_iap_sent_sms(msg_result, unlink_failed=unlink_failed, unlink_sent=unlink_sent)
            else:
                self._postprocess_iap_sent_sms(
                    [{'res_id': sms.id, 'state': self.IAP_TO_SMS_STATE[state]} for sms in self],
                    unlink_failed=unlink_failed, unlink_sent=unlink_sent)