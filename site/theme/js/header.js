/**
 * Header Navigation JavaScript
 * Handles mobile menu, submenu toggling, and sticky header
 * Uses the same class names as the original HubSpot template
 */

(function() {
    'use strict';

    // Mobile Navigation
    const mnavOpen = document.querySelector('.mnav__open');
    const mnavClose = document.querySelector('.mnav__close');
    const mnavOverlay = document.querySelector('.mnav__overlay');
    const mnavToggles = document.querySelectorAll('.mnav__menu__toggle');
    const mnavParentLinks = document.querySelectorAll('.mnav__menu__item--parent > .mnav__menu__link');

    function openMobileNav() {
        document.body.classList.add('mnav-active');
        if (mnavOpen) mnavOpen.setAttribute('aria-expanded', 'true');
    }

    function closeMobileNav() {
        document.body.classList.remove('mnav-active');
        if (mnavOpen) mnavOpen.setAttribute('aria-expanded', 'false');
    }

    if (mnavOpen) {
        mnavOpen.addEventListener('click', (e) => {
            e.preventDefault();
            openMobileNav();
        });
    }

    if (mnavClose) {
        mnavClose.addEventListener('click', (e) => {
            e.preventDefault();
            closeMobileNav();
        });
    }

    if (mnavOverlay) {
        mnavOverlay.addEventListener('click', closeMobileNav);
    }

    // Submenu toggle
    mnavToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            const item = toggle.closest('.mnav__menu__item');

            if (item) {
                // Close other expanded items at the same level
                const siblings = item.parentElement.querySelectorAll('.mnav__menu__item--expanded');
                siblings.forEach(sibling => {
                    if (sibling !== item) {
                        sibling.classList.remove('mnav__menu__item--expanded');
                        const siblingToggle = sibling.querySelector('.mnav__menu__toggle');
                        if (siblingToggle) siblingToggle.setAttribute('aria-expanded', 'false');
                    }
                });

                const isExpanded = item.classList.toggle('mnav__menu__item--expanded');
                toggle.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
            }
        });
    });

    // Also toggle when clicking the parent link (if it's javascript:;)
    mnavParentLinks.forEach(link => {
        if (link.getAttribute('href') === 'javascript:;') {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const item = link.closest('.mnav__menu__item');
                const toggle = item ? item.querySelector('.mnav__menu__toggle') : null;
                if (toggle) toggle.click();
            });
        }
    });

    // Close mobile nav on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && document.body.classList.contains('mnav-active')) {
            closeMobileNav();
        }
    });

    // Sticky header - matches original template_main.min.js behaviour exactly
    const headerStickyElement = document.querySelector('.header__sticky-element');
    if (headerStickyElement) {
        const headerSticky = document.querySelector('.header--sticky');
        const headerStickyProp = headerSticky.getBoundingClientRect();

        function handleStickyHeader() {
            if (window.pageYOffset > headerStickyProp.height) {
                // Scrolled past header height - make it sticky
                headerSticky.style.height = headerStickyProp.height + 'px';
                headerSticky.classList.add('header--sticky-active');
                headerSticky.classList.remove('header--sticky-inactive');
            } else {
                // At top - remove sticky
                if (headerSticky.classList.contains('header--sticky-active')) {
                    headerSticky.classList.add('header--sticky-inactive');
                }
                headerSticky.style.height = '';
                headerSticky.classList.remove('header--sticky-active');
            }
        }

        // Listen on resize, scroll, and load
        ['resize', 'scroll', 'load'].forEach(function(eventType) {
            window.addEventListener(eventType, handleStickyHeader, { passive: true });
        });

        // Initial call
        handleStickyHeader();
    }
})();
