# !/usr/bin/env python
# coding: utf-8
"""
#!!================================================================
#版权 (C) 2023, Huawei Technologies Co.
#==================================================================
#文 件 名：                 TencentVideoButton.py
#文件说明：                 腾讯视频测试用例：打开应用，跳过广告，首页button切换（button切换）, 首页向下滑动
#作    者：                 author
#生成日期：                 2025-12-11
#!!================================================================
"""

import time
from devicetest.core.test_case import Step
from hypium import *
from TencentVideoBase import TencentVideoBase


class TencentVideoMemTest(TencentVideoBase):
    def __init__(self, controllers):
        super().__init__(controllers)
        # button列表由基类统一定义，如需自定义可在此覆盖：
        # self.button_list = ["首页", "NBA","电视剧", "动漫", "电影", "综艺","吉家宴",  "纪录片", "体育", "播客"]
        # 视频滑动次数，基准20次，压测时乘以 stress_multiplier
        self.video_swipe_count = 20 * self.stress_multiplier
        # 评论区滑动次数，基准50次，压测时乘以 stress_multiplier
        self.comment_swipe_count = 50 * self.stress_multiplier
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1

    def setup(self):
        """调用父类的setup方法"""
        super().setup()

    def tabSwitch(self):
        Step('4.首页button来回切换')
        self._tab_switch(memdump_remaining=1)

    def homepageSlide(self):
        Step('4.首页上划，每秒上划一次')
        self._slide_page(self.video_swipe_count, end_y_ratio=0.2, sleep_interval=0.3)

    def commentPageSlide(self):
        Step('4.选择首页第一个视频')
        self._click_first_video()

        Step('5.切换到评论')
        self._switch_to_comment()

        Step('6.评论区上划，每秒上划一次')
        self._slide_page(self.comment_swipe_count, end_y_ratio=0.4, sleep_interval=0.3, memdump_remaining=8)

    def process(self):
        # 调用公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        self._start_app_with_monitor_and_skip_ad()
        self.homepageSlide()
        self.tabSwitch()
        self.commentPageSlide()


        time.sleep(2)

    def teardown(self):
        """调用父类的teardown方法"""
        super().teardown()

