// Utility functions for UI improvements

// Toast notification system
class Toast {
    static show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Add to page
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Remove after duration
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    
    static success(message) {
        this.show(message, 'success');
    }
    
    static error(message) {
        this.show(message, 'error', 5000);
    }
    
    static info(message) {
        this.show(message, 'info');
    }
    
    static warning(message) {
        this.show(message, 'warning');
    }
}

// Loading state manager
class LoadingManager {
    static show(element, message = 'در حال بارگذاری...') {
        if (!element) return;
        
        const loading = document.createElement('div');
        loading.className = 'loading-overlay';
        loading.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-message">${message}</div>
        `;
        
        element.style.position = 'relative';
        element.appendChild(loading);
        
        return loading;
    }
    
    static hide(element) {
        if (!element) return;
        const loading = element.querySelector('.loading-overlay');
        if (loading) {
            loading.remove();
        }
    }
}

// Error handler
class ErrorHandler {
    static handle(error, context = '') {
        console.error(`Error in ${context}:`, error);
        
        let message = 'خطایی رخ داد';
        if (error.message) {
            message = error.message;
        } else if (typeof error === 'string') {
            message = error;
        }
        
        Toast.error(message);
    }
}

// Format helpers
const Formatters = {
    number: (num, decimals = 2) => {
        if (num === null || num === undefined) return '0';
        if (num >= 1e9) return (num / 1e9).toFixed(decimals) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(decimals) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(decimals) + 'K';
        return num.toFixed(decimals);
    },
    
    price: (price, decimals = 6) => {
        return `$${Formatters.number(price, decimals)}`;
    },
    
    percent: (value, decimals = 2) => {
        const sign = value >= 0 ? '+' : '';
        return `${sign}${value.toFixed(decimals)}%`;
    },
    
    date: (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleString('fa-IR');
    }
};

// Export for use in other files
window.Toast = Toast;
window.LoadingManager = LoadingManager;
window.ErrorHandler = ErrorHandler;
window.Formatters = Formatters;

