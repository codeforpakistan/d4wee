document.addEventListener('DOMContentLoaded', () => {
    const htmlElement = document.documentElement;
    const themeToggler = document.getElementById('themeToggler');

    // 1. Check for saved user preference, otherwise default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    htmlElement.setAttribute('data-bs-theme', savedTheme);
    updateButtonText(savedTheme);

    // 2. Listen for clicks on the toggle button
    themeToggler.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        // Update DOM attribute
        htmlElement.setAttribute('data-bs-theme', newTheme);
        
        // Save choice to localStorage
        localStorage.setItem('theme', newTheme);
        
        // Update button appearance
        updateButtonText(newTheme);
    });

    // Helper function to keep button text synchronized
    function updateButtonText(theme) {
        themeToggler.innerHTML = theme === 'light' ? '🌚' : '🌞';
    }
});