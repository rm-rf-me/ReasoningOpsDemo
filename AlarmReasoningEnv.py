from reasoning.fake_api import (
    GraphAPI, DeviceAPI, BARuleAPI, AlarmInputAPI,
    get_instance, create_all_instances
)
from reasoning.r1_decoder_act_when_thinking_root_cause_analysis import process_alarm


class HistoryWindows:
    def __init__(self):
        self.all_alarms = []  # 所有告警
        self.not_processed_alarms = []  # 未收敛的告警
        self.current_id = 0  # 添加 ID 计数器
        
    def update(self, new_alarm, reasoning_result):
        """处理新告警和其推理结果"""
        self.current_id += 1
        alarm_record = {
            "id": self.current_id,
            "alarm_msg": new_alarm,
            "conclusion": reasoning_result
        }
        self.all_alarms.append(alarm_record)
        
        # 添加到未处理列表
        self.not_processed_alarms.append(alarm_record)
        
        # 更新未收敛告警列表
        self._update_not_processed_alarms(reasoning_result)
        
    def get_not_processed_alarms(self):
        """获取未收敛的告警列表"""
        return [{
            "id": alarm["id"],
            "alarm_msg": alarm["alarm_msg"],
            "conclusion": alarm["conclusion"]
        } for alarm in self.not_processed_alarms]
        
    def _update_not_processed_alarms(self, reasoning_result):
        """根据推理结果更新未收敛告警列表"""
        # 如果是历史收敛，从未收敛列表中移除被收敛的告警
        for result in reasoning_result:
            if result["convergence_type"] == "历史收敛":
                alarm_id = result["related_alarm_id"]
                if alarm_id:
                    self.not_processed_alarms = [
                        alarm for alarm in self.not_processed_alarms 
                        if alarm["id"] != alarm_id
                    ]


class AlarmReasoningEnv:
    def __init__(self):
        self.history_windows = HistoryWindows()
        self.alarm_input_api = AlarmInputAPI()
        self.current_alarm = None
        self.all_alarms_list = []  # 存储所有告警
        self._load_all_alarms()

    def _load_all_alarms(self):
        """加载所有告警"""
        self.all_alarms_list = list(self.alarm_input_api.get_all_alarms())

    def get_current_alarm(self):
        """获取当前需要处理的告警"""
        try:
            self.current_alarm = next(self.alarm_input_api.wait_new())
            print(f"当前告警：{self.current_alarm}")
            return self.current_alarm
        except StopIteration:
            return None

    def get_history_alarms(self):
        """获取历史未收敛告警"""
        return self.history_windows.get_not_processed_alarms()

    def get_all_alarms(self):
        """获取所有告警列表"""
        return [
            {
                "id": idx + 1,
                "alarm_msg": alarm,
                "is_processed": idx < len(self.history_windows.all_alarms),
                "is_current": idx == len(self.history_windows.all_alarms),
                "conclusion": self.history_windows.all_alarms[idx]["conclusion"] if idx < len(self.history_windows.all_alarms) else None
            }
            for idx, alarm in enumerate(self.all_alarms_list)
        ]

    def update_alarm_state(self, reasoning_result):
        """更新告警状态"""
        if self.current_alarm:
            self.history_windows.update(self.current_alarm, reasoning_result)

    def process_alarm(self, alarm_info, output_callback=None):
        """处理告警"""
        return process_alarm(alarm_info, output_callback=output_callback)

    def run(self):
        # 主循环逻辑
        for alarm in self.alarm_input_api.wait_new():
            # 1. 从HistoryWindows获取未收敛的告警历史
            history_alarms = self.history_windows.get_not_processed_alarms()
            
            # 2. 调用推理模型
            reasoning_result, all_reasoning = self.process_alarm({
                "current_alarm": alarm,
                "history_alarms": history_alarms
            })
            
            # 3. 更新HistoryWindows
            self.history_windows.update(alarm, reasoning_result)

    def reset(self):
        """重置环境状态"""
        self.alarm_input_api.reset()
        self.history_windows = HistoryWindows()
        self._load_all_alarms()




