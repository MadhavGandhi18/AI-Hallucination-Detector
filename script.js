// ===== Hallucination Detector - Clean Script =====
// All duplicate code removed, proper event handling

(function() {
    'use strict';

    // ===== State =====
    let currentTab = 'text';
    let uploadedFile = null;
    let extractedText = '';
    const API_URL = 'http://localhost:5000';

    // ===== Initialize on DOM Ready =====
    document.addEventListener('DOMContentLoaded', init);

    function init() {
        initParticles();
        initNavbar();
        initTabs();
        initTextInput();
        initFileUpload();
        initAnalyzeButton();
        initAnimations();
        animateStats();
        initKeyboardShortcuts();
    }

    // ===== Particle Animation =====
    function initParticles() {
        const container = document.getElementById('particles');
        if (!container) return;

        for (let i = 0; i < 50; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
            particle.style.animationDelay = Math.random() * 10 + 's';
            particle.style.opacity = Math.random() * 0.5 + 0.2;
            container.appendChild(particle);
        }
    }

    // ===== Navbar =====
    function initNavbar() {
        const navbar = document.querySelector('.navbar');
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');

        // Scroll effect
        window.addEventListener('scroll', () => {
            if (navbar) {
                navbar.classList.toggle('scrolled', window.scrollY > 50);
            }
        });

        // Mobile menu
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', (e) => {
                e.preventDefault();
                mobileMenuBtn.classList.toggle('active');
            });
        }

        // Smooth scroll - prevent default and handle manually
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const targetId = this.getAttribute('href');
                if (targetId && targetId !== '#') {
                    const target = document.querySelector(targetId);
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        });

        // Get Started button
        const ctaBtn = document.querySelector('.nav-cta');
        if (ctaBtn) {
            ctaBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const detector = document.getElementById('detector');
                if (detector) {
                    detector.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        }
    }

    // ===== Tabs =====
    function initTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const tab = btn.dataset.tab;
                currentTab = tab;

                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                tabContents.forEach(content => {
                    content.classList.toggle('active', content.id === `${tab}-tab`);
                });
            });
        });
    }

    // ===== Text Input =====
    function initTextInput() {
        const textInput = document.getElementById('textInput');
        const charCount = document.getElementById('charCount');
        const clearBtn = document.getElementById('clearText');

        if (textInput && charCount) {
            textInput.addEventListener('input', () => {
                charCount.textContent = textInput.value.length;
            });
        }

        if (clearBtn && textInput && charCount) {
            clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                textInput.value = '';
                charCount.textContent = '0';
            });
        }
    }

    // ===== File Upload =====
    function initFileUpload() {
        const uploadZone = document.getElementById('uploadZone');
        const pdfInput = document.getElementById('pdfInput');
        const fileInfo = document.getElementById('fileInfo');
        const removeBtn = document.getElementById('removeFile');

        if (!uploadZone || !pdfInput) return;

        uploadZone.addEventListener('click', (e) => {
            if (e.target.closest('.remove-file')) return;
            pdfInput.click();
        });

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                handleFileSelect(file);
            } else {
                showNotification('Please upload a PDF file', 'error');
            }
        });

        pdfInput.addEventListener('change', (e) => {
            if (e.target.files[0]) {
                handleFileSelect(e.target.files[0]);
            }
        });

        if (removeBtn) {
            removeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                removeFile();
            });
        }
    }

    function handleFileSelect(file) {
        uploadedFile = file;
        const fileInfo = document.getElementById('fileInfo');
        const fileName = fileInfo?.querySelector('.file-name');
        if (fileName) fileName.textContent = file.name;
        if (fileInfo) fileInfo.classList.add('show');
        extractTextFromPDF(file);
    }

    function removeFile() {
        uploadedFile = null;
        extractedText = '';
        const pdfInput = document.getElementById('pdfInput');
        const fileInfo = document.getElementById('fileInfo');
        if (pdfInput) pdfInput.value = '';
        if (fileInfo) fileInfo.classList.remove('show');
    }

    async function extractTextFromPDF(file) {
        try {
            const arrayBuffer = await file.arrayBuffer();
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
            
            const pdf = await pdfjsLib.getDocument(arrayBuffer).promise;
            let text = '';
            
            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const textContent = await page.getTextContent();
                text += textContent.items.map(item => item.str).join(' ') + '\n';
            }
            
            extractedText = text;
            showNotification('PDF loaded successfully!', 'success');
        } catch (error) {
            console.error('PDF extraction error:', error);
            showNotification('Error reading PDF. Please try another file.', 'error');
            removeFile();
        }
    }

    // ===== Analyze Button =====
    function initAnalyzeButton() {
        const analyzeBtn = document.getElementById('analyzeBtn');
        if (!analyzeBtn) return;

        analyzeBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            const textInput = document.getElementById('textInput');
            const text = currentTab === 'text' ? textInput?.value : extractedText;

            if (!text || text.trim().length === 0) {
                showNotification('Please enter text or upload a PDF to analyze', 'error');
                return;
            }

            // Start loading
            analyzeBtn.classList.add('loading');
            analyzeBtn.disabled = true;

            try {
                await performFullAnalysis(text);
            } finally {
                // Always stop loading
                analyzeBtn.classList.remove('loading');
                analyzeBtn.disabled = false;
            }
        });
    }

    // ===== Main Analysis Function =====
    async function performFullAnalysis(text) {
        try {
            // Step 1: Extract claims
            showNotification('Step 1/2: Extracting claims with Ollama...', 'info');

            const extractResponse = await fetch(`${API_URL}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            if (!extractResponse.ok) {
                throw new Error(`Extract failed: ${extractResponse.status}`);
            }

            const extractData = await extractResponse.json();
            console.log('Extract response:', extractData);

            if (!extractData.success || !extractData.claims?.length) {
                showNotification('No claims found in the text', 'error');
                return;
            }

            showNotification(`Found ${extractData.claims.length} claims. Verifying...`, 'info');

            // Step 2: Verify claims
            const verifyResponse = await fetch(`${API_URL}/api/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });

            if (!verifyResponse.ok) {
                throw new Error(`Verify failed: ${verifyResponse.status}`);
            }

            const verifyData = await verifyResponse.json();
            console.log('Verify response:', verifyData);

            if (!verifyData.success) {
                showNotification(verifyData.error || 'Verification failed', 'error');
                return;
            }

            // Display results
            displayVerificationResults(verifyData);
            showNotification('Analysis complete!', 'success');

        } catch (error) {
            console.error('Analysis error:', error);
            showNotification('Error: ' + error.message, 'error');
        }
    }

    // ===== Display Results =====
    function displayVerificationResults(data) {
        console.log('Displaying results:', data);

        const resultsSection = document.getElementById('resultsSection');
        if (!resultsSection) {
            console.error('Results section not found');
            return;
        }

        // Show results section
        resultsSection.classList.add('show');
        resultsSection.style.display = 'block';

        // Scroll to results after a short delay
        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);

        const summary = data.summary || {};
        const results = data.results || [];
        const trustScore = data.overall_trust_score || 0;

        // Update score circle
        updateScoreCircle(trustScore);

        // Update counts
        updateElement('verifiedCount', summary.verified || 0);
        updateElement('hallucinationCount', summary.false || 0);
        updateElement('uncertainCount', (summary.ambiguous || 0) + (summary.unverifiable || 0));

        // Update metrics
        const avgConfidence = results.length > 0
            ? Math.round(results.reduce((sum, r) => sum + (r.confidence_score || 0), 0) / results.length)
            : 0;

        updateElement('confidenceScore', avgConfidence + '%');
        updateElement('sourcesChecked', data.total_sources_checked || 0);
        updateElement('claimsFound', data.total_claims || results.length);
        updateElement('analysisTime', (data.processing_time || 0).toFixed(1) + 's');

        // Update header
        const header = document.querySelector('.results-header h3');
        if (header) {
            header.innerHTML = `<i class="fas fa-clipboard-check"></i> Verification Results (${summary.false || 0} errors found)`;
        }

        // Display findings
        displayFindings(results);

        // Setup export button
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.onclick = () => exportResults(data);
        }
    }

    function updateElement(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function updateScoreCircle(score) {
        const progress = document.getElementById('scoreProgress');
        const number = document.getElementById('scoreNumber');

        if (!progress || !number) return;

        const circumference = 2 * Math.PI * 45;

        // Add gradient if not exists
        if (!document.getElementById('scoreGradient')) {
            const svg = progress.closest('svg');
            if (svg) {
                const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
                defs.innerHTML = `
                    <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#6366f1"/>
                        <stop offset="50%" style="stop-color:#8b5cf6"/>
                        <stop offset="100%" style="stop-color:#d946ef"/>
                    </linearGradient>
                `;
                svg.insertBefore(defs, svg.firstChild);
            }
        }

        const offset = circumference - (score / 100) * circumference;
        progress.style.strokeDashoffset = offset;
        animateValue(number, 0, Math.round(score), 1500);
    }

    function displayFindings(results) {
        const list = document.getElementById('findingsList');
        if (!list) return;

        list.innerHTML = '';

        if (results.length === 0) {
            list.innerHTML = `
                <div class="finding-item" style="text-align: center; padding: 40px;">
                    <i class="fas fa-check-circle" style="font-size: 2rem; color: #22c55e; margin-bottom: 16px;"></i>
                    <p>No claims to verify.</p>
                </div>
            `;
            return;
        }

        const statusConfig = {
            verified: { class: 'verified', icon: 'fa-check-circle', label: 'Verified ✓' },
            false: { class: 'hallucination', icon: 'fa-times-circle', label: 'False ✗' },
            partially_true: { class: 'uncertain', icon: 'fa-exclamation-triangle', label: 'Partially True' },
            ambiguous: { class: 'uncertain', icon: 'fa-question-circle', label: 'Ambiguous' },
            unverifiable: { class: 'uncertain', icon: 'fa-question-circle', label: 'Unverifiable' }
        };

        results.forEach((result, index) => {
            const config = statusConfig[result.status] || statusConfig.ambiguous;
            const el = document.createElement('div');
            el.className = `finding-item ${config.class}`;
            el.style.animationDelay = `${index * 0.1}s`;

            let html = `
                <div class="finding-header">
                    <span class="finding-status">
                        <i class="fas ${config.icon}"></i> ${config.label}
                    </span>
                    <span class="finding-confidence">${result.confidence_score || 0}% confidence</span>
                </div>
                <p class="finding-text">"${escapeHtml(result.claim)}"</p>
            `;

            // Correction (only for false claims)
            if (result.correction && result.status === 'false') {
                html += `
                    <div class="finding-correction">
                        <strong><i class="fas fa-edit"></i> Correction:</strong>
                        <p>${escapeHtml(result.correction)}</p>
                    </div>
                `;
            }

            // Key facts
            if (result.key_facts?.length) {
                html += `
                    <div class="finding-facts">
                        <strong><i class="fas fa-lightbulb"></i> Key Facts:</strong>
                        <ul>${result.key_facts.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
                    </div>
                `;
            }

            // Sources
            if (result.sources?.length) {
                html += `
                    <div class="finding-sources">
                        <strong><i class="fas fa-link"></i> Sources:</strong>
                        <ul>
                            ${result.sources.slice(0, 3).map(s => `
                                <li>
                                    <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.domain)}</a>
                                    <span class="source-tier">(${escapeHtml(s.credibility)})</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                `;
            }

            // Explanation
            if (result.explanation) {
                html += `<p class="finding-reason"><i class="fas fa-info-circle"></i> ${escapeHtml(result.explanation)}</p>`;
            }

            el.innerHTML = html;
            list.appendChild(el);
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ===== Export Results =====
    function exportResults(data) {
        const summary = data.summary || {};
        const results = data.results || [];

        let report = `HALLUCINATION DETECTION REPORT
==============================
Generated: ${new Date().toLocaleString()}
Powered by: Ollama + Web Verification

SUMMARY
-------
Trust Score: ${data.overall_trust_score || 0}%
Total Claims: ${data.total_claims || results.length}
Sources Checked: ${data.total_sources_checked || 0}
Analysis Time: ${data.processing_time || 0}s

BREAKDOWN
---------
✓ Verified: ${summary.verified || 0}
✗ False: ${summary.false || 0}
⚠ Partially True: ${summary.partially_true || 0}
? Ambiguous: ${summary.ambiguous || 0}
○ Unverifiable: ${summary.unverifiable || 0}

DETAILED FINDINGS
-----------------
`;

        results.forEach((r, i) => {
            report += `\n${i + 1}. [${r.status.toUpperCase()}] (${r.confidence_score}% confidence)\n`;
            report += `   Claim: "${r.claim}"\n`;
            if (r.correction) report += `   ❌ CORRECTION: ${r.correction}\n`;
            if (r.key_facts?.length) report += `   📚 Facts: ${r.key_facts.join('; ')}\n`;
            if (r.sources?.length) {
                report += `   🔗 Sources:\n`;
                r.sources.slice(0, 3).forEach(s => {
                    report += `      - ${s.domain} (${s.credibility})\n`;
                });
            }
            report += `   Note: ${r.explanation || 'N/A'}\n`;
        });

        const blob = new Blob([report], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'hallucination-report.txt';
        a.click();
        URL.revokeObjectURL(url);

        showNotification('Report downloaded!', 'success');
    }

    // ===== Utility Functions =====
    function animateValue(element, start, end, duration) {
        let startTime = null;
        const step = (timestamp) => {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            element.textContent = Math.floor(progress * (end - start) + start);
            if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    function animateStats() {
        const stats = document.querySelectorAll('.stat-number');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const target = entry.target;
                    const endValue = parseFloat(target.dataset.count);
                    animateValue(target, 0, endValue, 2000);
                    observer.unobserve(target);
                }
            });
        }, { threshold: 0.5 });

        stats.forEach(stat => observer.observe(stat));
    }

    function showNotification(message, type = 'info') {
        // Remove existing
        document.querySelectorAll('.notification').forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;

        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };

        const colors = {
            success: 'rgba(34, 197, 94, 0.95)',
            error: 'rgba(239, 68, 68, 0.95)',
            info: 'rgba(99, 102, 241, 0.95)'
        };

        notification.innerHTML = `
            <i class="fas ${icons[type] || icons.info}"></i>
            <span>${escapeHtml(message)}</span>
        `;

        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 24px;
            background: ${colors[type] || colors.info};
            border-radius: 12px;
            color: white;
            font-weight: 500;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            animation: notifSlideIn 0.3s ease;
        `;

        // Add animation styles if needed
        if (!document.getElementById('notifStyles')) {
            const style = document.createElement('style');
            style.id = 'notifStyles';
            style.textContent = `
                @keyframes notifSlideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
                @keyframes notifSlideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'notifSlideOut 0.3s ease forwards';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    function initAnimations() {
        const elements = document.querySelectorAll('.process-step, .feature-card, .about-content');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });

        elements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.transition = 'all 0.6s ease';
            observer.observe(el);
        });
    }

    function initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter to analyze
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('analyzeBtn')?.click();
            }

            // Escape to clear
            if (e.key === 'Escape') {
                if (currentTab === 'text') {
                    document.getElementById('clearText')?.click();
                } else {
                    removeFile();
                }
            }
        });
    }

    // Handle window resize
    window.addEventListener('resize', () => {
        document.querySelectorAll('.particle').forEach(p => {
            p.style.left = Math.random() * 100 + '%';
        });
    });

})();
