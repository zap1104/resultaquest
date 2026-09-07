document.addEventListener('DOMContentLoaded', () => {
    const rawData = document.getElementById('quiz-data');
    if (!rawData) return;
    const quiz = JSON.parse(rawData.textContent);

    const wrap = document.getElementById('quiz-question-wrap');
    const progressFill = document.getElementById('quiz-progress-fill');
    const progressLabel = document.getElementById('quiz-progress-label');
    const actionBtn = document.getElementById('action-btn');

    // Feedback Sheet Elements
    const sheet = document.getElementById('quiz-feedback-sheet');
    const sheetToggle = document.getElementById('feedback-sheet-toggle');
    const sheetContinue = document.getElementById('sheet-continue-btn');

    // Result & Review Modals
    const resultSheet = document.getElementById('result-sheet');
    const reviewModal = document.getElementById('review-drawer-modal');
    const reviewContainer = document.getElementById('review-items-container');

    // Required Elements Guard
    if (!wrap || !actionBtn || !sheet) {
        console.error('Quiz initialization aborted: missing essential DOM elements.');
        return;
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value ?? '';
    }

    const letters = ['A', 'B', 'C', 'D'];
    let currentIndex = 0;
    let selectedAnswers = {};
    let gradedHistory = [];
    let isCurrentGraded = false;
    let serverReviewData = null;

    function getCookie(name) {
        const parts = (`; ${document.cookie}`).split(`; ${name}=`);
        return parts.length === 2 ? parts.pop().split(';').shift() : '';
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function escapeList(items) {
        return (items || []).map(escapeHtml).join(' • ');
    }

    function renderQuestion() {
        isCurrentGraded = false;
        const q = quiz.questions[currentIndex];
        if (!q) return;

        const isTF = q.type === 'true_false';
        const typeLabels = {
            multiple_choice: 'Multiple Choice',
            true_false: 'True or False',
            identification: 'Identification',
            enumeration: 'Enumeration'
        };

        // Reset Feedback Sheet
        sheet.classList.add('is-hidden');
        sheet.classList.remove('is-collapsed', 'is-entering', 'is-correct', 'is-partial', 'is-incorrect');

        // Restore the single action button
        actionBtn.classList.remove('is-hidden');
        actionBtn.disabled = !selectedAnswers[q.id];
        actionBtn.textContent = 'Check Answer';

        // Update Progress Bar
        const pct = Math.round((currentIndex / quiz.questions.length) * 100);
        if (progressFill) progressFill.style.width = `${pct}%`;
        setText('quiz-progress-label', `Question ${currentIndex + 1} of ${quiz.questions.length}`);

        // Generate Question Body
        let bodyHtml = '';
        if (q.type === 'multiple_choice' || q.type === 'true_false') {
            const currentPick = selectedAnswers[q.id]?.choice_id;
            bodyHtml = `
                <div class="quiz-choices ${isTF ? 'tf-layout' : ''}" id="choices-container">
                    ${q.choices.map((c, i) => {
                        let badge = letters[i] || '';
                        if (isTF) {
                            badge = c.text.trim().toLowerCase().startsWith('t') ? 'T' : 'F';
                        }
                        const isSelected = currentPick === c.id;
                        return `
                            <button type="button" class="quiz-option ${isSelected ? 'selected' : ''}" data-choice-id="${c.id}">
                                <span class="quiz-letter">${badge}</span>
                                <span>${c.text}</span>
                            </button>
                        `;
                    }).join('')}
                </div>
            `;
        } else if (q.type === 'identification') {
            const currentVal = selectedAnswers[q.id]?.text || '';
            bodyHtml = `
                <div class="quiz-typed-answer">
                    <input type="text" class="quiz-text-input" id="id-answer-input" placeholder="Type your answer..." value="${currentVal}" autocomplete="off" autocapitalize="off">
                </div>
            `;
        } else if (q.type === 'enumeration') {
            const currentItems = selectedAnswers[q.id]?.items || [];
            const count = q.expected_count || 3;
            let inputs = '';
            for (let i = 0; i < count; i++) {
                inputs += `
                    <input type="text" class="quiz-text-input enumeration-input" data-index="${i}" placeholder="Item ${i + 1}..." value="${currentItems[i] || ''}" autocomplete="off">
                `;
            }
            bodyHtml = `<div class="enumeration-inputs">${inputs}</div>`;
        }

        wrap.innerHTML = `
            <div class="quiz-tag-row">
                <span class="quiz-tag">Question ${currentIndex + 1}</span>
                <span class="quiz-tag tag-type">${typeLabels[q.type] || q.type}</span>
            </div>
            <h2 class="quiz-question-text">${q.text}</h2>
            ${bodyHtml}
        `;

        bindInputEvents(q);
    }

    function bindInputEvents(q) {
        wrap.querySelectorAll('.quiz-option').forEach(btn => {
            btn.addEventListener('click', () => {
                if (isCurrentGraded) return;
                const cId = Number(btn.dataset.choiceId);
                selectedAnswers[q.id] = { choice_id: cId };
                wrap.querySelectorAll('.quiz-option').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                actionBtn.disabled = false;
            });
        });

        const idInput = wrap.querySelector('#id-answer-input');
        if (idInput) {
            idInput.addEventListener('input', () => {
                const val = idInput.value.trim();
                if (val) {
                    selectedAnswers[q.id] = { text: val };
                    actionBtn.disabled = false;
                } else {
                    delete selectedAnswers[q.id];
                    actionBtn.disabled = true;
                }
            });
            idInput.addEventListener('focus', () => {
                setTimeout(() => idInput.scrollIntoView({ behavior: 'smooth', block: 'center' }), 280);
            });
        }

        const enumInputs = wrap.querySelectorAll('.enumeration-input');
        if (enumInputs.length) {
            enumInputs.forEach(input => {
                input.addEventListener('input', () => {
                    const items = Array.from(enumInputs).map(inp => inp.value.trim());
                    const hasAny = items.some(Boolean);
                    if (hasAny) {
                        selectedAnswers[q.id] = { items };
                        actionBtn.disabled = false;
                    } else {
                        delete selectedAnswers[q.id];
                        actionBtn.disabled = true;
                    }
                });
                input.addEventListener('focus', () => {
                    setTimeout(() => input.scrollIntoView({ behavior: 'smooth', block: 'center' }), 280);
                });
            });
        }
    }

    async function handleCheckAnswer() {
        if (isCurrentGraded) return;
        const q = quiz.questions[currentIndex];
        const isLast = currentIndex === quiz.questions.length - 1;
        const answerPayload = selectedAnswers[q.id];

        actionBtn.disabled = true;
        actionBtn.textContent = 'Verifying...';

        try {
            const res = await fetch(quiz.checkUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ question_id: q.id, answer: answerPayload })
            });

            if (!res.ok) throw new Error('Grading check failed');
            const data = await res.json();
            isCurrentGraded = true;
            gradedHistory.push({ question: q, userPick: answerPayload, result: data });

            if (q.type === 'multiple_choice' || q.type === 'true_false') {
                wrap.querySelectorAll('.quiz-option').forEach(btn => {
                    btn.classList.add('locked');
                    const cId = Number(btn.dataset.choiceId);
                    if (cId === data.correct_choice_id) btn.classList.add('is-correct');
                    if (cId === answerPayload.choice_id && !data.is_correct) btn.classList.add('is-incorrect');
                    if (cId !== data.correct_choice_id && cId !== answerPayload.choice_id) btn.classList.add('is-dimmed');
                });
            } else if (q.type === 'identification') {
                const idInput = wrap.querySelector('#id-answer-input');
                if (idInput) {
                    idInput.disabled = true;
                    idInput.classList.add(data.is_correct ? 'is-correct' : 'is-incorrect');
                }
            } else if (q.type === 'enumeration') {
                wrap.querySelectorAll('.enumeration-input').forEach(inp => inp.disabled = true);
            }

            actionBtn.classList.add('is-hidden');

            const earned = Number(data.earned_points ?? (data.is_correct ? 1 : 0));
            const maxPts = Number(data.maximum_points ?? q.max_points ?? 1);
            const feedbackState = earned === maxPts ? 'is-correct' : (earned > 0 ? 'is-partial' : 'is-incorrect');

            sheet.className = `quiz-feedback-sheet ${feedbackState}`;
            setText('sheet-status-pill', feedbackState === 'is-correct' ? 'Correct' : (feedbackState === 'is-partial' ? 'Partially Correct' : 'Needs Review'));
            setText('sheet-points-pill', `${earned} / ${maxPts} Pt${maxPts === 1 ? '' : 's'}`);
            setText('sheet-title-text', feedbackState === 'is-correct' ? 'Nicely Done!' : (feedbackState === 'is-partial' ? 'Almost There' : 'Concept Review'));
            setText('sheet-expl-text', data.explanation || '');

            let extraHtml = '';
            if (data.canonical_answer) {
                extraHtml += `<div>Accepted Term: <strong>${data.canonical_answer}</strong></div>`;
            }
            if (data.matched_items && data.matched_items.length) {
                extraHtml += `<div>Matched: <strong>${data.matched_items.join(', ')}</strong></div>`;
            }
            if (data.missing_items && data.missing_items.length) {
                extraHtml += `<div style="color: var(--gold);">Missing: <strong>${data.missing_items.join(', ')}</strong></div>`;
            }
            const extraEl = document.getElementById('sheet-extra-wrap');
            if (extraEl) extraEl.innerHTML = extraHtml;

            if (sheetContinue) {
                sheetContinue.innerHTML = isLast ? 'Complete Quiz &rarr;' : 'Next Question &rarr;';
            }

            sheet.classList.remove('is-hidden');
            sheet.classList.add('is-entering');
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    sheet.classList.remove('is-entering');
                });
            });

            if (window.innerWidth > 640) {
                sheet.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }

        } catch (err) {
            console.error('Answer check error:', err);
            actionBtn.disabled = false;
            actionBtn.textContent = 'Check Answer';
        }
    }

    actionBtn.addEventListener('click', handleCheckAnswer);

    sheetContinue?.addEventListener('click', () => {
        if (currentIndex < quiz.questions.length - 1) {
            currentIndex++;
            renderQuestion();
        } else {
            finalizeQuiz();
        }
    });

    sheetToggle?.addEventListener('click', () => {
        sheet.classList.toggle('is-collapsed');
    });

    let touchStartY = null;
    sheet.addEventListener('touchstart', (e) => {
        if (!e.target.closest('.feedback-sheet-handle')) return;
        touchStartY = e.touches[0].clientY;
    }, { passive: true });

    sheet.addEventListener('touchend', (e) => {
        if (touchStartY === null) return;
        const diff = e.changedTouches[0].clientY - touchStartY;
        if (diff > 45) {
            sheet.classList.add('is-collapsed');
        } else if (diff < -45) {
            sheet.classList.remove('is-collapsed');
        }
        touchStartY = null;
    }, { passive: true });

    async function finalizeQuiz() {
        sheet.classList.add('is-hidden');
        wrap.innerHTML = `
            <div style="text-align: center; padding: 70px 20px;">
                <div style="font-size: 2.2rem; margin-bottom: 12px;">📝</div>
                <h2 style="margin: 0; font-size: 1.35rem; color: var(--ink);">Evaluating Learning Path...</h2>
                <p style="margin: 6px 0 0; color: var(--muted); font-size: 0.9rem;">Compiling answer review and topic anchors.</p>
            </div>
        `;

        try {
            const res = await fetch(quiz.submitUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ answers: selectedAnswers })
            });

            if (!res.ok) throw new Error('Evaluation submission failed');
            const data = await res.json();
            serverReviewData = data;

            setText('sheet-score', `${data.score} / ${data.maximum_score}`);
            setText('sheet-percentage', `${data.percentage}%`);
            setText('sheet-xp', `+${data.xp_earned} XP`);

            const passBadge = document.getElementById('result-pass-badge');
            if (passBadge) {
                passBadge.textContent = data.passed ? 'Assessment Passed' : 'Review Suggested';
                passBadge.className = `result-badge ${data.passed ? 'passed' : 'retry'}`;
            }

            if (resultSheet) {
                resultSheet.classList.add('open');
                resultSheet.scrollIntoView({ behavior: 'smooth' });
            }
        } catch (err) {
            console.error('Finalize error:', err);
            wrap.innerHTML = `
                <div style="text-align: center; padding: 50px 20px;">
                    <p style="color: var(--danger);">Failed to save assessment results.</p>
                    <button type="button" class="btn btn-secondary" onclick="location.reload()">Retry</button>
                </div>
            `;
        }
    }

    function buildReviewModal() {
        if (!reviewContainer || !serverReviewData || !serverReviewData.review_items) return;
        const reviewUrlBase = document.getElementById('return-chapter-btn')?.getAttribute('href') || '';

        reviewContainer.innerHTML = serverReviewData.review_items.map((item, idx) => {
            const statusClass = ['correct', 'partial', 'incorrect'].includes(item.result_state) 
                ? item.result_state 
                : 'incorrect';
            
            const statusLabel = statusClass === 'correct' 
                ? 'Correct' 
                : (statusClass === 'partial' ? 'Partially Correct' : 'Needs Review');
            
            const anchor = escapeHtml(item.review_anchor || 'overview');
            const topicHref = `${reviewUrlBase}#${anchor}`;

            let detailHtml = '';

            if (item.question_type === 'multiple_choice' || item.question_type === 'true_false') {
                detailHtml = `
                    <div class="review-data-row">
                        <span>Submitted answer:</span>
                        <strong class="${item.is_correct ? 'text-accent' : 'text-danger'}">${escapeHtml(item.submitted_text || 'No answer provided')}</strong>
                    </div>
                    ${!item.is_correct ? `
                        <div class="review-data-row">
                            <span>Correct answer:</span>
                            <strong class="text-accent">${escapeHtml(item.correct_text)}</strong>
                        </div>
                    ` : ''}
                `;
            } else if (item.question_type === 'identification') {
                detailHtml = `
                    <div class="review-data-row">
                        <span>Submitted response:</span>
                        <strong class="${item.is_correct ? 'text-accent' : 'text-danger'}">${escapeHtml(item.submitted_text || 'No answer provided')}</strong>
                    </div>
                    ${!item.is_correct ? `
                        <div class="review-data-row">
                            <span>Accepted term:</span>
                            <strong class="text-accent">${escapeHtml(item.canonical_text)}</strong>
                        </div>
                        ${item.accepted_variants && item.accepted_variants.length ? `
                            <div class="review-data-row">
                                <span>Accepted variants:</span>
                                <span>${escapeList(item.accepted_variants)}</span>
                            </div>
                        ` : ''}
                    ` : ''}
                `;
            } else if (item.question_type === 'enumeration') {
                detailHtml = `
                    <div class="review-data-block">
                        <div class="review-data-row">
                            <span>Submitted items:</span>
                            <span>${escapeList(item.submitted_items)}</span>
                        </div>
                        ${item.matched_items && item.matched_items.length ? `
                            <div class="review-data-row text-accent">
                                <span>Matched items:</span>
                                <strong>${escapeList(item.matched_items)}</strong>
                            </div>
                        ` : ''}
                        ${item.missing_items && item.missing_items.length ? `
                            <div class="review-data-row text-danger">
                                <span>Missing items:</span>
                                <strong>${escapeList(item.missing_items)}</strong>
                            </div>
                        ` : ''}
                        <div class="review-data-row">
                            <span>Expected full list:</span>
                            <span>${escapeList(item.canonical_items)}</span>
                        </div>
                        ${item.order_matters ? '<small class="review-hint">Order of enumeration was graded strictly.</small>' : ''}
                    </div>
                `;
            }

            return `
                <article class="review-item-card ${statusClass}">
                    <div class="review-item-header">
                        <div class="review-item-status-group">
                            <span class="feedback-status-pill">${statusLabel}</span>
                            <span class="quiz-tag">${escapeHtml(item.question_type.replace('_', ' '))}</span>
                        </div>
                        <span class="feedback-points-pill">${item.earned_points} / ${item.maximum_points} Pt${item.maximum_points === 1 ? '' : 's'}</span>
                    </div>

                    <h4 class="review-item-qtext">Q${idx + 1}. ${escapeHtml(item.prompt)}</h4>

                    <div class="review-answer-block">
                        ${detailHtml}
                    </div>

                    ${item.explanation ? `
                        <div class="review-expl-box">
                            <strong class="review-expl-label">Explanation</strong>
                            <p class="review-expl-text">${escapeHtml(item.explanation)}</p>
                        </div>
                    ` : ''}
                </article>
            `;
        }).join('');
    }

    document.getElementById('open-review-btn')?.addEventListener('click', () => {
        buildReviewModal();
        if (reviewModal) {
            reviewModal.hidden = false;
            reviewModal.classList.add('is-active');
            document.body.classList.add('modal-open');
        }
    });

    function closeReviewModal() {
        if (reviewModal) {
            reviewModal.hidden = true;
            reviewModal.classList.remove('is-active');
            document.body.classList.remove('modal-open');
        }
    }

    document.getElementById('close-review-btn')?.addEventListener('click', closeReviewModal);
    document.getElementById('back-to-results-btn')?.addEventListener('click', closeReviewModal);

    // ================= KEYBOARD SHORTCUTS =================
    document.addEventListener('keydown', (event) => {
        if (event.repeat) return;

        // Disengage if result summary or review modal is active
        if (resultSheet?.classList.contains('open')) return;
        if (reviewModal && !reviewModal.hidden) return;

        const question = quiz.questions[currentIndex];
        if (!question) return;

        const isSpace = event.key === ' ' || event.code === 'Space';
        const isEnter = event.key === 'Enter';

        if (!isSpace && !isEnter) return;

        const activeEl = document.activeElement;
        const isTyping = Boolean(activeEl?.matches('input, textarea, select, [contenteditable="true"]'));
        const isChoiceQuestion = question.type === 'multiple_choice' || question.type === 'true_false';

        // 1. Before Grading (Submitting Answers)
        if (!isCurrentGraded) {
            // Space submits only Multiple Choice and True/False
            if (isSpace) {
                if (isChoiceQuestion && !isTyping && !actionBtn.disabled) {
                    event.preventDefault();
                    event.stopPropagation();
                    if (activeEl && typeof activeEl.blur === 'function') activeEl.blur();
                    handleCheckAnswer();
                }
                return;
            }

            // Enter submits when ready (avoids interrupting typing in Enumeration)
            if (isEnter) {
                if (question.type === 'enumeration' && isTyping) {
                    return;
                }
                if (!actionBtn.disabled) {
                    event.preventDefault();
                    event.stopPropagation();
                    if (isTyping && activeEl) activeEl.blur();
                    handleCheckAnswer();
                }
            }
            return;
        }

        // 2. After Grading (Drawer open: Next Question)
        if (isSpace || isEnter) {
            if (isTyping) return;
            event.preventDefault();
            event.stopPropagation();
            if (activeEl && typeof activeEl.blur === 'function') activeEl.blur();
            sheetContinue?.click();
        }
    });

    // ================= REVIEW MODAL NAVIGATION & DISMISS =================
    const urlParams = new URLSearchParams(window.location.search);
    const isReviewMode = urlParams.get('view') === 'review';
    const chapterReviewUrl = document.getElementById('quiz-exit-link')?.getAttribute('href') || '';
    const backToScoreBtn = document.getElementById('back-to-results-btn');

    function exitReviewDrawer() {
        if (isReviewMode && chapterReviewUrl) {
            window.location.href = chapterReviewUrl;
        } else {
            if (reviewModal) {
                reviewModal.hidden = true;
                reviewModal.classList.remove('is-active');
                document.body.classList.remove('modal-open');
            }
        }
    }

    document.getElementById('close-review-btn')?.addEventListener('click', exitReviewDrawer);
    backToScoreBtn?.addEventListener('click', exitReviewDrawer);

    // Clicking outside modal content on backdrop also dismisses properly
    reviewModal?.addEventListener('click', (e) => {
        if (e.target === reviewModal) exitReviewDrawer();
    });

    // ================= VIEW ROUTING (?view=review vs New Quiz) =================
    let preloadedReview = null;
    const reviewDataEl = document.getElementById('latest-review-data');
    if (reviewDataEl && reviewDataEl.textContent) {
        try {
            preloadedReview = JSON.parse(reviewDataEl.textContent);
        } catch (e) {
            console.error('Failed to parse preloaded review data:', e);
        }
    }

    if (isReviewMode && preloadedReview && preloadedReview.review_items && preloadedReview.review_items.length > 0) {
        serverReviewData = preloadedReview;

        // 1. Hide quiz-runner and score sheet so background stays completely blank
        actionBtn.classList.add('is-hidden');
        if (progressFill && progressFill.parentElement) {
            progressFill.parentElement.style.display = 'none';
        }
        setText('quiz-progress-label', '');

        // 2. Hide "Back to Score" button in review mode since user came from Chapter Review
        if (backToScoreBtn) {
            backToScoreBtn.style.display = 'none';
        }

        // 3. Immediately launch Answer Review drawer
        buildReviewModal();
        if (reviewModal) {
            reviewModal.hidden = false;
            reviewModal.classList.add('is-active');
            document.body.classList.add('modal-open');
        }
    } else if (quiz.questions && quiz.questions.length > 0) {
        renderQuestion();
    }
});