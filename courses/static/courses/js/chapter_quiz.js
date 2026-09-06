document.addEventListener('DOMContentLoaded', () => {
    const dataElement = document.getElementById('quiz-data');
    if (!dataElement) return;

    const quiz = JSON.parse(dataElement.textContent);
    const questions = quiz.questions || [];
    const questionWrap = document.getElementById('quiz-question-wrap');
    const progressFill = document.getElementById('quiz-progress-fill');
    const progressLabel = document.getElementById('quiz-progress-label');
    const resultSheet = document.getElementById('result-sheet');
    const reviewDrawer = document.getElementById('review-drawer-modal');
    const reviewContainer = document.getElementById('review-items-container');
    const reviewHeaderScore = document.getElementById('review-header-score');
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
        reviewContainer.innerHTML = '';
        reviewHeaderScore.textContent = `Score: ${results.reduce((sum, item) => sum + item.earned_points, 0)} points`;
        results.forEach((result, index) => {
            const card = document.createElement('div');
            const isFull = result.earned_points === result.maximum_points;
            card.className = `review-item-card ${isFull ? 'is-correct' : (result.earned_points > 0 ? 'is-partial' : '')}`;
            const header = document.createElement('div');
            header.className = 'review-item-header';
            addText(header, '', `${index + 1}. ${result.question_type.replace('_', ' ')}`);
            addText(header, '', `${result.earned_points}/${result.maximum_points} points`);
            card.appendChild(header);
            addText(card, 'review-item-qtext', result.question_text || 'Question');
            const answerBlock = document.createElement('div');
            answerBlock.className = 'review-answer-block';
            if (result.question_type === 'multiple_choice' || result.question_type === 'true_false') {
                addText(answerBlock, '', `Your selection: ${result.submitted_choice_text || 'No answer'}`);
                if (!result.is_correct) addText(answerBlock, '', `Correct choice: ${result.correct_choice_text || 'Unavailable'}`);
            } else if (result.question_type === 'identification') {
                addText(answerBlock, '', `Your answer: ${result.submitted_answer?.text || 'Blank'}`);
                if (!result.is_correct) addText(answerBlock, '', `Accepted answer: ${result.canonical_answer || 'Unavailable'}`);
            } else {
                addText(answerBlock, '', `Matched: ${(result.matched_items || []).join(', ') || 'None'}`);
                if (result.missing_items?.length) addText(answerBlock, '', `Missing: ${result.missing_items.join(', ')}`);
            }
            card.appendChild(answerBlock);
            addText(card, 'review-expl', result.explanation || 'Review the lesson for this concept.');
            review.appendChild(card);
            reviewContainer.appendChild(card.cloneNode(true));
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

    document.getElementById('open-review-btn')?.addEventListener('click', () => {
        resultSheet.classList.remove('open');
        reviewDrawer.classList.add('is-active');
        reviewDrawer.setAttribute('aria-hidden', 'false');
    });
    document.getElementById('close-review-btn')?.addEventListener('click', () => {
        reviewDrawer.classList.remove('is-active');
        reviewDrawer.setAttribute('aria-hidden', 'true');
        resultSheet.classList.add('open');
    });

    if (questions.length) renderQuestion();
});
