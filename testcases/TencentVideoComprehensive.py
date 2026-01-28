# !/usr/bin/env python
# coding: utf-8
"""
#!!================================================================
#版权 (C) 2023, Huawei Technologies Co.
#==================================================================
#文 件 名：                 TencentVideoComprehensive.py
#文件说明：                 腾讯视频综合测试用例：首页button切换、视频播放滑动、评论区滑动
#作    者：                 author
#生成日期：                 2025-12-24
#!!================================================================
"""

import time
import subprocess
from devicetest.core.test_case import Step
from hypium import *
from TencentVideoBase import TencentVideoBase


class TencentVideoComprehensive(TencentVideoBase):
    def __init__(self, controllers):
        super().__init__(controllers)
        # button列表
        self.button_list = ["首页", "电视剧", "动漫", "电影", "综艺", "NBA", "纪录片", "体育"]
        # 视频滑动次数（20秒，每秒一次）
        self.video_swipe_count = 20
        # 评论区滑动次数（50秒，每秒一次）
        self.comment_swipe_count = 50
        # pmap采样间隔时间（秒），默认1秒
        self.hidumper_interval = 1

    def setup(self):
        """调用父类的setup方法"""
        super().setup()

    def _click_button(self, button_name):
        """点击指定的button，使用BY.text().type("Button")的方式"""
        try:
            # 使用BY.text().type("Button")的方式点击button
            self.driver.touch(BY.text(button_name).type("Button"))
            return True
        except:
            try:
                # 如果失败，尝试只使用text查找
                button_element = self.driver.find_element(By.text(button_name))
                button_element.click()
                return True
            except:
                try:
                    # 如果By不存在，尝试直接通过文本查找
                    button_element = self.driver.find_element_by_text(button_name)
                    button_element.click()
                    return True
                except:
                    try:
                        # 如果都失败，使用CONTAINS模糊匹配，不限制类型
                        self.driver.touch(BY.text(button_name, MatchType.CONTAINS))
                        return True
                    except:
                        return False

    def process(self):
        # 调用公共方法：强制退出app、启动pmap监控、启动应用、跳过广告
        self._start_app_with_monitor_and_skip_ad()

        Step('4.首页button切换一次（来回）')
        # 顺序点击button
        for button_name in self.button_list:
            if self._click_button(button_name):
                time.sleep(1.3)
            else:
                # 如果找不到button，等待一下继续
                time.sleep(0.2)
        
        # 逆序点击button，最终回到首页
        for button_name in reversed(self.button_list):
            if self._click_button(button_name):
                time.sleep(1.3)
            else:
                # 如果找不到button，等待一下继续
                time.sleep(0.2)

        Step('5.选择首页第一个视频')
        # 点击第一个视频的中心位置(630, 721)
        self.driver.touch((334, 1258))
        time.sleep(1)  # 等待视频加载

        Step('6.视频播放界面向上滑动20秒')
        window_size = self.driver.get_window_size()
        width = window_size[0]  # tuple的第一个元素是width
        height = window_size[1]  # tuple的第二个元素是height
        start_x = int(width * 0.5)
        start_y = int(height * 0.7)
        end_x = int(width * 0.5)
        end_y = int(height * 0.3)
        
        # 上划指定次数，每次间隔1秒，使用slide方法进行精准滑动
        for i in range(self.video_swipe_count):
            # 执行滑动
            self.driver.slide((start_x, start_y), (end_x, end_y), slide_time=0.3)
            time.sleep(0.3)

        Step('8.切换到评论')
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

        Step('9.评论区上划50秒')
        # 上划指定次数，每次间隔1秒，使用slide方法进行精准滑动
        for i in range(self.comment_swipe_count):
            remaining = self.comment_swipe_count - i - 1  # 剩余次数
            
            # 当开关开启且剩余8次时，触发gc dump
            if self.enable_memdump and remaining == 11:
                Step('10.执行hdc shell命令触发gc dump')
                # 执行hdc shell命令写入control.log
                command1 = 'hdc shell \'echo "1" > /data/app/el2/100/base/com.tencent.videohm/files/control.log\''
                subprocess.run(command1, shell=True)
                time.sleep(1)
            
            # 执行滑动
            self.driver.slide((start_x, start_y), (end_x, end_y), slide_time=0.3)
            time.sleep(0.2)

    def teardown(self):
        """调用父类的teardown方法"""
        super().teardown()

