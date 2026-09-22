/* ============================================
   PIRMOJO PRISIJUNGIMO PAGALBININKAS (ONBOARDING)
   ============================================ */

(function() {
    'use strict';

    const RAKTAS = 'onboarding-baigtas';

    const ZINGSNIAI_DARBUOTOJUI = [
        {
            ikona: 'layout-dashboard',
            pavadinimas: 'Sveiki atvykę į sistemą!',
            tekstas: 'Ši sistema padės jums valdyti mokinius, klases, skelbimus ir kitą svarbią informaciją vienoje vietoje.',
        },
        {
            ikona: 'command',
            pavadinimas: 'Greita navigacija',
            tekstas: 'Norite greitai rasti bet ką? Paspauskite valdymo klavišų kombinaciją ir įveskite paieškos frazę. Komandų paletė atsidarys per akimirką.',
        },
        {
            ikona: 'shield-check',
            pavadinimas: 'Apsaugokite savo paskyrą',
            tekstas: 'Rekomenduojame įjungti dviejų veiksnių autentikaciją. Tai apsaugos jūsų paskyrą net jei slaptažodis būtų atskleistas.',
        },
        {
            ikona: 'bell',
            pavadinimas: 'Sekite pranešimus',
            tekstas: 'Varpelio ikona viršuje rodo naujus pranešimus. Kai bus svarbių įvykių — pamatysite raudoną skaitiklį.',
        },
    ];

    const ZINGSNIAI_TEVUI = [
        {
            ikona: 'heart-handshake',
            pavadinimas: 'Sveiki, mieli tėvai!',
            tekstas: 'Ši sistema leidžia jums matyti aktualius savo vaiko duomenis: klasę, klasės vadovą, mokyklos autobuso naudojimą ir kitą informaciją.',
        },
        {
            ikona: 'users',
            pavadinimas: 'Jūsų vaikai',
            tekstas: 'Kairėje juostoje matote savo vaikų sąrašą. Paspaudę ant vardo — pamatysite visą informaciją ir gyvenimo įvykių juostą.',
        },
        {
            ikona: 'megaphone',
            pavadinimas: 'Mokyklos skelbimai',
            tekstas: 'Skelbimų skiltyje rasite visus mokyklos pranešimus, skirtus tėvams: renginius, susirinkimus, svarbią informaciją.',
        },
        {
            ikona: 'calendar',
            pavadinimas: 'Kalendorius ir kontaktai',
            tekstas: 'Kalendoriuje matysite artimiausius renginius. Kontaktų skiltyje — klasės vadovo el. pašto ir telefono numerio informaciją.',
        },
    ];

    let dabartinis = 0;
    let zingsniai = [];

    function jauMatyta() {
        try { return localStorage.getItem(RAKTAS) === '1'; } catch { return true; }
    }

    function pazymetiKaipMatyta() {
        try { localStorage.setItem(RAKTAS, '1'); } catch {}
    }

    function _sukurti() {
        const backdrop = document.createElement('div');
        backdrop.className = 'onboarding-backdrop';
        backdrop.id = 'onboarding-backdrop';

        backdrop.innerHTML = `
            <div class="onboarding-dialog">
                <button type="button" class="onboarding-close" onclick="baigtiOnboarding()" aria-label="Uždaryti">
                    <i data-lucide="x" style="width:16px;height:16px"></i>
                </button>

                <div id="onboarding-turinys"></div>

                <div class="onboarding-nav">
                    <div class="onboarding-taskeliai" id="onboarding-taskeliai"></div>
                    <div class="onboarding-mygtukai">
                        <button type="button" class="btn-secondary" id="onboarding-atgal" onclick="onboardingAtgal()">
                            Atgal
                        </button>
                        <button type="button" class="btn-primary" id="onboarding-toliau" onclick="onboardingToliau()">
                            Toliau
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(backdrop);
        return backdrop;
    }

    function atvaizduoti() {
        const z = zingsniai[dabartinis];
        const turinys = document.getElementById('onboarding-turinys');
        if (!turinys || !z) return;

        turinys.innerHTML = `
            <div class="onboarding-ikona">
                <i data-lucide="${z.ikona}" style="width:32px;height:32px"></i>
            </div>
            <h2 class="onboarding-title">${z.pavadinimas}</h2>
            <p class="onboarding-text">${z.tekstas}</p>
        `;

        const taskeliai = document.getElementById('onboarding-taskeliai');
        if (taskeliai) {
            taskeliai.innerHTML = zingsniai.map((_, i) =>
                `<span class="onboarding-taskas ${i === dabartinis ? 'aktyvus' : ''}"></span>`
            ).join('');
        }

        const atgal = document.getElementById('onboarding-atgal');
        if (atgal) atgal.style.display = dabartinis === 0 ? 'none' : 'inline-flex';

        const toliau = document.getElementById('onboarding-toliau');
        if (toliau) {
            toliau.textContent = dabartinis === zingsniai.length - 1 ? 'Pradėti darbą' : 'Toliau';
        }

        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    window.onboardingToliau = function() {
        if (dabartinis < zingsniai.length - 1) {
            dabartinis++;
            atvaizduoti();
        } else {
            baigtiOnboarding();
        }
    };

    window.onboardingAtgal = function() {
        if (dabartinis > 0) {
            dabartinis--;
            atvaizduoti();
        }
    };

    window.baigtiOnboarding = function() {
        const b = document.getElementById('onboarding-backdrop');
        if (b) b.remove();
        pazymetiKaipMatyta();
    };

    document.addEventListener('DOMContentLoaded', function() {
        if (jauMatyta()) return;

        const rolē = document.body.dataset.role;
        if (!rolē) return;

        zingsniai = rolē === 'tevas' ? ZINGSNIAI_TEVUI : ZINGSNIAI_DARBUOTOJUI;
        dabartinis = 0;

        setTimeout(function() {
            _sukurti();
            atvaizduoti();
        }, 500);
    });
})();
