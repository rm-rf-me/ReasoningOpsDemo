new Vue({
    el: '#app',
    data: {
        resultData: window.serverResultData || null,
        engineerName: '',
        expandedPrompts: {},
        expandedJsonResults: {},
        newComments: {},
        configDialogVisible: false,
        // 导入对话框相关
        importDialogVisible: false,
        selectedFile: null,
        fileList: [],
        // 侧边栏相关
        isCollapse: false,
        activeMenu: '5',
        // 事件和告警展开状态
        expandedEvents: [],
        expandedAlarms: {},
        allEventsExpanded: false
    },
    methods: {
        // 确认工程师姓名
        confirmEngineerName() {
            if (!this.engineerName.trim()) {
                this.$message.warning('请输入工程师姓名');
                return;
            }
            
            this.$message.success(`工程师姓名已设置为：${this.engineerName}`);
        },
        
        // 侧边栏相关方法
        toggleCollapse() {
            this.isCollapse = !this.isCollapse;
        },
        handleMenuSelect(index) {
            this.activeMenu = index;
            // 根据菜单项跳转到不同页面
            switch(index) {
                case '1':
                    window.location.href = '/';
                    break;
                case '2':
                    // 管理拓扑页面
                    break;
                case '3':
                    // 管理设备API页面
                    break;
                case '4':
                    // 管理BA规则页面
                    break;
                case '5':
                    // 当前页面
                    break;
            }
        },
        
        // 导入对话框相关方法
        showImportDialog() {
            this.importDialogVisible = true;
            this.selectedFile = null;
            this.fileList = [];
        },
        
        handleFileChange(file) {
            this.selectedFile = file;
            this.fileList = [file];
        },
        
        handleFileRemove() {
            this.selectedFile = null;
            this.fileList = [];
        },
        
        confirmImport() {
            if (!this.selectedFile) {
                this.$message.warning('请先选择文件');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    // 验证数据格式
                    if (this.validateDataFormat(data)) {
                        this.resultData = data;
                        this.importDialogVisible = false;
                        this.$message.success('文件导入成功');
                    } else {
                        this.$message.error('文件格式不正确，请检查数据结构');
                    }
                } catch (error) {
                    this.$message.error('文件解析失败：' + error.message);
                }
            };
            reader.readAsText(this.selectedFile.raw);
        },
        
        validateDataFormat(data) {
            // 简单的数据格式验证
            return data && 
                   typeof data === 'object' &&
                   data.meta_data && 
                   typeof data.meta_data === 'object' &&
                   data.summary && 
                   typeof data.summary === 'object' &&
                   data.events && 
                   Array.isArray(data.events);
        },
        
        // 获取所有告警信息
        getAllAlarms() {
            if (!this.resultData || !this.resultData.events) {
                return [];
            }
            
            const allAlarms = [];
            this.resultData.events.forEach(event => {
                if (event.alarms && Array.isArray(event.alarms)) {
                    allAlarms.push(...event.alarms);
                }
            });
            return allAlarms;
        },
        
        // 配置显示
        showConfig() {
            if (this.resultData && this.resultData.meta_data.config) {
                const config = this.resultData.meta_data.config;
                let configText = '';
                
                // 格式化配置信息
                if (typeof config === 'object' && config !== null) {
                    configText = JSON.stringify(config, null, 2);
                } else {
                    configText = String(config);
                }
                
                this.$alert(configText, '配置信息', {
                    confirmButtonText: '确定',
                    customClass: 'config-dialog',
                    dangerouslyUseHTMLString: false
                });
            } else {
                this.$message.info('暂无配置信息');
            }
        },
        
        // 批次处理
        getBatches(alarms) {
            const batches = {};
            alarms.forEach(alarm => {
                const batchIds = alarm.output.batch_alarm_ids || [alarm.alarm_id];
                const batchKey = batchIds.sort().join(',');
                if (!batches[batchKey]) {
                    batches[batchKey] = {
                        batchIds: batchIds,
                        alarms: []
                    };
                }
                batches[batchKey].alarms.push(alarm);
            });
            return Object.values(batches);
        },
        
        // 推理过程格式化
        formatThinking(thinking) {
            if (!thinking) return '';
            return thinking.replace(/\n/g, '<br>');
        },
        
        // 系统提示词格式化
        formatSystemPrompt(prompt) {
            if (!prompt) return '';
            return prompt.replace(/\n/g, '<br>');
        },
        
        // 准确率格式化
        formatAccuracy(accuracy) {
            if (typeof accuracy === 'string') {
                // 如果是字符串格式（如"85.90%"），直接返回
                return accuracy;
            } else if (typeof accuracy === 'number') {
                // 如果是数字格式，转换为百分比字符串
                return (accuracy * 100).toFixed(2) + '%';
            }
            return '0.00%';
        },
        
        // 获取准确率等级
        getAccuracyLevel(accuracy) {
            if (accuracy === null || accuracy === undefined) {
                return 'low';
            }
            
            let value;
            if (typeof accuracy === 'string') {
                value = parseFloat(accuracy.replace('%', ''));
            } else if (typeof accuracy === 'number') {
                value = accuracy * 100;
            } else {
                return 'low';
            }
            
            if (value >= 80) return 'high';
            if (value >= 60) return 'medium';
            return 'low';
        },
        
        // API调用检测
        hasApiCalls(res) {
            return res && (res.includes('API') || res.includes('api') || res.includes('调用'));
        },
        
        extractApiCalls(res) {
            if (!this.hasApiCalls(res)) return [];
            // 简单的API调用提取逻辑
            const lines = res.split('\n');
            return lines.filter(line => 
                line.includes('API') || line.includes('api') || line.includes('调用')
            );
        },
        
        // 正确性判断
        getCorrectTagType(alarm) {
            const predicted = alarm.output.model_answer_id;
            const actual = alarm.input.label;
            return predicted === actual ? 'success' : 'danger';
        },
        
        getCorrectText(alarm) {
            const predicted = alarm.output.model_answer_id;
            const actual = alarm.input.label;
            return predicted === actual ? '正确' : '错误';
        },
        
        // 提示词展开/收起
        togglePrompt(alarmId) {
            this.$set(this.expandedPrompts, alarmId, !this.expandedPrompts[alarmId]);
        },
        
        // JSON结果展开/收起
        toggleJsonResult(alarmId) {
            this.$set(this.expandedJsonResults, alarmId, !this.expandedJsonResults[alarmId]);
        },
        
        // 评论功能
        addComment(alarmId) {
            if (!this.engineerName.trim()) {
                this.$message.warning('请先输入工程师姓名');
                return;
            }
            
            if (!this.newComments[alarmId] || !this.newComments[alarmId].trim()) {
                this.$message.warning('请输入评论内容');
                return;
            }
            
            // 找到对应的告警并添加评论
            this.resultData.events.forEach(event => {
                event.alarms.forEach(alarm => {
                    if (alarm.alarm_id === alarmId) {
                        if (!alarm.comments) {
                            this.$set(alarm, 'comments', []);
                        }
                        alarm.comments.push({
                            engineer: this.engineerName,
                            timestamp: new Date().toLocaleString(),
                            content: this.newComments[alarmId]
                        });
                        this.newComments[alarmId] = '';
                    }
                });
            });
            
            this.$message.success('评论添加成功');
        },
        
        deleteComment(alarmId, commentIndex) {
            this.$confirm('确定要删除这条评论吗？', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                this.resultData.events.forEach(event => {
                    event.alarms.forEach(alarm => {
                        if (alarm.alarm_id === alarmId && alarm.comments) {
                            alarm.comments.splice(commentIndex, 1);
                        }
                    });
                });
                this.$message.success('评论删除成功');
            }).catch(() => {
                // 用户取消删除
            });
        },
        
        // 事件和告警展开/收起功能
        toggleEvent(eventIndex) {
            const index = this.expandedEvents.indexOf(eventIndex);
            if (index > -1) {
                this.expandedEvents.splice(index, 1);
                // 收起事件时，同时收起该事件下的所有告警
                this.$set(this.expandedAlarms, eventIndex, []);
            } else {
                this.expandedEvents.push(eventIndex);
                // 展开事件时，初始化该事件的告警展开状态
                if (!this.expandedAlarms[eventIndex]) {
                    this.$set(this.expandedAlarms, eventIndex, []);
                }
            }
        },
        
        toggleAlarm(eventIndex, alarmIndex) {
            if (!this.expandedAlarms[eventIndex]) {
                this.$set(this.expandedAlarms, eventIndex, []);
            }
            
            const index = this.expandedAlarms[eventIndex].indexOf(alarmIndex);
            if (index > -1) {
                this.expandedAlarms[eventIndex].splice(index, 1);
            } else {
                this.expandedAlarms[eventIndex].push(alarmIndex);
            }
        },
        
        expandAllEvents() {
            if (this.allEventsExpanded) {
                // 全部收起
                this.expandedEvents = [];
                this.expandedAlarms = {};
                this.allEventsExpanded = false;
            } else {
                // 全部展开
                this.expandedEvents = this.resultData.events.map((_, index) => index);
                this.resultData.events.forEach((event, eventIndex) => {
                    this.$set(this.expandedAlarms, eventIndex, event.alarms.map((_, alarmIndex) => alarmIndex));
                });
                this.allEventsExpanded = true;
            }
        },
        
        // 获取事件准确率
        getEventAccuracy(event) {
            if (!event.alarms || event.alarms.length === 0) return 0;
            
            const correctCount = event.alarms.filter(alarm => {
                const predicted = alarm.output.model_answer_id;
                const actual = alarm.input.label;
                return predicted === actual;
            }).length;
            
            return Math.round((correctCount / event.alarms.length) * 100);
        },
        
        // 获取事件准确率标签类型
        getEventAccuracyType(event) {
            const accuracy = this.getEventAccuracy(event);
            if (accuracy >= 80) return 'success';
            if (accuracy >= 60) return 'warning';
            return 'danger';
        },
        
        // 导出功能
        exportResults() {
            if (!this.engineerName.trim()) {
                this.$message.warning('请先输入工程师姓名');
                return;
            }
            
            // 创建导出数据
            const exportData = {
                ...this.resultData,
                export_info: {
                    engineer: this.engineerName,
                    export_time: new Date().toISOString(),
                    export_timestamp: new Date().toLocaleString()
                }
            };
            
            // 创建下载链接
            const dataStr = JSON.stringify(exportData, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `推理结果_${this.engineerName}_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            this.$message.success('导出成功');
        }
    },
    
    mounted() {
        // 如果有服务器数据，自动填充一些默认值
        if (this.resultData) {
            console.log('加载服务器数据:', this.resultData);
        }
    }
});
