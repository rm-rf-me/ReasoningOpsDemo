from reasoning.fake_api import (
    GraphAPI, DeviceAPI, BARuleAPI, AlarmInputAPI,
    get_instance, create_all_instances
)
from reasoning.r1_decoder_act_when_thinking_root_cause_analysis import process_alarm as reasoning_process_alarm


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
        """初始化环境"""
        self.history_windows = HistoryWindows()
        self.alarm_input_api = AlarmInputAPI()
        self.current_alarm = None
        self.reset()

    def _load_all_alarms(self):
        """加载所有告警到 history_windows"""
        alarms = self.alarm_input_api.get_all_alarms()
        print(f"Loaded {len(alarms)} alarms")
        if alarms:
            print("Sample alarm:", alarms[0])
        
        # 直接设置 all_alarms 属性
        self.history_windows.all_alarms = [{
            **alarm,
            'is_processed': False,
            'is_current': False,
            'conclusion': []
        } for alarm in alarms]

    def get_current_alarm(self):
        """获取当前处理的告警"""
        return next(
            (alarm for alarm in self.history_windows.all_alarms 
             if not alarm['is_processed']),
            None
        )

    def get_history_alarms(self):
        """获取历史未收敛告警"""
        current_alarm = self.get_next_not_processed_alarm()
        if not current_alarm:
            return []
        
        history_alarms = []
        for alarm in self.history_windows.all_alarms:
            if (alarm['alarm_time'] < current_alarm['alarm_time'] and 
                (not alarm.get('conclusion') or 
                 (isinstance(alarm.get('conclusion'), list) and 
                  len(alarm['conclusion']) > 0 and 
                  alarm['conclusion'][0].get('convergence_type') == '未来收敛'))):
                history_alarms.append(alarm)
        
        return history_alarms

    def get_next_not_processed_alarm(self):
        """获取下一个未处理的告警"""
        for alarm in self.history_windows.all_alarms:
            if not alarm['is_processed']:
                return alarm
        return None

    def process_alarm(self, context, output_callback=None):
        """处理单个告警"""
        current_alarm = context['current_alarm']
        history_alarms = self.get_history_alarms()
        context['history_alarms'] = history_alarms
        return reasoning_process_alarm(context, output_callback=output_callback)

    def update_alarm_state(self, reasoning_result):
        """更新告警状态"""
        current_alarm = self.get_next_not_processed_alarm()
        if current_alarm:
            current_alarm['is_processed'] = True
            current_alarm.pop('is_current', None)
            current_alarm['conclusion'] = reasoning_result
            return current_alarm

    def reset(self):
        """重置环境"""
        self.alarm_input_api.reset()
        self._load_all_alarms()

    def get_all_alarms(self):
        """获取所有告警"""
        return self.history_windows.all_alarms




