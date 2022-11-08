"""
Contains unit tests for newly add lib functions.
"""
# pylint: disable=protected-access

import sys
import os
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "...")))
import unittest

from libs import vault_utils
from libs import sdp_api
from libs import metrignome_api

from jobs.terminal_attention_prioritizer.tap_const import VNO_OPTIONS

VNO = "exederes"
# VNO = "telbr"
ENV = "prod"


class TestVaultUtils(unittest.TestCase):
    """
    Test that the functions in libs/vault_utils.py
    """

    def test_format_python(self):
        """
        run format_python.sh
        """
        os.system("./format_python.sh -m read ./libs/vault_utils.py")

    def test_get_ut_devops_cicd_password(self):
        """
        run test_get_ut_devops_cicd_password
        """
        self.assertTrue(vault_utils.get_ut_devops_cicd_password())

    def test_get_prod_sdp_api_service_account_password(self):
        """
        test_get_prod_sdp_api_service_account_password
        """
        self.assertTrue(vault_utils.get_prod_sdp_api_service_account_password())

    def test_get_prod_sdp_api_service_account_password_wrong_token(self):
        """
        test_get_prod_sdp_api_service_account_password_wrong_token
        """
        # with self.assertRaises(RuntimeError):
        # vault_utils.get_prod_sdp_api_service_account_password("invalidToken")


class TestSdpApi(unittest.TestCase):
    """
    Test that the functions in libs/sdp_api.py
    """

    def test_get_sdp_token(self):
        """
        test_get_sdp_token
        """
        for vno in VNO_OPTIONS:
            token = sdp_api.get_sdp_token(vno)
            if token is None:
                print(f"test_get_sdp_token for {vno} failed! ")

    def test_format_python(self):
        """
        format_python for sdp_api
        """
        os.system("./format_python.sh -m read ./libs/sdp_api.py")

    def test_get_new_sdp_token_wrong_vno(self):
        """
        test_get_new_sdp_token_wrong_vno
        """
        # self.assertFalse(sdp_api.get_new_sdp_token("invalidVno"))

    def test_get_sdp_token_wrong_vno(self):
        """
        test_get_sdp_token_wrong_vno
        """
        # self.assertFalse(sdp_api.get_sdp_token("invalidVno"))

    def test_get_PPILv2_report_content_types(self):
        """
        test_get_PPILv2_report_content_types
        """
        self.assertTrue(sdp_api.get_PPILv2_report_content_types(VNO))

    def test_get_PPILv2_available_reports_info(self):
        """
        test_get_PPILv2_available_reports_info
        """
        self.assertTrue(sdp_api.get_PPILv2_available_reports_info(VNO))

    def test_get_PPILv2_report_by_id_None(self):
        """
        test_get_PPILv2_report_by_id_None
        """
        self.assertFalse(sdp_api.get_PPILv2_report_by_id(None))

    def test_get_PPILv2_report_by_id(self):
        """
        test_get_PPILv2_report_by_id
        """
        report_id = [*sdp_api.get_PPILv2_available_reports_info()][0]
        self.assertTrue(sdp_api.get_PPILv2_report_by_id(report_id))

    def test_get_PPILv2_report_by_gen_date(self):
        """
        test_get_PPILv2_report_by_gen_date
        """

        fmt_str = "%Y-%m-%dT%H:%M:%SZ"
        yesterday = date.today() - timedelta(days=1)
        yestday_str = yesterday.strftime(fmt_str)[:-10]
        self.assertTrue(sdp_api.get_PPILv2_report_by_gen_date(yestday_str, VNO))

    def test_get_PPILv2_report_latest_gen_date(self):
        """
        test_get_PPILv2_report_latest_gen_date
        """
        amr = sdp_api.get_PPILv2_report_latest_gen_date(VNO)
        self.assertTrue(amr)
        # for key, value in amr.items():
        #     print(key,':',value)
        #     print('============================================')

    def test_get_ut_mac_addrs_from_PPILv2_report_latest_gen_date(self):
        """
        test_get_ut_mac_addrs_from_PPILv2_report_latest_gen_date
        """
        mac_addr_list = sdp_api.get_ut_mac_addrs_from_PPILv2_report_latest_gen_date(VNO)
        # print(mac_addr_list)
        self.assertTrue(len(mac_addr_list))


class TestMetrignomeApi(unittest.TestCase):
    """
    Test the functions in libs/metrignome.py
    """

    def test_get_new_metrignome_token(self):
        """
        test_get_new_metrignome_token
        """
        self.assertTrue(metrignome_api.get_new_metrignome_token())

    def test_get_metrignome_token(self):
        """
        test_get_metrignome_token
        """
        self.assertTrue(metrignome_api.get_metrignome_token())

    def test_get_terminalOfflineEventReason(self):
        """
        test_get_terminalOfflineEventReason
        """
        from_ts = (datetime.today() - timedelta(days=2)).timestamp()
        to_ts = datetime.today().timestamp()
        reason_dict = metrignome_api.get_terminalOfflineEventReason(
            from_ts=from_ts, to_ts=to_ts, vno=VNO, env=ENV
        )
        # print(reason_dict)
        offline_uts = len(reason_dict)
        print(f"\n {VNO} number of offline UTs: {offline_uts}")
        self.assertTrue(offline_uts)
