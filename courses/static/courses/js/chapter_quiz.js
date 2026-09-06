document.addEventListener('DOMContentLoaded', () => {
    const dataElement = document.getElementById('quiz-data');
    if (!dataElement) return;

    const quiz = JSON.parse(dataElement.textContent);
    const questions = quiz.questions || [];
    const questionWrap = document.getElementById('quiz-question-wrap');
    const progressFill = document.getElementById('quiz-progress-fill');
    const progressLabel = document.getElementById('quiz-progress-label');
    const resultSheet = document.getElementById('result-sheet');
    const userAnswers = {};
    let currentIndex = 0;
    let currentFeedback = null;

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        return parts.length === 2 ? parts.pop().split(';').shift() : '';
    }

    function addText(parent, className, text) {
        const element = document.createElement('div');
        element.className = className;
        element.textContent = text;
        parent.appendChild(element);
        return element;
    }

    function renderAnswerReview(results) {
        const review = document.getElementById('answer-review');
        review.innerHTML = '';
        addText(review, 'feedback-title', 'Answer Review');
        results.forEach((result, index) => {
            const card = document.createElement('div');
            card.className = 'answer-review-card';
            const status = result.is_correct ? 'Correct' : 'Needs review';
            addText(card, '', `${index + 1}. ${status} - ${result.earned_points}/${result.maximum_points} points`);
            if (result.correct_choice_text) {
                addText(card, 'review-copy', `Correct choice: ${result.correct_choice_text}`);
            } else if (result.canonical_answer) {
                addText(card, 'review-copy', `Accepted answer: ${result.canonical_answer}`);
            } else if (result.question_type === 'enumeration') {
                addText(card, 'review-copy', `Matched: ${(result.matched_items || []).join(', ') || 'None'}`);
                if (result.missing_items?.length) {
                    addText(card, 'review-copy', `Missing: ${result.missing_items.join(', ')}`);
                }
            }
            addText(card, 'review-copy', result.explanation || 'Review the lesson for this concept.');
            review.appendChild(card);
        });
    }

    function updateProgress(complete = false) {
        const percentage = complete ? 100 : Math.round((currentIndex / questions.length) * 100);
        progressFill.style.width = `${percentage}%`;
        progressLabel.textContent = complete
            ? 'Quiz complete'
            : `Question ${currentIndex + 1} of ${questions.length}`;
    }

    function renderQuestion() {
        const question = questions[currentIndex];
        currentFeedback = null;
        questionWrap.innerHTML = '';
        updateProgress();

        const tags = document.createElement('div');
        tags.className = 'quiz-tag-row';
        addText(tags, 'quiz-tag', `Question ${currentIndex + 1}`);
        addText(tags, 'quiz-tag tag-type', {
            multiple_choice: 'Multiple Choice',
            true_false: 'True or False',
            identification: 'Identification',
            enumeration: 'Enumeration',
        }[question.type] || 'Assessment');
        questionWrap.appendChild(tags);
        addText(questionWrap, 'quiz-question-text', question.text);

        const answerMount = document.createElement('div');
        answerMount.className = question.type === 'enumeration' ? 'quiz-typed-answer enumeration-inputs' : 'quiz-typed-answer';
        questionWrap.appendChild(answerMount);

        if (question.type === 'multiple_choice' || question.type === 'true_false') {
            const choices = document.createElement('div');
            choices.className = `quiz-choices ${question.type === 'true_false' ? 'tf-layout' : ''}`;
            question.choices.forEach((choice, index) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'quiz-option';
                button.dataset.choiceId = choice.id;
                const letter = document.createElement('span');
                letter.className = 'quiz-letter';
                letter.textContent = question.type === 'true_false'
                    ? choice.text.trim().charAt(0).toUpperCase()
                    : ['A', 'B', 'C', 'D'][index] || '?';
                button.append(letter);
                const label = document.createElement('span');
                label.textContent = choice.text;
                button.append(label);
                button.addEventListener('click', () => {
                    choices.querySelectorAll('.quiz-option').forEach(option => option.classList.remove('selected'));
                    button.classList.add('selected');
                    userAnswers[question.id] = { choice_id: choice.id };
                    action.disabled = false;
                });
                choices.appendChild(button);
            });
            answerMount.appendChild(choices);
        } else if (question.type === 'identification') {
            const input = document.createElement('input');
            input.className = 'quiz-text-input';
            input.type = 'text';
            input.placeholder = 'Type your answer';
            input.addEventListener('input', () => {
                userAnswers[question.id] = { text: input.value };
                action.disabled = !input.value.trim();
            });
            answerMount.appendChild(input);
        } else if (question.type === 'enumeration') {
            const count = Math.max(question.expected_count || 2, 2);
            const inputs = [];
            for (let index = 0; index < count; index += 1) {
                const input = document.createElement('input');
                input.className = 'quiz-text-input';
                input.type = 'text';
                input.placeholder = `Answer ${index + 1}`;
                input.addEventListener('input', () => {
                    userAnswers[question.id] = { items: inputs.map(item => item.value) };
                    action.disabled = !inputs.some(item => item.value.trim());
                });
                inputs.push(input);
                answerMount.appendChild(input);
            }
        }

        const feedbackMount = document.createElement('div');
        feedbackMount.className = 'quiz-feedback-mount';
        questionWrap.appendChild(feedbackMount);

        const action = document.createElement('button');
        action.type = 'button';
        action.className = 'btn btn-primary btn-chunky quiz-action-btn';
        action.textContent = 'Check Answer';
        action.disabled = true;
        action.addEventListener('click', async () => {
            if (!currentFeedback) {
                await checkAnswer(question, action, feedbackMount, answerMount);
            } else if (currentIndex === questions.length - 1) {
                await submitQuiz();
            } else {
                currentIndex += 1;
                renderQuestion();
            }
        });
        questionWrap.appendChild(action);
    }

    async function checkAnswer(question, action, feedbackMount, answerMount) {
        action.disabled = true;
        try {
            const response = await fetch(quiz.checkUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    question_id: question.id,
                    answer: userAnswers[question.id] || {},
                }),
            });
            const feedback = await response.json();
            if (!response.ok) throw new Error(feedback.error || 'Answer check failed');
            currentFeedback = feedback;
            renderFeedback(question, feedback, feedbackMount, answerMount);
            action.textContent = currentIndex === questions.length - 1 ? 'Complete Quiz' : 'Next Question';
            action.disabled = false;
        } catch (error) {
            feedbackMount.textContent = error.message;
            action.disabled = false;
        }
    }

    function renderFeedback(question, feedback, mount, answerMount) {
        const box = document.createElement('div');
        box.className = `quiz-feedback-box ${feedback.is_correct ? 'correct' : 'incorrect'}`;
        addText(box, 'feedback-eyebrow', feedback.is_correct ? 'Correct' : 'Review This');
        if (feedback.correct_choice_text) addText(box, 'feedback-title', feedback.correct_choice_text);
        if (feedback.canonical_answer) addText(box, 'feedback-title', feedback.canonical_answer);
        if (question.type === 'enumeration') {
            addText(box, 'feedback-title', `${feedback.earned_points} of ${feedback.maximum_points} identified`);
            if (feedback.missing_items && feedback.missing_items.length) {
                addText(box, 'feedback-text', `Missing: ${feedback.missing_items.join(', ')}`);
            }
        }
        addText(box, 'feedback-text', feedback.explanation || question.explanation || 'Review this concept before continuing.');
        mount.innerHTML = '';
        mount.appendChild(box);

        answerMount.querySelectorAll('button, input').forEach(element => {
            element.disabled = true;
        });
        if (question.type === 'multiple_choice' || question.type === 'true_false') {
            answerMount.querySelectorAll('.quiz-option').forEach(button => {
                const choiceId = Number(button.dataset.choiceId);
                if (choiceId === feedback.correct_choice_id) button.classList.add('is-correct');
                else if (choiceId === userAnswers[question.id]?.choice_id) button.classList.add('is-incorrect');
                else button.classList.add('is-dimmed');
            });
        }
    }

    async function submitQuiz() {
        questionWrap.innerHTML = '<div class="quiz-saving">Saving authoritative results...</div>';
        try {
            const response = await fetch(quiz.submitUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({ answers: userAnswers }),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Grading failed');
            document.getElementById('sheet-score').textContent = `${result.score}/${result.total_questions}`;
            document.getElementById('sheet-percentage').textContent = `${result.percentage}%`;
            document.getElementById('sheet-xp').textContent = `+${result.xp_earned}`;
            document.getElementById('sheet-level').textContent = result.new_level;
            document.getElementById('sheet-streak').textContent = result.new_streak;
            renderAnswerReview(result.results || []);
            updateProgress(true);
            resultSheet.classList.add('open');
        } catch (error) {
            questionWrap.textContent = error.message;
        }
    }

    if (questions.length) renderQuestion();
});
