# !/usr/bin/env python
# coding: utf-8
"""
#!!================================================================
#版权 (C) 2023, Huawei Technologies Co.
#==================================================================
#文 件 名：                 TencentVideoComment.py
#文件说明：                 腾讯视频测试用例：打开应用，跳过广告，播放视频，查看评论并上划（评论区滑动）
#作    者：                 author
#生成日期：                 2025-12-11
#!!================================================================
"""

import time
import subprocess
from devicetest.core.test_case import Step
from hypium import *
from TencentVideoBase import TencentVideoBase


class TencentVideoComment(TencentVideoBase):
    def __init__(self, controllers):
        super().__init__(controllers)
        # 可自定义滑动次数，默认60次
        self.swipe_count = 60
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1

    def setup(self):
        """调用父类的setup方法"""
        super().setup()

    def process(self):
        # 调用公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        self._start_app_with_monitor_and_skip_ad()

        Step('4.选择首页第一个视频')
        # 点击第一个视频的中心位置(630, 721)
        self.driver.touch((334, 1258))
        time.sleep(1)  # 等待视频加载

        Step('5.切换到评论')
        # 通过Text类型查找"讨论"按钮
        try:
            # 尝试通过文本查找讨论按钮（Text类型）
            comment_element = self.driver.find_element(By.text("讨论"))
            comment_element.click()
        except:
            try:
                # 如果By不存在，尝试直接通过文本查找
                comment_element = self.driver.find_element_by_text("讨论")
                comment_element.click()
            except:
                # 如果都失败，使用driver执行坐标点击
                self.driver.touch((267, 910))
        time.sleep(1)

        Step('6.评论区上划，每秒上划一次')
        window_size = self.driver.get_window_size()
        width = window_size[0]  # tuple的第一个元素是width
        height = window_size[1]  # tuple的第二个元素是height
        start_x = int(width * 0.5)
        start_y = int(height * 0.7)
        end_x = int(width * 0.5)
        end_y = int(height * 0.4)
        
        # 上划指定次数，每次间隔1秒，使用slide方法进行精准滑动
        for i in range(self.swipe_count):
            remaining = self.swipe_count - i - 1  # 剩余次数
            
            # 当开关开启且剩余8次时，触发gc dump
            if self.enable_memdump and remaining == 8:
                Step('7.执行hdc shell命令触发gc dump')
                # 执行hdc shell命令写入control.log
                command1 = 'hdc shell \'echo "1" > /data/app/el2/100/base/com.tencent.videohm/files/control.log\''
                subprocess.run(command1, shell=True)
                time.sleep(1)
            
            # 执行滑动
            self.driver.slide((start_x, start_y), (end_x, end_y), slide_time=0.3)
            time.sleep(0.1)

    def teardown(self):
        """调用父类的teardown方法"""
        super().teardown()

