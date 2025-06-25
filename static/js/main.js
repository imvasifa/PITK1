// Import modules
import { UserConditions } from './modules/user-conditions.js';
import { AdminConditions } from './modules/admin-conditions.js';

// Global variables
let isInitialized = false;

/**
 * Initialize the application
 */
function initializeApp() {
    if (isInitialized) return;
    isInitialized = true;
    
    console.log('Initializing application...');
    
    try {
        // Initialize modules if they exist
        if (typeof UserConditions !== 'undefined') {
            window.userConditions = new UserConditions();
            console.log('UserConditions module initialized');
        }
        
        if (typeof AdminConditions !== 'undefined') {
            window.adminConditions = new AdminConditions();
            console.log('AdminConditions module initialized');
        }
        
        // Initialize dashboard
        updateDashboard();
        
        // Initialize conditions modal
        initializeConditionsModal();
        
        // Initialize settings form if it exists
        initializeSettingsForm();
        
        // Initialize any other components
        initializeComponents();
        
    } catch (error) {
        console.error('Error initializing application:', error);
        showAlert('Error initializing application. Please refresh the page.', 'danger');
    }
}

/**
 * Initialize conditions modal and its event listeners
 */
function initializeConditionsModal() {
    const conditionsModal = document.getElementById('conditionsModal');
    if (!conditionsModal) {
        console.warn('Conditions modal not found');
        return;
    }
    
    // Handle modal show event
    conditionsModal.addEventListener('show.bs.modal', function() {
        console.log('Conditions modal shown');
        // Load admin conditions by default
        if (window.adminConditions) {
            window.adminConditions.loadConditions();
        }
    });
    
    // Handle tab changes
    const tabButtons = conditionsModal.querySelectorAll('button[data-bs-toggle="tab"]');
    tabButtons.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            if (event.target.id === 'user-conditions-tab' && window.userConditions) {
                console.log('Switched to user conditions tab');
                window.userConditions.loadConditions();
            } else if (event.target.id === 'admin-conditions-tab' && window.adminConditions) {
                console.log('Switched to admin conditions tab');
                window.adminConditions.loadConditions();
            }
        });
    });
}

/**
 * Initialize settings form if it exists
 */
function initializeSettingsForm() {
    const updateSettingsForm = document.getElementById('update-settings-form');
    if (updateSettingsForm) {
        updateSettingsForm.addEventListener('submit', handleSettingsSubmit);
    }
}

/**
 * Handle settings form submission
 */
async function handleSettingsSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const settings = Object.fromEntries(formData.entries());
    
    try {
        const response = await fetch('/update-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });
        
        const result = await response.json();
        if (result.success) {
            showAlert('Settings updated successfully', 'success');
            // Update UI if needed
            if (settings.refresh_interval) {
                const refreshDisplay = document.getElementById('refresh-interval-display');
                if (refreshDisplay) {
                    refreshDisplay.textContent = `${settings.refresh_interval} seconds`;
                }
            }
        } else {
            showAlert(result.message || 'Failed to update settings', 'danger');
        }
    } catch (error) {
        console.error('Error updating settings:', error);
        showAlert('Error updating settings. Please try again.', 'danger');
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container.mt-4') || document.body;
    container.prepend(alertDiv);
    
    // Auto-remove alert after 5 seconds
    setTimeout(() => {
        const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
        if (alert) alert.close();
    }, 5000);
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);

// Make initializeApp available globally for manual initialization if needed
window.initializeApp = initializeApp;

// Test function to check user conditions endpoint (kept for backward compatibility)
async function testUserConditionsEndpoint() {
    try {
        console.log('Testing user conditions endpoint...');
        const response = await fetch('/api/user-conditions');
        const data = await response.json();
        console.log('User conditions response:', data);
        return data;
    } catch (error) {
        console.error('Error testing user conditions endpoint:', error);
        return null;
    }
}

// Ensure form exists before adding event listener
const updateSettingsForm = document.getElementById('update-settings-form');
if (updateSettingsForm) {
    updateSettingsForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const selected = Array.from(document.querySelectorAll('#admin-conditions-list input:checked')).map(el => el.value);
        
        try {
            const response = await fetch('/update-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ conditions: selected })
            });
            const data = await response.json();
            if (data.success) {
                const modalInstance = bootstrap.Modal.getInstance(conditionsModal);
                if (modalInstance) {
                    modalInstance.hide();
                }
                window.location.reload(); // Reload to apply changes
            } else {
                alert('Failed to save settings.');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            alert('An error occurred while saving settings.');
        }
    });
}

// Core dashboard functionality
function showLoading() {
    console.log("Showing loading overlay...");
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        // Add click handler to close on click anywhere
        overlay.onclick = function(e) {
            if (e.target === overlay) {
                hideLoading();
            }
        };
        // Add ESC key handler
        document.addEventListener('keydown', handleEscKey);
    }
}

function hideLoading() {
    console.log("Hiding loading overlay...");
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
        // Remove event listeners
        overlay.onclick = null;
        document.removeEventListener('keydown', handleEscKey);
    }
}

function handleEscKey(e) {
    if (e.key === 'Escape' || e.key === 'Esc') {
        hideLoading();
    }
}

// Add a global error handler to hide loading on errors
window.addEventListener('error', function() {
    hideLoading();
});

// Also hide loading when page is fully loaded
window.addEventListener('load', function() {
    // Add a small delay to ensure everything is ready
    setTimeout(hideLoading, 1000);
});

// Add global ESC key handler to dismiss loader
document.addEventListener('keydown', function(e) {
    if ((e.key === 'Escape' || e.key === 'Esc') && document.getElementById('loadingOverlay')?.style.display === 'flex') {
        console.log('ESC key pressed - hiding loader');
        hideLoading();
    }
});

async function updateDashboard() {
    console.log("updateDashboard called. Showing loader.");
    showLoading();
    
    // Ensure loading is hidden when function completes or fails
    const hideLoadingOnFinish = () => {
        setTimeout(hideLoading, 500); // Small delay to prevent flicker
    };
    
    try {
        const response = await fetch('/get-scan-results');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        const container = document.getElementById('scan-results-container');
        if (!container) {
            console.error('Scan results container not found!');
            hideLoadingOnFinish();
            return;
        }
        
        container.innerHTML = ''; // Clear previous results

        if (Object.keys(data).length === 0) {
            container.innerHTML = '<div class="col-12"><div class="alert alert-info">No scan results found for the selected conditions.</div></div>';
            hideLoadingOnFinish();
            return;
        }

        for (const [condition, stocks] of Object.entries(data)) {
            const card = createCard(condition, stocks);
            container.appendChild(card);
        }
        
        hideLoadingOnFinish();
    } catch (error) {
        console.error('Error updating dashboard:', error);
        hideLoadingOnFinish();
        const container = document.getElementById('scan-results-container');
        if (container) {
            container.innerHTML = '<div class="col-12"><div class="alert alert-danger">Failed to load scan results. Please try refreshing the page.</div></div>';
        }
    } finally {
        console.log("updateDashboard finished. Hiding loader.");
        hideLoading();
    }
}

function createCard(condition, stocks) {
    const card = document.createElement('div');
    card.className = 'col-12 mb-4';

    let stockRows = '';
    if (stocks.length > 0) {
        stockRows = stocks.map(stock => `
            <tr>
                <td>${stock.symbol}</td>
                <td>${stock.close}</td>
                <td><a href="${stock.chartink_link}" target="_blank">View</a></td>
                <td class="${stock.per_chg >= 0 ? 'text-success' : 'text-danger'}">${stock.per_chg}%</td>
                <td>${stock.volume}</td>
                <td>${stock.score}</td>
            </tr>
        `).join('');
    } else {
        stockRows = '<tr><td colspan="6" class="text-center">No stocks found for this condition.</td></tr>';
    }

    card.innerHTML = `
        <div class="card scan-card">
            <div class="card-header">
                ${condition}
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Stock</th>
                                <th>Close</th>
                                <th>Chartink</th>
                                <th>Change %</th>
                                <th>Volume</th>
                                <th>Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stockRows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    return card;
}

// Initial load
console.log("main.js loaded. Setting up DOMContentLoaded listener.");
document.addEventListener('DOMContentLoaded', updateDashboard);

// User Conditions Modal logic (restored)
const userConditionsModal = new bootstrap.Modal(document.getElementById('userConditionsModal'));
window.showCustomConditionsModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('conditionsModal'));
    modal.show();
    // Switch to the 'Your Conditions' tab
    setTimeout(() => {
        const tab = document.getElementById('user-conditions-tab');
        if (tab) tab.click();
    }, 200);
};

// Show Admin Conditions Modal (kept for backward compatibility)
function showConditionsModal() {
    const modal = document.getElementById('conditionsModal');
    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    } else {
        console.warn('Conditions modal not found');
    }
};

// Function to initialize user conditions functionality
function initializeUserConditions() {
    console.log('Initializing user conditions functionality...');
    
    // Handle tab changes for user conditions in the main modal
    const userTab = document.getElementById('user-conditions-tab');
    if (userTab) {
        console.log('Found user conditions tab, adding event listeners...');
        
        // Remove any existing event listeners to prevent duplicates
        const newUserTab = userTab.cloneNode(true);
        userTab.parentNode.replaceChild(newUserTab, userTab);
        
        // Initialize the "Add New Condition" button
        document.addEventListener('click', function(e) {
            if (e.target.closest('#show-add-condition-form-btn')) {
                e.preventDefault();
                showUserConditionForm();
            }
            
            // Handle edit button
            const editBtn = e.target.closest('.edit-condition');
            if (editBtn) {
                e.preventDefault();
                e.stopPropagation();
                const condition = JSON.parse(editBtn.dataset.condition);
                editUserCondition(condition);
            }
            
            // Handle delete button
            const deleteBtn = e.target.closest('.delete-condition');
            if (deleteBtn) {
                e.preventDefault();
                e.stopPropagation();
                deleteUserCondition(deleteBtn.dataset.conditionId);
            }
            
            // Handle condition row click
            const conditionRow = e.target.closest('.list-group-item[data-condition-id]');
            if (conditionRow && !e.target.closest('.btn')) {
                const conditionId = conditionRow.dataset.conditionId;
                const container = document.querySelector('#user-conditions-list-container');
                const condition = container.dataset.conditions ? 
                    JSON.parse(container.dataset.conditions).find(c => c.id === conditionId) : null;
                
                if (condition?.scan_clause) {
                    const scanButton = document.querySelector('.btn-scan');
                    if (scanButton) {
                        const scanInput = document.getElementById('scanInput');
                        if (scanInput) {
                            scanInput.value = condition.scan_clause;
                            scanButton.click();
                        }
                    }
                }
            }
        });
        
        // Initialize the cancel button in the form
        const cancelButton = document.getElementById('cancel-edit-condition-btn');
        if (cancelButton) {
            cancelButton.addEventListener('click', function(e) {
                e.preventDefault();
                showUserConditionsList();
            });
        }
        
        // Handle form submission
        const userConditionForm = document.getElementById('user-condition-form');
        if (userConditionForm) {
            userConditionForm.addEventListener('submit', handleUserConditionSubmit);
        }
    } else {
        console.warn('User conditions tab not found in the DOM');
    }
    
    // Test the user conditions endpoint
    testUserConditionsEndpoint().catch(console.error);
}

// Function to show add condition form
function showAddConditionForm() {
    const listView = document.getElementById('user-conditions-list-view');
    const formView = document.getElementById('user-condition-form-view');
    const formTitle = document.getElementById('user-condition-form-title');
    const form = document.getElementById('user-condition-form');
    
    if (listView && formView && formTitle && form) {
        listView.style.display = 'none';
        formView.style.display = 'block';
        formTitle.textContent = 'Add New Condition';
        document.getElementById('edit-condition-id').value = '';
        form.reset();
    } else {
        console.warn('Required elements for add condition form not found');
    }
}

// Function to cancel edit and return to list view
function cancelEditCondition() {
    const listView = document.getElementById('user-conditions-list-view');
    const formView = document.getElementById('user-condition-form-view');
    
    if (listView && formView) {
        listView.style.display = 'block';
        formView.style.display = 'none';
    }
}

// Handle user condition form submission
async function handleUserConditionSubmit(e) {
    e.preventDefault();
    
    const nameInput = document.getElementById('user-condition-name');
    const linkInput = document.getElementById('user-condition-link');
    const clauseInput = document.getElementById('user-condition-clause');
    const editIdInput = document.getElementById('edit-condition-id');
    
    if (!nameInput || !clauseInput || !editIdInput) {
        console.error('Required form elements not found');
        return;
    }
    
    const formData = {
        name: nameInput.value.trim(),
        link: (linkInput?.value || '#').trim(),
        scan_clause: clauseInput.value.trim()
    };
    
    // Validate required fields
    if (!formData.name || !formData.scan_clause) {
        showAlert('Name and scan clause are required', 'warning');
        return;
    }
    
    const isEdit = editIdInput.value !== '';
    const url = isEdit ? `/api/user-conditions/${editIdInput.value}` : '/api/user-conditions';
    
    try {
        showLoading();
        const response = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            cancelEditCondition();
            if (window.userConditions) {
                await window.userConditions.loadConditions();
            }
            showAlert(`Condition ${isEdit ? 'updated' : 'added'} successfully`, 'success');
        } else {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || 'Failed to save condition');
        }
    } catch (error) {
        console.error('Error saving condition:', error);
        showAlert(`Error: ${error.message || 'Failed to save condition'}`, 'danger');
    } finally {
        hideLoading();
    }
}

// Initialize event listeners for user conditions
function initializeUserConditionEventListeners() {
    const addButton = document.getElementById('show-add-condition-form-btn');
    const cancelButton = document.getElementById('cancel-edit-condition-btn');
    const form = document.getElementById('user-condition-form');
    
    if (addButton) {
        addButton.addEventListener('click', showAddConditionForm);
    }
    
    if (cancelButton) {
        cancelButton.addEventListener('click', cancelEditCondition);
    }
    
    if (form) {
        form.addEventListener('submit', handleUserConditionSubmit);
    }
}

// Initialize user conditions when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeUserConditionEventListeners); 