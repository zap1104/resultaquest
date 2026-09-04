// Server-graded quiz runner. Answers are collected locally as the user
// clicks through, then submitted in one batch to submit_quiz(). The
// correct/incorrect breakdown and XP total only ever come from the
// server response — nothing about correctness is ever present in the
// page source before that point.
(function () {
    const data = JSON.parse(document.getElementById('quiz-data').textContent);
    const questions = data.questions || [];
    const chapterId = data.chapterId;

    const wrap = document.getElementById('quiz-question-wrap');
    const progressFill = document.getElementById('quiz-progress-fill');
    const resultPanel = document.getElementById('quiz-result');
    const scoreLine = document.getElementById('quiz-score');

    let current = 0;
    let answered = false;
    const answers = {}; // { questionId: choiceId }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function renderQuestion() {
        const q = questions[current];
        progressFill.style.width = `${(current / questions.length) * 100}%`;
        answered = false;

        const choiceButtons = q.choices.map((choice) => `
            <button type="button" class="quiz-choice-btn" data-choice-id="${choice.id}">${choice.text}</button>
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

        answers[question.id] = Number(btn.dataset.choiceId);

        const feedback = document.getElementById('quiz-feedback');
        wrap.querySelectorAll('.quiz-choice-btn').forEach((b) => { b.disabled = true; });
        btn.classList.add('selected');
        feedback.textContent = 'Answer locked in.';
        feedback.className = 'quiz-feedback';

        setTimeout(() => {
            current += 1;
            if (current < questions.length) {
                renderQuestion();
            } else {
                submitQuiz();
            }
        }, 500);
    }

    async function submitQuiz() {
        progressFill.style.width = '100%';
        wrap.innerHTML = '<p class="hint">Grading your quiz...</p>';

        try {
            const response = await fetch(`/chapters/${chapterId}/quiz/submit/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ answers }),
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }

            const result = await response.json();
            showResults(result);
        } catch (err) {
            wrap.innerHTML = `<p class="quiz-feedback incorrect">Something went wrong submitting your quiz. Please try again.</p>`;
            console.error('Quiz submission failed:', err);
        }
    }

    function showResults(result) {
        wrap.innerHTML = '';
        resultPanel.classList.remove('hidden');
        scoreLine.textContent =
            `You scored ${result.score} / ${result.total_questions} — +${result.xp_earned} XP ` +
            `(Now Lv. ${result.new_level}, ${result.new_total_xp} total XP)`;
    }

    if (questions.length) {
        renderQuestion();
    }
})();