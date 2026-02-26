/**
 * DocsPort i18n - Lightweight internationalization helper
 */
class I18n {
    constructor() {
        this.locale = 'en';
        this.translations = {};
        this.fallback = {};
    }

    async init() {
        const saved = localStorage.getItem('docsport-locale');
        this.locale = saved || this._detectBrowserLocale();
        this.fallback = await this._fetchLocale('en');
        if (this.locale !== 'en') {
            this.translations = await this._fetchLocale(this.locale);
        } else {
            this.translations = this.fallback;
        }
        this.translateDOM(document);
    }

    _detectBrowserLocale() {
        const lang = (navigator.language || 'en').split('-')[0];
        const supported = ['en', 'de', 'es'];
        return supported.includes(lang) ? lang : 'en';
    }

    async _fetchLocale(locale) {
        try {
            const resp = await fetch(`/locales/${locale}.json`);
            if (!resp.ok) throw new Error(resp.status);
            return await resp.json();
        } catch {
            console.warn(`i18n: Could not load locale "${locale}", falling back to en`);
            return this.fallback || {};
        }
    }

    t(key, vars) {
        let val = this._resolve(this.translations, key)
              || this._resolve(this.fallback, key)
              || key;
        if (vars && typeof val === 'string') {
            for (const [k, v] of Object.entries(vars)) {
                val = val.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
            }
        }
        return val;
    }

    _resolve(obj, path) {
        return path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : undefined), obj);
    }

    translateDOM(root) {
        const els = (root || document).querySelectorAll('[data-i18n]');
        els.forEach(el => {
            const key = el.getAttribute('data-i18n');
            const val = this.t(key);
            if (val && val !== key) {
                if (el.tagName === 'INPUT' && el.type !== 'submit') {
                    el.placeholder = val;
                } else if (el.tagName === 'OPTION' && el.value === '') {
                    el.textContent = val;
                } else {
                    el.textContent = val;
                }
            }
        });
    }

    async setLocale(locale) {
        this.locale = locale;
        localStorage.setItem('docsport-locale', locale);
        if (locale === 'en') {
            this.translations = this.fallback;
        } else {
            this.translations = await this._fetchLocale(locale);
        }
        this.translateDOM(document);
    }
}

window.i18n = new I18n();
