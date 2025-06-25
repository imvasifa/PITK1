/**
 * Admin Conditions Module
 * Handles all admin conditions functionality
 */

export class AdminConditions {
    constructor() {
        this.container = null;
        this.initialize();
    }

    initialize() {
        this.container = document.getElementById('admin-conditions-list');
        if (!this.container) {
            console.warn('Admin conditions container not found');
            return;
        }

        // Initialize event listeners
        this.initializeEventListeners();
        
        // Load conditions if container is visible
        if (this.isVisible()) {
            this.loadConditions();
        }
    }

    isVisible() {
        const tabPane = document.getElementById('admin-conditions');
        return tabPane && !tabPane.classList.contains('d-none') && tabPane.offsetParent !== null;
    }

    initializeEventListeners() {
        // Handle show all toggle
        document.addEventListener('click', (e) => {
            if (e.target && e.target.matches('#showAllAdminConditions')) {
                this.toggleShowAll(e.target.checked);
            } else if (e.target && e.target.closest('#apply-conditions-btn')) {
                this.saveSelectedConditions();
            }
        });
    }

    initialize() {
        this.container = document.getElementById('admin-conditions-list');
        if (!this.container) {
            console.warn('Admin conditions container not found');
            return;
        }
        
        // Initialize event listeners
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Handle show all toggle
        const showAllToggle = document.getElementById('showAllAdminConditions');
        if (showAllToggle) {
            showAllToggle.addEventListener('change', (e) => this.toggleShowAll(e.target.checked));
        }
        
        // Handle apply button
        const applyBtn = document.getElementById('apply-conditions-btn');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.saveSelectedConditions());
        }
    }

    async loadConditions() {
        if (!this.container) {
            console.warn('Cannot load conditions: container not found');
            return;
        }

        this.showLoading();

        try {
            const [settingsRes, conditionsRes] = await Promise.all([
                fetch('/get-settings'),
                fetch('/conditions')
            ]);
            
            if (!settingsRes.ok || !conditionsRes.ok) {
                throw new Error(`HTTP error! settings: ${settingsRes.status}, conditions: ${conditionsRes.status}`);
            }
            
            const settings = await settingsRes.json();
            const conditions = await conditionsRes.json();
            
            if (!Array.isArray(conditions)) {
                throw new Error('Invalid conditions data format');
            }
            
            this.renderConditions(conditions, settings.conditions || []);
        } catch (error) {
            console.error('Error loading admin conditions:', error);
            this.showError('Failed to load conditions. Please try again.');
        }
    }

    renderConditions(conditions, selectedConditions = []) {
        if (!this.container) {
            console.warn('Cannot render conditions: container not found');
            return;
        }
        
        try {
            if (!conditions || !conditions.length) {
                this.container.innerHTML = `
                    <div class="alert alert-info m-0">
                        <i class="fas fa-info-circle me-2"></i>
                        No admin conditions available.
                    </div>`;
                return;
            }

            let html = '<div class="list-group">';
            
            // Filter admin conditions
            const adminConditions = conditions.filter(c => c && c.type === 'admin');
            
            if (adminConditions.length === 0) {
                html += `
                    <div class="alert alert-info m-0">
                        <i class="fas fa-info-circle me-2"></i>
                        No admin conditions available.
                    </div>`;
            } else {
                adminConditions.forEach(condition => {
                    if (!condition || !condition.name) return;
                    
                    const isChecked = selectedConditions.includes(condition.name);
                    const displayName = String(condition.name)
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, l => l.toUpperCase());
                        
                    html += `
                        <label class="list-group-item">
                            <input class="form-check-input me-1" 
                                   type="checkbox" 
                                   value="${this.escapeHtml(condition.name)}" 
                                   ${isChecked ? 'checked' : ''}>
                            ${displayName}
                        </label>`;
                });
            }
            
            html += '</div>';
            this.container.innerHTML = html;
            
        } catch (error) {
            console.error('Error rendering conditions:', error);
            this.showError('Error displaying conditions. Please try again.');
        }
        
        // Store the conditions data for later use
        this.container.dataset.conditions = JSON.stringify(adminConditions);
    }

    async saveSelectedConditions() {
        if (!this.container) return;
        
        const checkboxes = this.container.querySelectorAll('input[type="checkbox"]');
        const selectedConditions = [];
        
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                selectedConditions.push(checkbox.value);
            }
        });
        
        try {
            const response = await fetch('/update-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ conditions: selectedConditions })
            });
            
            if (!response.ok) {
                throw new Error('Failed to save settings');
            }
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('conditionsModal'));
            if (modal) {
                modal.hide();
            }
            
            // Refresh the dashboard
            if (typeof updateDashboard === 'function') {
                updateDashboard();
            }
            
        } catch (error) {
            console.error('Error saving conditions:', error);
            alert('Failed to save conditions. Please try again.');
        }
    }

    toggleShowAll(showAll) {
        console.log('Show all admin conditions:', showAll);
        // Reload conditions with new filter
        this.loadConditions();
    }
    
    escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return '';
        return unsafe
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    showLoading() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2 small text-muted">Loading conditions...</div>
            </div>`;
    }

    showError(message) {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="alert alert-danger m-0">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>`;
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.adminConditions = new AdminConditions();
});
