/* ============================================
   COMMAND PALETTE (Ctrl+K / Cmd+K)
   ============================================ */

(function() {
    'use strict';

    let paletteEl = null;
    let filtras = '';
    let atrinkti = [];
    let dabartinis = 0;
    let visiVeiksmai = [];

    function inicializuoti() {
        visiVeiksmai = (window.KomandosPaletei || []).slice();
    }

    function _sukurti() {
        if (paletteEl) return paletteEl;

        paletteEl = document.createElement('div');
        paletteEl.className = 'palette-backdrop';
        paletteEl.setAttribute('role', 'dialog');
        paletteEl.setAttribute('aria-modal', 'true');
        paletteEl.style.display = 'none';

        paletteEl.innerHTML = `
            <div class="palette-container">
                <div class="palette-input-wrap">
                    <i data-lucide="search" class="palette-search-icon"></i>
                    <input type="text"
                           class="palette-input"
                           placeholder="Ieškoti veiksmų arba puslapių..."
                           autocomplete="off"
                           aria-label="Ieškoti komandų"
                           spellcheck="false">
                    <kbd class="palette-kbd">ESC</kbd>
                </div>
                <div class="palette-results"></div>
                <div class="palette-footer">
                    <div class="flex items-center gap-3">
                        <span><kbd class="palette-kbd">↑↓</kbd> Naršyti</span>
                        <span><kbd class="palette-kbd">↵</kbd> Pasirinkti</span>
                    </div>
                    <div>Command palette</div>
                </div>
            </div>
        `;

        document.body.appendChild(paletteEl);

        const inputas = paletteEl.querySelector('.palette-input');
        inputas.addEventListener('input', function() {
            filtras = inputas.value.toLowerCase().trim();
            dabartinis = 0;
            atvaizduoti();
        });

        paletteEl.addEventListener('click', function(e) {
            if (e.target === paletteEl) uzdaryti();
        });

        return paletteEl;
    }

    function _filtruoti() {
        if (!filtras) return visiVeiksmai;
        return visiVeiksmai.filter(function(v) {
            const teksto = (v.pavadinimas + ' ' + (v.aprasymas || '') + ' ' + (v.raktazodziai || '')).toLowerCase();
            return teksto.includes(filtras);
        });
    }

    function atvaizduoti() {
        atrinkti = _filtruoti();
        const box = paletteEl.querySelector('.palette-results');

        if (atrinkti.length === 0) {
            box.innerHTML = `
                <div class="palette-empty">
                    <i data-lucide="search-x" style="width:32px;height:32px;margin-bottom:8px;opacity:0.4"></i>
                    <p>Nieko nerasta pagal "${escapeHTML(filtras)}"</p>
                </div>
            `;
            if (typeof lucide !== 'undefined') lucide.createIcons();
            return;
        }

        let grupes = {};
        atrinkti.forEach(function(v) {
            const g = v.grupe || 'Kita';
            if (!grupes[g]) grupes[g] = [];
            grupes[g].push(v);
        });

        let html = '';
        let idx = 0;
        Object.keys(grupes).forEach(function(g) {
            html += `<div class="palette-group-title">${escapeHTML(g)}</div>`;
            grupes[g].forEach(function(v) {
                const aktyvus = idx === dabartinis ? 'palette-item-active' : '';
                html += `
                    <div class="palette-item ${aktyvus}" data-idx="${idx}">
                        <div class="palette-item-icon">
                            <i data-lucide="${v.ikona || 'arrow-right'}"></i>
                        </div>
                        <div class="palette-item-content">
                            <p class="palette-item-title">${escapeHTML(v.pavadinimas)}</p>
                            ${v.aprasymas ? '<p class="palette-item-desc">' + escapeHTML(v.aprasymas) + '</p>' : ''}
                        </div>
                    </div>
                `;
                idx++;
            });
        });
        box.innerHTML = html;
        if (typeof lucide !== 'undefined') lucide.createIcons();

        box.querySelectorAll('.palette-item').forEach(function(el) {
            el.addEventListener('click', function() {
                const i = parseInt(el.dataset.idx);
                paleisti(atrinkti[i]);
            });
        });

        const aktyvus = box.querySelector('.palette-item-active');
        if (aktyvus) aktyvus.scrollIntoView({ block: 'nearest' });
    }

    function paleisti(veiksmas) {
        uzdaryti();
        if (veiksmas.url) {
            setTimeout(function() { window.location.href = veiksmas.url; }, 50);
        } else if (typeof veiksmas.veiksmas === 'function') {
            veiksmas.veiksmas();
        }
    }

    function atidaryti() {
        _sukurti();
        paletteEl.style.display = 'flex';
        filtras = '';
        dabartinis = 0;
        paletteEl.querySelector('.palette-input').value = '';
        atvaizduoti();
        document.body.style.overflow = 'hidden';
        setTimeout(function() {
            paletteEl.querySelector('.palette-input').focus();
        }, 50);
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function uzdaryti() {
        if (!paletteEl) return;
        paletteEl.style.display = 'none';
        document.body.style.overflow = '';
    }

    function escapeHTML(s) {
        const el = document.createElement('div');
        el.textContent = s;
        return el.innerHTML;
    }

    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            atidaryti();
            return;
        }

        if (!paletteEl || paletteEl.style.display === 'none') return;

        if (e.key === 'Escape') {
            e.preventDefault();
            uzdaryti();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            dabartinis = Math.min(dabartinis + 1, atrinkti.length - 1);
            atvaizduoti();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            dabartinis = Math.max(dabartinis - 1, 0);
            atvaizduoti();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (atrinkti[dabartinis]) paleisti(atrinkti[dabartinis]);
        }
    });

    document.addEventListener('DOMContentLoaded', inicializuoti);

    window.CommandPalette = {
        atidaryti: atidaryti,
        uzdaryti: uzdaryti,
    };
})();
