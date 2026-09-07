document.addEventListener('DOMContentLoaded', () => {
    const readerContent = document.getElementById('reader-content');
    const navBar = document.getElementById('reader-section-nav');
    if (!readerContent || !navBar) return;

    const sections = Array.from(readerContent.querySelectorAll('[data-review-section]'));
    if (sections.length <= 1) {
        navBar.hidden = true;
        return;
    }

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const chips = [];

    // 1. Dynamically build chip buttons only for sections rendered in the DOM
    sections.forEach((sec, idx) => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = `reader-nav-chip ${idx === 0 ? 'active' : ''}`;
        chip.textContent = sec.dataset.sectionLabel || sec.id || 'Section';
        chip.dataset.targetId = sec.id;

        chip.addEventListener('click', () => {
            // Container-relative scroll calculation
            const targetOffset = sec.getBoundingClientRect().top 
                - readerContent.getBoundingClientRect().top 
                + readerContent.scrollTop 
                - 16;

            readerContent.scrollTo({
                top: Math.max(0, targetOffset),
                behavior: reduceMotion ? 'auto' : 'smooth'
            });

            // Set active chip on click
            chips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            chip.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', inline: 'nearest', block: 'nearest' });
        });

        navBar.appendChild(chip);
        chips.push(chip);
    });

    navBar.hidden = false;

    // 2. IntersectionObserver tracking scroll relative to #reader-content container
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            const targetId = entry.target.id;
            const matchingChip = chips.find(c => c.dataset.targetId === targetId);

            if (matchingChip) {
                chips.forEach(c => c.classList.remove('active'));
                matchingChip.classList.add('active');
                matchingChip.scrollIntoView({ 
                    behavior: reduceMotion ? 'auto' : 'smooth', 
                    inline: 'nearest', 
                    block: 'nearest' 
                });
            }
        });
    }, {
        root: readerContent,
        rootMargin: '-5% 0px -75% 0px', // Bias towards topmost section
        threshold: 0
    });

    sections.forEach(sec => observer.observe(sec));
});