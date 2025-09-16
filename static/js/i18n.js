/**
 * I18n - Internationalization helper for E-ink Display Manager
 */
class I18n {
    constructor() {
        this.currentLang = localStorage.getItem('language') || 'en';
        this.translations = {};
        this.fallbackLang = 'en';

        // Initialize
        this.init();
    }

    async init() {
        try {
            await this.loadTranslations();
            this.updatePageLanguage();
            console.log(`I18n initialized with language: ${this.currentLang}`);
        } catch (error) {
            console.error('Failed to initialize I18n:', error);
            // Fallback to English if initialization fails
            this.currentLang = 'en';
            await this.loadTranslations();
            this.updatePageLanguage();
        }
    }

    async loadTranslations() {
        try {
            // Load current language
            const response = await fetch(`/static/locales/${this.currentLang}.json`);
            if (!response.ok) {
                throw new Error(`Failed to load ${this.currentLang}.json`);
            }
            this.translations[this.currentLang] = await response.json();

            // Load fallback language if different
            if (this.currentLang !== this.fallbackLang && !this.translations[this.fallbackLang]) {
                const fallbackResponse = await fetch(`/static/locales/${this.fallbackLang}.json`);
                if (fallbackResponse.ok) {
                    this.translations[this.fallbackLang] = await fallbackResponse.json();
                }
            }
        } catch (error) {
            console.error('Error loading translations:', error);
            throw error;
        }
    }

    /**
     * Get translation for a key
     * @param {string} key - Translation key (e.g., 'app.title', 'settings.language')
     * @param {object} params - Parameters for string interpolation
     * @returns {string} Translated string
     */
    t(key, params = {}) {
        let translation = this.getNestedValue(this.translations[this.currentLang], key);

        // Fallback to default language if translation not found
        if (translation === undefined && this.currentLang !== this.fallbackLang) {
            translation = this.getNestedValue(this.translations[this.fallbackLang], key);
        }

        // If still not found, return the key itself
        if (translation === undefined) {
            console.warn(`Translation not found for key: ${key}`);
            return key;
        }

        // Handle string interpolation
        return this.interpolate(translation, params);
    }

    /**
     * Get nested object value by dot notation key
     * @param {object} obj - Object to search in
     * @param {string} key - Dot notation key (e.g., 'app.title')
     * @returns {*} Value or undefined
     */
    getNestedValue(obj, key) {
        return key.split('.').reduce((current, prop) => {
            return current && current[prop] !== undefined ? current[prop] : undefined;
        }, obj);
    }

    /**
     * Interpolate parameters into string
     * @param {string} str - String with placeholders like {count}
     * @param {object} params - Parameters to interpolate
     * @returns {string} Interpolated string
     */
    interpolate(str, params) {
        return str.replace(/\{(\w+)\}/g, (match, key) => {
            return params[key] !== undefined ? params[key] : match;
        });
    }

    /**
     * Change language
     * @param {string} lang - Language code (e.g., 'en', 'hu')
     */
    async setLanguage(lang) {
        if (lang === this.currentLang) return;

        console.log(`I18n: Setting language from ${this.currentLang} to ${lang}`);
        this.currentLang = lang;
        localStorage.setItem('language', lang);

        try {
            await this.loadTranslations();
            console.log(`I18n: Translations loaded for ${lang}`);

            this.updatePageLanguage();
            console.log(`I18n: Page language updated`);

            this.notifyLanguageChange();
            console.log(`I18n: Language change notification sent`);

            console.log(`I18n: Language successfully changed to: ${lang}`);
        } catch (error) {
            console.error(`Failed to change language to ${lang}:`, error);
        }
    }

    /**
     * Update page language attribute and direction
     */
    updatePageLanguage() {
        document.documentElement.lang = this.currentLang;

        // Update page title
        document.title = this.t('app.title');

        // Update all elements with data-i18n attributes
        this.updateElements();
    }

    /**
     * Update all elements with data-i18n attributes
     */
    updateElements() {
        const elements = document.querySelectorAll('[data-i18n]');
        console.log(`I18n: Updating ${elements.length} elements with data-i18n attributes`);

        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const params = this.getElementParams(element);

            if (element.tagName === 'INPUT' && (element.type === 'text' || element.type === 'search')) {
                element.placeholder = this.t(key, params);
            } else if (element.hasAttribute('title')) {
                element.title = this.t(key, params);
            } else {
                // Handle HTML content
                const translation = this.t(key, params);
                if (element.hasAttribute('data-i18n-html')) {
                    element.innerHTML = translation;
                } else {
                    element.textContent = translation;
                }
            }
        });

        console.log(`I18n: All ${elements.length} elements updated`);
    }

    /**
     * Get parameters from element data attributes
     * @param {Element} element - DOM element
     * @returns {object} Parameters object
     */
    getElementParams(element) {
        const params = {};
        const attributes = element.attributes;

        for (let i = 0; i < attributes.length; i++) {
            const attr = attributes[i];
            if (attr.name.startsWith('data-i18n-param-')) {
                const paramName = attr.name.replace('data-i18n-param-', '');
                params[paramName] = attr.value;
            }
        }

        return params;
    }

    /**
     * Notify other components about language change
     */
    notifyLanguageChange() {
        const event = new CustomEvent('languageChanged', {
            detail: { language: this.currentLang }
        });
        document.dispatchEvent(event);
    }

    /**
     * Get current language
     * @returns {string} Current language code
     */
    getCurrentLanguage() {
        return this.currentLang;
    }

    /**
     * Get available languages
     * @returns {Array} Array of available language codes
     */
    getAvailableLanguages() {
        return ['en', 'hu'];
    }

    /**
     * Get language display name
     * @param {string} lang - Language code
     * @returns {string} Display name
     */
    getLanguageDisplayName(lang) {
        const names = {
            'en': 'English',
            'hu': 'Magyar'
        };
        return names[lang] || lang;
    }
}

// Create global instance
window.i18n = new I18n();
