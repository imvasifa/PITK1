// Modal Management
let userConditionsModal = null;
let adminConditionsModal = null;

// Show the user conditions modal
// Show the admin conditions modal
function showAdminConditionsModal() {
    console.log('showAdminConditionsModal called');
    
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap is not loaded');
        return;
    }
    
    const modalElement = document.getElementById('conditionsModal');
    if (!modalElement) {
        console.error('Admin conditions modal element not found');
        return;
    }
    
    if (!adminConditionsModal) {
        try {
            adminConditionsModal = new bootstrap.Modal(modalElement);
            console.log('Bootstrap Admin Modal instance created');
        } catch (error) {
            console.error('Error creating Admin Bootstrap Modal:', error);
            return;
        }
    }
    
    // Load admin conditions
    if (typeof populateAdminConditions === 'function') {
        populateAdminConditions();
    }
    
    // Show the modal
    adminConditionsModal.show();
}

// Show the user conditions modal
function showUserConditionsModal() {
    console.log('showUserConditionsModal called');
    
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap is not loaded');
        return;
    }
    
    const modalElement = document.getElementById('userConditionsModal');
    if (!modalElement) {
        console.error('User conditions modal element not found');
        return;
    }
    
    if (!userConditionsModal) {
        try {
            userConditionsModal = new bootstrap.Modal(modalElement);
            console.log('Bootstrap User Modal instance created');
        } catch (error) {
            console.error('Error creating User Bootstrap Modal:', error);
            return;
        }
    }
    
    // Load user conditions
    if (typeof populateUserConditions === 'function') {
        populateUserConditions();
    }
    
    // Show the modal
    userConditionsModal.show();
}

// Show the add condition form
function showAddConditionForm() {
    document.getElementById('user-conditions-list-view').style.display = 'none';
    document.getElementById('user-condition-form-view').style.display = 'block';
    document.getElementById('user-condition-form-title').textContent = 'Add New Condition';
    document.getElementById('user-condition-form').reset();
    document.getElementById('edit-condition-id').value = '';
    document.getElementById('user-condition-name').focus();
}

// Cancel editing and return to list view
function cancelEditCondition() {
    document.getElementById('user-conditions-list-view').style.display = 'block';
    document.getElementById('user-condition-form-view').style.display = 'none';
}

// Edit an existing condition
function editUserCondition(condition) {
    document.getElementById('user-conditions-list-view').styleDisplay = 'none';
    document.getElementById('user-condition-form-view').style.display = 'block';
    document.getElementById('user-condition-form-title').textContent = 'Edit Condition';
    
    document.getElementById('edit-condition-id').value = condition.id || '';
    document.getElementById('user-condition-name').value = condition.name || '';
    document.getElementById('user-condition-link').value = condition.chart_link || '';
    document.getElementById('user-condition-clause').value = condition.scan_clause || '';
    
    document.getElementById('user-condition-name').focus();
}

// Populate user conditions
async function populateUserConditions() {
    const container = document.getElementById('user-conditions-list-container');
    if (!container) return;
    
    container.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    try {
        const response = await fetch('/api/user-conditions');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const conditions = Array.isArray(data) ? data : (data.user_conditions || []);
        
        container.innerHTML = '';
        
        if (conditions.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No custom conditions found. Click "Add New Condition" to create one.
                </div>`;
            return;
        }
        
        conditions.forEach(condition => {
            const div = document.createElement('div');
            div.className = 'list-group-item d-flex justify-content-between align-items-center';
            div.innerHTML = `
                <div class="flex-grow-1">
                    <h6 class="mb-1">${escapeHtml(condition.name)}</h6>
                    <small class="text-muted">${escapeHtml(condition.scan_clause.substring(0, 100))}${condition.scan_clause.length > 100 ? '...' : ''}</small>
                </div>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editUserCondition(${JSON.stringify(condition).replace(/"/g, '&quot;')})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteUserCondition('${condition.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading user conditions:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load conditions. 
                <button class="btn btn-sm btn-outline-secondary ms-2" onclick="populateUserConditions()">
                    <i class="fas fa-sync-alt me-1"></i>Retry
                </button>
            </div>`;
    }
}

// Delete a condition
async function deleteUserCondition(conditionId) {
    if (!confirm('Are you sure you want to delete this condition? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/user-conditions/${conditionId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        await populateUserConditions();
        showToast('Condition deleted successfully', 'success');
    } catch (error) {
        console.error('Error deleting condition:', error);
        showToast('Failed to delete condition', 'error');
    }
}

// Handle form submission
async function handleUserConditionSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const conditionId = document.getElementById('edit-condition-id').value;
    const isEdit = !!conditionId;
    
    const conditionData = {
        name: document.getElementById('user-condition-name').value.trim(),
        chart_link: document.getElementById('user-condition-link').value.trim(),
        scan_clause: document.getElementById('user-condition-clause').value.trim()
    };
    
    if (!conditionData.name || !conditionData.scan_clause) {
        showToast('Please fill in all required fields', 'error');
        return;
    }
    
    try {
        const url = isEdit 
            ? `/api/user-conditions/${conditionId}`
            : '/api/user-conditions';
        
        const response = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
            },
            body: JSON.stringify(conditionData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        form.reset();
        document.getElementById('user-conditions-list-view').style.display = 'block';
        document.getElementById('user-condition-form-view').style.display = 'none';
        
        await populateUserConditions();
        
        showToast(
            isEdit ? 'Condition updated successfully' : 'Condition added successfully',
            'success'
        );
        
    } catch (error) {
        console.error('Error saving condition:', error);
        showToast('Failed to save condition', 'error');
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
    toast.role = 'alert';
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 150);
    }, 5000);
}

// Helper function to escape HTML
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Initialize event listeners when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, initializing user conditions...');
    
    // Add click handler for the custom conditions button
    const customConditionsBtn = document.getElementById('customConditionsButton');
    if (customConditionsBtn) {
        console.log('Found custom conditions button, adding click handler');
        customConditionsBtn.addEventListener('click', function(e) {
            console.log('Custom conditions button clicked');
            e.stopPropagation();
            showUserConditionsModal();
        });
    } else {
        console.warn('Custom conditions button not found');
    }
    // Add event listeners for user conditions form
    const showAddFormBtn = document.getElementById('show-add-condition-form-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-condition-btn');
    const userConditionForm = document.getElementById('user-condition-form');

    if (showAddFormBtn) {
        showAddFormBtn.addEventListener('click', showAddConditionForm);
    }

    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', cancelEditCondition);
    }

    if (userConditionForm) {
        userConditionForm.addEventListener('submit', handleUserConditionSubmit);
    }

    // Populate conditions when modal is shown
    const userConditionsModal = document.getElementById('userConditionsModal');
    if (userConditionsModal) {
        userConditionsModal.addEventListener('show.bs.modal', populateUserConditions);
    }
});
