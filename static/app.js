async function runAgent() {
    const goalInput = document.getElementById('goalInput');
    const runBtn = document.getElementById('runBtn');
    const terminal = document.getElementById('terminal');

    const goal = goalInput.value.trim();
    if (!goal) return;

    // UI Updates
    runBtn.disabled = true;
    runBtn.textContent = 'Agent Running...';

    addLog('info', `> Initiating Marathon Agent...`);
    addLog('info', `> Goal: "${goal}"`);
    addLog('system', `> Connecting to Gemini 3 Brain (Planning Phase)...`);

    try {
        const response = await fetch('/api/marathon/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                goal: goal,
                max_iterations: 15,
                thinking_level: "high"
            })
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }

        const data = await response.json();

        // 1. Show Plan
        if (data.plan && data.plan.tool_calls) {
            addLog('plan', `\n🧠 GENERATED PLAN (${data.plan.tool_calls.length} Steps):`);
            data.plan.tool_calls.forEach((step, index) => {
                addLog('plan', `  ${index + 1}. [${step.tool_name}] ${step.purpose}`);
            });
        }

        // 2. Show Results (Simulating stream since we get bulk response)
        if (data.execution_results) {
            addLog('info', `\n⚡ EXECUTING LOCAL TOOLS...`);

            for (const res of data.execution_results) {
                // Formatting delay for dramatic effect? No, just dump it.
                const statusIcon = res.success ? '✅' : '❌';
                addLog('tool', `> Running ${res.tool}...`);

                if (res.result) {
                    let preview = JSON.stringify(res.result).substring(0, 100);
                    if (preview.length === 100) preview += "...";
                    addLog('info', `  Input: ${JSON.stringify(res.args)}`);
                    addLog(res.success ? 'success' : 'error', `  ${statusIcon} Result: ${preview}`);
                }

                if (res.error) {
                    addLog('error', `  ❌ Error: ${res.error}`);
                }
            }
        }

        // 3. Final Report
        if (data.response) {
            addLog('success', `\n🎉 MISSION COMPLETE`);
            addLog('default', data.response); // Markdown-like text
        }

    } catch (error) {
        addLog('error', `\n❌ CRITICAL FAILURE: ${error.message}`);
    } finally {
        runBtn.disabled = false;
        runBtn.textContent = 'Run Agent';
        addLog('info', `\n> Agent Standby.`);
    }
}

function addLog(type, message) {
    const terminal = document.getElementById('terminal');
    const div = document.createElement('div');
    div.className = 'log-entry';

    if (type === 'plan') div.classList.add('log-plan');
    else if (type === 'tool') div.classList.add('log-tool');
    else if (type === 'success') div.classList.add('log-success');
    else if (type === 'error') div.classList.add('log-error');
    else if (type === 'info') div.classList.add('log-info');
    else if (type === 'system') {
        div.innerHTML = `<span class="loading-spinner"></span> ${message}`;
        div.classList.add('log-warning');
    }
    else div.style.color = '#c9d1d9';

    if (type !== 'system') div.textContent = message;

    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}
