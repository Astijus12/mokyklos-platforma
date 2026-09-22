/* ============================================
   UI KOMPONENTŲ BIBLIOTEKA:
   Toast pranešimai + Modal patvirtinimo dialogai
   ============================================ */

(function() {
    'use strict';

    let toastContainer = null;

    function ikonosPagalTipa(tipas) {
        const ikonos = {
            'success': 'check-circle',
            'danger': 'alert-circle',
            'warning': 'alert-triangle',
            'info': 'info',
        };
        return ikonos[tipas] || 'info';
    }

    function _sukurtiToastContainer() {
        if (toastContainer) return toastContainer;
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        toastContainer.setAttribute('role', 'status');
        toastContainer.setAttribute('aria-live', 'polite');
        document.body.appendChild(toastContainer);
        return toastContainer;
    }

    function toast(zinute, tipas, trukme) {
        tipas = tipas || 'info';
        trukme = trukme || 4000;

        _sukurtiToastContainer();

        const el = document.createElement('div');
        el.className = 'toast';

        el.innerHTML = `
            <span class="toast-icon toast-${tipas}">
                <i data-lucide="${ikonosPagalTipa(tipas)}" style="width:20px;height:20px"></i>
            </span>
            <div class="toast-content">${escapeHTML(zinute)}</div>
            <button type="button" class="toast-close" aria-label="Uždaryti pranešimą">
                <i data-lucide="x" style="width:16px;height:16px"></i>
            </button>
            <div class="toast-progress toast-${tipas}"></div>
        `;

        toastContainer.appendChild(el);
        if (typeof lucide !== 'undefined') lucide.createIcons();

        function pasalinti() {
            el.classList.add('removing');
            setTimeout(function() {
                if (el.parentNode) el.parentNode.removeChild(el);
            }, 200);
        }

        el.querySelector('.toast-close').addEventListener('click', pasalinti);
        setTimeout(pasalinti, trukme);
    }

    function escapeHTML(s) {
        const el = document.createElement('div');
        el.textContent = s;
        return el.innerHTML;
    }

    function confirmDialog(nustatymai) {
        nustatymai = Object.assign({
            title: 'Ar tikrai?',
            text: '',
            confirmText: 'Patvirtinti',
            cancelText: 'Atšaukti',
            variant: 'danger',
            onConfirm: function() {},
            onCancel: function() {},
        }, nustatymai);

        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';
        backdrop.setAttribute('role', 'dialog');
        backdrop.setAttribute('aria-modal', 'true');
        backdrop.setAttribute('aria-labelledby', 'modal-title');

        const ikona = nustatymai.variant === 'danger' ? 'alert-triangle'
                    : nustatymai.variant === 'warning' ? 'alert-circle'
                    : 'info';

        const patvirtinimoKlase = nustatymai.variant === 'danger' ? 'btn-modal-danger'
                                 : 'btn-modal-primary';

        backdrop.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-icon ${nustatymai.variant}">
                    <i data-lucide="${ikona}" style="width:24px;height:24px"></i>
                </div>
                <h3 class="modal-title" id="modal-title">${escapeHTML(nustatymai.title)}</h3>
                <p class="modal-text">${escapeHTML(nustatymai.text)}</p>
                <div class="modal-actions">
                    <button type="button" class="btn-modal-cancel" data-action="cancel">
                        ${escapeHTML(nustatymai.cancelText)}
                    </button>
                    <button type="button" class="${patvirtinimoKlase}" data-action="confirm">
                        ${escapeHTML(nustatymai.confirmText)}
                    </button>
                </div>
            </div>
        `;

        function uzdaryti(patvirtinta) {
            document.removeEventListener('keydown', esc);
            backdrop.remove();
            document.body.style.overflow = '';
            if (patvirtinta) nustatymai.onConfirm();
            else nustatymai.onCancel();
        }

        function esc(e) {
            if (e.key === 'Escape') uzdaryti(false);
            if (e.key === 'Enter') uzdaryti(true);
        }

        backdrop.querySelector('[data-action="cancel"]').addEventListener('click', function() { uzdaryti(false); });
        backdrop.querySelector('[data-action="confirm"]').addEventListener('click', function() { uzdaryti(true); });
        backdrop.addEventListener('click', function(e) { if (e.target === backdrop) uzdaryti(false); });
        document.addEventListener('keydown', esc);

        document.body.style.overflow = 'hidden';
        document.body.appendChild(backdrop);
        if (typeof lucide !== 'undefined') lucide.createIcons();

        setTimeout(function() {
            const b = backdrop.querySelector('[data-action="confirm"]');
            if (b) b.focus();
        }, 50);
    }

    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('form[data-confirm]').forEach(function(forma) {
            forma.addEventListener('submit', function(e) {
                if (forma.dataset.confirmPatvirtinta === 'true') return;
                e.preventDefault();
                confirmDialog({
                    title: forma.dataset.confirmTitle || 'Ar tikrai?',
                    text: forma.dataset.confirm,
                    confirmText: forma.dataset.confirmBtn || 'Ištrinti',
                    cancelText: 'Atšaukti',
                    variant: forma.dataset.confirmVariant || 'danger',
                    onConfirm: function() {
                        forma.dataset.confirmPatvirtinta = 'true';
                        forma.submit();
                    },
                });
            });
        });
    });

    window.MokyklosUI = {
        toast: toast,
        confirm: confirmDialog,
    };
})();
