const app = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],  // 避免与Flask模板冲突
    data: {
        socket: null,
        activeAlarms: [],
        allAlarms: [],
        notProcessedAlarms: [],
        reasoningText: '',  // 改用单个文本字符串
        processing: false,
        currentAlarmId: null,
        started: false
    },
    methods: {
        initSocket() {
            console.log('Initializing socket connection...');
            this.socket = io();
            
            // 监听初始状态
            this.socket.on('init_state', (data) => {
                console.log('Received init state:', data);
                this.allAlarms = data.all_alarms;
                this.notProcessedAlarms = data.not_processed_alarms;
            });
            
            // 监听推理完成
            this.socket.on('reasoning_complete', (data) => {
                console.log('Reasoning complete:', data);
                this.processing = false;
                this.allAlarms = data.all_alarms;
                this.notProcessedAlarms = data.not_processed_alarms;
                
                // 显示推理过程
                this.reasoningText = data.reasoning_text;
                
                // 确保当前处理的告警保持展开
                const currentAlarm = this.allAlarms.find(alarm => alarm.is_current);
                if (currentAlarm && !this.activeAlarms.includes(currentAlarm.id)) {
                    this.activeAlarms.push(currentAlarm.id);
                }
            });

            // 监听错误
            this.socket.on('reasoning_error', (data) => {
                console.error('Reasoning error:', data);
                this.processing = false;
                alert('处理过程中出现错误：' + data.error);
            });
        },
        
        getStatusType(alarm) {
            return alarm.is_processed ? 'success' : 
                   alarm.is_current ? 'danger' : 'info';
        },
        
        getStatusText(alarm) {
            return alarm.is_processed ? '已处理' : 
                   alarm.is_current ? '处理中' : '待处理';
        },
        
        formatJSON(obj) {
            return JSON.stringify(obj, null, 2);
        },
        
        processNextAlarm() {
            if (this.processing) return;
            
            console.log('Starting reasoning process...');
            this.processing = true;
            if (!this.started) {
                this.started = true;
            }
            this.clearReasoningOutput();
            this.socket.emit('process_next_alarm');
        },
        
        clearReasoningOutput() {
            this.reasoningText = '';
        }
    },
    computed: {
        buttonText() {
            if (!this.started) {
                return '开始处理告警';
            }
            return this.processing ? '处理中...' : '处理下一条告警';
        },
        allAlarmIds() {
            // 返回所有告警的 ID 列表，用于默认展开
            return this.allAlarms.map(alarm => alarm.id);
        },
        formattedSteps() {
            return this.reasoningSteps.map(step => {
                if (step.includes('<think>')) {
                    return {
                        content: step.replace(/<\/?think>/g, ''),
                        type: 'warning',
                        color: '#E6A23C',
                        size: 'large'
                    };
                } else if (step.includes('<action>')) {
                    const content = step.replace(/<\/?action>/g, '');
                    return {
                        content: `<strong>执行操作:</strong><br/>${content}`,
                        type: 'primary',
                        color: '#409EFF',
                        size: 'normal'
                    };
                } else if (step.includes('<result>')) {
                    const content = step.replace(/<\/?result>/g, '');
                    return {
                        content: `<strong>操作结果:</strong><br/>${content}`,
                        type: 'success',
                        color: '#67C23A',
                        size: 'normal'
                    };
                } else if (step.includes('<answer>')) {
                    return {
                        content: step.replace(/<\/?answer>/g, ''),
                        type: 'success',
                        color: '#67C23A',
                        size: 'large'
                    };
                }
                return {
                    content: step,
                    type: 'info',
                    color: '#909399',
                    size: 'normal'
                };
            });
        },
        defaultActiveAlarms() {
            // 返回所有已处理的告警ID和当前处理的告警ID
            return this.allAlarms
                .filter(alarm => alarm.is_processed || alarm.is_current)
                .map(alarm => alarm.id);
        }
    },
    watch: {
        // 监听告警列表变化，更新展开状态
        allAlarms: {
            handler(newAlarms) {
                // 找到当前处理的告警
                const currentAlarm = newAlarms.find(alarm => alarm.is_current);
                if (currentAlarm && !this.activeAlarms.includes(currentAlarm.id)) {
                    this.activeAlarms.push(currentAlarm.id);
                }
            },
            deep: true
        }
    },
    mounted() {
        this.initSocket();
    }
}); 