from reasoning.fake_api import GraphAPI, DeviceAPI, BARuleAPI, AlarmInputAPI


class HistoryWindows:
    def __init__(self):
        self.all_alarms = []  # 所有告警
        self.not_processed_alarms = []  # 未收敛的告警
        
    def update(self, new_alarm, reasoning_result):
        """处理新告警和其推理结果"""
        self.all_alarms.append({
            "alarm": new_alarm,
            "reasoning": reasoning_result
        })
        
        # 根据推理结果更新未收敛告警列表
        self._update_not_processed_alarms(reasoning_result)
        
    def _update_not_processed_alarms(self, reasoning_result):
        # 根据推理结果更新未收敛告警列表的逻辑
        pass


class AlarmReasoningEnv:
    def __init__(self):
        # 需要初始化各个组件
        self.history_windows = HistoryWindows()
        self.alarm_input_api = get_instance(AlarmInputAPI)
        self.graph_api = get_instance(GraphAPI)
        self.device_api = get_instance(DeviceAPI)
        self.ba_rule_api = get_instance(BARuleAPI)

    def run(self):
        # 主循环逻辑
        for alarm in self.alarm_input_api.wait_new():
            # 1. 从HistoryWindows获取未收敛的告警历史
            history_alarms = self.history_windows.not_processed_alarms
            
            # 2. 调用推理模型
            reasoning_result = process_alarm({
                "current_alarm": alarm,
                "history_alarms": history_alarms
            })
            
            # 3. 更新HistoryWindows
            self.history_windows.update(alarm, reasoning_result)




