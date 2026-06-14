const hamburger = document.getElementById('hamburger-btn');
const nav = document.getElementById('nav');
const mobileMenu = document.querySelector('.navbar-mobile-left');

// Create overlay
const overlay = document.createElement('div');
overlay.className = 'menu-overlay';
document.body.appendChild(overlay);

function openMenu() {
    mobileMenu.classList.add('open');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    hamburger.classList.add('active');
    nav.classList.add('active');
}

function closeMenu() {
    mobileMenu.classList.remove('open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
    hamburger.classList.remove('active');
    nav.classList.remove('active');
}

if (hamburger && nav) {
    hamburger.addEventListener('click', function(e) {
        e.stopPropagation();
        if (mobileMenu.classList.contains('open')) {
            closeMenu();
        } else {
            openMenu();
        }
    });
}

// Close when clicking overlay
overlay.addEventListener('click', closeMenu);