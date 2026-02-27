/**
 * DocsPort Main JavaScript
 * Handles all client-side functionality for the DocsPort application
 */

class DocsPort {
    constructor() {
        this.apiBase = '';
        this.monacoEditor = null;
        this.executionMonaco = null;
        this.currentFile = null;
        this.analysisData = null;
        this.comments = [];
        this.executionHistory = [];
        this.currentTab = 'editor';
        this.codeStructure = null;
        this.d3Visualization = null;
        this._dirty = false;

        // Initialize mermaid for flowcharts
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        });
    }

    /**
     * Initialize the DocsPort application
     */
    init() {
        console.log('DocsPort initializing...');

        // Initialize Monaco editors
        this.initCodeEditor();
        this.initExecutionEditor();

        // Load initial data
        this.loadFiles();
        this.loadComments();

        // Setup event listeners
        this.setupEventListeners();

        // Check health
        this.checkHealth();

        console.log('DocsPort initialized successfully');
    }

    /**
     * Initialize the main code editor with Monaco
     */
    initCodeEditor() {
        require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.44.0/min/vs' } });

        require(['vs/editor/editor.main'], () => {
            this.monacoEditor = monaco.editor.create(document.getElementById('monaco-editor'), {
                value: '# Select a file or start typing...',
                language: 'python',
                theme: 'vs-dark',
                automaticLayout: true,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                fontSize: 14,
                lineNumbers: 'on',
                renderWhitespace: 'selection',
                wordWrap: 'on',
                quickSuggestions: true,
                parameterHints: { enabled: true },
                suggestOnTriggerCharacters: true,
                acceptSuggestionOnCommitCharacter: true,
                tabCompletion: 'on',
                folding: true,
                foldingStrategy: 'indentation',
                showFoldingControls: 'always'
            });

            // Add keyboard shortcuts
            this.monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KEY_S, () => {
                this.saveFile();
            });

            this.monacoEditor.addCommand(monaco.KeyCode.F5, () => {
                this.executeSelectedCode();
            });

            this.monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.US_SLASH, () => {
                this.toggleComment();
            });

            this.monacoEditor.onDidChangeModelContent(() => {
                this.onCodeChange();
            });

            this.monacoEditor.onDidChangeCursorPosition(() => {
                this.onCursorActivity();
            });

            this.monacoEditor.addAction({
                id: 'add-comment',
                label: 'Add Comment',
                contextMenuGroupId: 'navigation',
                run: () => {
                    this.addCommentAtCursor();
                }
            });
        });
    }

    /**
     * Initialize the execution editor with Monaco
     */
    initExecutionEditor() {
        require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.44.0/min/vs' } });

        require(['vs/editor/editor.main'], () => {
            this.executionMonaco = monaco.editor.create(document.getElementById('execution-monaco'), {
                value: '# Enter Python code to execute...',
                language: 'python',
                theme: 'vs-dark',
                automaticLayout: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                lineNumbers: 'on',
                wordWrap: 'on',
                quickSuggestions: true
            });

            this.executionMonaco.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
                this.executeCode();
            });
        });
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        document.getElementById('comment-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitComment();
        });

        document.getElementById('comment-modal').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.closeCommentModal();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                if (this.currentTab === 'execution') {
                    this.executeCode();
                }
            }
        });
    }

    /**
     * API request helper
     */
    async apiRequest(endpoint, options = {}) {
        const url = this.apiBase + endpoint;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };

        try {
            this.showLoading();
            const response = await fetch(url, config);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('API Request Error:', error);
            this.showError(i18n.t('messages.api_error') + error.message);
            throw error;
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Check application health
     */
    async checkHealth() {
        try {
            const health = await this.apiRequest('/api/health');
            this.updateStatusIndicator(true);
            console.log('DocsPort Health:', health);
        } catch (error) {
            this.updateStatusIndicator(false);
            console.error('Health Check Failed:', error);
        }
    }

    /**
     * Update status indicator
     */
    updateStatusIndicator(isHealthy) {
        const indicator = document.getElementById('status-indicator');
        if (!indicator) return;

        if (isHealthy) {
            indicator.innerHTML = `<i class="fas fa-circle" style="color: var(--success-color)"></i> ${i18n.t('app.status.connected')}`;
        } else {
            indicator.innerHTML = `<i class="fas fa-circle" style="color: var(--danger-color)"></i> ${i18n.t('app.status.disconnected')}`;
        }
    }

    showLoading() {
        const loading = document.getElementById('loading');
        if (loading) loading.classList.add('active');
    }

    hideLoading() {
        const loading = document.getElementById('loading');
        if (loading) loading.classList.remove('active');
    }

    showError(message) {
        this._showToast(i18n.t('messages.error_prefix') + message, 'error');
    }

    showSuccess(message) {
        this._showToast(message, 'success');
    }

    _showToast(message, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.addEventListener('click', () => toast.remove());
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('toast-fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    /**
     * Tab management
     */
    showTab(tabName) {
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');

        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        if (tabName === 'editor' && this.monacoEditor) {
            setTimeout(() => this.monacoEditor.layout(), 100);
        }
        if (tabName === 'execution' && this.executionMonaco) {
            setTimeout(() => this.executionMonaco.layout(), 100);
        }
    }

    /**
     * File management
     */
    async loadFiles() {
        try {
            const response = await this.apiRequest('/api/files');
            this.populateFileSelector(response.files);
        } catch (error) {
            console.error('Error loading files:', error);
        }
    }

    populateFileSelector(files) {
        const fileSelect = document.getElementById('file-select');
        const commentFileFilter = document.getElementById('comment-file-filter');

        if (!fileSelect) return;

        fileSelect.innerHTML = `<option value="">${i18n.t('editor.select_file')}</option>`;
        if (commentFileFilter) {
            commentFileFilter.innerHTML = `<option value="">${i18n.t('comments_tab.all_files')}</option>`;
        }

        files.forEach(file => {
            const option = document.createElement('option');
            option.value = file.path;
            option.textContent = file.path;
            fileSelect.appendChild(option);

            if (commentFileFilter) {
                const commentOption = option.cloneNode(true);
                commentFileFilter.appendChild(commentOption);
            }
        });
    }

    async loadFile() {
        const fileSelect = document.getElementById('file-select');
        const filePath = fileSelect.value;

        if (!filePath) {
            this.clearEditor();
            return;
        }

        try {
            const response = await this.apiRequest(`/api/files/${filePath}`);
            this.currentFile = filePath;

            if (this.monacoEditor) {
                this.monacoEditor.setValue(response.content);
            }

            this._dirty = false;
            this.updateFileInfo(response);
            this.loadFileComments(filePath);

        } catch (error) {
            console.error('Error loading file:', error);
            this.showError(i18n.t('messages.file_not_loaded'));
        }
    }

    async refreshFileList() {
        await this.loadFiles();
    }

    clearEditor() {
        if (this.monacoEditor) {
            this.monacoEditor.setValue('');
        }
        this.currentFile = null;
        this.updateFileInfo(null);
        this.clearFileComments();
    }

    updateFileInfo(fileData) {
        const fileInfo = document.getElementById('file-info');
        if (!fileInfo) return;

        if (!fileData) {
            fileInfo.innerHTML = `<p>${i18n.t('editor.no_file_selected')}</p>`;
            return;
        }

        fileInfo.innerHTML = `
            <div class="file-details">
                <p><strong>${i18n.t('editor.file')}:</strong> ${fileData.path}</p>
                <p><strong>${i18n.t('editor.size')}:</strong> ${fileData.size} Bytes</p>
                <p><strong>${i18n.t('editor.lines')}:</strong> ${fileData.lines}</p>
            </div>
        `;
    }

    async saveFile() {
        if (!this.currentFile || !this.monacoEditor) {
            this.showError(i18n.t('messages.no_file_to_save'));
            return;
        }

        try {
            const content = this.monacoEditor.getValue();
            const formData = new FormData();
            formData.append('content', content);

            const response = await fetch(`/api/files/${this.currentFile}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Save failed');
            }

            this._clearDirty();
            this.showSuccess(i18n.t('messages.file_saved'));

        } catch (error) {
            console.error('Error saving file:', error);
            this.showError(i18n.t('messages.file_not_saved'));
        }
    }

    onCodeChange() {
        if (this.currentFile && !this._dirty) {
            this._dirty = true;
            const fileSelect = document.getElementById('file-select');
            if (fileSelect && fileSelect.selectedIndex > 0) {
                const opt = fileSelect.options[fileSelect.selectedIndex];
                if (!opt.textContent.startsWith('● ')) {
                    opt.textContent = '● ' + opt.textContent;
                }
            }
        }
    }

    _clearDirty() {
        this._dirty = false;
        const fileSelect = document.getElementById('file-select');
        if (fileSelect && fileSelect.selectedIndex > 0) {
            const opt = fileSelect.options[fileSelect.selectedIndex];
            opt.textContent = opt.textContent.replace(/^● /, '');
        }
    }

    onCursorActivity() {
        if (this.monacoEditor) {
            const position = this.monacoEditor.getPosition();
        }
    }

    /**
     * Code analysis
     */
    async analyzeCurrentFile() {
        if (!this.currentFile) {
            this.showError(i18n.t('messages.no_file_to_analyze'));
            return;
        }

        try {
            const response = await this.apiRequest('/api/analyze', {
                method: 'POST',
                body: JSON.stringify({
                    file_path: this.currentFile,
                    force_refresh: true
                })
            });

            console.log('Analysis result:', response);
            this.showSuccess(i18n.t('messages.file_analyzed'));

            this.showTab('analysis');
            this.displayAnalysisResults([response]);
            this.updateDropdownMenus([response]);
            await this.getVisualAnalysis();

        } catch (error) {
            console.error('Error analyzing file:', error);
            this.showError(i18n.t('messages.analysis_failed'));
        }
    }

    async analyzeProject() {
        try {
            const response = await this.apiRequest('/api/analyze/project');
            this.analysisData = response;

            this.updateAnalysisStats(response.total_stats);
            this.displayAnalysisResults(response.files);
            this.updateDropdownMenus(response.files);

        } catch (error) {
            console.error('Error analyzing project:', error);
            this.showError(i18n.t('messages.project_analysis_failed'));
        }
    }

    updateAnalysisStats(stats) {
        document.getElementById('total-files').textContent = stats.total_files || 0;
        document.getElementById('total-classes').textContent = stats.total_classes || 0;
        document.getElementById('total-functions').textContent = stats.total_functions || 0;
        document.getElementById('total-methods').textContent = stats.total_methods || 0;
    }

    displayAnalysisResults(files) {
        const resultsContainer = document.getElementById('analysis-results');
        if (!resultsContainer) return;

        if (!files || files.length === 0) {
            resultsContainer.innerHTML = `<p class="placeholder">${i18n.t('analysis.no_results')}</p>`;
            return;
        }

        let html = '';
        files.forEach(file => {
            if (file.error) {
                html += `
                    <div class="analysis-file">
                        <div class="analysis-file-header">
                            <h4>${file.file_path}</h4>
                            <span class="text-danger">${i18n.t('analysis.error')}: ${file.error}</span>
                        </div>
                    </div>
                `;
                return;
            }

            html += `
                <div class="analysis-file">
                    <div class="analysis-file-header" onclick="toggleAnalysisFile(this)">
                        <h4>${file.file_path}</h4>
                        <div class="analysis-file-stats">
                            <span class="badge">${i18n.t('analysis.classes')}: ${file.stats?.classes || 0}</span>
                            <span class="badge">${i18n.t('analysis.functions')}: ${file.stats?.functions || 0}</span>
                            <span class="badge">${i18n.t('analysis.methods')}: ${file.stats?.methods || 0}</span>
                        </div>
                    </div>
                    <div class="analysis-file-content" style="display: none;">
                        ${this.renderCodeElements(file.elements || [])}
                    </div>
                </div>
            `;
        });

        resultsContainer.innerHTML = html;
    }

    updateDropdownMenus(files) {
        const classDropdown = document.getElementById('class-dropdown');
        const functionDropdown = document.getElementById('function-dropdown');
        const methodDropdown = document.getElementById('method-dropdown');

        if (!classDropdown || !functionDropdown || !methodDropdown) return;

        classDropdown.innerHTML = `<option value="">${i18n.t('analysis.select_class')}</option>`;
        functionDropdown.innerHTML = `<option value="">${i18n.t('analysis.select_function')}</option>`;
        methodDropdown.innerHTML = `<option value="">${i18n.t('analysis.select_method')}</option>`;

        files.forEach(file => {
            if (file.elements) {
                file.elements.forEach(element => {
                    const option = document.createElement('option');
                    option.value = element.line_start;
                    option.textContent = `${element.name} (${i18n.t('analysis.line')} ${element.line_start})`;

                    if (element.type === 'class') {
                        classDropdown.appendChild(option);
                    } else if (element.type === 'function') {
                        functionDropdown.appendChild(option);
                    } else if (element.type === 'method') {
                        methodDropdown.appendChild(option);
                    }
                });
            }
        });
    }

    async getVisualAnalysis() {
        if (!this.currentFile) return;

        try {
            const response = await this.apiRequest('/api/visualization/analyze', {
                method: 'POST',
                body: JSON.stringify({
                    file_path: this.currentFile,
                    force_refresh: true
                })
            });

            if (response.nodes && response.links) {
                this.codeStructure = {
                    nodes: response.nodes,
                    links: response.links
                };
                this.displayStructureTree(response.structure_tree);
            }
        } catch (error) {
            console.error('Error getting visual analysis:', error);
        }
    }

    displayStructureTree(tree) {
        const container = document.getElementById('structure-tree');
        if (!container || !tree) return;

        function renderNode(node, level = 0) {
            let html = `<div class="tree-node" style="margin-left: ${level * 20}px;">`;
            html += `<span class="tree-node-type">${node.type}</span> `;
            html += `<span class="tree-node-name" onclick="jumpToCode(${node.line})">${node.name}</span>`;
            html += `</div>`;

            if (node.children && node.children.length > 0) {
                for (const child of node.children) {
                    html += renderNode(child, level + 1);
                }
            }

            return html;
        }

        container.innerHTML = renderNode(tree);
    }

    jumpToCode(lineNumber) {
        if (!this.monacoEditor || !lineNumber) return;

        const line = parseInt(lineNumber);
        if (line > 0) {
            this.monacoEditor.revealLineInCenter(line);
            this.monacoEditor.setPosition({ lineNumber: line, column: 1 });
            this.monacoEditor.focus();
            this.showTab('editor');
        }
    }

    renderCodeElements(elements) {
        if (!elements || elements.length === 0) {
            return `<p class="text-muted">${i18n.t('analysis.no_elements')}</p>`;
        }

        let html = '';
        elements.forEach(element => {
            html += `
                <div class="code-element">
                    <div class="code-element-header" onclick="toggleCodeElement(this)">
                        <div class="code-element-info">
                            <span class="code-element-type">${element.type}</span>
                            <strong>${element.name}</strong>
                            <span class="text-muted">(${i18n.t('analysis.lines_range')} ${element.line_start}-${element.line_end})</span>
                        </div>
                        <div class="code-element-actions">
                            <button class="btn btn-sm btn-info" onclick="event.stopPropagation(); executeCodeElement('${encodeURIComponent(element.content)}')">
                                <i class="fas fa-play"></i> ${i18n.t('editor.execute')}
                            </button>
                            <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); addCommentToElement('${element.name}', ${element.line_start})">
                                <i class="fas fa-comment"></i> ${i18n.t('tabs.comments')}
                            </button>
                        </div>
                    </div>
                    <div class="code-element-content" style="display: none;">
                        <pre><code>${this.escapeHtml(element.content)}</code></pre>
                    </div>
                </div>
            `;
        });

        return html;
    }

    /**
     * Code execution
     */
    async executeCode() {
        if (!this.executionMonaco) {
            this.showError(i18n.t('messages.execution_editor_unavailable'));
            return;
        }

        const code = this.executionMonaco.getValue();
        if (!code.trim()) {
            this.showError(i18n.t('messages.no_code_to_execute'));
            return;
        }

        try {
            const timeout = parseInt(document.getElementById('execution-timeout')?.value || '30');
            const response = await this.apiRequest('/api/execute', {
                method: 'POST',
                body: JSON.stringify({
                    code: code,
                    execution_type: 'python',
                    timeout: timeout
                })
            });

            this.displayExecutionResult(response);

        } catch (error) {
            console.error('Error executing code:', error);
            this.showError(i18n.t('messages.execution_failed'));
        }
    }

    async executeSelectedCode() {
        if (!this.monacoEditor) {
            this.showError(i18n.t('messages.no_code_selected'));
            return;
        }

        const selectedText = this.monacoEditor.getModel().getValueInRange(this.monacoEditor.getSelection());
        if (!selectedText) {
            this.showError(i18n.t('messages.select_code_to_execute'));
            return;
        }

        try {
            const timeout = parseInt(document.getElementById('execution-timeout')?.value || '30');
            const response = await this.apiRequest('/api/execute', {
                method: 'POST',
                body: JSON.stringify({
                    code: selectedText,
                    execution_type: 'python',
                    timeout: timeout
                })
            });

            this.displayExecutionResult(response);
            this.showTab('execution');

        } catch (error) {
            console.error('Error executing code:', error);
            this.showError(i18n.t('messages.execution_failed'));
        }
    }

    displayExecutionResult(result) {
        const resultContainer = document.getElementById('execution-result');
        if (!resultContainer) return;

        let html = '';

        if (result.success) {
            html = `
                <div class="execution-success">
                    <h4 class="text-success">${i18n.t('execution.success')}</h4>
                    <p><strong>${i18n.t('execution.time')}:</strong> ${result.execution_time.toFixed(3)}s</p>
                    ${result.output ? `<pre class="output-success">${this.escapeHtml(result.output)}</pre>` : ''}
                </div>
            `;
        } else {
            html = `
                <div class="execution-error">
                    <h4 class="text-danger">${i18n.t('execution.failed')}</h4>
                    <p><strong>${i18n.t('execution.time')}:</strong> ${result.execution_time.toFixed(3)}s</p>
                    ${result.error_output ? `<pre class="output-error">${this.escapeHtml(result.error_output)}</pre>` : ''}
                    ${result.output ? `<pre class="output-info">${this.escapeHtml(result.output)}</pre>` : ''}
                </div>
            `;
        }

        resultContainer.innerHTML = html;
    }

    clearExecutionOutput() {
        const resultContainer = document.getElementById('execution-result');
        if (resultContainer) {
            resultContainer.innerHTML = `<p class="placeholder">${i18n.t('execution.placeholder')}</p>`;
        }
    }

    async showExecutionHistory() {
        try {
            const response = await this.apiRequest('/api/execution/history');
            this.displayExecutionHistory(response.history);
        } catch (error) {
            console.error('Error loading execution history:', error);
            this.showError(i18n.t('messages.history_load_failed'));
        }
    }

    displayExecutionHistory(history) {
        const resultContainer = document.getElementById('execution-result');
        if (!resultContainer) return;

        if (!history || history.length === 0) {
            resultContainer.innerHTML = `<p class="placeholder">${i18n.t('execution.placeholder')}</p>`;
            return;
        }

        let html = '<div class="execution-history-list">';
        history.forEach(entry => {
            const success = !entry.error_output;
            const icon = success ? 'check-circle' : 'times-circle';
            const color = success ? 'var(--success-color)' : 'var(--danger-color)';
            const time = entry.execution_time ? `${parseFloat(entry.execution_time).toFixed(3)}s` : '';
            const date = entry.created_at ? this.formatTimestamp(entry.created_at) : '';

            html += `
                <div class="history-entry" onclick="window.DocsPort.loadHistoryEntry(${JSON.stringify(entry.code_content).replace(/"/g, '&quot;')})">
                    <div class="history-entry-header">
                        <i class="fas fa-${icon}" style="color: ${color}"></i>
                        <span class="text-muted">${date}</span>
                        <span class="text-muted">${time}</span>
                    </div>
                    <pre class="history-entry-code">${this.escapeHtml((entry.code_content || '').substring(0, 100))}${(entry.code_content || '').length > 100 ? '...' : ''}</pre>
                </div>
            `;
        });
        html += '</div>';
        resultContainer.innerHTML = html;
    }

    loadHistoryEntry(code) {
        if (this.executionMonaco && code) {
            this.executionMonaco.setValue(code);
        }
    }

    /**
     * Comments system
     */
    async loadComments() {
        try {
            if (this.currentFile) {
                await this.loadFileComments(this.currentFile);
            }
        } catch (error) {
            console.error('Error loading comments:', error);
        }
    }

    async loadFileComments(filePath) {
        try {
            const response = await this.apiRequest(`/api/comments/${filePath}`);
            this.displayFileComments(response.comments);
        } catch (error) {
            console.error('Error loading file comments:', error);
        }
    }

    displayFileComments(comments) {
        const fileComments = document.getElementById('file-comments');
        if (!fileComments) return;

        if (!comments || comments.length === 0) {
            fileComments.innerHTML = `<p class="text-muted">${i18n.t('editor.no_comments')}</p>`;
            return;
        }

        let html = '';
        comments.forEach(comment => {
            html += `
                <div class="comment-item" data-file="${this.escapeHtml(comment.file_path || '')}" data-type="${this.escapeHtml(comment.comment_type || '')}">
                    <div class="comment-header">
                        <span class="comment-type">${comment.comment_type}</span>
                        ${comment.line_number ? `<span class="text-muted">${i18n.t('comments_tab.line')} ${comment.line_number}</span>` : ''}
                    </div>
                    <div class="comment-content">${this.escapeHtml(comment.comment_text)}</div>
                </div>
            `;
        });

        fileComments.innerHTML = html;
    }

    clearFileComments() {
        const fileComments = document.getElementById('file-comments');
        if (fileComments) {
            fileComments.innerHTML = `<p class="text-muted">${i18n.t('editor.no_comments')}</p>`;
        }
    }

    showAddCommentDialog() {
        const modal = document.getElementById('comment-modal');
        const fileInput = document.getElementById('comment-file');

        if (!modal || !fileInput) return;
        fileInput.value = this.currentFile || '';
        modal.classList.add('active');
    }

    closeCommentModal() {
        const modal = document.getElementById('comment-modal');
        if (modal) {
            modal.classList.remove('active');
        }
        document.getElementById('comment-form').reset();
    }

    async submitComment() {
        const commentData = {
            file_path: document.getElementById('comment-file').value,
            line_number: document.getElementById('comment-line').value ? parseInt(document.getElementById('comment-line').value) : null,
            comment_text: document.getElementById('comment-text').value,
            comment_type: document.getElementById('comment-type').value
        };

        try {
            await this.apiRequest('/api/comments', {
                method: 'POST',
                body: JSON.stringify(commentData)
            });

            this.showSuccess(i18n.t('messages.comment_added'));
            this.closeCommentModal();

            if (this.currentFile) {
                await this.loadFileComments(this.currentFile);
            }

        } catch (error) {
            console.error('Error adding comment:', error);
            this.showError(i18n.t('messages.comment_not_added'));
        }
    }

    /**
     * Visualization
     */
    async generateFlowchart() {
        try {
            const response = await this.apiRequest('/api/visualization/flowchart');
            this.displayFlowchart(response);
        } catch (error) {
            console.error('Error generating flowchart:', error);
            this.showError(i18n.t('messages.flowchart_failed'));
        }
    }

    displayFlowchart(flowchartData) {
        const container = document.getElementById('flowchart-container');
        if (!container) return;

        if (flowchartData && flowchartData.mermaid) {
            container.innerHTML = `<div class="mermaid">${flowchartData.mermaid}</div>`;
            mermaid.init(undefined, container.querySelector('.mermaid'));
        } else {
            container.innerHTML = `<p class="placeholder">${i18n.t('visualization.placeholder')}</p>`;
        }
    }

    switchVisualization(type) {
        const mermaidContainer = document.getElementById('flowchart-container');
        const d3Container = document.getElementById('d3-visualization');

        if (type === 'mermaid') {
            mermaidContainer.style.display = 'block';
            d3Container.style.display = 'none';
        } else if (type === 'd3') {
            mermaidContainer.style.display = 'none';
            d3Container.style.display = 'block';
            this.renderD3Visualization();
        }
    }

    renderD3Visualization() {
        const svg = d3.select('#d3-svg');
        svg.selectAll('*').remove();

        if (!this.codeStructure) {
            svg.append('text')
                .attr('x', 50)
                .attr('y', 50)
                .text(i18n.t('visualization.analyze_first'));
            return;
        }

        const width = 800;
        const height = 600;

        const simulation = d3.forceSimulation(this.codeStructure.nodes)
            .force('link', d3.forceLink(this.codeStructure.links).id(d => d.id))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2));

        const link = svg.append('g')
            .selectAll('line')
            .data(this.codeStructure.links)
            .enter().append('line')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', 2);

        const node = svg.append('g')
            .selectAll('circle')
            .data(this.codeStructure.nodes)
            .enter().append('circle')
            .attr('r', d => d.type === 'class' ? 15 : 10)
            .attr('fill', d => d.type === 'class' ? '#ff6b6b' : '#4ecdc4')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended))
            .on('click', (event, d) => {
                this.onNodeClick(d);
            });

        const label = svg.append('g')
            .selectAll('text')
            .data(this.codeStructure.nodes)
            .enter().append('text')
            .text(d => d.name)
            .attr('font-size', 12)
            .attr('dx', 15)
            .attr('dy', 4);

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);

            label
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });

        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    }

    onNodeClick(node) {
        console.log('Node clicked:', node);
        if (this.monacoEditor && node.line) {
            this.monacoEditor.revealLineInCenter(node.line);
            this.monacoEditor.setPosition({ lineNumber: node.line, column: 1 });
            this.showTab('editor');
        }
    }

    toggleComment() {
        if (!this.monacoEditor) return;

        const selection = this.monacoEditor.getSelection();
        const model = this.monacoEditor.getModel();
        const lines = [];

        for (let i = selection.startLineNumber; i <= selection.endLineNumber; i++) {
            lines.push(i);
        }

        const edits = [];
        const allCommented = lines.every(line => {
            const lineContent = model.getLineContent(line);
            return lineContent.trim().startsWith('#');
        });

        lines.forEach(line => {
            const lineContent = model.getLineContent(line);
            const range = {
                startLineNumber: line,
                startColumn: 1,
                endLineNumber: line,
                endColumn: lineContent.length + 1
            };

            if (allCommented) {
                const newContent = lineContent.replace(/^(\s*)#\s?/, '$1');
                edits.push({ range, text: newContent });
            } else {
                const newContent = lineContent.replace(/^(\s*)/, '$1# ');
                edits.push({ range, text: newContent });
            }
        });

        model.pushEditOperations([], edits, () => null);
    }

    addCommentAtCursor() {
        if (!this.monacoEditor) return;

        const position = this.monacoEditor.getPosition();
        const filePath = this.currentFile;

        const modal = document.getElementById('comment-modal');
        const fileInput = document.getElementById('comment-file');
        const lineInput = document.getElementById('comment-line');

        if (modal && fileInput && lineInput) {
            fileInput.value = filePath || '';
            lineInput.value = position.lineNumber;
            modal.classList.add('active');
        }
    }

    /**
     * Utility functions
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }

    showOutput(type) {
        document.querySelectorAll('.output-tab').forEach(tab => {
            tab.classList.remove('active');
        });

        const activeTab = document.querySelector(`[onclick="showOutput('${type}')"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }
    }
}

// Global functions for HTML onclick handlers
window.DocsPort = new DocsPort();

window.showTab = (tabName) => { window.DocsPort.showTab(tabName); };
window.loadFile = () => { window.DocsPort.loadFile(); };
window.refreshFileList = () => { window.DocsPort.refreshFileList(); };
window.saveFile = () => { window.DocsPort.saveFile(); };
window.analyzeCurrentFile = () => { window.DocsPort.analyzeCurrentFile(); };
window.analyzeProject = () => { window.DocsPort.analyzeProject(); };
window.executeCode = () => { window.DocsPort.executeCode(); };
window.executeSelectedCode = () => { window.DocsPort.executeSelectedCode(); };
window.clearExecutionOutput = () => { window.DocsPort.clearExecutionOutput(); };
window.showExecutionHistory = () => { window.DocsPort.showExecutionHistory(); };
window.showAddCommentDialog = () => { window.DocsPort.showAddCommentDialog(); };
window.closeCommentModal = () => { window.DocsPort.closeCommentModal(); };
window.generateFlowchart = () => { window.DocsPort.generateFlowchart(); };
window.showOutput = (type) => { window.DocsPort.showOutput(type); };

window.toggleAnalysisFile = (header) => {
    const content = header.nextElementSibling;
    const isVisible = content.style.display !== 'none';
    content.style.display = isVisible ? 'none' : 'block';
};

window.toggleCodeElement = (header) => {
    const content = header.nextElementSibling;
    const isVisible = content.style.display !== 'none';
    content.style.display = isVisible ? 'none' : 'block';
};

window.executeCodeElement = (code) => {
    if (window.DocsPort.executionMonaco) {
        window.DocsPort.executionMonaco.setValue(decodeURIComponent(code));
        window.DocsPort.showTab('execution');
        window.DocsPort.executeCode();
    }
};

window.addCommentToElement = (elementName, lineNumber) => {
    const modal = document.getElementById('comment-modal');
    const fileInput = document.getElementById('comment-file');
    const lineInput = document.getElementById('comment-line');

    if (modal && fileInput && lineInput) {
        fileInput.value = window.DocsPort.currentFile || '';
        lineInput.value = lineNumber || '';
        modal.classList.add('active');
    }
};

window.filterComments = () => {
    const fileFilter = document.getElementById('comment-file-filter')?.value || '';
    const typeFilter = document.getElementById('comment-type-filter')?.value || '';
    const items = document.querySelectorAll('#comments-list .comment-item');

    items.forEach(item => {
        const file = item.dataset.file || '';
        const type = item.dataset.type || '';
        const matchFile = !fileFilter || file === fileFilter;
        const matchType = !typeFilter || type === typeFilter;
        item.style.display = (matchFile && matchType) ? '' : 'none';
    });
};

window.switchVisualization = (type) => { window.DocsPort.switchVisualization(type); };
window.jumpToCode = (lineNumber) => { window.DocsPort.jumpToCode(lineNumber); };
