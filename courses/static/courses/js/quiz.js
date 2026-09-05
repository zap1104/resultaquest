// Focus Mode quiz runner — 2x2 answer grid, select-then-confirm flow.
// Grading remains entirely server-side in one batch request; no
// per-question correctness is ever exposed before submission.
document.addEventListener('DOMContentLoaded', () => {
    const dataElement = document.getElementById('quiz-data');
    if (!dataElement) return;

    const quizData = JSON.parse(dataElement.textContent);
    const chapterId = quizData.chapterId;
    const questions = quizData.questions;
    const chapterTitle = document.querySelector('.quiz-focus-header')?.dataset.chapterTitle || '';

    let currentIndex = 0;
    let selectedChoiceId = null;
    const userAnswers = {};

    const questionWrap = document.getElementById('quiz-question-wrap');
    const progressFill = document.getElementById('quiz-progress-fill');
    const progressLabel = document.getElementById('quiz-progress-label');
    const resultSheet = document.getElementById('result-sheet');

    const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

    function updateProgress() {
        const pct = (currentIndex / questions.length) * 100;
        progressFill.style.width = `${pct}%`;
        progressLabel.textContent = `Question ${Math.min(currentIndex + 1, questions.length)} of ${questions.length}`;
    }

    function renderQuestion() {
        selectedChoiceId = null;
        questionWrap.innerHTML = '';

        if (currentIndex >= questions.length) {
            submitQuizToServer();
            return;
        }

        const q = questions[currentIndex];

        const heading = document.createElement('div');
        heading.className = 'quiz-question-text';
        heading.textContent = q.text;
        questionWrap.appendChild(heading);

        const choiceContainer = document.createElement('div');
        choiceContainer.className = 'quiz-choices';

        q.choices.forEach((choice, i) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'quiz-option';
            btn.dataset.choiceId = choice.id;
            btn.innerHTML = `
                <span class="quiz-letter">${LETTERS[i] || '?'}</span>
                <span>${choice.text}</span>
            `;
            btn.addEventListener('click', () => selectChoice(btn, choice.id));
            choiceContainer.appendChild(btn);
        });

        questionWrap.appendChild(choiceContainer);

        const confirmBtn = document.createElement('button');
        confirmBtn.type = 'button';
        confirmBtn.id = 'quiz-confirm-btn';
        confirmBtn.className = 'btn btn-primary btn-chunky quiz-confirm-btn';
        confirmBtn.textContent = currentIndex === questions.length - 1 ? 'Finish Quiz' : 'Next';
        confirmBtn.disabled = true;
        confirmBtn.addEventListener('click', () => confirmAnswer(q.id));
        questionWrap.appendChild(confirmBtn);

        updateProgress();
    }

    function selectChoice(clickedBtn, choiceId) {
        selectedChoiceId = choiceId;
        questionWrap.querySelectorAll('.quiz-option').forEach((b) => {
            b.classList.toggle('selected', b === clickedBtn);
        });
        document.getElementById('quiz-confirm-btn').disabled = false;
    }

    function confirmAnswer(questionId) {
        if (selectedChoiceId === null) return;
        userAnswers[questionId] = selectedChoiceId;
        currentIndex += 1;
        renderQuestion();
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    async function submitQuizToServer() {
        progressFill.style.width = '100%';
        progressLabel.textContent = 'Grading...';
        questionWrap.innerHTML = `
            <div class="quiz-submitted-anchor">
                <div class="quiz-submitted-check">✅</div>
                <div class="quiz-submitted-title">Quiz Submitted</div>
                <p class="quiz-submitted-sub">${chapterTitle}</p>
                <p class="quiz-submitted-status">Calculating results...</p>
            </div>
        `;

        try {
            const response = await fetch(`/chapters/${chapterId}/quiz/submit/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ answers: userAnswers }),
            });

            if (!response.ok) throw new Error(`Server responded with ${response.status}`);

            const result = await response.json();
            setTimeout(() => showResults(result), 400);
        } catch (err) {
            questionWrap.innerHTML = '<p style="text-align:center; color:var(--danger); margin-top:60px;">Something went wrong grading your quiz. Please try again.</p>';
            console.error('Quiz submission failed:', err);
        }
    }

    function showResults(data) {
        progressLabel.textContent = '';
        document.getElementById('sheet-score').textContent = `${data.score}/${data.total_questions}`;
        document.getElementById('sheet-xp').textContent = `+${data.xp_earned}`;
        document.getElementById('sheet-level').textContent = data.new_level;
        document.getElementById('sheet-streak').textContent = data.new_streak;
        resultSheet.classList.add('open');
    }

    if (questions.length) {
        renderQuestion();
    }
});