const app = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data: {
        socket: null,
        activeAlarms: [],
        allAlarms: [],
        notProcessedAlarms: [],
        reasoningText: '',
        processing: false,
        currentAlarmId: null,
        started: false,
        tempReasoningText: '', // 新增临时变量存储逐步更新的文本
        activeMenu: '1',  // 默认选中告警处理菜单
        isCollapse: false,  // 控制侧边栏展开/收起
        filterForm: {
            keyword: '',
            level: '',
            processStatus: '',
            convergenceStatus: '',
            timeRange: []
        },
        pickerOptions: {
            shortcuts: [{
                text: '最近一小时',
                onClick(picker) {
                    const end = new Date();
                    const start = new Date();
                    start.setTime(start.getTime() - 3600 * 1000);
                    picker.$emit('pick', [start, end]);
                }
            }, {
                text: '最近一天',
                onClick(picker) {
                    const end = new Date();
                    const start = new Date();
                    start.setTime(start.getTime() - 3600 * 1000 * 24);
                    picker.$emit('pick', [start, end]);
                }
            }]
        },
        expandedRows: [],  // 当前展开的行
        filteredData: [],  // 添加一个数组来存储筛选后的数据
        reasoningCards: [],  // 存储推理卡片
        currentAlarm: null,  // 当前处理的告警
        historyAlarms: [],   // 历史未收敛告警
        userInput: '',  // 用户输入的消息
    },
    methods: {
        // 其他代码不变
        initSocket() {
            console.log('Initializing socket connection...');
            this.socket = io();
            
            // 监听当前处理的告警
            this.socket.on('current_alarm', (alarm) => {
                console.log('Current alarm:', alarm);
                this.currentAlarm = alarm;
            });
            
            // 监听推理过程更新
            this.socket.on('reasoning_update', (data) => {
                console.log('Reasoning update:', data);
                if (data.content) {
                    this.reasoningText += data.content;
                    // 实时解析推理卡片
                    this.reasoningCards = this.parseReasoningText(this.reasoningText);
                }
            });
            
            // 监听初始状态
            this.socket.on('init_state', (data) => {
                console.log('Received init state:', data);
                this.allAlarms = data.all_alarms;
                this.notProcessedAlarms = data.not_processed_alarms;
            });
            // 监听推理完成
            this.socket.on('reasoning_complete', (data) => {
                console.log('推理完成:', data);
                this.processing = false;
                
                // 更新告警列表
                this.allAlarms = data.all_alarms;
                console.log('Updated alarms:', this.allAlarms);
                
                // 直接更新推理文本，移除打字机效果
                this.reasoningText = data.reasoning_text;
                this.reasoningCards = this.parseReasoningText(this.reasoningText);
                
                // 确保当前处理的告警保持展开
                const currentAlarm = this.allAlarms.find(alarm => alarm.is_current);
                if (currentAlarm && !this.expandedRows.includes(currentAlarm.id)) {
                    this.expandedRows = [currentAlarm.id];
                }
            });
            // 监听错误
            this.socket.on('reasoning_error', (data) => {
                console.error('Reasoning error:', data);
                this.processing = false;
                alert('处理过程中出现错误：' + data.error);
            });
        },
        
        getStatusType(row) {
            if (row.is_current) return 'primary';
            if (row.is_processed) return 'success';
            return 'info';
        },
        
        getStatusText(row) {
            if (row.is_current) return '处理中';
            if (row.is_processed) return '已处理';
            return '待处理';
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
        },
        
        getConvergenceType(type) {
            const typeMap = {
                '历史收敛': 'success',
                '未来收敛': 'warning',
                '实时收敛': 'primary',
                '默认': 'info'
            };
            return typeMap[type] || typeMap['默认'];
        },
        toggleCollapse() {
            this.isCollapse = !this.isCollapse;
        },
        handleMenuSelect(index) {
            this.activeMenu = index;
            // 在移动端自动收起侧边栏
            if (window.innerWidth < 768) {
                this.isCollapse = true;
            }
            // 这里可以添加路由跳转逻辑
        },
        handleFilter() {
            // 空实现，因为使用计算属性自动更新
            console.log('Filter applied:', this.filterForm);
        },
        
        handleExpandChange(row, expanded) {
            if (expanded) {
                this.expandedRows = [row.alarm_id];
            } else {
                this.expandedRows = [];
            }
        },
        
        getLevelType(level) {
            const typeMap = {
                '预警': 'info',
                '一般': 'success',
                '重要': 'warning',
                '紧急': 'danger'
            };
            return typeMap[level] || 'info';
        },
        
        refreshTable() {
            // 刷新表格数据
            this.initSocket();
        },
        
        exportTable() {
            // 导出表格数据
            // 这里可以实现导出逻辑
        },
        
        handleDetail(row) {
            // 处理查看详情
            // 可以打开详情弹窗等
        },
        
        formatDate(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        },
        
        showRecoveryInfo(row) {
            this.$alert(`恢复时间：${this.formatDate(row.recovery_time)}\n恢复原因：${row.recovery_reason || '未知'}`, '恢复信息', {
                confirmButtonText: '确定'
            });
        },

        getConvergenceTitle(conclusion) {
            if (!conclusion) return '待处理';
            switch (conclusion.convergence_type) {
                case '历史收敛':
                    return '已收敛';
                case '未来收敛':
                    return '预期收敛';
                default:
                    return '待收敛';
            }
        },

        getConvergenceTagType(type) {
            switch (type) {
                case '历史收敛':
                    return 'success';
                case '未来收敛':
                    return 'warning';
                default:
                    return 'info';
            }
        },

        getProcessStatusType(row) {
            if (row.is_processed) return 'success';
            return 'info';
        },
        
        getProcessStatusText(row) {
            if (row.is_processed) return '已处理';
            return '待处理';
        },
        
        parseReasoningText(text) {
            console.log('Parsing reasoning text:', text);
            const cards = [];
            let currentCard = null;
            
            // 分析文本，提取不同类型的内容
            const lines = text.split('\n');
            for (let line of lines) {
                // 匹配历史告警部分
                if (line.includes('历史未收敛告警：')) {
                    // 添加历史告警卡片
                    cards.push({
                        type: 'history',
                        content: line
                    });
                    continue;
                }
                
                // 匹配思考部分
                if (line.includes('<think>')) {
                    if (currentCard) {
                        cards.push(currentCard);
                    }
                    currentCard = { type: 'think', content: line.replace(/<\/?think>/g, '') };
                    continue;
                }
                
                // 匹配动作部分
                if (line.match(/^Action:/)) {
                    if (currentCard) {
                        cards.push(currentCard);
                    }
                    currentCard = { type: 'action', content: line.replace('Action:', '').trim() };
                    continue;
                }
                
                // 匹配结果部分
                if (line.match(/^Result:/)) {
                    if (currentCard) {
                        cards.push(currentCard);
                    }
                    currentCard = { type: 'result', content: line.replace('Result:', '').trim() };
                    continue;
                }
                
                // 匹配最终结论部分
                if (line.includes('<answer>')) {
                    if (currentCard) {
                        cards.push(currentCard);
                    }
                    currentCard = { type: 'conclusion', content: '' };
                    continue;
                }
                
                // 处理 JSON 结果
                if (currentCard && currentCard.type === 'conclusion' && line.includes('"convergence_type"')) {
                    try {
                        // 提取完整的 JSON 字符串
                        const jsonStart = text.indexOf('[', text.indexOf('<answer>'));
                        const jsonEnd = text.indexOf(']', jsonStart) + 1;
                        if (jsonStart !== -1 && jsonEnd !== -1) {
                            const jsonStr = text.substring(jsonStart, jsonEnd);
                            console.log('Extracted JSON:', jsonStr);
                            const conclusions = JSON.parse(jsonStr);
                            currentCard.content = conclusions;
                        }
                    } catch (e) {
                        console.error('Error parsing conclusion JSON:', e);
                        currentCard.content = line;
                    }
                    continue;
                }
                
                // 添加内容到当前卡片
                if (currentCard && currentCard.type !== 'conclusion') {
                    currentCard.content += line + '\n';
                }
            }
            
            // 添加最后一个卡片
            if (currentCard) {
                cards.push(currentCard);
            }
            
            console.log('Parsed cards:', cards);
            return cards;
        },
        
        parseHistoryAlarms(text) {
            // 解析历史未收敛告警
            const alarmPattern = /#(\d+):\s*(.+?)(?=\s*#|$)/g;
            const alarms = [];
            let match;
            
            while ((match = alarmPattern.exec(text)) !== null) {
                alarms.push({
                    id: match[1],
                    alarm_msg: match[2].trim()
                });
            }
            
            this.historyAlarms = alarms;
        },
        
        getCardIcon(type) {
            const icons = {
                'think': 'el-icon-chat-dot-square',
                'action': 'el-icon-coordinate',
                'result': 'el-icon-document-checked',
                'conclusion': 'el-icon-success',
                'user': 'el-icon-user',  // 添加用户消息的图标
                'assistant': 'el-icon-service'  // 添加助手消息的图标
            };
            return icons[type] || 'el-icon-info';
        },
        
        getCardTitle(type) {
            const titles = {
                'think': '推理思考',
                'action': '执行动作',
                'result': '执行结果',
                'conclusion': '最终结论',
                'user': '用户消息',  // 添加用户消息的标题
                'assistant': '助手回复'  // 添加助手消息的标题
            };
            return titles[type] || '未知类型';
        },
        
        formatContent(content) {
            // 如果是历史告警卡片
            if (content.includes('历史未收敛告警：')) {
                const alarms = content.replace('历史未收敛告警：', '').trim().split(' ');
                return `
                    <div class="history-alarms">
                        <el-timeline>
                            ${alarms.map(alarm => {
                                const [id, ...msg] = alarm.split(':');
                                return `
                                    <el-timeline-item type="warning">
                                        <div class="history-alarm-item">
                                            <span class="alarm-id">${id}</span>
                                            <div class="alarm-msg">${msg.join(':').trim()}</div>
                                        </div>
                                    </el-timeline-item>
                                `;
                            }).join('')}
                        </el-timeline>
                    </div>
                `;
            }
            
            // 如果是结论卡片且内容是对象
            if (Array.isArray(content)) {
                return content.map(item => {
                    return `
                        <div class="conclusion-item">
                            <div class="conclusion-header">
                                <el-tag size="small" type="${this.getConvergenceTagType(item.convergence_type)}">
                                    ${item.convergence_type}
                                </el-tag>
                                <el-tag size="small" type="info">
                                    ${item.related_alarm_id ? 
                                        `关联告警: #${item.related_alarm_id}` : 
                                        '无关联告警'}
                                </el-tag>
                            </div>
                            <el-descriptions :column="1" border size="small" class="conclusion-descriptions">
                                <el-descriptions-item label="推理过程">
                                    ${item.reasoning}
                                </el-descriptions-item>
                                <el-descriptions-item label="结论">
                                    <div class="highlight-conclusion">${item.conclusion}</div>
                                </el-descriptions-item>
                            </el-descriptions>
                        </div>
                    `;
                }).join('');
            }
            
            // 其他类型卡片保持原有格式化
            return content
                .replace(/\n/g, '<br>')
                .replace(/(#\d+)/g, '<span class="highlight-id">$1</span>')
                .replace(/(成功|失败)/g, '<span class="highlight-status">$1</span>');
        },
        
        sendMessage() {
            if (!this.userInput.trim() || this.processing) return;
            
            // 添加用户消息到推理卡片
            this.reasoningCards.push({
                type: 'user',  // 使用新的卡片类型
                content: this.userInput
            });
            
            // 发送消息到后端
            this.socket.emit('user_message', {
                message: this.userInput,
                current_alarm: this.currentAlarm
            });
            
            // 清空输入框
            this.userInput = '';
            
            // 滚动到底部
            this.$nextTick(() => {
                const container = document.querySelector('.reasoning-cards');
                container.scrollTop = container.scrollHeight;
            });
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
        },
        filteredAlarms() {
            return this.allAlarms.filter(alarm => {
                // 关键词筛选
                if (this.filterForm.keyword) {
                    const keyword = this.filterForm.keyword.toLowerCase();
                    if (!alarm.alarm_msg.toLowerCase().includes(keyword) && 
                        !alarm.id.toLowerCase().includes(keyword)) {
                        return false;
                    }
                }
                
                // 告警等级筛选
                if (this.filterForm.level && alarm.level !== this.filterForm.level) {
                    return false;
                }
                
                // 处理状态筛选
                if (this.filterForm.processStatus) {
                    switch (this.filterForm.processStatus) {
                        case 'pending':
                            if (alarm.is_processed || alarm.is_current) return false;
                            break;
                        case 'processing':
                            if (!alarm.is_current) return false;
                            break;
                        case 'processed':
                            if (!alarm.is_processed || alarm.is_current) return false;
                            break;
                    }
                }
                
                // 收敛状态筛选
                if (this.filterForm.convergenceStatus) {
                    if (this.filterForm.convergenceStatus === 'pending') {
                        if (alarm.conclusion && alarm.conclusion.length > 0) return false;
                    } else {
                        if (!alarm.conclusion || !alarm.conclusion.length || 
                            alarm.conclusion[0].convergence_type !== this.filterForm.convergenceStatus) {
                            return false;
                        }
                    }
                }
                
                return true;
            });
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
        },
        reasoningText: {
            handler(newText) {
                if (newText) {
                    this.reasoningCards = this.parseReasoningText(newText);
                } else {
                    this.reasoningCards = [];
                }
            },
            immediate: true
        }
    },
    mounted() {
        this.initSocket();
        
        // 监听推理过程更新
        this.socket.on('reasoning_update', (data) => {
            if (data.content) {
                this.tempReasoningText += data.content;
                this.reasoningText = this.tempReasoningText;
            }
        });
        
        // 监听窗口大小变化，在小屏幕下自动收起侧边栏
        window.addEventListener('resize', () => {
            if (window.innerWidth < 768) {
                this.isCollapse = true;
            }
        });
    }
}); 