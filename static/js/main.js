// Pagrindinė JavaScript failas

// Lucide ikonų atnaujinimas po dinaminio HTML pakeitimo
function atnaujintiIkonas() {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

// Flash pranešimai - automatinis paslėpimas po 5 sekundžių
document.addEventListener('DOMContentLoaded', function() {
    const flashai = document.querySelectorAll('.flash');
    flashai.forEach(function(flash) {
        setTimeout(function() {
            flash.style.transition = 'opacity 0.5s, transform 0.5s';
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-10px)';
            setTimeout(function() {
                flash.remove();
            }, 500);
        }, 5000);
    });
});

// Formos validacija - paryškiname laukus su klaidomis
document.querySelectorAll('form').forEach(function(forma) {
    forma.addEventListener('submit', function(e) {
        const privalomi = forma.querySelectorAll('[required]');
        let viskas_uzpildyta = true;

        privalomi.forEach(function(laukas) {
            if (!laukas.value.trim()) {
                laukas.style.borderColor = 'rgb(239 68 68)';
                viskas_uzpildyta = false;
            } else {
                laukas.style.borderColor = '';
            }
        });

        if (!viskas_uzpildyta) {
            e.preventDefault();
        }
    });
});
