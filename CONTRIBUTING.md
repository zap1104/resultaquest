# Contributing / GitHub Workflow

A quick tutorial for working on StudyQuest with Git and GitHub, aimed at
teammates who are still getting comfortable with the workflow.

## 1. One-time setup

```bash
git clone <repo-url>
cd studyquest
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
```

## 2. Everyday workflow

1. **Pull the latest changes before you start:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a branch for your task.** Don't commit directly to `main`.
   ```bash
   git checkout -b feature/short-description
   ```
   Branch naming:
   - `feature/...` — new functionality (e.g. `feature/quiz-scoring`)
   - `fix/...` — bug fixes (e.g. `fix/course-form-validation`)
   - `docs/...` — documentation only

3. **Make your changes, then check what changed:**
   ```bash
   git status
   git diff
   ```

4. **Stage and commit:**
   ```bash
   git add <files>
   git commit -m "Add short, present-tense description of the change"
   ```
   Good commit messages describe *what* changed, e.g.
   `"Add chapter review page"`, not `"fix stuff"`.

5. **Push your branch:**
   ```bash
   git push origin feature/short-description
   ```

6. **Open a Pull Request (PR) on GitHub** from your branch into `main`.
   - Give it a clear title and a short description of what you did and why
   - Link any related issue
   - Ask at least one teammate to review before merging

7. **After merge**, delete the branch and sync up:
   ```bash
   git checkout main
   git pull origin main
   git branch -d feature/short-description
   ```

## 3. Handling merge conflicts

If `git pull` or a PR shows a conflict:
1. Open the conflicting file(s) — Git marks conflicts with `<<<<<<<`, `=======`, `>>>>>>>`
2. Edit the file to keep the correct version (or combine both)
3. Remove the conflict markers
4. `git add <file>` then `git commit` to finish the merge

If you're unsure, ask before force-pushing or discarding changes — it's easy
to lose someone's work by guessing wrong.

## 4. Django-specific notes

- **Migrations:** if you change `reviewer/models.py`, run
  `python manage.py makemigrations` and commit the generated migration file
  along with your model change.
- **Don't commit `db.sqlite3`** — it's in `.gitignore`. Everyone runs their
  own local migrations.
- **Don't commit `.env` or secrets** — settings that shouldn't be public
  (like an AI API key, once that's added) belong in a local `.env` file that
  is never committed.

## 5. Code style

- Keep views thin — business logic (like the AI generation step) belongs in
  `services.py`, not `views.py`.
- Prefer small, focused PRs over large ones — easier to review.
