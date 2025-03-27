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
        current_alarm_id = self.current_id
        
        # 增强：为历史收敛结果添加当前告警ID标记
        for res in reasoning_result:
            if res.get("convergence_type") == "历史收敛":
                res["current_alarm_id"] = current_alarm_id
        
        alarm_record = {
            "id": current_alarm_id,
            "alarm_msg": new_alarm,
            "conclusion": reasoning_result,
            "converged_alarms": []  # 新增字段记录收敛的告警
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
        """根据推理结果更新未收敛告警列表（增强历史收敛标记）"""
        for result in reasoning_result:
            if result.get("convergence_type") == "历史收敛":
                related_alarm_id = result.get("related_alarm_id")
                current_alarm_id = result.get("current_alarm_id")
                
                if related_alarm_id and current_alarm_id:
                    # 标记被收敛告警
                    for alarm in self.all_alarms:
                        if alarm["id"] == related_alarm_id:
                            # 添加收敛标记
                            alarm.setdefault("converged_by", []).append(current_alarm_id)
                            # 记录收敛详细信息
                            alarm.setdefault("convergence_details", []).append({
                                "converged_by": current_alarm_id,
                                "reasoning": result.get("reasoning", ""),
                                "timestamp": result.get("timestamp")
                            })
                    
                    # 更新当前告警的收敛记录
                    current_alarm = next(
                        (a for a in self.all_alarms if a["id"] == current_alarm_id),
                        None
                    )
                    if current_alarm:
                        current_alarm["converged_alarms"].append(related_alarm_id)
                    
                    # 从未处理列表中移除被收敛告警
                    self.not_processed_alarms = [
                        alarm for alarm in self.not_processed_alarms 
                        if alarm["id"] != related_alarm_id
                    ]


class AlarmReasoningEnv:
    def __init__(self):
        self.history_windows = HistoryWindows()
        self.alarm_input_api = AlarmInputAPI()
        self.current_alarm = None
        self._load_all_alarms()

    def _load_all_alarms(self):
        """加载所有告警到 history_windows"""
        all_alarms = self.alarm_input_api.get_all_alarms()
        print(f"Loading {len(all_alarms)} alarms into history windows")
        
        # 初始化收敛相关字段
        for alarm in all_alarms:
            alarm.update({
                'is_processed': False,
                'is_current': False,
                'conclusion': [],
                'converged_by': [],      # 新增字段：被哪些告警收敛
                'converged_alarms': []   # 新增字段：收敛了哪些告警
            })
            self.history_windows.all_alarms.append(alarm)

    def get_current_alarm(self):
        """获取当前告警（保持不变）"""
        try:
            self.current_alarm = next(
                (alarm for alarm in self.history_windows.all_alarms 
                 if not alarm['is_processed'] and not alarm['is_current']),
                None
            )
            
            if self.current_alarm:
                self.current_alarm['is_current'] = True
                print(f"Current alarm set to: {self.current_alarm['id']}")
            else:
                print("No more alarms to process")
            
            return self.current_alarm
            
        except Exception as e:
            print(f"Error getting current alarm: {e}")
            return None

    def get_next_not_processed_alarm(self):
        """获取下一个未处理的告警（保持不变）"""
        for alarm in self.history_windows.all_alarms:
            if not alarm['is_processed']:
                return alarm
        return None

    def get_history_alarms(self):
        """获取历史未收敛告警（保持不变）"""
        current_alarm = self.get_next_not_processed_alarm()
        if not current_alarm:
            return []
        
        history_alarms = []
        current_time = current_alarm['alarm_time']
        
        for alarm in self.history_windows.all_alarms:
            if alarm['alarm_time'] < current_time:
                if alarm.get('conclusion') and any(c['convergence_type'] == '未来收敛' for c in alarm['conclusion']):
                    history_alarms.append(alarm)
        
        return history_alarms

    def process_alarm(self, context, output_callback=None):
        """处理单个告警（保持不变）"""
        current_alarm = context['current_alarm']
        history_alarms = self.get_history_alarms()
        
        if history_alarms:
            history_text = "历史未收敛告警：" + " ".join([
                f"#{alarm['id']}: {alarm['alarm_msg']}" 
                for alarm in history_alarms
            ])
            if output_callback:
                output_callback(history_text + "\n\n")
        
        context['history_alarms'] = history_alarms
        return reasoning_process_alarm(context, output_callback=output_callback)

    def update_alarm_state(self, reasoning_result):
        """更新告警状态（增强收敛关系存储）"""
        current_alarm = self.get_next_not_processed_alarm()
        if current_alarm:
            current_alarm['is_processed'] = True
            current_alarm.pop('is_current', None)
            
            # 记录完整的收敛关系
            enhanced_conclusion = []
            for res in reasoning_result:
                if res.get("convergence_type") == "历史收敛":
                    res.update({
                        "converged_alarm_id": res.get("related_alarm_id"),
                        "converging_alarm_id": current_alarm["id"]
                    })
                enhanced_conclusion.append(res)
            
            current_alarm['conclusion'] = enhanced_conclusion
            return current_alarm

    def get_all_alarms(self):
        """获取所有告警（保持不变）"""
        return self.history_windows.all_alarms

    def reset(self):
        """重置环境状态（保持不变）"""
        self.alarm_input_api.reset()
        self.history_windows = HistoryWindows()
        self.current_alarm = None
        self._load_all_alarms()