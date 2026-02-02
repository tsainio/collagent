"""
CollAgent - HTML Template for Web Interface

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

WEB_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CollAgent - Research Collaborator Search</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            background-attachment: fixed;
            color: #e4e4e7;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            text-align: center;
            margin-bottom: 2rem;
        }

        h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            color: #a1a1aa;
            font-size: 1.1rem;
        }

        .glass-panel {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }

        .form-group {
            margin-bottom: 1.25rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #d4d4d8;
        }

        .required::after {
            content: " *";
            color: #f87171;
        }

        .label-with-info {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .info-btn {
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            background: rgba(102, 126, 234, 0.3);
            border: 1px solid rgba(102, 126, 234, 0.5);
            border-radius: 50%;
            color: #a5b4fc;
            font-size: 12px;
            font-weight: 600;
            cursor: help;
        }

        .info-btn:hover .tooltip {
            opacity: 1;
            visibility: visible;
        }

        .tooltip {
            position: absolute;
            bottom: calc(100% + 10px);
            left: 50%;
            transform: translateX(-50%);
            width: 280px;
            padding: 0.75rem 1rem;
            background: rgba(30, 30, 50, 0.98);
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 8px;
            color: #d4d4d8;
            font-size: 0.8rem;
            font-weight: 400;
            line-height: 1.5;
            text-align: left;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.2s ease;
            z-index: 100;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
        }

        .tooltip::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 6px solid transparent;
            border-top-color: rgba(30, 30, 50, 0.98);
        }

        input[type="text"],
        input[type="number"],
        textarea,
        select {
            width: 100%;
            padding: 0.75rem 1rem;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            color: #e4e4e7;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        input:focus,
        textarea:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
        }

        textarea {
            min-height: 120px;
            resize: vertical;
        }

        select option {
            background: #1a1a2e;
            color: #e4e4e7;
        }

        .form-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.875rem 1.75rem;
            font-size: 1rem;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
        }

        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .btn-stop {
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
            color: white;
        }

        .btn-stop:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(220, 38, 38, 0.4);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #e4e4e7;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
        }

        .output-section {
            display: none;
        }

        .output-section.active {
            display: block;
        }

        .terminal {
            background: rgba(0, 0, 0, 0.4);
            border-radius: 12px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.875rem;
            overflow: hidden;
        }

        .terminal-header {
            background: rgba(255, 255, 255, 0.05);
            padding: 0.75rem 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .terminal-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }

        .terminal-dot.red { background: #ff5f56; }
        .terminal-dot.yellow { background: #ffbd2e; }
        .terminal-dot.green { background: #27c93f; }

        .terminal-title {
            margin-left: 0.5rem;
            color: #a1a1aa;
            font-size: 0.8rem;
        }

        .terminal-body {
            padding: 1rem;
            min-height: 500px;
            max-height: 800px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .terminal-body::-webkit-scrollbar {
            width: 8px;
        }

        .terminal-body::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
        }

        .terminal-body::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
        }

        .log-entry {
            margin-bottom: 0.25rem;
        }

        .log-info { color: #60a5fa; }
        .log-success { color: #34d399; }
        .log-warning { color: #fbbf24; }
        .log-error { color: #f87171; }
        .log-dim { color: #71717a; }

        /* Collapsible sections for parallel searches */
        .log-section {
            margin-bottom: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            overflow: hidden;
        }

        .log-section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0.75rem;
            background: rgba(255, 255, 255, 0.05);
            cursor: pointer;
            user-select: none;
            transition: background 0.2s ease;
        }

        .log-section-header:hover {
            background: rgba(255, 255, 255, 0.08);
        }

        .log-section-title {
            font-weight: 500;
            color: #a5b4fc;
            font-size: 0.85rem;
        }

        .log-section-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .log-section-count {
            background: rgba(102, 126, 234, 0.3);
            color: #a5b4fc;
            padding: 0.15rem 0.5rem;
            border-radius: 10px;
            font-size: 0.75rem;
        }

        .log-section-status {
            font-size: 0.75rem;
            padding: 0.15rem 0.5rem;
            border-radius: 10px;
        }

        .log-section-status.running {
            background: rgba(96, 165, 250, 0.2);
            color: #60a5fa;
        }

        .log-section-status.complete {
            background: rgba(52, 211, 153, 0.2);
            color: #34d399;
        }

        .log-section-toggle {
            color: #71717a;
            transition: transform 0.2s ease;
        }

        .log-section.collapsed .log-section-toggle {
            transform: rotate(-90deg);
        }

        .log-section-content {
            padding: 0.5rem 0.75rem;
            max-height: 300px;
            overflow-y: auto;
            transition: max-height 0.3s ease, padding 0.3s ease;
        }

        .log-section.collapsed .log-section-content {
            max-height: 0;
            padding-top: 0;
            padding-bottom: 0;
            overflow: hidden;
        }

        .log-section-content::-webkit-scrollbar {
            width: 6px;
        }

        .log-section-content::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
        }

        .log-section-content::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }

        /* General logs (no section) */
        .general-logs {
            margin-bottom: 0.5rem;
        }

        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }

        .status-running {
            background: rgba(96, 165, 250, 0.2);
            color: #60a5fa;
        }

        .status-complete {
            background: rgba(52, 211, 153, 0.2);
            color: #34d399;
        }

        .status-error {
            background: rgba(248, 113, 113, 0.2);
            color: #f87171;
        }

        .status-complete .spinner,
        .status-error .spinner {
            display: none;
        }

        .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid currentColor;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .results-actions {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
        }

        .help-text {
            font-size: 0.8rem;
            color: #71717a;
            margin-top: 0.25rem;
        }

        .file-upload-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-top: 0.5rem;
        }

        .btn-small {
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            cursor: pointer;
        }

        .file-name {
            font-size: 0.875rem;
            color: #a1a1aa;
        }

        .section-title {
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: #e4e4e7;
        }

        .subsection-title {
            font-size: 1rem;
            margin: 1.5rem 0 1rem 0;
            color: #a1a1aa;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 0.5rem;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            h1 {
                font-size: 1.75rem;
            }

            .form-row {
                grid-template-columns: 1fr;
            }
        }

        .site-footer {
            text-align: center;
            padding: 2rem 1rem;
            margin-top: 2rem;
            color: #71717a;
            font-size: 0.875rem;
        }

        .site-footer a {
            color: #667eea;
            text-decoration: none;
        }

        .site-footer a:hover {
            text-decoration: underline;
        }

        .site-footer .license {
            margin-top: 0.5rem;
        }

        /* Error Modal */
        .error-modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(4px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .error-modal-overlay.active {
            display: flex;
        }

        .error-modal {
            background: linear-gradient(135deg, #2d1b1b 0%, #1a1a2e 100%);
            border: 1px solid rgba(248, 113, 113, 0.3);
            border-radius: 16px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }

        .error-modal-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }

        .error-modal-icon {
            width: 40px;
            height: 40px;
            background: rgba(248, 113, 113, 0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }

        .error-modal-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #f87171;
        }

        .error-modal-body {
            color: #e4e4e7;
            margin-bottom: 1.5rem;
        }

        .error-modal-message {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 200px;
            overflow-y: auto;
            margin-top: 1rem;
        }

        .error-modal-footer {
            display: flex;
            gap: 1rem;
            justify-content: flex-end;
        }

        .error-modal-btn {
            padding: 0.5rem 1.25rem;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
        }

        .error-modal-btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
        }

        .error-modal-btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .error-modal-btn-secondary {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #a1a1aa;
        }

        .error-modal-btn-secondary:hover {
            background: rgba(255, 255, 255, 0.05);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>CollAgent</h1>
            <p class="subtitle">AI-Powered Research Collaborator Discovery</p>
        </header>

        <div class="glass-panel">
            <h2 class="section-title">Search Parameters</h2>
            <form id="searchForm">
                <div class="form-group">
                    <label for="profile" class="required">Research Profile</label>
                    <textarea id="profile" name="profile" placeholder="Describe your research interests, expertise, and what kind of collaborators you're looking for..."></textarea>
                    <div class="file-upload-row">
                        <label for="profileFile" class="btn btn-secondary btn-small">
                            <span>Upload from file</span>
                            <input type="file" id="profileFile" accept=".txt,.md,.text" style="display:none">
                        </label>
                        <span id="fileName" class="file-name"></span>
                    </div>
                    <p class="help-text">Include your research areas, methodologies, and collaboration goals</p>
                </div>

                <div class="form-group">
                    <label for="focus">Focus Areas</label>
                    <input type="text" id="focus" name="focus" placeholder="e.g., machine learning, computational chemistry, drug discovery">
                    <p class="help-text">Comma-separated research areas to focus on (optional)</p>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="institution">Target Institution</label>
                        <input type="text" id="institution" name="institution" placeholder="e.g., ETH Zürich, LUT University (optional)">
                        <p class="help-text">Leave empty for broad multi-institution search</p>
                    </div>
                    <div class="form-group">
                        <label for="region">Region</label>
                        <input type="text" id="region" name="region" placeholder="e.g., Europe, USA, Asia">
                        <p class="help-text">Filter institutions by geographic region</p>
                    </div>
                </div>

                <h3 class="subsection-title">Search Settings</h3>

                <div class="form-row">
                    <div class="form-group">
                        <label for="max_institutions">Max Institutions</label>
                        <input type="number" id="max_institutions" name="max_institutions" value="5" min="1" max="20">
                        <p class="help-text">For broad search mode (1-20)</p>
                    </div>
                    <div class="form-group">
                        <label for="max_turns" class="label-with-info">
                            Search Depth
                            <span class="info-btn">?<span class="tooltip">Each turn is an AI search iteration. More turns = broader coverage as the AI refines searches and explores different angles. Turns are split between institution discovery and per-institution searches. Higher values find more candidates but take longer and cost more.</span></span>
                        </label>
                        <input type="number" id="max_turns" name="max_turns" value="10" min="5" max="50">
                        <p class="help-text">Total budget distributed across search phases (5-50)</p>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="top_candidates">Top Candidates to Highlight</label>
                        <input type="number" id="top_candidates" name="top_candidates" value="5" min="1" max="20">
                        <p class="help-text">Show this many in main view (1-20)</p>
                    </div>
                    <div class="form-group">
                        <label for="model">Model</label>
                        <select id="model" name="model">
                            <option value="">Loading models...</option>
                        </select>
                        <p class="help-text" id="modelHelp">Select an AI model for the search</p>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary" id="searchBtn">
                    <span>Start Search</span>
                </button>
            </form>
        </div>

        <div class="output-section" id="outputSection">
            <div class="glass-panel">
                <h2 class="section-title">Search Progress</h2>
                <div class="status-indicator status-running" id="statusIndicator">
                    <div class="spinner"></div>
                    <span id="statusText">Search in progress...</span>
                </div>
                <div class="terminal">
                    <div class="terminal-header">
                        <span class="terminal-dot red"></span>
                        <span class="terminal-dot yellow"></span>
                        <span class="terminal-dot green"></span>
                        <span class="terminal-title">CollAgent Output</span>
                    </div>
                    <div class="terminal-body" id="terminalOutput"></div>
                </div>
                <div class="results-actions" id="resultsActions" style="display: none;">
                    <button class="btn btn-primary" id="viewResultsBtn">View Full Report</button>
                    <button class="btn btn-secondary" id="downloadHtmlBtn">Download HTML</button>
                    <button class="btn btn-secondary" id="downloadMdBtn">Download Markdown</button>
                    <button class="btn btn-secondary" id="downloadPdfBtn" style="{{PDF_BUTTON_STYLE}}">Download PDF</button>
                    <button class="btn btn-secondary" id="newSearchBtn">New Search</button>
                </div>
            </div>
        </div>
    </div>

    <footer class="site-footer">
        <p>Copyright &copy; 2026 Tuomo Sainio</p>
        <p class="license">Licensed under <a href="https://www.gnu.org/licenses/agpl-3.0.html" target="_blank">AGPL-3.0</a> &middot; <a href="https://github.com/tsainio/collagent" target="_blank">Source Code</a></p>
    </footer>

    <script>
        const form = document.getElementById('searchForm');
        const searchBtn = document.getElementById('searchBtn');
        const outputSection = document.getElementById('outputSection');
        const terminalOutput = document.getElementById('terminalOutput');
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        const resultsActions = document.getElementById('resultsActions');
        const modelSelect = document.getElementById('model');
        const modelHelp = document.getElementById('modelHelp');

        let currentSearchId = null;
        let eventSource = null;
        let isSearching = false;

        // Load available models on page load
        async function loadModels() {
            try {
                const response = await fetch('/api/models');
                const models = await response.json();

                modelSelect.innerHTML = '';

                if (models.length === 0) {
                    modelSelect.innerHTML = '<option value="">No models available</option>';
                    modelHelp.textContent = 'Set GOOGLE_API_KEY or OPENAI_API_KEY to enable models';
                    searchBtn.disabled = true;
                    return;
                }

                models.forEach(m => {
                    const option = document.createElement('option');
                    option.value = m.id;
                    option.textContent = `${m.display_name} [${m.provider}]`;
                    if (m.default) {
                        option.selected = true;
                    }
                    modelSelect.appendChild(option);
                });

                // Update help text with provider info
                const providers = [...new Set(models.map(m => m.provider))];
                modelHelp.textContent = `Available providers: ${providers.join(', ')}`;

            } catch (error) {
                modelSelect.innerHTML = '<option value="">Error loading models</option>';
                modelHelp.textContent = 'Failed to load models from server';
                console.error('Failed to load models:', error);
            }
        }

        // Load models when page loads
        loadModels();

        function stopSearch() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            isSearching = false;
            searchBtn.className = 'btn btn-primary';
            searchBtn.innerHTML = '<span>Start Search</span>';
            statusIndicator.className = 'status-indicator status-error';
            statusText.textContent = 'Search stopped';
            appendLog('Search stopped by user', 'warning');
        }

        searchBtn.addEventListener('click', (e) => {
            if (isSearching) {
                e.preventDefault();
                stopSearch();
                return;
            }
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (isSearching) {
                stopSearch();
                return;
            }

            const profile = document.getElementById('profile').value.trim();
            if (!profile) {
                alert('Please enter your research profile');
                return;
            }

            // Start search - change button to Stop
            isSearching = true;
            searchBtn.className = 'btn btn-stop';
            searchBtn.innerHTML = '<span>Stop</span>';
            outputSection.classList.add('active');
            terminalOutput.innerHTML = '';
            resetSections();
            resultsActions.style.display = 'none';
            statusIndicator.className = 'status-indicator status-running';
            statusText.textContent = 'Search in progress...';

            // Build form data
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // Close any existing connection
            if (eventSource) {
                eventSource.close();
            }

            // Start SSE connection
            eventSource = new EventSource('/search?' + new URLSearchParams(data).toString());

            eventSource.onmessage = (event) => {
                const msg = JSON.parse(event.data);

                if (msg.type === 'log') {
                    appendLog(msg.text, msg.level || 'info', msg.section);
                } else if (msg.type === 'status') {
                    statusText.textContent = msg.text;
                } else if (msg.type === 'complete') {
                    currentSearchId = msg.search_id;
                    statusIndicator.className = 'status-indicator status-complete';
                    statusText.textContent = 'Search complete!';
                    resultsActions.style.display = 'flex';
                    isSearching = false;
                    searchBtn.className = 'btn btn-primary';
                    searchBtn.innerHTML = '<span>Start Search</span>';
                    // Mark all sections as complete
                    document.querySelectorAll('.log-section-status.running').forEach(el => {
                        el.className = 'log-section-status complete';
                        el.textContent = 'Done';
                    });
                    eventSource.close();
                } else if (msg.type === 'error') {
                    appendLog(msg.text, 'error');
                    statusIndicator.className = 'status-indicator status-error';
                    statusText.textContent = 'Search failed';
                    isSearching = false;
                    searchBtn.className = 'btn btn-primary';
                    searchBtn.innerHTML = '<span>Start Search</span>';
                    eventSource.close();
                } else if (msg.type === 'fatal_error') {
                    // Show modal for catastrophic user-fixable errors
                    showErrorModal(msg.text, msg.code, msg.help_url);
                    statusIndicator.className = 'status-indicator status-error';
                    statusText.textContent = 'Search failed';
                    isSearching = false;
                    searchBtn.className = 'btn btn-primary';
                    searchBtn.innerHTML = '<span>Start Search</span>';
                    eventSource.close();
                }
            };

            eventSource.onerror = () => {
                if (eventSource.readyState === EventSource.CLOSED) {
                    return; // Normal close
                }
                appendLog('Connection lost', 'error');
                statusIndicator.className = 'status-indicator status-error';
                statusText.textContent = 'Connection error';
                isSearching = false;
                searchBtn.className = 'btn btn-primary';
                searchBtn.innerHTML = '<span>Start Search</span>';
                eventSource.close();
            };
        });

        // Track sections for collapsible groups
        const sections = {};
        let generalLogsContainer = null;

        function getOrCreateSection(sectionName) {
            if (!sectionName) {
                // General logs (no section)
                if (!generalLogsContainer) {
                    generalLogsContainer = document.createElement('div');
                    generalLogsContainer.className = 'general-logs';
                    terminalOutput.insertBefore(generalLogsContainer, terminalOutput.firstChild);
                }
                return generalLogsContainer;
            }

            if (!sections[sectionName]) {
                // Create new collapsible section (starts collapsed)
                const section = document.createElement('div');
                section.className = 'log-section collapsed';
                section.innerHTML = `
                    <div class="log-section-header">
                        <span class="log-section-title">${sectionName}</span>
                        <div class="log-section-badge">
                            <span class="log-section-count">0</span>
                            <span class="log-section-status running">Searching...</span>
                            <span class="log-section-toggle">▼</span>
                        </div>
                    </div>
                    <div class="log-section-content"></div>
                `;

                // Toggle collapse on header click
                section.querySelector('.log-section-header').addEventListener('click', () => {
                    section.classList.toggle('collapsed');
                });

                terminalOutput.appendChild(section);
                sections[sectionName] = {
                    element: section,
                    content: section.querySelector('.log-section-content'),
                    countEl: section.querySelector('.log-section-count'),
                    statusEl: section.querySelector('.log-section-status'),
                    count: 0
                };
            }
            return sections[sectionName];
        }

        function appendLog(text, level = 'info', sectionName = null) {
            const entry = document.createElement('div');
            entry.className = `log-entry log-${level}`;
            entry.textContent = text;

            if (sectionName) {
                const section = getOrCreateSection(sectionName);
                section.content.appendChild(entry);
                section.count++;
                section.countEl.textContent = section.count;
                section.content.scrollTop = section.content.scrollHeight;

                // Check if this is a completion message
                if (text.includes('Completed:') || text.includes('Search complete!')) {
                    section.statusEl.className = 'log-section-status complete';
                    section.statusEl.textContent = 'Done';
                }
            } else {
                const container = getOrCreateSection(null);
                container.appendChild(entry);
            }

            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        }

        function resetSections() {
            Object.keys(sections).forEach(key => delete sections[key]);
            generalLogsContainer = null;
        }

        // File upload handler
        document.getElementById('profileFile').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('fileName').textContent = file.name;
                const reader = new FileReader();
                reader.onload = (event) => {
                    document.getElementById('profile').value = event.target.result;
                };
                reader.readAsText(file);
            }
        });

        document.getElementById('viewResultsBtn').addEventListener('click', () => {
            if (currentSearchId) {
                window.open('/results/' + currentSearchId, '_blank');
            }
        });

        document.getElementById('downloadHtmlBtn').addEventListener('click', () => {
            if (currentSearchId) {
                const link = document.createElement('a');
                link.href = '/results/' + currentSearchId + '?download=html';
                link.download = 'collagent_report.html';
                link.click();
            }
        });

        document.getElementById('downloadMdBtn').addEventListener('click', () => {
            if (currentSearchId) {
                const link = document.createElement('a');
                link.href = '/results/' + currentSearchId + '?download=md';
                link.download = 'collagent_report.md';
                link.click();
            }
        });

        document.getElementById('downloadPdfBtn').addEventListener('click', () => {
            if (currentSearchId) {
                const link = document.createElement('a');
                link.href = '/results/' + currentSearchId + '?download=pdf';
                link.download = 'collagent_report.pdf';
                link.click();
            }
        });

        document.getElementById('newSearchBtn').addEventListener('click', () => {
            outputSection.classList.remove('active');
            form.reset();
            document.getElementById('max_institutions').value = '5';
            document.getElementById('max_turns').value = '10';
            document.getElementById('top_candidates').value = '5';
            document.getElementById('fileName').textContent = '';
        });

        // Error modal functions
        function showErrorModal(message, code, helpUrl) {
            const modal = document.getElementById('errorModal');
            const messageEl = document.getElementById('errorModalMessage');
            const helpBtn = document.getElementById('errorModalHelpBtn');

            messageEl.textContent = message;

            if (helpUrl) {
                helpBtn.href = helpUrl;
                helpBtn.style.display = 'inline-block';
            } else {
                helpBtn.style.display = 'none';
            }

            modal.classList.add('active');
        }

        function closeErrorModal() {
            document.getElementById('errorModal').classList.remove('active');
        }

        // Close modal on overlay click
        document.getElementById('errorModal').addEventListener('click', (e) => {
            if (e.target.id === 'errorModal') {
                closeErrorModal();
            }
        });
    </script>

    <!-- Error Modal -->
    <div id="errorModal" class="error-modal-overlay">
        <div class="error-modal">
            <div class="error-modal-header">
                <div class="error-modal-icon">⚠</div>
                <div class="error-modal-title">API Error</div>
            </div>
            <div class="error-modal-body">
                <p>A critical error occurred that requires your attention:</p>
                <div id="errorModalMessage" class="error-modal-message"></div>
            </div>
            <div class="error-modal-footer">
                <button class="error-modal-btn error-modal-btn-secondary" onclick="closeErrorModal()">Close</button>
                <a id="errorModalHelpBtn" class="error-modal-btn error-modal-btn-primary" href="#" target="_blank">Get Help</a>
            </div>
        </div>
    </div>
</body>
</html>
'''
