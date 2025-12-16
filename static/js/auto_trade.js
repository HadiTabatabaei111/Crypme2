document.addEventListener('DOMContentLoaded', () => {
    loadParams();
    document.getElementById('auto-trade-form').addEventListener('submit', saveParams);
    document.getElementById('btn-reset').addEventListener('click', loadParams);
});

async function loadParams() {
    try {
        const res = await fetch('/api/auto-trade/params');
        const params = await res.json();
        Object.keys(params).forEach(k => {
            const el = document.getElementById(k);
            if (el) el.value = params[k];
        });
    } catch (e) {
        console.error('Error loading auto-trade params', e);
    }
}

async function saveParams(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const params = {};
    formData.forEach((v, k) => {
        const num = parseFloat(v);
        params[k] = isNaN(num) ? v : num;
    });
    try {
        const res = await fetch('/api/auto-trade/params', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        const data = await res.json();
        if (data.success) {
            alert('تنظیمات ذخیره شد');
        } else {
            alert('خطا در ذخیره تنظیمات');
        }
    } catch (e) {
        console.error('Error saving auto-trade params', e);
        alert('خطا در ذخیره تنظیمات');
    }
}


