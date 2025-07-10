/**
 * User Conditions Module
 * Handles all user conditions functionality
 */

export class UserConditions {
    constructor() {
        this.container = null;
        this.initialize();
    }

    initialize() {
        this.container = document.querySelector('#user-conditions-list-container');
        if (!this.container) {
            console.warn('User conditions container not found');
            return;
        }

        // Initialize event listeners
        this.initializeEventListeners();
        
        // Load conditions if we're on the right tab
        const userTab = document.querySelector('#user-conditions-tab');
        if (userTab && userTab.classList.contains('active')) {
            this.loadConditions();
        }
    }

    initializeEventListeners() {
        // Delegate events for dynamic content
        document.addEventListener('click', (e) => {
            // Handle edit button
            if (e.target.closest('.edit-condition')) {
                const btn = e.target.closest('.edit-condition');
                const condition = JSON.parse(btn.dataset.condition);
                this.showEditForm(condition);
            }
            
            // Handle delete button
            if (e.target.closest('.delete-condition')) {
                const btn = e.target.closest('.delete-condition');
                this.deleteCondition(btn.dataset.conditionId);
            }
            
            // Handle retry button
            if (e.target.closest('.retry-loading')) {
                this.loadConditions();
            }
        });

        // Form submission
        const form = document.getElementById('user-condition-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Cancel button
        const cancelBtn = document.getElementById('cancel-edit-condition-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.showList());
        }

        // Add new condition button
        const addBtn = document.getElementById('show-add-condition-form-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showAddForm());
        }
    }

    async loadConditions() {
        if (!this.container) {
            console.warn('Container not found, cannot load conditions');
            return;
        }

        console.log('🔍 Loading user conditions...');
        const timestamp = new Date().toLocaleTimeString();
        this.showLoading(timestamp);

        // Add ESC key handler
        const handleEscKey = (e) => {
            if (e.key === 'Escape' || e.key === 'Esc') {
                this.showError('Loading cancelled by user', true);
                document.removeEventListener('keydown', handleEscKey);
            }
        };
        document.addEventListener('keydown', handleEscKey);

        try {
            console.log('🔍 Fetching user conditions from /api/user-conditions');
            const response = await fetch('/api/user-conditions');
            document.removeEventListener('keydown', handleEscKey);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Server error response:', errorText);
                throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
            }

            const data = await response.json();
            console.log('📦 Received data:', data);
            
            // Handle both array and object with user_conditions property
            let conditions = [];
            if (Array.isArray(data)) {
                conditions = data;
            } else if (data && data.user_conditions) {
                conditions = data.user_conditions;
            } else if (data && data.status === 'success' && data.user_conditions) {
                conditions = data.user_conditions;
            } else if (data && data.status === 'success' && Array.isArray(data)) {
                conditions = data;
            }
            
            console.log(`✅ Loaded ${conditions.length} conditions`);
            this.renderConditions(conditions);
        } catch (error) {
            console.error('❌ Error loading conditions:', error);
            this.showError(`Failed to load conditions: ${error.message}`);
        }
    }

    showLoading(timestamp) {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2 small">
                    <div>Loading your conditions...</div>
                    <div class="text-muted small mt-1">${timestamp || new Date().toLocaleTimeString()} - Fetching data</div>
                    <div class="text-muted small">Press ESC to cancel</div>
                </div>
            </div>`;
    }

    showError(message, isUserCancelled = false) {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="alert ${isUserCancelled ? 'alert-warning' : 'alert-danger'}">
                <i class="fas fa-${isUserCancelled ? 'exclamation-triangle' : 'exclamation-circle'} me-2"></i>
                ${message}
                <div class="small mt-1">Last updated: ${new Date().toLocaleTimeString()}</div>
                <button class="btn btn-sm btn-outline-primary mt-2 retry-loading">
                    <i class="fas fa-sync-alt me-1"></i> Retry
                </button>
            </div>`;
    }

    renderConditions(conditions) {
        if (!this.container) return;
        
        if (!conditions.length) {
            this.container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No custom conditions found. Click "Add New Condition" to create one.
                </div>`;
            return;
        }

        let html = '<div class="list-group">';
        conditions.forEach(condition => {
            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center" data-condition-id="${condition.id}">
                    <div class="flex-grow-1" style="cursor: pointer;">
                        <h6 class="mb-1">${this.escapeHtml(condition.name || 'Unnamed Condition')}</h6>
                        ${condition.scan_clause ? `
                            <small class="text-muted d-block mt-1 text-truncate" style="max-width: 600px;">
                                ${this.escapeHtml(condition.scan_clause.substring(0, 100))}${condition.scan_clause.length > 100 ? '...' : ''}
                            </small>` : ''}
                    </div>
                    <div class="btn-group ms-3">
                        <button class="btn btn-sm btn-outline-primary edit-condition" 
                                data-condition='${JSON.stringify(condition).replace(/"/g, '&quot;')}' 
                                title="Edit condition">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger delete-condition" 
                                data-condition-id="${condition.id}" 
                                title="Delete condition">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>`;
        });
        html += '</div>';
        
        this.container.innerHTML = html;
    }

    showAddForm() {
        this.showForm({
            id: '',
            name: '',
            link: '',
            scan_clause: ''
        }, 'Add New Condition');
    }

    showEditForm(condition) {
        this.showForm(condition, 'Edit Condition');
    }

    showForm(condition, title) {
        const formView = document.getElementById('user-condition-form-view');
        const listView = document.getElementById('user-conditions-list-view');
        const formTitle = document.getElementById('user-condition-form-title');
        const form = document.getElementById('user-condition-form');
        
        if (!formView || !listView || !formTitle || !form) return;
        
        formTitle.textContent = title;
        document.getElementById('edit-condition-id').value = condition.id;
        document.getElementById('user-condition-name').value = condition.name || '';
        document.getElementById('user-condition-link').value = condition.link || '';
        document.getElementById('user-condition-clause').value = condition.scan_clause || '';
        
        listView.style.display = 'none';
        formView.style.display = 'block';
        
        // Scroll to form
        formView.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    showList() {
        const formView = document.getElementById('user-condition-form-view');
        const listView = document.getElementById('user-conditions-list-view');
        
        if (formView && listView) {
            formView.style.display = 'none';
            listView.style.display = 'block';
            listView.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        
        const id = document.getElementById('edit-condition-id').value;
        const name = document.getElementById('user-condition-name').value.trim();
        const link = document.getElementById('user-condition-link').value.trim();
        const scanClause = document.getElementById('user-condition-clause').value.trim();
        
        if (!name) {
            alert('Condition name is required');
            return;
        }
        
        if (!scanClause) {
            alert('Scan clause is required');
            return;
        }
        
        const condition = { id: id || Date.now().toString(), name, link, scan_clause: scanClause };
        
        try {
            const response = await fetch(`/api/user-conditions${id ? `/${id}` : ''}`, {
                method: id ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(condition)
            });
            
            if (!response.ok) {
                throw new Error('Failed to save condition');
            }
            
            this.showList();
            await this.loadConditions();
            
        } catch (error) {
            console.error('Error saving condition:', error);
            alert(`Error saving condition: ${error.message}`);
        }
    }

    async deleteCondition(id) {
        if (!id) {
            console.error('No condition ID provided for deletion');
            return;
        }
        
        try {
            // Show loading state
            const deleteButtons = document.querySelectorAll(`.delete-condition[data-condition-id="${id}"]`);
            deleteButtons.forEach(btn => {
                const originalHTML = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
                btn.setAttribute('data-original-html', originalHTML);
            });
            
            const response = await fetch(`/api/user-conditions/${id}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete condition');
            }
            
            // Show success message
            if (typeof showToast === 'function') {
                showToast('Condition deleted successfully', 'success');
            }
            
            // Reload conditions to update the UI
            await this.loadConditions();
            
        } catch (error) {
            console.error('Error deleting condition:', error);
            
            // Restore button states on error
            const deleteButtons = document.querySelectorAll(`.delete-condition[data-condition-id="${id}"]`);
            deleteButtons.forEach(btn => {
                btn.disabled = false;
                if (btn.hasAttribute('data-original-html')) {
                    btn.innerHTML = btn.getAttribute('data-original-html');
                    btn.removeAttribute('data-original-html');
                }
            });
            
            // Show error message
            if (typeof showToast === 'function') {
                showToast(`Error: ${error.message}`, 'error');
            } else {
                alert(`Error deleting condition: ${error.message}`);
            }
        }
    }

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.userConditions = new UserConditions();
});
