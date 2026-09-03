// Simple client-side quiz runner — Duolingo/Kahoot-style one-question-at-a-time flow.
// No backend scoring yet; this is a UI-only starting point.
(function () {
    const data = JSON.parse(document.getElementById('quiz-data').textContent);
    const questions = data.questions || [];

    const wrap = document.getElementById('quiz-question-wrap');
    const progressFill = document.getElementById('quiz-progress-fill');
    const resultPanel = document.getElementById('quiz-result');
    const scoreLine = document.getElementById('quiz-score');

    let current = 0;
    let score = 0;
    let answered = false;

    function renderQuestion() {
        const q = questions[current];
        progressFill.style.width = `${(current / questions.length) * 100}%`;
        answered = false;

        const choiceButtons = q.choices.map((choice, i) => `
            <button type="button" class="quiz-choice-btn" data-index="${i}">${choice.text}</button>
        `).join('');

        wrap.innerHTML = `
            <div class="quiz-question">
                <h2>${q.text}</h2>
                <div class="quiz-feedback" id="quiz-feedback"></div>
                <div class="quiz-choices">${choiceButtons}</div>
            </div>
        `;

        wrap.querySelectorAll('.quiz-choice-btn').forEach((btn) => {
            btn.addEventListener('click', () => handleAnswer(btn, q));
        });
    }

    function handleAnswer(btn, question) {
        if (answered) return;
        answered = true;

        const index = Number(btn.dataset.index);
        const isCorrect = question.choices[index].isCorrect;
        const feedback = document.getElementById('quiz-feedback');

        wrap.querySelectorAll('.quiz-choice-btn').forEach((b, i) => {
            b.disabled = true;
            if (question.choices[i].isCorrect) b.classList.add('correct');
        });

        if (isCorrect) {
            score += 1;
            btn.classList.add('correct');
            feedback.textContent = 'Correct! +10 XP';
            feedback.className = 'quiz-feedback correct';
        } else {
            btn.classList.add('incorrect');
            feedback.textContent = 'Not quite — check the highlighted answer.';
            feedback.className = 'quiz-feedback incorrect';
        }

        setTimeout(() => {
            current += 1;
            if (current < questions.length) {
                renderQuestion();
            } else {
                finishQuiz();
            }
        }, 1100);
    }

    function finishQuiz() {
        progressFill.style.width = '100%';
        wrap.innerHTML = '';
        resultPanel.classList.remove('hidden');
        scoreLine.textContent = `You scored ${score} / ${questions.length} — +${score * 10} XP`;
    }

    if (questions.length) {
        renderQuestion();
    }
})();
