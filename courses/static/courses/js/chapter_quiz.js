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

    // Defensive textContent helper to prevent TypeError on null elements
    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value ?? '';
    }

    const letters = ['A', 'B', 'C', 'D'];
    let currentIndex = 0;
    let selectedAnswers = {}; // Preserves backend schema: { choice_id } | { text } | { items }
    let gradedHistory = [];
    let isCurrentGraded = false;

    function getCookie(name) {
        const parts = (`; ${document.cookie}`).split(`; ${name}=`);
        return parts.length === 2 ? parts.pop().split(';').shift() : '';
    }

    function renderQuestion() {
        isCurrentGraded = false;
        const q = quiz.questions[currentIndex];
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

        // Generate Question Body without any extra action buttons
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
        // Multiple Choice / True-False
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

        // Identification
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

        // Enumeration
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

            // Lock in-page options and highlight results
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

            // Hide the Check Answer button with utility class
            actionBtn.classList.add('is-hidden');

            // Determine Partial vs Full Credit
            const earned = Number(data.earned_points ?? (data.is_correct ? 1 : 0));
            const maxPts = Number(data.maximum_points ?? q.max_points ?? 1);
            const feedbackState = earned === maxPts ? 'is-correct' : (earned > 0 ? 'is-partial' : 'is-incorrect');

            sheet.className = `quiz-feedback-sheet ${feedbackState}`;
            setText('sheet-status-pill', feedbackState === 'is-correct' ? 'Correct' : (feedbackState === 'is-partial' ? 'Partially Correct' : 'Needs Review'));
            setText('sheet-points-pill', `${earned} / ${maxPts} Pt${maxPts === 1 ? '' : 's'}`);
            setText('sheet-title-text', feedbackState === 'is-correct' ? 'Nicely Done!' : (feedbackState === 'is-partial' ? 'Almost There' : 'Concept Review'));
            setText('sheet-expl-text', data.explanation || '');

            // Extra details for identification & enumeration
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

            // Slide up feedback sheet
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

    // Touch swipe handling for mobile bottom sheet
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
                <div style="font-size: 2.2rem; margin-bottom: 8px;">⚡</div>
                <h2 style="margin: 0; font-size: 1.4rem;">Finalizing Assessment...</h2>
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

            const data = await res.json();
            setText('sheet-score', `${data.score}/${data.total_questions}`);
            setText('sheet-percentage', `${data.percentage}%`);
            setText('sheet-xp', `+${data.xp_earned}`);
            setText('sheet-level', data.new_level);
            setText('sheet-streak', data.new_streak);

            if (resultSheet) resultSheet.classList.add('open');
        } catch (err) {
            console.error('Finalize error:', err);
        }
    }

    document.getElementById('open-review-btn')?.addEventListener('click', () => {
        buildReviewModal();
        if (reviewModal) reviewModal.classList.add('is-active');
    });

    document.getElementById('close-review-btn')?.addEventListener('click', () => {
        if (reviewModal) reviewModal.classList.remove('is-active');
    });

    document.getElementById('back-to-results-btn')?.addEventListener('click', () => {
        if (reviewModal) reviewModal.classList.remove('is-active');
    });

    function buildReviewModal() {
        if (!reviewContainer) return;
        reviewContainer.innerHTML = gradedHistory.map((item, idx) => {
            const earned = Number(item.result.earned_points ?? (item.result.is_correct ? 1 : 0));
            const maxPts = Number(item.result.maximum_points ?? item.question.max_points ?? 1);
            const state = earned === maxPts ? 'is-correct' : (earned > 0 ? 'is-partial' : 'is-incorrect');

            return `
                <div class="review-item-card ${state}">
                    <div class="review-item-header">
                        <span>Question ${idx + 1}</span>
                        <span>${earned} / ${maxPts} Pt${maxPts === 1 ? '' : 's'}</span>
                    </div>
                    <p class="review-item-qtext">${item.question.text}</p>
                    <div class="review-answer-block">
                        <div><strong>Feedback:</strong> ${item.result.explanation || 'No additional note.'}</div>
                        ${item.result.canonical_answer ? `<div><strong>Accepted Answer:</strong> ${item.result.canonical_answer}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    // Initialize first question
    renderQuestion();
});