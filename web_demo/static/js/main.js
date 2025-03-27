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
        tempReasoningText: '',
        activeMenu: '1',
        isCollapse: false,
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
        expandedRows: [],
        filteredData: [],
        reasoningCards: [],
        currentAlarm: null,
        historyAlarms: [],
        userInput: '',
    },
    methods: {
        initSocket() {
            console.log('Initializing socket connection...');
            this.socket = io();
            
            this.socket.on('current_alarm', (alarm) => {
                console.log('Current alarm:', alarm);
                this.currentAlarm = alarm;
            });
            
            this.socket.on('reasoning_update', (data) => {
                console.log('Reasoning update:', data);
                if (data.content) {
                    this.reasoningText += data.content;
                    this.reasoningCards = this.parseReasoningText(this.reasoningText);
                }
            });
            
            this.socket.on('init_state', (data) => {
                console.log('Received init state:', data);
                this.allAlarms = data.all_alarms;
                this.notProcessedAlarms = data.not_processed_alarms;
            });

            this.socket.on('reasoning_complete', (data) => {
                console.log('推理完成:', data);
                this.processing = false;
                this.allAlarms = data.all_alarms;
                console.log('Updated alarms:', this.allAlarms);
                this.reasoningText = data.reasoning_text;
                this.reasoningCards = this.parseReasoningText(this.reasoningText);
                
                const currentAlarm = this.allAlarms.find(alarm => alarm.is_current);
                if (currentAlarm && !this.expandedRows.includes(currentAlarm.id)) {
                    this.expandedRows = [currentAlarm.id];
                }
            });

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
            if (window.innerWidth < 768) {
                this.isCollapse = true;
            }
        },

        handleFilter() {
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
            this.initSocket();
        },
        
        exportTable() {
            // 导出逻辑
        },
        
        handleDetail(row) {
            // 详情处理
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
                case '历史收敛': return '已收敛';
                case '未来收敛': return '预期收敛';
                default: return '待收敛';
            }
        },

        getConvergenceTagType(type) {
            switch (type) {
                case '历史收敛': return 'success';
                case '未来收敛': return 'warning';
                default: return 'info';
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
            
            const lines = text.split('\n');
            for (let line of lines) {
                if (line.includes('历史未收敛告警：')) {
                    cards.push({
                        type: 'history',
                        content: line
                    });
                    continue;
                }
                
                if (line.includes('<think>')) {
                    if (currentCard) cards.push(currentCard);
                    currentCard = { type: 'think', content: line.replace(/<\/?think>/g, '') };
                    continue;
                }
                
                if (line.match(/^Action:/)) {
                    if (currentCard) cards.push(currentCard);
                    currentCard = { type: 'action', content: line.replace('Action:', '').trim() };
                    continue;
                }
                
                if (line.match(/^Result:/)) {
                    if (currentCard) cards.push(currentCard);
                    currentCard = { type: 'result', content: line.replace('Result:', '').trim() };
                    continue;
                }
                
                if (line.includes('<answer>')) {
                    if (currentCard) cards.push(currentCard);
                    currentCard = { type: 'conclusion', content: '' };
                    continue;
                }
                
                if (currentCard && currentCard.type === 'conclusion' && line.includes('"convergence_type"')) {
                    try {
                        const jsonStart = text.indexOf('[', text.indexOf('<answer>'));
                        const jsonEnd = text.indexOf(']', jsonStart) + 1;
                        if (jsonStart !== -1 && jsonEnd !== -1) {
                            const jsonStr = text.substring(jsonStart, jsonEnd);
                            console.log('Extracted JSON:', jsonStr);
                            currentCard.content = JSON.parse(jsonStr);
                        }
                    } catch (e) {
                        console.error('Error parsing conclusion JSON:', e);
                        currentCard.content = line;
                    }
                    continue;
                }
                
                if (currentCard && currentCard.type !== 'conclusion') {
                    currentCard.content += line + '\n';
                }
            }
            
            if (currentCard) cards.push(currentCard);
            
            console.log('Parsed cards:', cards);
            return cards;
        },
        
        parseHistoryAlarms(text) {
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
                'user': 'el-icon-user',
                'assistant': 'el-icon-service'
            };
            return icons[type] || 'el-icon-info';
        },
        
        getCardTitle(type) {
            const titles = {
                'think': '推理思考',
                'action': '执行动作',
                'result': '执行结果',
                'conclusion': '最终结论',
                'user': '用户消息',
                'assistant': '助手回复'
            };
            return titles[type] || '未知类型';
        },
        
        formatContent(content) {
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
            
            if (Array.isArray(content)) {
                return content.map(item => {
                    // 收敛关系标记
                    const convergenceMark = item.convergence_type === '历史收敛' && item.converged_alarm_id 
                        ? `<el-tag size="mini" type="danger" class="converge-mark" effect="dark">
                            <i class="el-icon-connection"></i> 收敛自 #${item.converged_alarm_id}
                           </el-tag>`
                        : '';
                    
                    // 关联告警标记
                    const relatedAlarmMark = item.related_alarm_id 
                        ? `<el-tag size="mini" type="info" class="related-mark">
                            <i class="el-icon-link"></i> 关联告警 #${item.related_alarm_id}
                           </el-tag>`
                        : '';
                    
                    // 收敛目标标记
                    const convergingMark = item.converging_alarm_id 
                        ? `<el-tag size="mini" type="success" class="converging-mark">
                            <i class="el-icon-arrow-right"></i> 收敛至 #${item.converging_alarm_id}
                           </el-tag>`
                        : '';
                    
                    return `
                        <div class="conclusion-item">
                            <div class="conclusion-header">
                                <el-tag size="small" type="${this.getConvergenceTagType(item.convergence_type)}">
                                    <i class="el-icon-${item.convergence_type === '历史收敛' ? 'success' : 'info'}"></i>
                                    ${item.convergence_type}
                                </el-tag>
                                ${convergenceMark}
                                ${relatedAlarmMark}
                                ${convergingMark}
                            </div>
                            <el-descriptions :column="1" border size="small" class="conclusion-descriptions">
                                <el-descriptions-item label="推理过程" class="reasoning-process">
                                    <div class="reasoning-text">${item.reasoning}</div>
                                </el-descriptions-item>
                                <el-descriptions-item label="最终结论">
                                    <div class="highlight-conclusion">
                                        <i class="el-icon-finished"></i> ${item.conclusion}
                                    </div>
                                </el-descriptions-item>
                            </el-descriptions>
                        </div>
                    `;
                }).join('');
            }
            
            return content
                .replace(/\n/g, '<br>')
                .replace(/(#\d+)/g, '<span class="highlight-id">$1</span>')
                .replace(/(成功|失败)/g, '<span class="highlight-status">$1</span>');
        },
        
        sendMessage() {
            if (!this.userInput.trim() || this.processing) return;
            
            this.reasoningCards.push({
                type: 'user',
                content: this.userInput
            });
            
            this.socket.emit('user_message', {
                message: this.userInput,
                current_alarm: this.currentAlarm
            });
            
            this.userInput = '';
            
            this.$nextTick(() => {
                const container = document.querySelector('.reasoning-cards');
                container.scrollTop = container.scrollHeight;
            });
        }
    },
    computed: {
        buttonText() {
            if (!this.started) return '开始处理告警';
            return this.processing ? '处理中...' : '处理下一条告警';
        },
        allAlarmIds() {
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
            return this.allAlarms
                .filter(alarm => alarm.is_processed || alarm.is_current)
                .map(alarm => alarm.id);
        },
        filteredAlarms() {
            return this.allAlarms.filter(alarm => {
                if (this.filterForm.keyword) {
                    const keyword = this.filterForm.keyword.toLowerCase();
                    if (!alarm.alarm_msg.toLowerCase().includes(keyword) && 
                        !alarm.id.toLowerCase().includes(keyword)) {
                        return false;
                    }
                }
                
                if (this.filterForm.level && alarm.level !== this.filterForm.level) {
                    return false;
                }
                
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
        allAlarms: {
            handler(newAlarms) {
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
        
        // 添加收敛关系样式
        const style = document.createElement('style');
        style.textContent = `
            .converge-mark {
                margin-left: 8px;
                animation: pulse 1.5s infinite;
                border-color: #f56c6c;
            }
            .related-mark {
                margin-left: 8px;
            }
            .converging-mark {
                margin-left: 8px;
            }
            @keyframes pulse {
                0% { opacity: 0.7; box-shadow: 0 0 3px rgba(245,108,108,0.3); }
                50% { opacity: 1; box-shadow: 0 0 8px rgba(245,108,108,0.6); }
                100% { opacity: 0.7; box-shadow: 0 0 3px rgba(245,108,108,0.3); }
            }
            .conclusion-header {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                align-items: center;
                margin-bottom: 10px;
            }
            .highlight-id {
                color: #409EFF;
                font-weight: bold;
            }
            .highlight-conclusion {
                color: #67C23A;
                font-weight: 500;
            }
            .reasoning-text {
                white-space: pre-wrap;
                line-height: 1.6;
            }
            .conclusion-item {
                margin-bottom: 16px;
                padding: 12px;
                background: #f8fafc;
                border-radius: 4px;
                border-left: 3px solid #409EFF;
            }
        `;
        document.head.appendChild(style);

        this.socket.on('reasoning_update', (data) => {
            if (data.content) {
                this.tempReasoningText += data.content;
                this.reasoningText = this.tempReasoningText;
            }
        });
        
        window.addEventListener('resize', () => {
            if (window.innerWidth < 768) {
                this.isCollapse = true;
            }
        });
    }
});