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
            
            // 确保收敛类型存在
            const type = conclusion.convergence_type;
            if (!type || typeof type !== 'string') {
                return '待收敛';
            }
            
            // 标准化类型名称
            const normalizedType = type.trim();
            
            switch (normalizedType) {
                case '历史收敛': return '已收敛';
                case '未来收敛': return '预期收敛';
                case '实时收敛': return '实时收敛';
                case '未知': return '待收敛';
                default: return '待收敛';
            }
        },

        getConvergenceTagType(type) {
            // 确保类型存在且为字符串
            if (!type || typeof type !== 'string') {
                return 'info';
            }
            
            // 标准化类型名称，移除可能的空格
            const normalizedType = type.trim();
            
            switch (normalizedType) {
                case '历史收敛':
                    return 'success';
                case '未来收敛':
                    return 'warning';
                case '实时收敛':
                    return 'primary';
                case '未知':
                    return 'info';
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
            if (!text) return [];
            
            // 改进的解析逻辑
            const parts = [];
            let currentThink = '';
            let currentAction = '';
            let currentResult = '';
            let currentAnswer = '';
            
            // 状态跟踪
            let inThink = false;
            let inAction = false;
            let inResult = false;
            let inAnswer = false;
            
            // 按行处理文本
            const lines = text.split('\n');
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                
                // 处理思考开始标签
                if (line.includes('<think>')) {
                    inThink = true;
                    // 移除标签，保留内容
                    currentThink = line.replace('<think>', '') + '\n';
                }
                // 处理思考结束标签
                else if (line.includes('</think>')) {
                    inThink = false;
                    // 移除标签，保留内容
                    currentThink += line.replace('</think>', '') + '\n';
                    // 添加思考卡片
                    parts.push({
                        type: 'think',
                        content: currentThink.trim()
                    });
                    currentThink = '';
                }
                // 处理动作开始标签 - 只在思考内部有效
                else if (line.includes('<action>')) {
                    if (inThink) {
                        // 如果当前有思考内容，先保存思考卡片
                        if (currentThink.trim()) {
                            parts.push({
                                type: 'think',
                                content: currentThink.trim()
                            });
                            currentThink = '';
                        }
                        
                        inAction = true;
                        currentAction = line + '\n';
                    } else if (inAnswer) {
                        // 在答案中的动作标签应被忽略，作为普通文本处理
                        currentAnswer += line + '\n';
                    }
                }
                // 处理动作结束标签
                else if (line.includes('</action>')) {
                    if (inThink && inAction) {
                        inAction = false;
                        currentAction += line + '\n';
                        // 添加动作卡片
                        parts.push({
                            type: 'action',
                            content: currentAction.trim()
                        });
                        currentAction = '';
                    } else if (inAnswer) {
                        // 在答案中的动作标签应被忽略，作为普通文本处理
                        currentAnswer += line + '\n';
                    }
                }
                // 处理结果开始标签 - 只在思考内部有效
                else if (line.includes('<result>')) {
                    if (inThink) {
                        inResult = true;
                        currentResult = line + '\n';
                    } else if (inAnswer) {
                        // 在答案中的结果标签应被忽略，作为普通文本处理
                        currentAnswer += line + '\n';
                    }
                }
                // 处理结果结束标签
                else if (line.includes('</result>')) {
                    if (inThink && inResult) {
                        inResult = false;
                        currentResult += line + '\n';
                        // 添加结果卡片
                        parts.push({
                            type: 'result',
                            content: currentResult.trim()
                        });
                        currentResult = '';
                    } else if (inAnswer) {
                        // 在答案中的结果标签应被忽略，作为普通文本处理
                        currentAnswer += line + '\n';
                    }
                }
                // 处理答案开始标签
                else if (line.includes('<answer>')) {
                    inAnswer = true;
                    // 如果当前有思考内容，先保存思考卡片
                    if (currentThink.trim()) {
                        parts.push({
                            type: 'think',
                            content: currentThink.trim()
                        });
                        currentThink = '';
                    }
                    currentAnswer = line.replace('<answer>', '') + '\n';
                }
                // 处理答案结束标签
                else if (line.includes('</answer>')) {
                    inAnswer = false;
                    currentAnswer += line.replace('</answer>', '') + '\n';
                    // 添加答案卡片
                    parts.push({
                        type: 'conclusion',
                        content: currentAnswer.trim()
                    });
                    currentAnswer = '';
                }
                // 处理普通内容
                else {
                    if (inThink && !inAction && !inResult) {
                        currentThink += line + '\n';
                    } else if (inAction) {
                        currentAction += line + '\n';
                    } else if (inResult) {
                        currentResult += line + '\n';
                    } else if (inAnswer) {
                        currentAnswer += line + '\n';
                    }
                }
            }
            
            // 处理可能的未闭合标签
            if (currentThink.trim()) {
                parts.push({
                    type: 'think',
                    content: currentThink.trim()
                });
            }
            if (currentAction.trim()) {
                parts.push({
                    type: 'action',
                    content: currentAction.trim()
                });
            }
            if (currentResult.trim()) {
                parts.push({
                    type: 'result',
                    content: currentResult.trim()
                });
            }
            if (currentAnswer.trim()) {
                parts.push({
                    type: 'conclusion',
                    content: currentAnswer.trim()
                });
            }
            
            return parts;
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
            const iconMap = {
                'think': 'el-icon-loading',
                'action': 'el-icon-connection',
                'result': 'el-icon-data-analysis',
                'conclusion': 'el-icon-check',
                'info': 'el-icon-info',
                'success': 'el-icon-success',
                'warning': 'el-icon-warning',
                'error': 'el-icon-error'
            };
            return iconMap[type] || 'el-icon-info';
        },
        
        getCardTitle(type) {
            const titleMap = {
                'think': '推理思考',
                'action': '执行动作',
                'result': '执行结果',
                'conclusion': '最终结论',
                'info': '信息',
                'success': '成功',
                'warning': '警告',
                'error': '错误'
            };
            return titleMap[type] || '信息';
        },
        
        formatContent(content) {
            if (!content) return '';
            
            // 移除标签
            let formatted = content
                .replace(/<\/?think>/g, '')
                .replace(/<\/?action>/g, '')
                .replace(/<\/?result>/g, '')
                .replace(/<\/?answer>/g, '');
            
            // 格式化JSON
            if (formatted.includes('{') && formatted.includes('}')) {
                try {
                    // 尝试查找并格式化JSON部分
                    const jsonRegex = /{[\s\S]*?}/g;
                    const matches = formatted.match(jsonRegex);
                    
                    if (matches) {
                        for (const match of matches) {
                            try {
                                const parsed = JSON.parse(match);
                                const formatted = JSON.stringify(parsed, null, 2);
                                content = content.replace(match, '<pre class="json-code">' + formatted + '</pre>');
                            } catch (e) {
                                // 如果解析失败，保持原样
                            }
                        }
                    }
                } catch (e) {
                    // 解析失败，保持原样
                }
            }
            
            // 高亮API调用
            formatted = formatted.replace(/GraphAPI\.query\("([^"]*)"\)/g, 
                '<span class="api-call">GraphAPI.query</span>("<span class="api-param">$1</span>")');
            formatted = formatted.replace(/DeviceAPI\.query\("([^"]*)"\)/g, 
                '<span class="api-call">DeviceAPI.query</span>("<span class="api-param">$1</span>")');
            formatted = formatted.replace(/BARuleAPI\.query\("([^"]*)"\)/g, 
                '<span class="api-call">BARuleAPI.query</span>("<span class="api-param">$1</span>")');
            
            // 转换换行符为HTML换行
            formatted = formatted.replace(/\n/g, '<br>');
            
            return formatted;
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
        },

        debugConvergenceInfo(row) {
            if (row && row.conclusion && row.conclusion.length > 0) {
                console.log('收敛信息:', {
                    id: row.id,
                    hasConclusion: !!row.conclusion,
                    conclusionLength: row.conclusion.length,
                    firstConclusion: row.conclusion[0],
                    convergenceType: row.conclusion[0].convergence_type
                });
            } else {
                console.log('无收敛信息:', row);
            }
            return '';
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